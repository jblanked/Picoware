//
//  PicoCalc SD Card driver for FAT32 formatted SD cards
//
//  This driver provides block-level access to SD cards and implements
//  basic FAT32 file system operations for reading and writing files.
//
//  Only Master Boot Record (MBR) disk layout is supported (not GPT).
//  FAT32 without the MBR partition table is supported.
//  Standard SD cards (SDSC) and SD High Capacity (SDHC) cards are supported.
//

#include <string.h>
#include <stdio.h>
#include <ctype.h>
#include <strings.h> // For strcasecmp

#include "pico/stdlib.h"
#include "hardware/spi.h"
#include "pico/sem.h"

#include "sdcard.h"
#include "fat32.h"

#define RETURN_ON_ERROR(expr)        \
    {                                \
        fat32_error_t _res = (expr); \
        if (_res != FAT32_OK)        \
        {                            \
            return _res;             \
        }                            \
    }

#define CLOSE_AND_RETURN_ON_ERROR(expr) \
    {                                   \
        fat32_error_t _res = (expr);    \
        if (_res != FAT32_OK)           \
        {                               \
            fat32_close(&dir);          \
            return _res;                \
        }                               \
    }

// Global state
static bool fat32_mounted = false;
static fat32_error_t mount_status = FAT32_OK; // Error code for mount operation
bool fat32_initialised = false;               // Set to true after successful file system initialization

// FAT32 file system state
static fat32_boot_sector_t boot_sector;
static fat32_fsinfo_t fsinfo;

static uint32_t volume_start_block = 0; // First block of the volume
static uint32_t first_data_sector;      // First sector of the data region
static uint32_t data_region_sectors;    // Total sectors in the data region
static uint32_t cluster_count;          // Total number of clusters in the data region
static uint32_t bytes_per_cluster;

static uint32_t current_dir_cluster = 0; // Current directory cluster

// Working buffers
static uint8_t sector_buffer[FAT32_SECTOR_SIZE] __attribute__((aligned(4)));
static fat32_lfn_entry_t lfn_buffer[MAX_LFN_PART]; // Buffer for long file name entries

// Timer for SD card detection
static repeating_timer_t sd_card_detect_timer;

//
//  Sector-level access functions
//

static inline uint32_t cluster_to_sector(uint32_t cluster)
{
    return ((cluster - 2) * boot_sector.sectors_per_cluster) + first_data_sector;
}

static inline fat32_error_t read_sector(uint32_t sector, uint8_t *buffer)
{
    return sd_read_block(volume_start_block + sector, buffer);
}

static inline fat32_error_t write_sector(uint32_t sector, const uint8_t *buffer)
{
    return sd_write_block(volume_start_block + sector, buffer);
}

//
// FAT32 file system functions
//

static bool is_sector_mbr(const uint8_t *sector)
{
    // Check for 0x55AA signature
    if (sector[510] != 0x55 || sector[511] != 0xAA)
    {
        return false;
    }

    // Check for valid partition type in partition table
    for (int i = 0; i < 4; i++)
    {
        uint8_t part_type = sector[446 + i * 16 + 4];
        if (part_type != 0x00)
        {
            return true; // At least one valid partition
        }
    }
    return false;
}

static bool is_sector_boot_sector(const uint8_t *sector)
{
    // Check for 0x55AA signature
    if (sector[510] != 0x55 || sector[511] != 0xAA)
    {
        return false;
    }

    // Check for valid jump instruction
    if (sector[0] != 0xEB && sector[0] != 0xE9)
    {
        return false;
    }

    // Check for reasonable bytes per sector (should be 512, 1024, 2048, or 4096)
    uint16_t bps = sector[11] | (sector[12] << 8);
    if (bps != 512 && bps != 1024 && bps != 2048 && bps != 4096)
    {
        return false;
    }

    return true;
}

static fat32_error_t is_valid_fat32_boot_sector(const fat32_boot_sector_t *bs)
{
    // Check bytes per sector - this is critical
    if (bs->bytes_per_sector != FAT32_SECTOR_SIZE)
    {
        return FAT32_ERROR_INVALID_FORMAT;
    }

    // Check sectors per cluster (must be power of 2)
    uint8_t spc = bs->sectors_per_cluster;
    if (spc == 0 || spc > 128 || (spc & (spc - 1)) != 0)
    {
        return FAT32_ERROR_INVALID_FORMAT;
    }

    // Check number of FATs
    if (bs->num_fats == 0 || bs->num_fats > 2)
    {
        return FAT32_ERROR_INVALID_FORMAT;
    }

    // Check if we have valid reserved sectors
    if (bs->reserved_sectors == 0)
    {
        return FAT32_ERROR_INVALID_FORMAT;
    }

    // Check if fat size is valid
    if (bs->fat_size_16 != 0 || bs->fat_size_32 == 0)
    {
        return FAT32_ERROR_INVALID_FORMAT;
    }

    if (bs->total_sectors_32 == 0)
    {
        return FAT32_ERROR_INVALID_FORMAT;
    }

    return FAT32_OK;
}

static fat32_error_t update_fsinfo()
{
    // Write the updated FSInfo sector back to disk
    return write_sector(boot_sector.fat32_info, (const uint8_t *)&fsinfo);
}

static fat32_error_t read_cluster_fat_entry(uint32_t cluster, uint32_t *value)
{
    // The first data cluster is 2, less than 2 is invalid
    if (cluster < 2)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    uint32_t fat_offset = cluster * 4; // 4 bytes per entry in FAT32
    uint32_t fat_sector = boot_sector.reserved_sectors + (fat_offset / FAT32_SECTOR_SIZE);
    uint32_t entry_offset = fat_offset % FAT32_SECTOR_SIZE;

    // Read the FAT sector
    RETURN_ON_ERROR(read_sector(fat_sector, sector_buffer));

    uint32_t entry = *(uint32_t *)(sector_buffer + entry_offset);
    *value = entry & 0x0FFFFFFF; // Mask out upper 4 bits for FAT32
    return FAT32_OK;
}

static fat32_error_t write_cluster_fat_entry(uint32_t cluster, uint32_t value)
{
    // The first data cluster is 2, less than 2 is invalid
    if (cluster < 2)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    uint32_t fat_offset = cluster * 4; // 4 bytes per entry in FAT32
    uint32_t fat_sector = boot_sector.reserved_sectors + (fat_offset / FAT32_SECTOR_SIZE);
    uint32_t entry_offset = fat_offset % FAT32_SECTOR_SIZE;

    // Read the FAT sector
    RETURN_ON_ERROR(read_sector(fat_sector, sector_buffer));

    // Write the FAT entry
    *(uint32_t *)(sector_buffer + entry_offset) &= 0xF0000000;
    *(uint32_t *)(sector_buffer + entry_offset) |= value & 0x0FFFFFFF;

    // Write the modified sector back
    RETURN_ON_ERROR(write_sector(fat_sector, sector_buffer));

    return FAT32_OK;
}

static fat32_error_t get_next_free_cluster(uint32_t *cluster)
{
    // Start searching from next free or first data cluster
    uint32_t start_cluster = fsinfo.next_free != 0xFFFFFFFF ? fsinfo.next_free : 2;

    // Iterate through the FAT to find a free cluster
    for (uint32_t i = start_cluster; i < cluster_count + 2; i++)
    {
        uint32_t value;
        RETURN_ON_ERROR(read_cluster_fat_entry(i, &value));

        if (value == FAT32_FAT_ENTRY_FREE)
        {
            *cluster = i;
            return FAT32_OK; // Found a free cluster
        }
    }
    return FAT32_ERROR_DISK_FULL; // No free clusters found
}

static fat32_error_t release_cluster_chain(uint32_t start_cluster)
{
    uint32_t total_clusters = 0;
    uint32_t lowest_cluster = 0xFFFFFFFF;

    if (start_cluster < 2)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    uint32_t cluster = start_cluster;
    while (cluster < FAT32_FAT_ENTRY_EOC)
    {
        uint32_t next_cluster;
        RETURN_ON_ERROR(read_cluster_fat_entry(cluster, &next_cluster));
        RETURN_ON_ERROR(write_cluster_fat_entry(cluster, FAT32_FAT_ENTRY_FREE));
        total_clusters++;
        if (cluster < lowest_cluster)
        {
            lowest_cluster = cluster; // Find the lowest cluster number in the chain
        }
        cluster = next_cluster;
    }

    // Update FSInfo with the new free count
    fsinfo.free_count += total_clusters;
    if (fsinfo.next_free > lowest_cluster)
    {
        fsinfo.next_free = lowest_cluster; // Update next free cluster if needed
    }
    // Write the updated FSInfo sector back to disk
    RETURN_ON_ERROR(write_sector(boot_sector.fat32_info, (const uint8_t *)&fsinfo));

    return FAT32_OK;
}

static fat32_error_t find_last_cluster(uint32_t start_cluster, uint32_t count, uint32_t *last_cluster)
{
    *last_cluster = start_cluster;
    for (uint32_t i = 1; i < count; i++)
    {
        uint32_t next_cluster;
        RETURN_ON_ERROR(read_cluster_fat_entry(*last_cluster, &next_cluster));
        *last_cluster = next_cluster;
    }
    return FAT32_OK;
}

static fat32_error_t allocate_and_link_cluster(uint32_t last_cluster, uint32_t *new_cluster)
{
    RETURN_ON_ERROR(get_next_free_cluster(new_cluster));
    RETURN_ON_ERROR(write_cluster_fat_entry(last_cluster, *new_cluster));
    RETURN_ON_ERROR(write_cluster_fat_entry(*new_cluster, FAT32_FAT_ENTRY_EOC));

    if (fsinfo.free_count != 0xFFFFFFFF)
    {
        fsinfo.free_count--; // Decrease free count
        update_fsinfo();     // Update FSInfo sector
    }

    return FAT32_OK;
}

static fat32_error_t clear_cluster(uint32_t cluster)
{
    uint32_t sector = cluster_to_sector(cluster);
    memset(sector_buffer, 0, FAT32_SECTOR_SIZE);
    for (uint32_t i = 0; i < boot_sector.sectors_per_cluster; i++)
    {
        RETURN_ON_ERROR(write_sector(sector + i, sector_buffer));
    }
    return FAT32_OK;
}

static fat32_error_t seek_to_cluster(uint32_t start_cluster, uint32_t offset, uint32_t *result_cluster)
{
    uint32_t cluster = start_cluster;
    for (uint32_t i = 0; i < offset; i++)
    {
        uint32_t next_cluster;
        RETURN_ON_ERROR(read_cluster_fat_entry(cluster, &next_cluster));
        if (next_cluster >= FAT32_FAT_ENTRY_EOC)
        {
            return FAT32_ERROR_INVALID_POSITION;
        }
        cluster = next_cluster;
    }
    *result_cluster = cluster;
    return FAT32_OK;
}

//
// Mount the SD Card functions
//

fat32_error_t fat32_mount(void)
{
    if (!sd_card_present())
    {
        fat32_unmount(); // Unmount if card is not present
        return FAT32_ERROR_NO_CARD;
    }

    if (fat32_mounted)
    {
        return FAT32_OK;
    }

    RETURN_ON_ERROR(sd_card_init());

    // Read boot sector
    RETURN_ON_ERROR(sd_read_block(0, sector_buffer));

    // Is this a Master Boot Record (MBR)?
    if (is_sector_mbr(sector_buffer))
    {
        volume_start_block = 0; // Set to zero to detect if no partitions are acceptable

        // Read partition table entries
        for (int i = 0; i < 4; i++)
        {
            // Read next partition table entry
            mbr_partition_entry_t *partition_entry = (mbr_partition_entry_t *)(sector_buffer + 446 + i * 16);

            // Check if this partition is active
            if (partition_entry->boot_indicator != 0x00 && partition_entry->boot_indicator != 0x80)
            {
                continue; // No partition here
            }
            if (partition_entry->partition_type == 0x0B || // FAT32 with CHS addressing
                partition_entry->partition_type == 0x0C)   // FAT32 with LBA addressing
            {
                // Align disk accesses with the partition we have decided to use
                volume_start_block = partition_entry->start_lba;

                // Read the boot sector from the partition
                RETURN_ON_ERROR(sd_read_block(volume_start_block, sector_buffer));
                break;
            }
        }
        if (volume_start_block == 0)
        {
            return FAT32_ERROR_INVALID_FORMAT; // No valid FAT32 partition found
        }
    }
    else if (is_sector_boot_sector(sector_buffer))
    {
        // No partition table, treat the entire disk as a single partition
        volume_start_block = 0;

        // We already have the boot sector in sector_buffer, no fat32_read_block needed
    }
    else
    {
        return FAT32_ERROR_INVALID_FORMAT; // This is not a valid FAT32 boot sector
    }

    // Copy boot sector data
    memcpy(&boot_sector, sector_buffer, sizeof(fat32_boot_sector_t));

    // Validate boot sector
    RETURN_ON_ERROR(is_valid_fat32_boot_sector(&boot_sector));

    // Calculate important sectors/clusters
    bytes_per_cluster = boot_sector.sectors_per_cluster * FAT32_SECTOR_SIZE;
    first_data_sector = boot_sector.reserved_sectors + (boot_sector.num_fats * boot_sector.fat_size_32);
    data_region_sectors = boot_sector.total_sectors_32 - (boot_sector.num_fats * boot_sector.fat_size_32);
    cluster_count = data_region_sectors / boot_sector.sectors_per_cluster;
    if (cluster_count < 65525)
    {
        return FAT32_ERROR_INVALID_FORMAT; // This is FAT12 or FAT16, not FAT32!
    }

    current_dir_cluster = boot_sector.root_cluster; // Start at root directory

    // Cache the FSInfo sector
    RETURN_ON_ERROR(read_sector(boot_sector.fat32_info, sector_buffer));
    memcpy(&fsinfo, sector_buffer, sizeof(fat32_fsinfo_t));

    if (fsinfo.lead_sig != 0x41615252 ||
        fsinfo.struc_sig != 0x61417272 ||
        fsinfo.trail_sig != 0xAA550000)
    {
        return FAT32_ERROR_INVALID_FORMAT; // FSInfo is not valid
    }

    fat32_mounted = true;
    return FAT32_OK;
}

void fat32_unmount(void)
{
    fat32_mounted = false;
    mount_status = FAT32_ERROR_NO_CARD;
    volume_start_block = 0;
    first_data_sector = 0;
    data_region_sectors = 0;
    cluster_count = 0;
    bytes_per_cluster = 0;
    current_dir_cluster = 0;
}

bool fat32_is_mounted(void)
{
    return fat32_mounted;
}

bool fat32_is_ready(void)
{
    if (sd_card_present())
    {
        if (!fat32_mounted)
        {
            mount_status = fat32_mount();
        }
    }
    else
    {
        if (fat32_mounted)
        {
            fat32_unmount(); // Unmount if card is not present
        }
        mount_status = FAT32_ERROR_NO_CARD; // Set status to no card present
    }
    return mount_status == FAT32_OK;
}

fat32_error_t fat32_get_status(void)
{
    fat32_is_ready();
    return mount_status;
}

fat32_error_t fat32_get_free_space(uint64_t *free_space)
{
    // We can only get free space for FAT32 using FSInfo
    // Computing free space will be too slow for us

    if (!fat32_is_ready())
    {
        return mount_status;
    }

    if (fsinfo.free_count != 0xFFFFFFFF &&
        fsinfo.free_count <= cluster_count)
    {
        *free_space = ((uint64_t)fsinfo.free_count) * bytes_per_cluster;
        return FAT32_OK; // Successfully retrieved free space
    }

    // If FSInfo is not valid, we will count free clusters manually
    uint64_t free_clusters = 0;
    for (uint32_t sector = 0; sector < boot_sector.fat_size_32; sector++)
    {
        RETURN_ON_ERROR(read_sector(boot_sector.reserved_sectors + sector, sector_buffer));
        for (int i = 0; i < FAT32_SECTOR_SIZE; i += 4)
        {
            uint32_t entry = *(uint32_t *)(sector_buffer + i) & 0x0FFFFFFF;
            if (entry == 0)
            {
                free_clusters++;
            }
        }
    }

    fsinfo.free_count = free_clusters; // Update FSInfo with counted free clusters
    RETURN_ON_ERROR(write_sector(boot_sector.fat32_info, (uint8_t *)&fsinfo));

    *free_space = free_clusters * bytes_per_cluster;
    return FAT32_OK;
}

fat32_error_t fat32_get_total_space(uint64_t *total_space)
{
    if (!fat32_is_ready())
    {
        return mount_status;
    }

    // Get the total number of sectors
    uint64_t total_sectors = boot_sector.total_sectors_32;

    // Calculate total space in bytes
    *total_space = total_sectors * FAT32_SECTOR_SIZE;

    return FAT32_OK;
}

uint32_t fat32_get_cluster_size(void)
{
    return boot_sector.sectors_per_cluster * FAT32_SECTOR_SIZE;
}

fat32_error_t fat32_get_volume_name(char *name, size_t name_len)
{
    if (!name || name_len < 12)
    {
        return FAT32_ERROR_INVALID_PARAMETER; // Name buffer too small
    }

    if (!fat32_is_ready())
    {
        return mount_status;
    }

    // Read the volume label from the root directory
    fat32_file_t dir = {0};
    dir.is_open = true;
    dir.start_cluster = boot_sector.root_cluster;
    dir.current_cluster = boot_sector.root_cluster;
    dir.position = 0;

    fat32_entry_t entry;
    while (fat32_dir_read(&dir, &entry) == FAT32_OK && entry.filename[0])
    {
        if (entry.attr & FAT32_ATTR_VOLUME_ID)
        {
            // Found a volume label entry
            strncpy(name, entry.filename, name_len - 1);
            name[name_len - 1] = '\0'; // Ensure null-termination
            return FAT32_OK;
        }
    }
    name[0] = '\0'; // No volume label found
    return FAT32_OK;
}

//
// File system naming utility functions
//

static inline char utf16_to_utf8(uint16_t utf16)
{
    // Convert UTF-16 to UTF-8 (simplified - only handles ASCII range)
    return utf16 < 0x80 ? (char)utf16 : '?';
}

static inline uint16_t utf8_to_utf16(char utf8)
{
    // Convert UTF-8 to UTF-16 (simplified - only handles ASCII range)
    return (uint16_t)(unsigned char)utf8;
}

static inline uint16_t utf8_to_lfn_ch(char utf8, uint8_t index, uint8_t len)
{
    // Convert UTF-8 to long file name entry (simplified - only handles ASCII range)
    if (index == len)
    {
        return 0; // End of name
    }
    if (index > len)
    {
        return 0xFFFF; // Invalid index
    }
    return utf8_to_utf16(utf8);
}

static void filename_to_shortname(const char *filename, char *shortname)
{
    memset(shortname, ' ', 11);
    shortname[11] = '\0';

    const char *dot = strrchr(filename, '.');
    int name_len = dot ? (dot - filename) : strlen(filename);

    // Copy name part (max 8 characters)
    for (int i = 0; i < name_len && i < 8; i++)
    {
        shortname[i] = toupper(filename[i]);
    }

    // Copy extension part (max 3 characters)
    if (dot && strlen(dot + 1) > 0)
    {
        for (int i = 0; i < 3 && dot[1 + i]; i++)
        {
            shortname[8 + i] = toupper(dot[1 + i]);
        }
    }
}

static void shortname_to_filename(const char *shortname, char *filename)
{
    int pos = 0;

    // Copy name part
    for (int i = 0; i < 8 && shortname[i] != ' '; i++)
    {
        filename[pos++] = tolower(shortname[i]);
    }

    // Copy extension part
    bool has_ext = false;
    for (int i = 8; i < 11; i++)
    {
        if (shortname[i] != ' ')
        {
            if (!has_ext)
            {
                filename[pos++] = '.';
                has_ext = true;
            }
            filename[pos++] = tolower(shortname[i]);
        }
    }

    filename[pos] = '\0';
}

static bool valid_shortname(const char *filename)
{
    // Forbidden ASCII codes for FAT 8.3 names
    static const char forbidden[] = "\"*+,./:;<=>?[\\]|";

    if (!filename)
    {
        return false;
    }

    int len = strlen(filename);
    if (len < 1 || len > 12)
    {
        return false; // "FILENAME.EXT" (8+1+3)
    }

    // Only one dot allowed, not at start
    const char *dot = strchr(filename, '.');
    if (dot)
    {
        if (dot != strrchr(filename, '.'))
        {
            return false; // More than one dot
        }
        if (dot == filename)
        {
            return false; // Dot at start
        }
    }

    int name_len = dot ? (dot - filename) : len;
    int ext_len = dot ? (len - name_len - 1) : 0;

    if (name_len < 1 || name_len > 8)
    {
        return false;
    }
    if (ext_len < 0 || ext_len > 3)
    {
        return false;
    }

    // Check name part
    for (int i = 0; i < name_len; i++)
    {
        unsigned char c = filename[i];
        if (c <= 0x20 || strchr(forbidden, c))
        {
            return false;
        }
    }

    // Check extension part
    if (dot)
    {
        for (int i = 0; i < ext_len; i++)
        {
            unsigned char c = dot[1 + i];
            if (c <= 0x20 || strchr(forbidden, c))
            {
                return false;
            }
        }
    }

    return true;
}

static uint8_t filename_to_lfn(const char *filename)
{
    // Convert filename to long file name entry
    memset(lfn_buffer, 0, sizeof(fat32_lfn_entry_t) * MAX_LFN_PART);

    // Split into UTF-16 parts (5 characters per part)
    int len = strlen(filename);
    const char *name = filename;
    fat32_lfn_entry_t *lfn_entry = &lfn_buffer[0];
    int part_count = (len + 12) / 13; // 13 UTF-16 chars per LFN entry

    for (int i = 0, j = 0; i < part_count; i++)
    {
        // Convert UTF-16 parts to UTF-8
        lfn_entry->name1[0] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name1[1] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name1[2] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name1[3] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name1[4] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name2[0] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name2[1] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name2[2] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name2[3] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name2[4] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name2[5] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name3[0] = utf8_to_lfn_ch(*(name++), j++, len);
        lfn_entry->name3[1] = utf8_to_lfn_ch(*(name++), j++, len);

        lfn_entry++;
    }
    return part_count; // Return number of LFN parts created
}

static bool shortname_exists(const char *shortname, fat32_file_t *dir)
{
    fat32_file_t scan = *dir;
    fat32_entry_t entry;
    scan.position = 0;
    while (fat32_dir_read(&scan, &entry) == FAT32_OK && entry.filename[0])
    {
        char entry83[12];
        filename_to_shortname(entry.filename, entry83);
        if (memcmp(entry83, shortname, 11) == 0)
        {
            return true;
        }
    }
    return false;
}

static fat32_error_t unique_shortname(fat32_file_t *dir, const char *longname, char *shortname)
{
    // Generates a unique FAT 8.3 short name for a given long filename in a directory
    // dir: open directory to check for collisions
    // longname: input long filename (UTF-8, ASCII only here)
    // shortname: output buffer, must be at least 12 bytes (11 chars + null terminator)

    // Step 1: Uppercase and Step 2: Convert to OEM (ASCII only here)
    char upper[FAT32_MAX_FILENAME_LEN + 1];
    size_t len = strlen(longname);
    for (size_t i = 0; i < len && i < FAT32_MAX_FILENAME_LEN; ++i)
    {
        upper[i] = toupper((unsigned char)longname[i]);
    }
    upper[len] = '\0';

    // Step 3: Strip leading/embedded spaces
    char temp[FAT32_MAX_FILENAME_LEN + 1];
    size_t j = 0;
    for (size_t i = 0; i < len; ++i)
    {
        if (upper[i] != ' ')
        {
            temp[j++] = upper[i];
        }
    }
    temp[j] = '\0';

    // Step 4: Strip leading periods
    char *p = temp;
    while (*p == '.')
        p++;

    // Step 5: Copy up to 8 chars before dot, replace invalids with '_'
    size_t name_len = 0;
    size_t ext_len = 0;
    int lossy = 0;
    char *dot = strrchr(p, '.');
    if (dot == p)
        dot = NULL; // ignore leading dot

    char base[9] = {0};
    for (size_t i = 0; p[i] && &p[i] != dot && name_len < 8; ++i)
    {
        char c = p[i];
        if ((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
            strchr("$%'-_@~`!(){}^#&", c))
        {
            base[name_len++] = c;
        }
        else
        {
            base[name_len++] = '_';
            lossy = 1;
        }
    }
    base[name_len] = '\0';

    // Extension
    char ext[4] = {0};
    if (dot && *(dot + 1))
    {
        for (size_t i = 1; i <= 3 && dot[i]; ++i)
        {
            char c = dot[i];
            if ((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
                strchr("$%'-_@~`!(){}^#&", c))
            {
                ext[ext_len++] = c;
            }
            else
            {
                ext[ext_len++] = '_';
                lossy = 1;
            }
        }
    }
    ext[ext_len] = '\0';

    // Compose initial candidate
    char candidate[12];
    memset(candidate, ' ', 11);
    memcpy(candidate, base, strlen(base));
    memcpy(candidate + 8, ext, strlen(ext));
    candidate[11] = '\0';

    // Check if numeric tail is needed
    bool need_tail = lossy || name_len > 8 || ext_len > 3 || shortname_exists(candidate, dir);

    if (!need_tail)
    {
        memcpy(shortname, candidate, 12);
        return FAT32_OK;
    }

    // Numeric tail generation: try ~1 to ~999999
    for (int n = 1; n < 1000000; n++)
    {
        char tail[8];
        snprintf(tail, sizeof(tail), "~%d", n);
        size_t tail_len = strlen(tail);

        size_t base_len = 8 - tail_len;
        if (base_len > strlen(base))
            base_len = strlen(base);

        memset(candidate, ' ', 11);
        memcpy(candidate, base, base_len);
        memcpy(candidate + base_len, tail, tail_len);
        memcpy(candidate + 8, ext, strlen(ext));
        candidate[11] = '\0';

        if (!shortname_exists(candidate, dir))
        {
            memcpy(shortname, candidate, 12);
            return FAT32_OK;
        }
    }

    // If we get here, we failed to generate a unique name
    return FAT32_ERROR_DISK_FULL;
}

static uint8_t shortname_checksum(const char *shortname)
{
    // Calculate checksum for 8.3 filename
    uint8_t sum = 0;
    for (uint8_t i = 11; i > 0; i--)
    {
        // NOTE: The operation is an unsigned char rotate right
        sum = ((sum & 1) ? 0x80 : 0) + (sum >> 1) + (uint8_t)*shortname++;
    }
    return sum;
}

static void lfn_to_str(fat32_lfn_entry_t *lfn_entry, char *buffer)
{
    // Convert UTF-16 parts to UTF-8
    *(buffer++) = utf16_to_utf8(lfn_entry->name1[0]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name1[1]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name1[2]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name1[3]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name1[4]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name2[0]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name2[1]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name2[2]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name2[3]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name2[4]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name2[5]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name3[0]);
    *(buffer++) = utf16_to_utf8(lfn_entry->name3[1]);
}

static fat32_error_t find_entry(fat32_entry_t *dir_entry, const char *path)
{
    if (!dir_entry || !path)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    memset(dir_entry, 0, sizeof(fat32_entry_t));

    // Determine starting cluster: root or current
    uint32_t cluster = current_dir_cluster;

    if (strcmp(path, "/") == 0)
    {
        // If path is empty, return current directory
        dir_entry->start_cluster = boot_sector.root_cluster;
        dir_entry->attr = FAT32_ATTR_DIRECTORY;
        return FAT32_OK;
    }

    // If the path is empty, or refers to the current or parent directory of the root directory
    if (path[0] == '\0' || ((strcmp(path, ".") == 0 || strcmp(path, "..") == 0) &&
                            current_dir_cluster == boot_sector.root_cluster))
    {
        // Special case: current directory or parent directory of the root directory
        dir_entry->start_cluster = current_dir_cluster;
        dir_entry->attr = FAT32_ATTR_DIRECTORY;
        return FAT32_OK;
    }

    if (path[0] == '/')
    {
        cluster = boot_sector.root_cluster;
    }

    // Copy path and tokenize
    char path_copy[FAT32_MAX_PATH_LEN];
    strncpy(path_copy, path + (path[0] == '/' ? 1 : 0), sizeof(path_copy) - 1);
    path_copy[sizeof(path_copy) - 1] = '\0';

    char *saveptr = NULL;
    char *token = strtok_r(path_copy, "/", &saveptr);
    char *next_token = NULL;

    while (token)
    {
        next_token = strtok_r(NULL, "/", &saveptr);

        // Open the current directory cluster
        fat32_file_t dir = {0};
        dir.is_open = true;
        dir.attributes = FAT32_ATTR_DIRECTORY;
        dir.start_cluster = cluster;
        dir.current_cluster = cluster;
        dir.position = 0;

        bool found = false;
        fat32_entry_t entry;
        while (fat32_dir_read(&dir, &entry) == FAT32_OK && entry.filename[0])
        {
            if (strcasecmp(entry.filename, token) == 0)
            {
                // If this is the last component, return the entry
                if (!next_token)
                {
                    memcpy(dir_entry, &entry, sizeof(fat32_entry_t));
                    fat32_close(&dir);
                    return FAT32_OK;
                }
                // If not last, must be a directory
                if (entry.attr & FAT32_ATTR_DIRECTORY)
                {
                    cluster = entry.start_cluster ? entry.start_cluster : boot_sector.root_cluster;
                    found = true;
                    break;
                }
            }
        }
        fat32_close(&dir);
        if (!found && next_token)
        {
            return FAT32_ERROR_DIR_NOT_FOUND; // Intermediate directory not found
        }
        token = next_token;
    }

    return FAT32_ERROR_FILE_NOT_FOUND; // Not found
}

static fat32_error_t unlink_entry(fat32_entry_t *entry)
{
    if (!entry || entry->start_cluster == 0)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    // Mark the entry as deleted
    uint32_t sector = entry->sector;
    uint32_t offset = entry->offset;

    RETURN_ON_ERROR(read_sector(sector, sector_buffer));

    // Scan backwards for LFN entries
    int lfn_count = 0;
    for (int i = 1; i <= MAX_LFN_PART; i++)
    {
        if (offset < i * 32)
        {
            break;
        }
        fat32_dir_entry_t *lfn_entry = (fat32_dir_entry_t *)(sector_buffer + offset - i * 32);
        if (lfn_entry->attr == FAT32_ATTR_LONG_NAME)
        {
            lfn_entry->shortname[0] = FAT32_DIR_ENTRY_FREE;
            lfn_count++;
        }
        else
        {
            break;
        }
    }

    // Mark 8.3 entry as deleted
    fat32_dir_entry_t *dir_entry = (fat32_dir_entry_t *)(sector_buffer + offset);
    dir_entry->shortname[0] = FAT32_DIR_ENTRY_FREE;

    RETURN_ON_ERROR(write_sector(sector, sector_buffer));

    return FAT32_OK;
}

static fat32_error_t link_entry(fat32_entry_t *entry, const char *path)
{
    if (!entry || !path)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    if (!fat32_is_ready())
    {
        return mount_status;
    }

    fat32_entry_t temp_entry;
    fat32_error_t result = find_entry(&temp_entry, path);
    if (result != FAT32_ERROR_FILE_NOT_FOUND)
    {
        if (result == FAT32_OK)
        {
            return FAT32_ERROR_FILE_EXISTS;
        }
        return result;
    }

    // Split path into parent and filename
    char path_copy[FAT32_MAX_PATH_LEN];
    strncpy(path_copy, path, sizeof(path_copy) - 1);
    path_copy[sizeof(path_copy) - 1] = '\0';
    char *filename = strrchr(path_copy, '/');
    char *parent_path = path_copy;
    if (filename)
    {
        *filename = '\0';
        filename++;
    }
    else
    {
        filename = path_copy;
        parent_path = "";
    }

    // Open parent directory
    fat32_file_t dir;
    RETURN_ON_ERROR(fat32_open(&dir, parent_path));

    // Prepare short and long file names
    // We always use long files names to preserve case and special characters
    char shortname[12];
    size_t needed_entries = filename_to_lfn(filename);

    if (valid_shortname(filename))
    {
        filename_to_shortname(filename, shortname);
    }
    else
    {
        CLOSE_AND_RETURN_ON_ERROR(unique_shortname(&dir, filename, shortname));
    }

    // Find enough free directory entries (LFN + 8.3)
    uint32_t free_entry_pos = 0;
    uint32_t free_entry_cluster = dir.current_cluster;
    size_t free_count = 0;
    bool found = false;
    dir.position = 0;
    uint32_t entry_pos = 0;
    uint32_t cluster = dir.current_cluster;
    while (!found)
    {
        uint32_t cluster_offset = entry_pos % bytes_per_cluster;
        uint32_t sector_in_cluster = cluster_offset / FAT32_SECTOR_SIZE;
        uint32_t sector = cluster_to_sector(cluster) + sector_in_cluster;

        CLOSE_AND_RETURN_ON_ERROR(read_sector(sector, sector_buffer));

        for (uint32_t i = 0; i < FAT32_SECTOR_SIZE; i += 32)
        {
            fat32_dir_entry_t *entry_ptr = (fat32_dir_entry_t *)(sector_buffer + i);
            if (entry_ptr->shortname[0] == FAT32_DIR_ENTRY_FREE || entry_ptr->shortname[0] == FAT32_DIR_ENTRY_END_MARKER)
            {
                if (free_count == 0)
                {
                    free_entry_pos = entry_pos + i;
                    free_entry_cluster = cluster;
                }
                free_count++;
                if (free_count > needed_entries)
                {
                    found = true;
                    break;
                }
            }
            else
            {
                free_count = 0;
            }
        }
        if (found)
        {
            break;
        }

        entry_pos += FAT32_SECTOR_SIZE;
        if ((entry_pos % bytes_per_cluster) == 0)
        {
            uint32_t next_cluster;
            result = read_cluster_fat_entry(cluster, &next_cluster);
            if (result != FAT32_OK || next_cluster >= FAT32_FAT_ENTRY_EOC)
            {
                // Allocate a new cluster for the directory
                uint32_t new_dir_cluster = 0;
                CLOSE_AND_RETURN_ON_ERROR(allocate_and_link_cluster(cluster, &new_dir_cluster));
                CLOSE_AND_RETURN_ON_ERROR(clear_cluster(new_dir_cluster));
                cluster = new_dir_cluster;
            }
            else
            {
                cluster = next_cluster;
            }
        }
    }

    // Update the directory entry with the new cluster
    uint8_t checksum = shortname_checksum(shortname);

    // Write LFN entries in reverse order (last entry first)
    for (int i = 0; i < needed_entries; i++)
    {
        uint8_t index = needed_entries - i - 1;

        // Calculate position for this LFN entry
        uint32_t entry_offset = free_entry_pos + (i * 32);
        uint32_t entry_cluster_offset = entry_offset % bytes_per_cluster;
        uint32_t entry_sector_in_cluster = entry_cluster_offset / FAT32_SECTOR_SIZE;
        uint32_t entry_byte_in_sector = entry_cluster_offset % FAT32_SECTOR_SIZE;
        uint32_t current_cluster = free_entry_cluster;

        // Check if we need to move to next cluster
        while (entry_sector_in_cluster >= boot_sector.sectors_per_cluster)
        {
            uint32_t next_cluster;
            result = read_cluster_fat_entry(current_cluster, &next_cluster);
            if (result != FAT32_OK || next_cluster >= FAT32_FAT_ENTRY_EOC)
            {
                fat32_close(&dir);
                return FAT32_ERROR_DISK_FULL;
            }
            current_cluster = next_cluster;
            entry_sector_in_cluster -= boot_sector.sectors_per_cluster;
        }

        uint32_t entry_sector = cluster_to_sector(current_cluster) + entry_sector_in_cluster;

        // Read the sector if needed
        CLOSE_AND_RETURN_ON_ERROR(read_sector(entry_sector, sector_buffer));

        // Set up the LFN entry with checksum and sequence number
        fat32_lfn_entry_t *lfn_entry = &lfn_buffer[index];
        lfn_entry->seq = (i == 0) ? (index + 1) | 0x40 : (index + 1); // Set last entry flag
        lfn_entry->attr = FAT32_ATTR_LONG_NAME;
        lfn_entry->type = 0;
        lfn_entry->checksum = checksum;
        lfn_entry->first_clus = 0;

        // Copy LFN entry to sector buffer
        memcpy(sector_buffer + entry_byte_in_sector, lfn_entry, sizeof(fat32_lfn_entry_t));

        // Write the sector back
        CLOSE_AND_RETURN_ON_ERROR(write_sector(entry_sector, sector_buffer));
    }

    // Allocate a new cluster for the file, if needed
    if (entry->start_cluster == 0)
    {
        CLOSE_AND_RETURN_ON_ERROR(get_next_free_cluster(&entry->start_cluster));
        CLOSE_AND_RETURN_ON_ERROR(write_cluster_fat_entry(entry->start_cluster, FAT32_FAT_ENTRY_EOC));

        if (fsinfo.free_count != 0xFFFFFFFF)
        {
            fsinfo.free_count--;
            update_fsinfo();
        }
    }

    // Write 8.3 entry
    fat32_dir_entry_t dir_entry = {0};
    memcpy(dir_entry.shortname, shortname, 11);
    dir_entry.attr = entry->attr; // Normal file
    dir_entry.nt_res = 0;
    dir_entry.crt_time_tenth = 0;
    dir_entry.crt_time = 0;
    dir_entry.crt_date = 0;
    dir_entry.lst_acc_date = 0;
    dir_entry.fst_clus_hi = entry->start_cluster >> 16;
    dir_entry.wrt_time = 0;
    dir_entry.wrt_date = 0;
    dir_entry.fst_clus_lo = entry->start_cluster & 0xFFFF;
    dir_entry.file_size = entry->size;

    uint32_t raw_offset = free_entry_pos + (needed_entries * 32);
    entry->sector = cluster_to_sector(free_entry_cluster) + ((raw_offset % bytes_per_cluster) / FAT32_SECTOR_SIZE);
    entry->offset = (raw_offset % FAT32_SECTOR_SIZE);
    CLOSE_AND_RETURN_ON_ERROR(read_sector(entry->sector, sector_buffer));
    memcpy(sector_buffer + entry->offset, &dir_entry, sizeof(dir_entry));
    CLOSE_AND_RETURN_ON_ERROR(write_sector(entry->sector, sector_buffer));

    fat32_close(&dir);

    return FAT32_OK; // Successfully linked the entry
}

static fat32_error_t new_entry(fat32_file_t *file, const char *path, uint8_t attr)
{
    if (!file || !path)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    memset(file, 0, sizeof(fat32_file_t));

    fat32_entry_t entry;
    memset(&entry, 0, sizeof(fat32_entry_t));
    entry.attr = attr;

    RETURN_ON_ERROR(link_entry(&entry, path));

    file->is_open = true;
    file->start_cluster = entry.start_cluster;
    file->current_cluster = file->start_cluster;
    file->attributes = entry.attr;
    file->dir_entry_sector = entry.sector;
    file->dir_entry_offset = entry.offset;

    return FAT32_OK; // Successfully created new file
}

static fat32_error_t delete_entry(const char *path)
{
    fat32_entry_t entry;
    RETURN_ON_ERROR(find_entry(&entry, path));

    if (entry.attr & FAT32_ATTR_DIRECTORY)
    {
        // Check if directory is empty (only "." and ".." allowed)
        fat32_file_t dir;
        RETURN_ON_ERROR(fat32_open(&dir, path));

        fat32_entry_t sub_entry;
        int entry_count = 0;
        while (fat32_dir_read(&dir, &sub_entry) == FAT32_OK && sub_entry.filename[0])
        {
            if (strcmp(sub_entry.filename, ".") != 0 && strcmp(sub_entry.filename, "..") != 0)
            {
                fat32_close(&dir);
                return FAT32_ERROR_DIR_NOT_EMPTY;
            }
            entry_count++;
        }
        fat32_close(&dir);
    }

    // Unlink the entry
    RETURN_ON_ERROR(unlink_entry(&entry));

    // Free the clusters used by the entry
    RETURN_ON_ERROR(release_cluster_chain(entry.start_cluster));

    return FAT32_OK;
}

//
// File operations (simplified implementation)
//

fat32_error_t fat32_open(fat32_file_t *file, const char *path)
{
    if (!file || !path)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    if (strlen(path) > FAT32_MAX_PATH_LEN)
    {
        return FAT32_ERROR_INVALID_PATH; // Path too long
    }

    if (!fat32_is_ready())
    {
        return mount_status;
    }

    memset(file, 0, sizeof(fat32_file_t));

    fat32_entry_t entry;
    RETURN_ON_ERROR(find_entry(&entry, path));

    if (entry.attr & FAT32_ATTR_VOLUME_ID)
    {
        return FAT32_ERROR_NOT_A_FILE; // Not a valid file
    }
    if (entry.attr & FAT32_ATTR_DIRECTORY)
    {
        file->start_cluster = entry.start_cluster ? entry.start_cluster : boot_sector.root_cluster;
        file->file_size = 0; // Directories have no size in FAT32
    }
    else
    {
        // Found the file
        file->start_cluster = entry.start_cluster;
        file->file_size = entry.size;
    }
    file->is_open = true;
    file->current_cluster = file->start_cluster;
    file->position = 0;
    file->attributes = entry.attr;
    file->dir_entry_sector = entry.sector;
    file->dir_entry_offset = entry.offset;

    return FAT32_OK;
}

fat32_error_t fat32_create(fat32_file_t *file, const char *path)
{
    return new_entry(file, path, FAT32_ATTR_ARCHIVE);
}

fat32_error_t fat32_close(fat32_file_t *file)
{
    if (file && file->is_open)
    {
        memset(file, 0, sizeof(fat32_file_t));
    }

    return FAT32_OK;
}

fat32_error_t fat32_read(fat32_file_t *file, void *buffer, size_t size, size_t *bytes_read)
{
    if (!file || !file->is_open || !buffer)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    if (file->attributes & FAT32_ATTR_DIRECTORY)
    {
        return FAT32_ERROR_NOT_A_FILE; // Cannot read from a directory
    }

    if (!fat32_is_ready())
    {
        return mount_status;
    }

    if (bytes_read)
    {
        *bytes_read = 0;
    }

    if (file->position >= file->file_size)
    {
        return FAT32_OK; // EOF
    }

    size_t remaining = file->file_size - file->position;
    if (size > remaining)
    {
        size = remaining;
    }

    // Ensure current_cluster is correct for current file position
    uint32_t cluster = 0;
    uint32_t cluster_offset = file->position / bytes_per_cluster;
    RETURN_ON_ERROR(seek_to_cluster(file->start_cluster, cluster_offset, &cluster));
    file->current_cluster = cluster;

    size_t total_read = 0;
    uint8_t *dest = (uint8_t *)buffer;

    while (total_read < size)
    {
        uint32_t cluster_offset = file->position % bytes_per_cluster;
        uint32_t sector_in_cluster = cluster_offset / FAT32_SECTOR_SIZE;
        uint32_t byte_in_sector = cluster_offset % FAT32_SECTOR_SIZE;

        uint32_t sector = cluster_to_sector(file->current_cluster) + sector_in_cluster;

        RETURN_ON_ERROR(read_sector(sector, sector_buffer));

        size_t bytes_to_copy = FAT32_SECTOR_SIZE - byte_in_sector;
        if (bytes_to_copy > size - total_read)
        {
            bytes_to_copy = size - total_read;
        }

        memcpy(dest + total_read, sector_buffer + byte_in_sector, bytes_to_copy);
        total_read += bytes_to_copy;
        file->position += bytes_to_copy;

        // Check if we need to move to the next cluster
        if ((file->position % bytes_per_cluster) == 0 && total_read < size)
        {
            uint32_t next_cluster;
            RETURN_ON_ERROR(read_cluster_fat_entry(file->current_cluster, &next_cluster));
            if (next_cluster >= FAT32_FAT_ENTRY_EOC)
            {
                // End of cluster chain or error
                break;
            }
            file->current_cluster = next_cluster;
        }
    }

    if (bytes_read)
    {
        *bytes_read = total_read;
    }
    return FAT32_OK;
}

fat32_error_t fat32_write(fat32_file_t *file, const void *buffer, size_t size, size_t *bytes_written)
{
    if (!file || !file->is_open || !buffer)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    if (file->attributes & FAT32_ATTR_DIRECTORY)
    {
        return FAT32_ERROR_NOT_A_FILE; // Cannot write to a directory
    }

    if (!fat32_is_ready())
    {
        return mount_status;
    }

    if (bytes_written)
    {
        *bytes_written = 0;
    }

    uint32_t old_file_size = file->file_size;

    // Ensure current_cluster is correct for current file position
    uint32_t cluster = file->start_cluster;
    uint32_t cluster_offset = file->position / bytes_per_cluster;
    for (uint32_t i = 0; i < cluster_offset; i++)
    {
        uint32_t next_cluster;
        RETURN_ON_ERROR(read_cluster_fat_entry(cluster, &next_cluster));
        if (next_cluster >= FAT32_FAT_ENTRY_EOC)
        {
            // Allocate a new cluster and link it
            uint32_t new_cluster = 0;
            RETURN_ON_ERROR(allocate_and_link_cluster(cluster, &new_cluster));
            next_cluster = new_cluster;
        }
        cluster = next_cluster;
    }
    file->current_cluster = cluster;

    size_t total_written = 0;
    const uint8_t *src = (const uint8_t *)buffer;

    // Calculate how many clusters are needed for the write
    uint32_t end_pos = file->position + size;
    uint32_t needed_clusters = (end_pos + bytes_per_cluster - 1) / bytes_per_cluster;
    uint32_t current_clusters = file->file_size == 0 ? 1 : (file->file_size + bytes_per_cluster - 1) / bytes_per_cluster;

    // Find last cluster in chain
    cluster = file->start_cluster;
    uint32_t last_cluster = cluster;
    if (current_clusters > 0)
    {
        RETURN_ON_ERROR(find_last_cluster(cluster, current_clusters, &last_cluster));
    }

    // Allocate clusters if needed
    for (uint32_t i = current_clusters; i < needed_clusters; i++)
    {
        uint32_t new_cluster = 0;

        if (current_clusters > 0 || i > 0)
        {
            RETURN_ON_ERROR(allocate_and_link_cluster(last_cluster, &new_cluster));
        }
        else
        {
            // First cluster for empty file
            RETURN_ON_ERROR(get_next_free_cluster(&new_cluster));
            RETURN_ON_ERROR(write_cluster_fat_entry(new_cluster, FAT32_FAT_ENTRY_EOC));

            if (fsinfo.free_count != 0xFFFFFFFF)
            {
                fsinfo.free_count--;
                update_fsinfo();
            }

            file->start_cluster = new_cluster;
        }
        last_cluster = new_cluster;
    }

    // Find cluster for file->position
    cluster = 0;
    cluster_offset = file->position / bytes_per_cluster;
    RETURN_ON_ERROR(seek_to_cluster(file->start_cluster, cluster_offset, &cluster));
    file->current_cluster = cluster;

    size_t pos_in_file = file->position;
    while (total_written < size)
    {
        uint32_t offset_in_cluster = pos_in_file % bytes_per_cluster;
        uint32_t sector_in_cluster = offset_in_cluster / FAT32_SECTOR_SIZE;
        uint32_t byte_in_sector = offset_in_cluster % FAT32_SECTOR_SIZE;
        uint32_t sector = cluster_to_sector(cluster) + sector_in_cluster;

        RETURN_ON_ERROR(read_sector(sector, sector_buffer));

        size_t bytes_to_write = FAT32_SECTOR_SIZE - byte_in_sector;
        if (bytes_to_write > size - total_written)
        {
            bytes_to_write = size - total_written;
        }

        memcpy(sector_buffer + byte_in_sector, src + total_written, bytes_to_write);

        RETURN_ON_ERROR(write_sector(sector, sector_buffer));

        total_written += bytes_to_write;
        pos_in_file += bytes_to_write;

        // Move to next cluster if needed
        if ((pos_in_file % bytes_per_cluster) == 0 && total_written < size)
        {
            uint32_t next_cluster;
            fat32_error_t fat_res = read_cluster_fat_entry(cluster, &next_cluster);
            if (fat_res != FAT32_OK || next_cluster >= FAT32_FAT_ENTRY_EOC)
            {
                return FAT32_ERROR_DISK_FULL;
            }
            cluster = next_cluster;
            file->current_cluster = cluster;
        }
    }

    file->position = pos_in_file;
    if (file->position > file->file_size)
    {
        file->file_size = file->position;
    }

    if (bytes_written)
    {
        *bytes_written = total_written;
    }

    // --- Truncate cluster chain if file shrank ---
    if (file->file_size < old_file_size)
    {
        // Calculate clusters needed for new size
        uint32_t needed_clusters = (file->file_size == 0) ? 0 : (file->file_size + bytes_per_cluster - 1) / bytes_per_cluster;
        uint32_t current_clusters = (old_file_size == 0) ? 0 : (old_file_size + bytes_per_cluster - 1) / bytes_per_cluster;

        if (needed_clusters < current_clusters && file->start_cluster >= 2)
        {
            uint32_t last_cluster_to_keep = file->start_cluster;
            if (needed_clusters > 0)
            {
                // Seek to last cluster to keep
                fat32_error_t seek_res = seek_to_cluster(file->start_cluster, needed_clusters - 1, &last_cluster_to_keep);
                if (seek_res == FAT32_OK)
                {
                    uint32_t first_cluster_to_free = 0;
                    if (read_cluster_fat_entry(last_cluster_to_keep, &first_cluster_to_free) == FAT32_OK)
                    {
                        // Mark end of chain
                        write_cluster_fat_entry(last_cluster_to_keep, FAT32_FAT_ENTRY_EOC);
                        // Free the rest
                        release_cluster_chain(first_cluster_to_free);
                    }
                }
            }
            else
            {
                // File is now empty, free entire chain
                release_cluster_chain(file->start_cluster);
                file->start_cluster = 0;
            }
        }
    }

    // Update directory entry file size on disk
    // After updating file->file_size:
    if (file->dir_entry_sector && file->dir_entry_offset < FAT32_SECTOR_SIZE)
    {
        RETURN_ON_ERROR(read_sector(file->dir_entry_sector, sector_buffer));

        fat32_dir_entry_t *dir_entry = (fat32_dir_entry_t *)(sector_buffer + file->dir_entry_offset);
        dir_entry->file_size = file->file_size;

        RETURN_ON_ERROR(write_sector(file->dir_entry_sector, sector_buffer));
    }

    return FAT32_OK;
}

fat32_error_t fat32_seek(fat32_file_t *file, uint32_t position)
{
    if (!file || !file->is_open)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    file->position = position;

    return FAT32_OK;
}

inline uint32_t fat32_tell(fat32_file_t *file)
{
    return file ? file->position : 0;
}

inline uint32_t fat32_size(fat32_file_t *file)
{
    return file ? file->file_size : 0;
}

inline bool fat32_eof(fat32_file_t *file)
{
    return file ? (file->position >= file->file_size) : true;
}

fat32_error_t fat32_delete(const char *path)
{
    if (!path || !*path)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }
    if (!fat32_is_ready())
    {
        return mount_status;
    }
    return delete_entry(path);
}

fat32_error_t fat32_rename(const char *old_path, const char *new_path)
{
    if (!old_path || !*old_path || !new_path || !*new_path)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }
    if (!fat32_is_ready())
    {
        return mount_status;
    }

    // Find the old entry
    fat32_entry_t entry;
    RETURN_ON_ERROR(find_entry(&entry, old_path));

    // Check if new path already exists
    fat32_entry_t new_entry;
    fat32_error_t result = find_entry(&new_entry, new_path);
    if (result == FAT32_OK)
    {
        return FAT32_ERROR_FILE_EXISTS; // New path already exists
    }
    else if (result != FAT32_ERROR_FILE_NOT_FOUND)
    {
        return result; // Other error
    }

    // Rename by deleting the old entry and creating a new one with the same start cluster
    RETURN_ON_ERROR(unlink_entry(&entry));
    RETURN_ON_ERROR(link_entry(&entry, new_path));

    return FAT32_OK;
}

//
// Directory operations (placeholder implementations)
//

fat32_error_t fat32_set_current_dir(const char *path)
{
    if (!path || !*path)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    if (!fat32_is_ready())
    {
        return mount_status;
    }

    // If we can open the directory, it exists
    fat32_file_t dir;
    RETURN_ON_ERROR(fat32_open(&dir, path));

    // Update current directory cluster and name
    current_dir_cluster = dir.start_cluster;
    fat32_close(&dir); // Close the directory

    return FAT32_OK;
}

fat32_error_t fat32_get_current_dir(char *path, size_t path_len)
{
    if (!path || path_len < FAT32_MAX_PATH_LEN)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    if (!fat32_is_ready())
    {
        return mount_status;
    }

    // Special case: root
    if (current_dir_cluster == boot_sector.root_cluster)
    {
        strncpy(path, "/", path_len);
        path[path_len - 1] = '\0';
        return FAT32_OK;
    }

    // Walk up the tree, collecting names
    char components[16][FAT32_MAX_FILENAME_LEN + 1]; // Up to 16 levels deep
    int depth = 0;
    uint32_t cluster = current_dir_cluster;

    while (cluster != boot_sector.root_cluster && depth < 16)
    {
        // Open current directory and read ".." entry to get parent cluster
        fat32_file_t dir = {0};
        dir.is_open = true;
        dir.attributes = FAT32_ATTR_DIRECTORY;
        dir.start_cluster = cluster;
        dir.current_cluster = cluster;
        dir.position = 0;

        fat32_entry_t entry;
        uint32_t parent_cluster = boot_sector.root_cluster;
        int entry_count = 0;
        bool found_parent = false;

        // Find ".." entry (always the second entry)
        while (fat32_dir_read(&dir, &entry) == FAT32_OK && entry.filename[0])
        {
            if ((entry.attr & FAT32_ATTR_DIRECTORY) && strcmp(entry.filename, "..") == 0)
            {
                parent_cluster = entry.start_cluster ? entry.start_cluster : boot_sector.root_cluster;
                found_parent = true;
                break;
            }
            entry_count++;
            if (entry_count > 2)
            {
                break;
            }
        }
        fat32_close(&dir);
        if (!found_parent)
        {
            break;
        }

        // Now, open parent directory and search for this cluster's name
        fat32_file_t parent_dir = {0};
        parent_dir.is_open = true;
        parent_dir.attributes = FAT32_ATTR_DIRECTORY;
        parent_dir.start_cluster = parent_cluster;
        parent_dir.current_cluster = parent_cluster;
        parent_dir.position = 0;

        bool found_name = false;
        while (fat32_dir_read(&parent_dir, &entry) == FAT32_OK && entry.filename[0])
        {
            if ((entry.attr & FAT32_ATTR_DIRECTORY) && entry.start_cluster == cluster &&
                strcmp(entry.filename, ".") != 0 && strcmp(entry.filename, "..") != 0)
            {
                memcpy(components[depth], entry.filename, FAT32_MAX_FILENAME_LEN);
                components[depth][FAT32_MAX_FILENAME_LEN] = '\0';
                found_name = true;
                break;
            }
        }
        fat32_close(&parent_dir);
        if (!found_name)
        {
            break;
        }
        cluster = parent_cluster;
        depth++;
    }

    // Build the path string
    path[0] = '\0';
    for (int i = depth - 1; i >= 0; i--)
    {
        strncat(path, "/", path_len - strlen(path) - 1);
        strncat(path, components[i], path_len - strlen(path) - 1);
    }
    if (path[0] == '\0')
    {
        strncpy(path, "/", path_len);
    }

    return FAT32_OK;
}

fat32_error_t fat32_dir_read(fat32_file_t *dir, fat32_entry_t *dir_entry)
{
    if (!dir || !dir_entry)
    {
        return FAT32_ERROR_INVALID_PARAMETER;
    }

    if (!dir->is_open)
    {
        return FAT32_ERROR_READ_FAILED;
    }

    if (!(dir->attributes & FAT32_ATTR_DIRECTORY))
    {
        return FAT32_ERROR_NOT_A_DIRECTORY;
    }

    if (!fat32_is_ready())
    {
        return mount_status;
    }

    memset(dir_entry, 0, sizeof(fat32_dir_entry_t));

    if (dir->last_entry_read)
    {
        // If we have already read the last entry, return end of directory
        return FAT32_OK;
    }

    char filename[FAT32_MAX_FILENAME_LEN + 1];
    uint8_t expected_checksum = 0;
    uint32_t current_sector = 0xFFFFFFFF; // Invalid sector to start with

    filename[0] = '\0'; // Reset long filename buffer

    // Search through all directory sectors
    while (!dir->last_entry_read && dir_entry->filename[0] == '\0')
    {
        uint32_t cluster_offset = dir->position % bytes_per_cluster;
        uint32_t sector_in_cluster = cluster_offset / FAT32_SECTOR_SIZE;

        uint32_t sector = cluster_to_sector(dir->current_cluster) + sector_in_cluster;

        if (sector != current_sector)
        {
            fat32_error_t result = read_sector(sector, sector_buffer);
            if (result != FAT32_OK)
            {
                return result;
            }
            current_sector = sector;
        }

        fat32_dir_entry_t *entry = (fat32_dir_entry_t *)(sector_buffer + dir->position % FAT32_SECTOR_SIZE);

        if (entry->shortname[0] == FAT32_DIR_ENTRY_END_MARKER)
        {
            // End of directory
            dir->last_entry_read = true; // Mark that we reached the end
        }
        else if (entry->attr == FAT32_ATTR_LONG_NAME)
        {
            // Populate long filename buffer with this entry's name contents
            fat32_lfn_entry_t *lfn_entry = (fat32_lfn_entry_t *)entry;
            if (lfn_entry->seq & 0x40)
            {
                // This is the last entry for the long filename and the first entry of the sequence
                // We are starting to build a new long filename, clear the filename buffer
                memset(filename, 0, sizeof(filename));
                expected_checksum = lfn_entry->checksum; // Save checksum for later comparison
            }

            if (lfn_entry->checksum == expected_checksum)
            {
                // Copy this entry's part of the long filename into the filename buffer
                int offset = ((lfn_entry->seq & 0x3F) - 1) * FAT32_DIR_LFN_PART_SIZE;
                lfn_to_str(lfn_entry, filename + offset);
            }
        }
        else if (entry->shortname[0] != FAT32_DIR_ENTRY_FREE)
        {
            uint8_t checksum = shortname_checksum(entry->shortname);
            // Now check to see if this is the entry we are looking for
            if (filename[0] != '\0' && expected_checksum == checksum)
            {
                strcpy(dir_entry->filename, filename);
            }
            else
            {
                shortname_to_filename(entry->shortname, dir_entry->filename);
            }
            dir_entry->attr = entry->attr;
            dir_entry->start_cluster = (entry->fst_clus_hi << 16) | entry->fst_clus_lo;
            dir_entry->size = entry->file_size;
            dir_entry->date = entry->wrt_date;
            dir_entry->time = entry->wrt_time;
            dir_entry->sector = sector;
            dir_entry->offset = dir->position % FAT32_SECTOR_SIZE;
        }

        dir->position += 32; // Move to next entry (32 bytes per entry)

        // Check if we need to move to the next cluster
        if ((dir->position % bytes_per_cluster) == 0)
        {
            uint32_t next_cluster;
            RETURN_ON_ERROR(read_cluster_fat_entry(dir->current_cluster, &next_cluster));
            if (next_cluster >= FAT32_FAT_ENTRY_EOC)
            {
                // End of cluster chain
                dir->last_entry_read = true; // Mark that we reached the end
                return FAT32_OK;             // No more entries to read
            }
            dir->current_cluster = next_cluster;
        }
    }

    return FAT32_OK; // Successfully read a directory entry
}

fat32_error_t fat32_dir_create(fat32_file_t *dir, const char *path)
{
    fat32_file_t file;

    memset(dir, 0, sizeof(fat32_file_t));

    fat32_error_t result = new_entry(&file, path, FAT32_ATTR_DIRECTORY);
    if (result != FAT32_OK)
    {
        return result; // Error creating directory
    }

    // Initialize directory struct
    dir->is_open = true;
    dir->start_cluster = file.start_cluster;
    dir->current_cluster = dir->start_cluster;

    // Clear the directory cluster
    RETURN_ON_ERROR(clear_cluster(dir->start_cluster));

    // Find parent directory cluster
    uint32_t parent_cluster = current_dir_cluster;
    if (path[0] == '/')
    {
        parent_cluster = boot_sector.root_cluster;
    }

    // For non-root paths, find the actual parent
    if (strcmp(path, "/") != 0)
    {
        char path_copy[FAT32_MAX_PATH_LEN];
        strncpy(path_copy, path, sizeof(path_copy) - 1);
        path_copy[sizeof(path_copy) - 1] = '\0';

        char *last_slash = strrchr(path_copy, '/');
        if (last_slash && last_slash != path_copy)
        {
            *last_slash = '\0';
            fat32_entry_t parent_entry;
            result = find_entry(&parent_entry, path_copy);
            if (result == FAT32_OK && (parent_entry.attr & FAT32_ATTR_DIRECTORY))
            {
                parent_cluster = parent_entry.start_cluster ? parent_entry.start_cluster : boot_sector.root_cluster;
            }
        }
    }

    // Create "." entry (current directory)
    fat32_dir_entry_t dot_entry = {0};
    memset(dot_entry.shortname, ' ', 11);
    dot_entry.shortname[0] = '.';
    dot_entry.attr = FAT32_ATTR_DIRECTORY;
    dot_entry.fst_clus_hi = (dir->start_cluster >> 16) & 0xFFFF;
    dot_entry.fst_clus_lo = dir->start_cluster & 0xFFFF;
    dot_entry.file_size = 0;

    // Create ".." entry (parent directory)
    fat32_dir_entry_t dotdot_entry = {0};
    memset(dotdot_entry.shortname, ' ', 11);
    dotdot_entry.shortname[0] = '.';
    dotdot_entry.shortname[1] = '.';
    dotdot_entry.attr = FAT32_ATTR_DIRECTORY;
    // For root directory parent, cluster should be 0
    if (parent_cluster == boot_sector.root_cluster)
    {
        dotdot_entry.fst_clus_hi = 0;
        dotdot_entry.fst_clus_lo = 0;
    }
    else
    {
        dotdot_entry.fst_clus_hi = (parent_cluster >> 16) & 0xFFFF;
        dotdot_entry.fst_clus_lo = parent_cluster & 0xFFFF;
    }
    dotdot_entry.file_size = 0;

    // Write both entries to the first sector of the directory
    RETURN_ON_ERROR(read_sector(cluster_to_sector(dir->start_cluster), sector_buffer));

    memcpy(sector_buffer, &dot_entry, sizeof(fat32_dir_entry_t));
    memcpy(sector_buffer + 32, &dotdot_entry, sizeof(fat32_dir_entry_t));

    RETURN_ON_ERROR(write_sector(cluster_to_sector(dir->start_cluster), sector_buffer));

    return FAT32_OK;
}

const char *fat32_error_string(fat32_error_t error)
{
    switch (error)
    {
    case FAT32_OK:
        return "Success";
    case FAT32_ERROR_NO_CARD:
        return "No SD card present";
    case FAT32_ERROR_INIT_FAILED:
        return "SD card initialization failed";
    case FAT32_ERROR_READ_FAILED:
        return "Read operation failed";
    case FAT32_ERROR_WRITE_FAILED:
        return "Write operation failed";
    case FAT32_ERROR_INVALID_FORMAT:
        return "Invalid SD card format";
    case FAT32_ERROR_NOT_MOUNTED:
        return "File system not mounted";
    case FAT32_ERROR_FILE_NOT_FOUND:
        return "File not found";
    case FAT32_ERROR_INVALID_PATH:
        return "Invalid path";
    case FAT32_ERROR_NOT_A_DIRECTORY:
        return "Not a directory";
    case FAT32_ERROR_NOT_A_FILE:
        return "Not a file";
    case FAT32_ERROR_DIR_NOT_EMPTY:
        return "Directory not empty";
    case FAT32_ERROR_DIR_NOT_FOUND:
        return "Directory not found";
    case FAT32_ERROR_DISK_FULL:
        return "Disk full";
    case FAT32_ERROR_FILE_EXISTS:
        return "File already exists";
    case FAT32_ERROR_INVALID_POSITION:
        return "Invalid file position";
    case FAT32_ERROR_INVALID_PARAMETER:
        return "Invalid parameter";
    case FAT32_ERROR_INVALID_SECTOR_SIZE:
        return "Invalid sector size";
    case FAT32_ERROR_INVALID_CLUSTER_SIZE:
        return "Invalid cluster size";
    case FAT32_ERROR_INVALID_FATS:
        return "Invalid FAT size";
    case FAT32_ERROR_INVALID_RESERVED_SECTORS:
        return "Invalid reserved sectors";
    default:
        return "Unknown error";
    }
}

// Timer callback to check SD card presence and unmount if removed
static bool on_sd_card_detect(repeating_timer_t *rt)
{
    // All we need to do is check if the SD card is not present and
    // if we have a mounted FAT32 file system, we will unmount it.
    //
    // This will cover the case if the SD card is changed as we mount
    // the file system when it is needed.

    if (!sd_card_present() && fat32_is_mounted())
    {
        fat32_unmount();                    // Unmount if card is not present
        mount_status = FAT32_ERROR_NO_CARD; // Update status
    }

    return true;
}

void fat32_init(void)
{
    if (fat32_initialised)
    {
        return; // Already initialized
    }

    // Initialize the SD card
    sd_init();

    // Initialize the file system state
    fat32_unmount(); // Ensure we start unmounted

    // Check if a SD card is present
    add_repeating_timer_ms(500, on_sd_card_detect, NULL, &sd_card_detect_timer);

    fat32_initialised = true;
}