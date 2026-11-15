#include "lan_discovery.h"
#include <arpa/inet.h>
#include <errno.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define MAX_SOCKETS 32
#define MAX_PEERS 128
#define MAX_RECENT 128
#define MAX_DISCOVERY_PACKET 2048
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static void (*provider)(unsigned, int);
static int native_enabled = 1;
static struct { int used, fd; unsigned port; uint32_t address, mask; } sockets[MAX_SOCKETS];
static struct { char key[512], instance[256]; struct sockaddr_in addr; } peers[MAX_PEERS];
/* Only suppress a matching pair received via DIFFERENT paths, never repeated
 * unicast gameplay or repeated native announcements. Bounded, exact comparison. */
static struct {
    int used, fd, broadcast;
    struct sockaddr_in from;
    uint64_t time;
    size_t len;
    unsigned char data[MAX_DISCOVERY_PACKET];
} recent[MAX_RECENT];
static unsigned next_recent;
static uint32_t broadcasts[32];
static unsigned broadcast_count;
static int valid_port(unsigned port) { return port >= 8086 && port <= 8093; }
static uint64_t milliseconds(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
static int tracked(int fd) {
    for (int i=0;i<MAX_SOCKETS;i++) if(sockets[i].used && sockets[i].fd==fd) return 1;
    return 0;
}
void ra3_lan_init(void (*changed)(unsigned,int), int native_broadcast) {
    const char *off=getenv("RA3_LAN_BONJOUR"), *native=getenv("RA3_LAN_BROADCAST");
    provider=off && !strcmp(off,"0") ? NULL : changed;
    native_enabled=native ? strcmp(native,"0")!=0 : native_broadcast;
    fprintf(stderr,"[lan] Bonjour=%s native-broadcast=%s wire=%s\n",
        provider?"on":"off",native_enabled?"on":"off",RA3_LAN_WIRE);
}
void ra3_lan_bound(int fd) {
    if(!provider) return;
    struct sockaddr_in a; socklen_t n=sizeof a; int type=0; socklen_t tn=sizeof type;
    if(getsockname(fd,(struct sockaddr*)&a,&n) || a.sin_family!=AF_INET ||
       getsockopt(fd,SOL_SOCKET,SO_TYPE,&type,&tn) || type!=SOCK_DGRAM || !valid_port(ntohs(a.sin_port))) return;
    int one=1;
#ifdef IP_RECVDSTADDR
    setsockopt(fd,IPPROTO_IP,IP_RECVDSTADDR,&one,sizeof one);
#elif defined(IP_PKTINFO)
    setsockopt(fd,IPPROTO_IP,IP_PKTINFO,&one,sizeof one);
#endif
    pthread_mutex_lock(&lock);
    if(tracked(fd)) { pthread_mutex_unlock(&lock); return; }
    int slot=-1, already=0; unsigned port=ntohs(a.sin_port);
    for(int i=0;i<MAX_SOCKETS;i++) {
        if(!sockets[i].used && slot<0) slot=i;
        if(sockets[i].used && sockets[i].port==port) already=1;
    }
    if(slot>=0) { sockets[slot].used=1; sockets[slot].fd=fd; sockets[slot].port=port; sockets[slot].address=a.sin_addr.s_addr; sockets[slot].mask=0; }
    broadcast_count=0;
    struct ifaddrs *ifs=NULL;
    if(!getifaddrs(&ifs)) {
        for(struct ifaddrs *i=ifs;i && broadcast_count<32;i=i->ifa_next) {
            if(slot>=0 && i->ifa_addr && i->ifa_netmask && i->ifa_addr->sa_family==AF_INET &&
               ((struct sockaddr_in*)i->ifa_addr)->sin_addr.s_addr==a.sin_addr.s_addr)
                sockets[slot].mask=((struct sockaddr_in*)i->ifa_netmask)->sin_addr.s_addr;
            if(i->ifa_addr && i->ifa_addr->sa_family==AF_INET &&
               (i->ifa_flags & IFF_BROADCAST) && i->ifa_broadaddr)
                broadcasts[broadcast_count++]=((struct sockaddr_in*)i->ifa_broadaddr)->sin_addr.s_addr;
        }
        freeifaddrs(ifs);
    }
    /* Serialize provider notifications with bind/close so fd reuse cannot
     * reverse a queued start/stop. Providers never call back synchronously. */
    if(slot>=0 && !already) provider(port,1);
    pthread_mutex_unlock(&lock);
}
void ra3_lan_closed(int fd) {
    pthread_mutex_lock(&lock);
    unsigned port=0;
    for(int i=0;i<MAX_SOCKETS;i++) if(sockets[i].used && sockets[i].fd==fd) {
        port=sockets[i].port; sockets[i].used=0;
    }
    for(int i=0;i<MAX_RECENT;i++) if(recent[i].fd==fd) recent[i].used=0;
    int remaining=0, any=0;
    for(int i=0;i<MAX_SOCKETS;i++) if(sockets[i].used) {
        any=1; if(sockets[i].port==port) remaining=1;
    }
    if(!any) memset(peers,0,sizeof peers);
    if(port && !remaining && provider) provider(port,0);
    pthread_mutex_unlock(&lock);
}
void ra3_lan_peer(const char *key,const char *instance,uint32_t ipv4,unsigned port,int present) {
    if(!key || !*key || strlen(key)>=sizeof peers[0].key) return;
    if(present && (!instance || !*instance || strlen(instance)>=sizeof peers[0].instance)) return;
    if(present && (!valid_port(port) || !ipv4 || ipv4==INADDR_BROADCAST || IN_MULTICAST(ntohl(ipv4)))) return;
    pthread_mutex_lock(&lock);
    int slot=-1;
    for(int i=0;i<MAX_PEERS;i++) {
        if(!strcmp(peers[i].key,key)) { slot=i; break; }
        if(!peers[i].key[0] && slot<0) slot=i;
    }
    if(slot>=0) {
        if(!present) { if(!strcmp(peers[slot].key,key)) peers[slot].key[0]=0; }
        else {
            snprintf(peers[slot].key,sizeof peers[slot].key,"%s",key);
            snprintf(peers[slot].instance,sizeof peers[slot].instance,"%s",instance);
            peers[slot].addr=(struct sockaddr_in){.sin_family=AF_INET,.sin_port=htons(port),.sin_addr={ipv4}};
        }
    }
    pthread_mutex_unlock(&lock);
}
ssize_t ra3_lan_send(int fd,const void *data,size_t len,int flags,const struct sockaddr_in *to) {
    struct sockaddr_in targets[MAX_PEERS]; unsigned count=0;
    pthread_mutex_lock(&lock);
    int discovery=provider && tracked(fd) && to->sin_addr.s_addr==INADDR_BROADCAST && valid_port(ntohs(to->sin_port));
    int selected[MAX_PEERS], scores[MAX_PEERS];
    uint32_t local=0,mask=0;
    for(int i=0;i<MAX_SOCKETS;i++) if(sockets[i].used && sockets[i].fd==fd) { local=sockets[i].address; mask=sockets[i].mask; }
    if(discovery) for(int i=0;i<MAX_PEERS;i++) if(peers[i].key[0] && peers[i].addr.sin_port==to->sin_port) {
        uint32_t ip=peers[i].addr.sin_addr.s_addr, host=ntohl(ip);
        int score=(host>>24)==127 ? 1 : (host>>16)==0xa9fe ? 5 : 10;
        if(mask && (ip & mask)==(local & mask)) score+=100;
        unsigned j=0;
        for(;j<count;j++) if(!strcmp(peers[selected[j]].instance,peers[i].instance) || peers[selected[j]].addr.sin_addr.s_addr==ip) break;
        if(j==count) { selected[count]=i; scores[count++]=score; }
        else if(score>scores[j]) { selected[j]=i; scores[j]=score; }
    }
    for(unsigned i=0;i<count;i++) targets[i]=peers[selected[i]].addr;
    pthread_mutex_unlock(&lock);
    ssize_t result=-1; int saved=EHOSTUNREACH;
    if(!discovery || native_enabled) {
        result=sendto(fd,data,len,flags,(const struct sockaddr*)to,sizeof *to);
        if(result<0) saved=errno;
    }
    for(unsigned i=0;i<count;i++) {
        ssize_t sent=sendto(fd,data,len,flags,(struct sockaddr*)&targets[i],sizeof targets[i]);
        if(sent>=0) result=sent;
        else if(result<0) saved=errno;
        if(getenv("HLE_NETTRACE")) fprintf(stderr,"[lan] unicast %s:%u %zu -> %zd\n",
            inet_ntoa(targets[i].sin_addr),ntohs(targets[i].sin_port),len,sent);
    }
    if(result<0) errno=saved; /* No peers is NOT a successful send. */
    return result;
}
static int duplicate(int fd,const struct sockaddr_in *from,int broadcast,const void *data,size_t len) {
    if(broadcast<0 || len>MAX_DISCOVERY_PACKET) return 0;
    uint64_t now=milliseconds(); int found=0;
    pthread_mutex_lock(&lock);
    for(int i=0;i<MAX_RECENT;i++) if(recent[i].used && recent[i].fd==fd &&
        recent[i].broadcast!=broadcast && now-recent[i].time<=250 && recent[i].len==len &&
        recent[i].from.sin_addr.s_addr==from->sin_addr.s_addr && recent[i].from.sin_port==from->sin_port &&
        !memcmp(recent[i].data,data,len)) { recent[i].used=0; found=1; break; }
    if(!found) {
        unsigned i=next_recent++ % MAX_RECENT;
        recent[i].used=1; recent[i].fd=fd; recent[i].from=*from; recent[i].broadcast=broadcast;
        recent[i].time=now; recent[i].len=len; memcpy(recent[i].data,data,len);
    }
    pthread_mutex_unlock(&lock); return found;
}
ssize_t ra3_lan_recv(int fd,void *data,size_t len,int flags,struct sockaddr *from,socklen_t *fromlen) {
    pthread_mutex_lock(&lock); int enabled=provider && tracked(fd); pthread_mutex_unlock(&lock);
    if(!enabled || (flags & MSG_PEEK)) return recvfrom(fd,data,len,flags,from,fromlen);
    for(unsigned attempts=0;attempts<32;attempts++) {
        struct sockaddr_in sender; struct iovec io={data,len};
        union { struct cmsghdr align; unsigned char bytes[128]; } control;
        struct msghdr msg={.msg_name=&sender,.msg_namelen=sizeof sender,.msg_iov=&io,.msg_iovlen=1,
            .msg_control=control.bytes,.msg_controllen=sizeof control.bytes};
        ssize_t n=recvmsg(fd,&msg,flags);
        if(n<0) return n;
        int broadcast=-1;
        for(struct cmsghdr *c=CMSG_FIRSTHDR(&msg);c;c=CMSG_NXTHDR(&msg,c)) {
            uint32_t dest=0; int known=0;
#ifdef IP_RECVDSTADDR
            if(c->cmsg_level==IPPROTO_IP && c->cmsg_type==IP_RECVDSTADDR && c->cmsg_len>=CMSG_LEN(4))
                { memcpy(&dest,CMSG_DATA(c),4); known=1; }
#elif defined(IP_PKTINFO)
            if(c->cmsg_level==IPPROTO_IP && c->cmsg_type==IP_PKTINFO && c->cmsg_len>=CMSG_LEN(sizeof(struct in_pktinfo)))
                { dest=((struct in_pktinfo*)CMSG_DATA(c))->ipi_addr.s_addr; known=1; }
#endif
            if(known) {
                broadcast=dest==INADDR_BROADCAST;
                pthread_mutex_lock(&lock);
                for(unsigned i=0;i<broadcast_count;i++) if(dest==broadcasts[i]) broadcast=1;
                pthread_mutex_unlock(&lock);
            }
        }
        if(!(msg.msg_flags & (MSG_TRUNC|MSG_CTRUNC)) && duplicate(fd,&sender,broadcast,data,(size_t)n)) continue;
        if(from && fromlen) { socklen_t copy=*fromlen<msg.msg_namelen?*fromlen:msg.msg_namelen; memcpy(from,&sender,copy); *fromlen=msg.msg_namelen; }
        return n;
    }
    errno=EWOULDBLOCK; return -1;
}
