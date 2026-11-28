"""Host regression for native PSRAM chunking; run with Python 3 and a C compiler."""
from pathlib import Path
import os
import subprocess
import tempfile
p=Path(__file__).resolve().parents[1] / 'src/MicroPython/PicoCalc/picoware_psram/picoware_psram.c'
s=p.read_text();s=s[s.index('void picoware_psram_write_data'):s.index('// Unified print function')]
head='''#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
static int psram_instance;
static unsigned char memory[4096];
static int calls;
static void psram_ensure_init(void) {}
static void psram_qspi_write(int *q,uint32_t a,const uint8_t *p,size_t n) {(void)q;assert(n>0 && n<=64 && (a&63)+n<=64);assert(a+n<=sizeof(memory));memcpy(memory+a,p,n);++calls;}
static void psram_qspi_read(int *q,uint32_t a,uint8_t *p,size_t n) {(void)q;assert(n>0 && n<=64 && (a&63)+n<=64);assert(a+n<=sizeof(memory));memcpy(p,memory+a,n);++calls;}
'''
tail='''int main(void) {
 uint8_t src[1026],dst[1026];int cases=0;
 for(int a=0;a<130;++a)for(int n=0;n<=1024;++n) {
  memset(memory,0xa5,sizeof(memory));memset(dst,0xcc,sizeof(dst));
  for(int i=0;i<n;++i)src[i+1]=(uint8_t)(i*37+a);
  calls=0;picoware_psram_write_data(a,src+1,n);
  assert(n || !calls);
  for(int i=0;i<4096;++i)assert(memory[i]==(i>=a && i<a+n?src[i-a+1]:0xa5));
  picoware_psram_read_data(a,dst+1,n);
  assert(!memcmp(src+1,dst+1,n));assert(dst[0]==0xcc && dst[n+1]==0xcc);++cases;
 }
 printf("PSRAM_TRANSFER_PASS %d alignment/length cases, independent bytes and guard regions\\n",cases);
}
'''
with tempfile.TemporaryDirectory(prefix="psram-transfers-") as directory:
    out=Path(directory)/"transfers.c"
    binary=Path(directory)/"transfers"
    out.write_text(head+s+tail)
    subprocess.run([os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-O1", "-g", "-fsanitize=address,undefined", str(out), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
