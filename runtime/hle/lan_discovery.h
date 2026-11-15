/* Optional DNS-SD discovery transport. Guest packets and native LAN stay intact. */
#ifndef RA3_LAN_DISCOVERY_H
#define RA3_LAN_DISCOVERY_H
#include <stdint.h>
#include <sys/socket.h>
#include <netinet/in.h>
#define RA3_LAN_SERVICE "_liftingra3._udp"
#ifndef RA3_LAN_GAME_VERSION
#define RA3_LAN_GAME_VERSION "1.12"
#endif
#define RA3_LAN_WIRE "ra3-" RA3_LAN_GAME_VERSION "-v1"
/* Install before the guest starts. Provider operations must be asynchronous. */
void ra3_lan_init(void (*port_changed)(unsigned port, int active), int native_broadcast);
void ra3_lan_bound(int fd);
void ra3_lan_closed(int fd);
/* Provider-owned key identifies one service/address/interface, not a room. */
void ra3_lan_peer(const char *key, const char *instance, uint32_t ipv4, unsigned port, int present);
ssize_t ra3_lan_send(int fd, const void *data, size_t len, int flags,
                     const struct sockaddr_in *to);
ssize_t ra3_lan_recv(int fd, void *data, size_t len, int flags,
                     struct sockaddr *from, socklen_t *fromlen);
#endif
