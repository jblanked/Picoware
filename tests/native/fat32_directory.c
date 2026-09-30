/* Exercise the actual FAT32 implementation against a poisoned in-memory disk. */
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "../../src/MicroPython/sd/fat32.c"
#define BLOCKS 33000
static uint8_t disk[BLOCKS][512];
static int fail_write = -1;
sd_error_t sd_card_init(void) { return SD_OK; }
void sd_init(void) {}
sd_error_t sd_read_block(uint32_t b,uint8_t *out) { assert(b<BLOCKS);memcpy(out,disk[b],512);return SD_OK; }
sd_error_t sd_write_block(uint32_t b,const uint8_t *in) { assert(b<BLOCKS);if ((int)b==fail_write) return SD_ERROR_WRITE_FAILED;memcpy(disk[b],in,512);return SD_OK; }
sd_error_t sd_read_blocks(uint32_t b,uint32_t n,uint8_t *out) { for(uint32_t i=0;i<n;i++) {sd_error_t e=sd_read_block(b+i,out+512*i);if(e)return e;}return SD_OK; }
sd_error_t sd_write_blocks(uint32_t b,uint32_t n,const uint8_t *in) { for(uint32_t i=0;i<n;i++){sd_error_t e=sd_write_block(b+i,in+512*i);if(e)return e;}return SD_OK; }
static void setup(unsigned spc) {
 memset(disk,0xa5,sizeof(disk));memset(&boot_sector,0,sizeof(boot_sector));
 boot_sector.sectors_per_cluster=spc;boot_sector.reserved_sectors=32;boot_sector.fat_size_32=9;boot_sector.root_cluster=2;boot_sector.fat32_info=1;
 memset(disk[32],0,9*512);first_data_sector=64;bytes_per_cluster=spc*512;cluster_count=1000;
 volume_start_block=0;current_dir_cluster=2;fsinfo.next_free=3;fsinfo.free_count=999;fat32_mounted=true;mount_status=FAT32_OK;
 assert(write_cluster_fat_entry(2,FAT32_FAT_ENTRY_EOC)==FAT32_OK);assert(clear_cluster(2)==FAT32_OK);fail_write=-1;
}
static void create_check(const char *path) {
 fat32_file_t f;size_t n;char out[8]={0};
 assert(fat32_create(&f,path)==FAT32_OK);assert(fat32_write(&f,"payload",7,&n)==FAT32_OK&&n==7);assert(fat32_close(&f)==FAT32_OK);
 assert(fat32_open(&f,path)==FAT32_OK);assert(fat32_read(&f,out,7,&n)==FAT32_OK&&n==7&&!memcmp(out,"payload",7));assert(fat32_close(&f)==FAT32_OK);
}
static void directories(unsigned spc) {
 setup(spc);fat32_file_t dir;assert(fat32_dir_create(&dir,"/test")==FAT32_OK);
 uint32_t start=cluster_to_sector(dir.start_cluster);
 for(unsigned i=64;i<bytes_per_cluster;i++)assert(disk[start+i/512][i%512]==0);
 for(unsigned i=0;i<280;i++){char path[100];snprintf(path,sizeof(path),"/test/snapshot%03u.bin",i);create_check(path);}
 for(unsigned i=0;i<280;i++){char path[100];fat32_file_t f;snprintf(path,sizeof(path),"/test/snapshot%03u.bin",i);assert(fat32_open(&f,path)==FAT32_OK);fat32_close(&f);}
 printf("PASS poisoned %u-sector clusters, 280 file writes/reopens across sectors and clusters\n",spc);
}
static void straddle(void) {
 setup(1);fat32_file_t dir;assert(fat32_dir_create(&dir,"/test")==FAT32_OK);
 // 2 dot entries + 3 slots for this name + 10 slots for five short names = 15.
 create_check("/test/longfilename01.bin");
 for(unsigned i=0;i<5;i++){char p[80];snprintf(p,sizeof(p),"/test/f%u.bin",i);create_check(p);}
 create_check("/test/boundary.bin"); // LFN in old cluster, short entry in new cluster.
 create_check("/test/after.bin");
 fat32_file_t f;assert(fat32_open(&f,"/test/longfilename01.bin")==FAT32_OK);fat32_close(&f);
 assert(fat32_delete("/test/boundary.bin")==FAT32_OK);
 create_check("/test/replacement.bin");
 puts("PASS split LFN/short entry, preserved neighboring files and reuse");
}
static void failure(void) {
 setup(32);fat32_file_t dir;fail_write=cluster_to_sector(3)+1;
 assert(fat32_dir_create(&dir,"/broken")!=FAT32_OK);fail_write=-1;
 fat32_entry_t entry;assert(find_entry(&entry,"/broken")==FAT32_ERROR_FILE_NOT_FOUND);
 uint32_t value;assert(read_cluster_fat_entry(3,&value)==FAT32_OK&&value==0);
 assert(fat32_dir_create(&dir,"/retry")==FAT32_OK);
 puts("PASS failed directory clearing does not publish a directory or allocate its cluster");
}
int main(void){directories(1);directories(32);straddle();failure();return 0;}
