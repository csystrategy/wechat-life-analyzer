/* dump_mem2.c — dump ALL readable, non-executable regions of WeChat (recursing
 * into submaps) to a file. Run as root. Usage: sudo ./dump_mem2 [pid] [out.bin]
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>

static pid_t find_pid(void){
    FILE *f = popen("pgrep -x WeChat","r"); char b[64]; pid_t p=-1;
    if (f){ if (fgets(b,sizeof(b),f)) p=atoi(b); pclose(f);} return p;
}

int main(int argc, char **argv){
    pid_t pid = (argc>=2)? atoi(argv[1]) : find_pid();
    const char *out = (argc>=3)? argv[2] : "wechat_mem2.bin";
    if (pid<=0){ fprintf(stderr,"WeChat not running\n"); return 1; }
    mach_port_t task;
    if (task_for_pid(mach_task_self(), pid, &task)!=KERN_SUCCESS){
        fprintf(stderr,"task_for_pid failed\n"); return 1; }
    FILE *fo = fopen(out,"wb"); if(!fo){ perror("fopen"); return 1; }

    mach_vm_address_t addr = 0; natural_t depth = 0;
    unsigned long total = 0, failed = 0; int regions = 0;
    const mach_vm_size_t CHUNK = 128ULL<<20;
    while (1){
        mach_vm_size_t size = 0;
        vm_region_submap_info_data_64_t info;
        mach_msg_type_number_t cnt = VM_REGION_SUBMAP_INFO_COUNT_64;
        kern_return_t kr = mach_vm_region_recurse(task,&addr,&size,&depth,
                              (vm_region_recurse_info_t)&info,&cnt);
        if (kr!=KERN_SUCCESS) break;
        if (info.is_submap){ depth++; continue; }
        if ((info.protection & VM_PROT_READ) && !(info.protection & VM_PROT_EXECUTE)){
            mach_vm_address_t a = addr; mach_vm_size_t rem = size;
            while (rem > 0){
                mach_vm_size_t csz = rem > CHUNK ? CHUNK : rem;
                vm_offset_t data; mach_msg_type_number_t dc;
                if (mach_vm_read(task,a,csz,&data,&dc)==KERN_SUCCESS){
                    fwrite((void*)data,1,dc,fo); total += dc;
                    mach_vm_deallocate(mach_task_self(),data,dc);
                } else { failed += csz; }
                a += csz; rem -= csz;
            }
            regions++;
        }
        addr += size;
    }
    fclose(fo);
    fprintf(stderr,"dumped %lu bytes, %d regions, %lu bytes unreadable -> %s\n",
            total, regions, failed, out);
    return 0;
}
