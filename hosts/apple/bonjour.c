/* System DNS-SD on a private serial queue; no guest memory or HLE calls here. */
#include "lan_discovery.h"
#include <dns_sd.h>
#include <dispatch/dispatch.h>
#include <uuid/uuid.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static dispatch_queue_t queue;
static DNSServiceRef browser, registrations[8];
static char instance[64];
typedef struct Peer {
    struct Peer *next;
    char name[256], domain[256], keys[8][512];
    uint32_t interface;
    unsigned port;
    DNSServiceRef resolve, addresses;
} Peer;
static Peer *peers;
static void clear_addresses(Peer *p) {
    if(p->addresses) { DNSServiceRefDeallocate(p->addresses); p->addresses=NULL; }
    for(int i=0;i<8;i++) if(p->keys[i][0]) { ra3_lan_peer(p->keys[i],NULL,0,0,0); p->keys[i][0]=0; }
}
static void destroy_peer(Peer *p) {
    clear_addresses(p); if(p->resolve) DNSServiceRefDeallocate(p->resolve); free(p);
}
static void address_reply(DNSServiceRef ref,DNSServiceFlags flags,uint32_t interface,
    DNSServiceErrorType error,const char *host,const struct sockaddr *address,uint32_t ttl,void *context) {
    (void)ref;(void)host;(void)ttl;
    Peer *p=context;
    if(error || !address || address->sa_family!=AF_INET) return;
    uint32_t ip=((const struct sockaddr_in*)address)->sin_addr.s_addr;
    char key[512]; snprintf(key,sizeof key,"apple:%u:%s:%08x",interface,p->name,ntohl(ip));
    int slot=-1;
    for(int i=0;i<8;i++) {
        if(!strcmp(p->keys[i],key)) { slot=i; break; }
        if(!p->keys[i][0] && slot<0) slot=i;
    }
    if(slot<0) return;
    if(flags & kDNSServiceFlagsAdd) {
        snprintf(p->keys[slot],sizeof p->keys[slot],"%s",key);
        ra3_lan_peer(key,p->name,ip,p->port,1);
        fprintf(stderr,"[bonjour] peer %s %s:%u\n",p->name,inet_ntoa(((const struct sockaddr_in*)address)->sin_addr),p->port);
    } else {
        ra3_lan_peer(key,NULL,0,0,0);
        if(!strcmp(p->keys[slot],key)) p->keys[slot][0]=0;
    }
}
static void resolved(DNSServiceRef ref,DNSServiceFlags flags,uint32_t interface,
    DNSServiceErrorType error,const char *fullname,const char *host,uint16_t port,
    uint16_t txtlen,const unsigned char *txt,void *context) {
    (void)ref;(void)flags;(void)fullname;
    Peer *p=context; clear_addresses(p);
    if(error) { fprintf(stderr,"[bonjour] resolve error %d\n",error); return; }
    uint8_t len=0; const void *wire=TXTRecordGetValuePtr(txtlen,txt,"wire",&len);
    if(!wire || len!=strlen(RA3_LAN_WIRE) || memcmp(wire,RA3_LAN_WIRE,len)) return;
    p->port=ntohs(port);
    if(p->port<8086 || p->port>8093) return;
    error=DNSServiceGetAddrInfo(&p->addresses,0,interface,kDNSServiceProtocol_IPv4,host,address_reply,p);
    if(!error) error=DNSServiceSetDispatchQueue(p->addresses,queue);
    if(error) { fprintf(stderr,"[bonjour] address error %d\n",error); clear_addresses(p); }
}
static void browse_reply(DNSServiceRef ref,DNSServiceFlags flags,uint32_t interface,
    DNSServiceErrorType error,const char *name,const char *type,const char *domain,void *context) {
    (void)ref;(void)context;
    if(error) { fprintf(stderr,"[bonjour] browse error %d\n",error); return; }
    if(!strncmp(name,instance,strlen(instance))) return;
    Peer **link=&peers; unsigned count=0;
    while(*link && ((*link)->interface!=interface || strcmp((*link)->name,name) || strcmp((*link)->domain,domain)))
        { link=&(*link)->next; count++; }
    if(!(flags & kDNSServiceFlagsAdd)) {
        if(*link) { Peer *p=*link; *link=p->next; destroy_peer(p); } return;
    }
    if(*link || count>=128 || strlen(name)>=256 || strlen(domain)>=256) return;
    Peer *p=calloc(1,sizeof *p); if(!p) return;
    strcpy(p->name,name); strcpy(p->domain,domain); p->interface=interface;
    p->next=peers; peers=p;
    error=DNSServiceResolve(&p->resolve,0,interface,name,type,domain,resolved,p);
    if(!error) error=DNSServiceSetDispatchQueue(p->resolve,queue);
    if(error) { fprintf(stderr,"[bonjour] resolve start error %d\n",error); peers=p->next; destroy_peer(p); }
}
static void registered(DNSServiceRef ref,DNSServiceFlags flags,DNSServiceErrorType error,
    const char *name,const char *type,const char *domain,void *context) {
    (void)ref;(void)flags;(void)type;(void)domain;(void)context;
    fprintf(stderr,"[bonjour] register %s: %d\n",name?name:"?",error);
}
static void port_changed(unsigned port,int active) {
    dispatch_async(queue, ^{
        unsigned index=port-8086;
        if(index>=8) return;
        if(!active) {
            if(registrations[index]) { DNSServiceRefDeallocate(registrations[index]); registrations[index]=NULL; }
            int any=0; for(int i=0;i<8;i++) if(registrations[i]) any=1;
            if(!any) {
                if(browser) { DNSServiceRefDeallocate(browser); browser=NULL; }
                while(peers) { Peer *p=peers; peers=p->next; destroy_peer(p); }
            }
            return;
        }
        if(!browser) {
            DNSServiceErrorType e=DNSServiceBrowse(&browser,0,0,RA3_LAN_SERVICE,"local.",browse_reply,NULL);
            if(!e) e=DNSServiceSetDispatchQueue(browser,queue);
            if(e) { fprintf(stderr,"[bonjour] browse start error %d\n",e); if(browser)DNSServiceRefDeallocate(browser); browser=NULL; }
        }
        if(registrations[index]) return;
        char name[80]; snprintf(name,sizeof name,"%s-%u",instance,port);
        TXTRecordRef txt; TXTRecordCreate(&txt,0,NULL);
        TXTRecordSetValue(&txt,"wire",strlen(RA3_LAN_WIRE),RA3_LAN_WIRE);
        DNSServiceErrorType e=DNSServiceRegister(&registrations[index],0,0,name,RA3_LAN_SERVICE,"local.",NULL,
            htons(port),TXTRecordGetLength(&txt),TXTRecordGetBytesPtr(&txt),registered,NULL);
        TXTRecordDeallocate(&txt);
        if(!e) e=DNSServiceSetDispatchQueue(registrations[index],queue);
        if(e) { fprintf(stderr,"[bonjour] register start error %d\n",e); if(registrations[index])DNSServiceRefDeallocate(registrations[index]); registrations[index]=NULL; }
    });
}
void ra3_apple_bonjour_init(int native_broadcast) {
    uuid_t id; char text[37]; uuid_generate(id); uuid_unparse_lower(id,text);
    snprintf(instance,sizeof instance,"LRA3-%s",text);
    queue=dispatch_queue_create("org.liftingcpath.lan-discovery",DISPATCH_QUEUE_SERIAL);
    ra3_lan_init(port_changed,native_broadcast);
}
