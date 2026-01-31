/*
Author: Blair Leduc
License: MIT License
Source: https://github.com/BlairLeduc/picocalc-text-starter
*/

#pragma once

#ifdef __cplusplus
#include <cstdlib>
#include <cstdint>
extern "C"
{
#endif

// FAT32 constants
#define FAT32_SECTOR_SIZE (SD_BLOCK_SIZE) // Standard sector size
#define FAT32_MAX_FILENAME_LEN (255)
#define FAT32_MAX_PATH_LEN (260)
#define MAX_LFN_PART (20) // Maximum number of LFN parts (13 UTF-16 chars each)

// File attributes
#define FAT32_ATTR_READ_ONLY (0x01)
#define FAT32_ATTR_HIDDEN (0x02)
#define FAT32_ATTR_SYSTEM (0x04)
#define FAT32_ATTR_VOLUME_ID (0x08)
#define FAT32_ATTR_DIRECTORY (0x10)
#define FAT32_ATTR_ARCHIVE (0x20)
#define FAT32_ATTR_LONG_NAME (0x0F)
#define FAT32_ATTR_MASK (0x3F) // Mask for valid attributes

// FAT32 Entry constants
#define FAT32_FAT_ENTRY_FREE (0x00)      // Free cluster
#define FAT32_FAT_ENTRY_EOC (0x0FFFFFF8) // End of cluster chain

#define FAT32_DIR_ENTRY_SIZE (32)         // Size of a directory entry in bytes
#define FAT32_DIR_ENTRY_FREE (0xE5)       // Free entry marker
#define FAT32_DIR_ENTRY_END_MARKER (0x00) // End of directory entry marker
#define FAT32_DIR_LFN_PART_SIZE (13)      // Size of each LFN part in bytes

    // Error codes
    typedef enum
    {
        FAT32_OK = 0,
        FAT32_ERROR_NO_CARD,
        FAT32_ERROR_INIT_FAILED,
        FAT32_ERROR_READ_FAILED,
        FAT32_ERROR_WRITE_FAILED,
        FAT32_ERROR_INVALID_FORMAT,
        FAT32_ERROR_NOT_MOUNTED,
        FAT32_ERROR_FILE_NOT_FOUND,
        FAT32_ERROR_INVALID_PATH,
        FAT32_ERROR_NOT_A_DIRECTORY,
        FAT32_ERROR_NOT_A_FILE,
        FAT32_ERROR_DIR_NOT_EMPTY,
        FAT32_ERROR_DIR_NOT_FOUND,
        FAT32_ERROR_DISK_FULL,
        FAT32_ERROR_FILE_EXISTS,
        FAT32_ERROR_INVALID_POSITION,
        FAT32_ERROR_INVALID_PARAMETER,
        FAT32_ERROR_INVALID_SECTOR_SIZE,
        FAT32_ERROR_INVALID_CLUSTER_SIZE,
        FAT32_ERROR_INVALID_FATS,
        FAT32_ERROR_INVALID_RESERVED_SECTORS,
    } fat32_error_t;

    // File handle structure
    typedef struct
    {
        bool is_open;
        bool last_entry_read;
        uint8_t attributes;
        uint32_t start_cluster;
        uint32_t current_cluster;
        uint32_t file_size;
        uint32_t position;
        uint32_t dir_entry_sector; // Sector containing the directory entry
        uint32_t dir_entry_offset; // Byte offset within the sector
    } fat32_file_t;

    // Directory entry structure
    typedef struct
    {
        char filename[FAT32_MAX_FILENAME_LEN + 1]; // Null-terminated filename
        uint32_t size;
        uint16_t date;
        uint16_t time;
        uint32_t start_cluster; // First cluster number (FAT32)
        uint8_t attr;
        uint32_t sector;
        uint32_t offset;
    } fat32_entry_t;

    // Partition entry structure
    typedef struct
    {
        uint8_t boot_indicator; // 0x80 for active partition
        uint8_t start_head;     // Starting head number
        uint16_t start_sector;  // Starting sector (cylinder, sector)
        uint8_t partition_type; // Partition type (0x0B for FAT32, 0x0C for FAT32 LBA)
        uint8_t end_head;       // Ending head number
        uint16_t end_sector;    // Ending sector (cylinder, sector)
        uint32_t start_lba;     // Starting LBA (Logical Block Addressing)
        uint32_t size;          // Size of the partition in sectors
    } __attribute__((packed)) mbr_partition_entry_t;

    // Boot sector structure (simplified)
    typedef struct
    {
        uint8_t jump[3];             // Jump[0] must be 0xEB or 0xE9
        char oem_name[8];            // OEM name (e.g., "MSWIN4.1") (ignore)
        uint16_t bytes_per_sector;   // Bytes per sector (must be 512)
        uint8_t sectors_per_cluster; // Sectors per cluster (must be power of 2, e.g., 1, 2, 4, 8, 16, 32, 64, 128)
        uint16_t reserved_sectors;   // Number of reserved sectors (must not be 0, usually 32 for FAT32)
        uint8_t num_fats;            // Number of FATs (we require 1 or 2)
        uint16_t root_entries;       // Number of root directory entries (must be 0 for FAT32)
        uint16_t total_sectors_16;   // Total sectors (must be 0 for FAT32, use total_sectors_32)
        uint8_t media_type;          // Media type (ignored)
        uint16_t fat_size_16;        // Size of each FAT in sectors (must be 0 for FAT32)
        uint16_t sectors_per_track;  // Sectors per track (CHS, ignored)
        uint16_t num_heads;          // Number of heads (CHS, ignored)
        uint32_t hidden_sectors;     // Number of hidden sectors (CHS,ignored)
        uint32_t total_sectors_32;   // Total sectors (must be non-zero for FAT32)

        // FAT32 specific
        uint32_t fat_size_32;     // Size of **each** FAT in sectors (must be non-zero)
        uint16_t ext_flags;       // Extended flags (ignored)
        uint16_t fat32_version;   // File system version (ignored)
        uint32_t root_cluster;    // First cluster of the root directory
        uint16_t fat32_info;      // FSInfo sector number (usually 1)
        uint16_t backup_boot;     // Backup boot sector number (usually 6)
        uint8_t reserved[12];     // Reserved bytes (must be zero)
        uint8_t drive_number;     // Drive number (ignored)
        uint8_t reserved1;        // Reserved byte (ignored)
        uint8_t boot_signature;   // Boot signature (0x29)
        uint32_t volume_id;       // Volume ID (ignored)
        char volume_label[11];    // Volume label (ignored)
        char file_system_type[8]; // File system type (should be "FAT32      ")
    } __attribute__((packed)) fat32_boot_sector_t;

    // FAT32 FSInfo sector structure
    typedef struct
    {
        uint32_t lead_sig;      // 0x41615252
        uint8_t reserved1[480]; // Reserved bytes
        uint32_t struc_sig;     // 0x61417272
        uint32_t free_count;    // Number of free clusters (0xFFFFFFFF if unknown)
        uint32_t next_free;     // Next free cluster (0xFFFFFFFF if unknown)
        uint8_t reserved2[12];  // Reserved bytes
        uint32_t trail_sig;     // 0xAA550000
    } __attribute__((packed)) fat32_fsinfo_t;

    typedef struct
    {
        char shortname[11];
        uint8_t attr;
        uint8_t nt_res;
        uint8_t crt_time_tenth;
        uint16_t crt_time;
        uint16_t crt_date;
        uint16_t lst_acc_date;
        uint16_t fst_clus_hi;
        uint16_t wrt_time;
        uint16_t wrt_date;
        uint16_t fst_clus_lo;
        uint32_t file_size;
    } __attribute__((packed)) fat32_dir_entry_t;

    typedef struct
    {
        uint8_t seq;         // Sequence number
        uint16_t name1[5];   // First 5 characters (UTF-16)
        uint8_t attr;        // Always 0x0F for LFN
        uint8_t type;        // Always 0 for LFN
        uint8_t checksum;    // Checksum of 8.3 name
        uint16_t name2[6];   // Next 6 characters (UTF-16)
        uint16_t first_clus; // Always 0 for LFN
        uint16_t name3[2];   // Last 2 characters (UTF-16)
    } __attribute__((packed)) fat32_lfn_entry_t;

    // File system functions
    bool fat32_is_ready(void);
    fat32_error_t fat32_mount(void);
    void fat32_unmount(void);
    bool fat32_is_mounted(void);
    fat32_error_t fat32_get_status(void);
    fat32_error_t fat32_get_free_space(uint64_t *free_space);
    fat32_error_t fat32_get_total_space(uint64_t *total_space);
    fat32_error_t fat32_get_volume_name(char *name, size_t name_len);
    uint32_t fat32_get_cluster_size(void);

    // File operations
    fat32_error_t fat32_open(fat32_file_t *file, const char *path);
    fat32_error_t fat32_create(fat32_file_t *file, const char *path);
    fat32_error_t fat32_close(fat32_file_t *file);
    fat32_error_t fat32_read(fat32_file_t *file, void *buffer, size_t size, size_t *bytes_read);
    fat32_error_t fat32_write(fat32_file_t *file, const void *buffer, size_t size, size_t *bytes_written);
    fat32_error_t fat32_seek(fat32_file_t *file, uint32_t position);
    uint32_t fat32_tell(fat32_file_t *file);
    uint32_t fat32_size(fat32_file_t *file);
    bool fat32_eof(fat32_file_t *file);
    fat32_error_t fat32_delete(const char *path);
    fat32_error_t fat32_rename(const char *old_path, const char *new_path);

    // Directory operations
    fat32_error_t fat32_set_current_dir(const char *path);
    fat32_error_t fat32_get_current_dir(char *path, size_t path_len);

    fat32_error_t fat32_dir_read(fat32_file_t *dir, fat32_entry_t *entry);
    fat32_error_t fat32_dir_create(fat32_file_t *dir, const char *path);

    // Utility functions
    const char *fat32_error_string(fat32_error_t error);

    void fat32_init(void);

#ifdef __cplusplus
}
#endif