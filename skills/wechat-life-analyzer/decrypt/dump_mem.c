/* dump_mem.c — dump WeChat process RW memory regions to a file (run as root).
 * Usage: sudo ./dump_mem [pid] [out.bin]
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>

static pid_t find_pid(void){
    FILE *f = popen("pgrep -x WeChat", "r");
    char b[64]; pid_t p = -1;
    if (f){ if (fgets(b,sizeof(b),f)) p = atoi(b); pclose(f);}
    return p;
}

int main(int argc, char **argv){
    pid_t pid = (argc>=2)? atoi(argv[1]) : find_pid();
    const char *out = (argc>=3)? argv[2] : "wechat_mem.bin";
    if (pid<=0){ fprintf(stderr,"WeChat not running\n"); return 1; }

    mach_port_t task;
    if (task_for_pid(mach_task_self(), pid, &task)!=KERN_SUCCESS){
        fprintf(stderr,"task_for_pid failed (need root + ad-hoc signed)\n"); return 1;
    }
    FILE *fo = fopen(out,"wb"); if(!fo){ perror("fopen"); return 1; }

    mach_vm_address_t addr = 0; unsigned long total = 0; int regions = 0;
    while (1){
        mach_vm_size_t size = 0; vm_region_basic_info_data_64_t info;
        mach_msg_type_number_t cnt = VM_REGION_BASIC_INFO_COUNT_64; mach_port_t obj;
        if (mach_vm_region(task,&addr,&size,VM_REGION_BASIC_INFO_64,(vm_region_info_t)&info,&cnt,&obj)!=KERN_SUCCESS) break;
        if (size==0){ addr++; continue; }
        if ((info.protection&(VM_PROT_READ|VM_PROT_WRITE))==(VM_PROT_READ|VM_PROT_WRITE)){
            vm_offset_t data; mach_msg_type_number_t dc;
            if (mach_vm_read(task,addr,size,&data,&dc)==KERN_SUCCESS){
                fwrite((void*)data,1,dc,fo); total += dc; regions++;
                mach_vm_deallocate(mach_task_self(),data,dc);
            }
        }
        addr += size;
    }
    fclose(fo);
    fprintf(stderr,"dumped %lu bytes from %d RW regions -> %s\n", total, regions, out);
    return 0;
}
