/* scan_key.c — brute-force the WeChat 4.x SQLCipher raw key from a memory dump.
 * Validates each 32-byte window against an encrypted DB's page-1 (SQLCipher4:
 * AES-256-CBC, HMAC-SHA512, KDF mac_key = PBKDF2-SHA512(rawkey, salt^0x3a, 2)).
 * Cheap AES pre-filter (decrypt first content block -> page-size 0x1000) before HMAC.
 *
 * Usage: ./scan_key wechat_mem.bin keytarget.bin [threads] [stride]
 *   keytarget.bin = first 4096 bytes (page 1) of an encrypted DB (e.g. contact.db)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <pthread.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <CommonCrypto/CommonCrypto.h>
#include <CommonCrypto/CommonKeyDerivation.h>

static uint8_t mac_salt[16];
static uint8_t hmac_data[4020];   /* page1[16:4032] (4016) + pgno=1 LE (4) */
static uint8_t stored_hmac[64];   /* page1[4032:4096] */
static uint8_t ct16[16];          /* page1[16:32]  first encrypted content block */
static uint8_t iv16[16];          /* page1[4016:4032]  CBC IV for page 1 */

static const uint8_t *g_mem; static size_t g_len; static int g_stride = 1;
static volatile int g_found = 0; static uint8_t g_key[32];
static pthread_mutex_t g_mx = PTHREAD_MUTEX_INITIALIZER;

typedef struct { size_t start, end; } range_t;

static inline int prefilter(const uint8_t *cand){
    uint8_t dec[16]; size_t moved;
    if (CCCrypt(kCCDecrypt,kCCAlgorithmAES,kCCOptionECBMode,cand,32,NULL,ct16,16,dec,16,&moved)!=kCCSuccess) return 0;
    /* CBC first block: plaintext = AES_ECB_dec(ct) XOR IV; SQLite page-size bytes = 0x10 0x00 (4096) */
    return ((dec[0]^iv16[0])==0x10) && ((dec[1]^iv16[1])==0x00);
}

static int validate(const uint8_t *cand){
    if (!prefilter(cand)) return 0;
    uint8_t mac_key[32];
    CCKeyDerivationPBKDF(kCCPBKDF2,(const char*)cand,32,mac_salt,16,kCCPRFHmacAlgSHA512,2,mac_key,32);
    uint8_t out[64];
    CCHmac(kCCHmacAlgSHA512,mac_key,32,hmac_data,sizeof(hmac_data),out);
    return memcmp(out,stored_hmac,64)==0;
}

static void *worker(void *arg){
    range_t *r = (range_t*)arg;
    for (size_t i=r->start; i+32<=r->end && !g_found; i+=g_stride){
        if (validate(g_mem+i)){
            pthread_mutex_lock(&g_mx);
            if (!g_found){ g_found=1; memcpy(g_key,g_mem+i,32); }
            pthread_mutex_unlock(&g_mx);
            return NULL;
        }
    }
    return NULL;
}

int main(int argc, char **argv){
    const char *memf = (argc>=2)? argv[1] : "wechat_mem.bin";
    const char *tgt  = (argc>=3)? argv[2] : "keytarget.bin";
    int nthreads = (argc>=4)? atoi(argv[3]) : 8;
    if (argc>=5) g_stride = atoi(argv[4]);
    if (nthreads<1) nthreads=1; if (nthreads>64) nthreads=64;

    FILE *ft = fopen(tgt,"rb"); if(!ft){ perror("keytarget"); return 1; }
    uint8_t page1[4096];
    if (fread(page1,1,4096,ft)!=4096){ fprintf(stderr,"keytarget must be >=4096 bytes\n"); return 1; }
    fclose(ft);
    for (int i=0;i<16;i++) mac_salt[i]=page1[i]^0x3a;
    memcpy(hmac_data, page1+16, 4016);
    hmac_data[4016]=1; hmac_data[4017]=0; hmac_data[4018]=0; hmac_data[4019]=0;
    memcpy(stored_hmac, page1+4032, 64);
    memcpy(ct16, page1+16, 16);
    memcpy(iv16, page1+4016, 16);

    int fd = open(memf,O_RDONLY); if(fd<0){ perror("mem"); return 1; }
    struct stat st; fstat(fd,&st); g_len=st.st_size;
    g_mem = mmap(NULL,g_len,PROT_READ,MAP_PRIVATE,fd,0);
    if (g_mem==MAP_FAILED){ perror("mmap"); return 1; }
    fprintf(stderr,"scanning %zu bytes, %d threads, stride %d\n", g_len, nthreads, g_stride);

    pthread_t th[64]; range_t rg[64];
    size_t chunk = g_len/nthreads;
    for (int t=0;t<nthreads;t++){
        rg[t].start = (size_t)t*chunk;
        rg[t].end   = (t==nthreads-1)? g_len : (size_t)(t+1)*chunk + 32;
        if (rg[t].end>g_len) rg[t].end=g_len;
        pthread_create(&th[t],NULL,worker,&rg[t]);
    }
    for (int t=0;t<nthreads;t++) pthread_join(th[t],NULL);

    if (g_found){
        printf("FOUND ");
        for (int i=0;i<32;i++) printf("%02x", g_key[i]);
        printf("\n");
        return 0;
    }
    fprintf(stderr,"NOT FOUND (try smaller stride or dump more regions)\n");
    return 2;
}
