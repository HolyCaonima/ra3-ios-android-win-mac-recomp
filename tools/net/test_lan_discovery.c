/* Compile the real transport with one syscall seam: never emit test packets
 * onto the user's LAN. Unicast still uses real OS UDP sockets. */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <poll.h>
#include <arpa/inet.h>
#include <sys/socket.h>
static int broadcasts_sent, broadcast_error;
static ssize_t test_sendto(int fd,const void *buf,size_t len,int flags,const struct sockaddr *to,socklen_t size) {
    if(((const struct sockaddr_in*)to)->sin_addr.s_addr==INADDR_BROADCAST) {
        broadcasts_sent++;
        if(broadcast_error) { errno=broadcast_error; return -1; }
        return (ssize_t)len;
    }
    return sendto(fd,buf,len,flags,to,size);
}
#define sendto test_sendto
#include "../../runtime/hle/lan_discovery.c"
#undef sendto
static int starts, stops;
static void port_changed(unsigned port,int active) { assert(valid_port(port)); if(active)starts++;else stops++; }
static int open_port(unsigned *port) {
    int fd=socket(AF_INET,SOCK_DGRAM,0); assert(fd>=0);
    struct sockaddr_in a={.sin_family=AF_INET,.sin_addr={htonl(INADDR_LOOPBACK)}};
    for(;*port<=8093;(*port)++) { a.sin_port=htons(*port); if(!bind(fd,(struct sockaddr*)&a,sizeof a)) return fd; }
    assert(!"Need two free LAN ports for local UDP test"); return -1;
}
int main(void) {
    unsetenv("RA3_LAN_BONJOUR"); unsetenv("RA3_LAN_BROADCAST");
    ra3_lan_init(port_changed,0);
    unsigned pa=8086,pb;
    int a=open_port(&pa); pb=pa+1; int b=open_port(&pb);
    ra3_lan_bound(a);ra3_lan_bound(a);ra3_lan_bound(b);assert(starts==2);
    unsigned char data[476], got[600];for(unsigned i=0;i<sizeof data;i++)data[i]=(i*113)%256;
    struct sockaddr_in to={.sin_family=AF_INET,.sin_port=htons(pb),.sin_addr={INADDR_BROADCAST}};
    assert(ra3_lan_send(a,data,sizeof data,0,&to)==-1 && errno==EHOSTUNREACH);
    ra3_lan_peer("one","same-instance",htonl(INADDR_LOOPBACK),pb,1);
    ra3_lan_peer("same-peer-second-interface","same-instance",htonl(INADDR_LOOPBACK),pb,1);
    ra3_lan_peer("same-peer-other-ip","same-instance",inet_addr("127.0.0.2"),pb,1);
    assert(ra3_lan_send(a,data,sizeof data,0,&to)==sizeof data && broadcasts_sent==0);
    struct sockaddr_in from; socklen_t n=sizeof from;
    { struct pollfd wait={b,POLLIN,0}; assert(poll(&wait,1,1000)==1);
      ssize_t received=ra3_lan_recv(b,got,sizeof got,MSG_DONTWAIT,(struct sockaddr*)&from,&n);
      if(received!=sizeof data)fprintf(stderr,"receive=%zd errno=%d\n",received,errno);
      assert(received==sizeof data); }
    assert(!memcmp(data,got,sizeof data) && ntohs(from.sin_port)==pa);
    assert(ra3_lan_recv(b,got,sizeof got,MSG_DONTWAIT,(struct sockaddr*)&from,&n)<0);
    native_enabled=1; broadcast_error=EHOSTUNREACH;
    assert(ra3_lan_send(a,data,sizeof data,0,&to)==sizeof data && broadcasts_sent==1);
    { struct pollfd wait={b,POLLIN,0}; assert(poll(&wait,1,1000)==1);
      ssize_t received=ra3_lan_recv(b,got,sizeof got,MSG_DONTWAIT,(struct sockaddr*)&from,&n);
      if(received!=sizeof data)fprintf(stderr,"receive=%zd errno=%d\n",received,errno);
      assert(received==sizeof data); }
    ra3_lan_peer("one",NULL,0,0,0);ra3_lan_peer("same-peer-second-interface",NULL,0,0,0);ra3_lan_peer("same-peer-other-ip",NULL,0,0,0);
    assert(ra3_lan_send(a,data,sizeof data,0,&to)<0 && errno==EHOSTUNREACH);
    broadcast_error=0;assert(ra3_lan_send(a,data,sizeof data,0,&to)==sizeof data);
    /* Same-path retransmits survive; opposite-path duplicate pairs collapse. */
    memset(recent,0,sizeof recent);
    assert(!duplicate(b,&from,1,data,sizeof data));
    assert(duplicate(b,&from,0,data,sizeof data));
    assert(!duplicate(b,&from,0,data,sizeof data));
    assert(!duplicate(b,&from,0,data,sizeof data));
    assert(duplicate(b,&from,1,data,sizeof data));
    data[0]^=1;assert(!duplicate(b,&from,1,data,sizeof data));
    from.sin_port++;assert(!duplicate(b,&from,0,data,sizeof data));
    for(int i=0;i<MAX_RECENT;i++)recent[i].time=0;
    assert(!duplicate(b,&from,1,data,sizeof data));
    ra3_lan_closed(a);ra3_lan_closed(b);close(a);close(b);assert(stops==2);
    for(int i=0;i<MAX_PEERS;i++)assert(!peers[i].key[0]);
    puts("PASS: original payload/source port, endpoint dedup, native/fallback errors, cross-path pairs, lifecycle");
}
