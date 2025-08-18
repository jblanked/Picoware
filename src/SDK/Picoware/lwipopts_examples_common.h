#ifndef _LWIPOPTS_EXAMPLE_COMMONH_H
#define _LWIPOPTS_EXAMPLE_COMMONH_H

/**
 * Copyright (c) 2020 Raspberry Pi (Trading) Ltd.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

// Optimized lwIP settings for Pico W to reduce RAM usage
// (see https://www.nongnu.org/lwip/2_1_x/group__lwip__opts.html for details)

// allow override in some examples
#ifndef NO_SYS
#define NO_SYS 1
#endif
// allow override in some examples
#ifndef LWIP_SOCKET
#define LWIP_SOCKET 0
#endif
#if PICO_CYW43_ARCH_POLL
#define MEM_LIBC_MALLOC 1
#else
// MEM_LIBC_MALLOC is incompatible with non polling versions
#define MEM_LIBC_MALLOC 0
#endif
#define MEM_ALIGNMENT 4
#ifndef MEM_SIZE
#define MEM_SIZE 3200
#endif
#define MEMP_NUM_TCP_SEG 8   // Reduced from 32 to save RAM
#define MEMP_NUM_ARP_QUEUE 4 // Reduced from 10 to save RAM
#define PBUF_POOL_SIZE 8     // Reduced from 24 to save RAM
#define LWIP_ARP 1
#define LWIP_ETHERNET 1
#define LWIP_ICMP 1
#define LWIP_RAW 0
#define TCP_WND (4 * TCP_MSS) // Reduced from 8 to save RAM
#define TCP_MSS 1460
#define TCP_SND_BUF (4 * TCP_MSS)                                          // Reduced from 8 to save RAM
#define TCP_SND_QUEUELEN ((2 * (TCP_SND_BUF) + (TCP_MSS - 1)) / (TCP_MSS)) // Reduced
#define LWIP_NETIF_STATUS_CALLBACK 1
#define LWIP_NETIF_LINK_CALLBACK 1
#define LWIP_NETIF_HOSTNAME 1
#define LWIP_NETCONN 0
#define MEM_STATS 0  // Disabled to save RAM
#define SYS_STATS 0  // Disabled to save RAM
#define MEMP_STATS 0 // Disabled to save RAM
#define LINK_STATS 0 // Disabled to save RAM
// #define ETH_PAD_SIZE                2
#define LWIP_CHKSUM_ALGORITHM 3
#define LWIP_DHCP 1
#define LWIP_IPV4 1
#define LWIP_IPV6 0 // Disabled to save significant RAM
#define LWIP_TCP 1
#define LWIP_UDP 1
#define LWIP_DNS 1
#define LWIP_TCP_KEEPALIVE 0 // Disabled to save RAM
#define LWIP_NETIF_TX_SINGLE_PBUF 1
#define DHCP_DOES_ARP_CHECK 0
#define LWIP_DHCP_DOES_ACD_CHECK 0

// Disable all debugging to save significant RAM
#define LWIP_DEBUG 0         // Disabled
#define LWIP_STATS 0         // Disabled
#define LWIP_STATS_DISPLAY 0 // Disabled

// Disable unnecessary features to save RAM
#define LWIP_AUTOIP 0      // Auto IP disabled
#define LWIP_SNMP 0        // SNMP disabled
#define LWIP_IGMP 0        // IGMP disabled
#define PPP_SUPPORT 0      // PPP disabled
#define LWIP_SO_RCVTIMEO 0 // Socket timeouts disabled
#define LWIP_SO_SNDTIMEO 0 // Socket timeouts disabled

// All debug settings disabled for release build
#define ETHARP_DEBUG LWIP_DBG_OFF
#define NETIF_DEBUG LWIP_DBG_OFF
#define PBUF_DEBUG LWIP_DBG_OFF
#define API_LIB_DEBUG LWIP_DBG_OFF
#define API_MSG_DEBUG LWIP_DBG_OFF
#define SOCKETS_DEBUG LWIP_DBG_OFF
#define ICMP_DEBUG LWIP_DBG_OFF
#define INET_DEBUG LWIP_DBG_OFF
#define IP_DEBUG LWIP_DBG_OFF
#define IP_REASS_DEBUG LWIP_DBG_OFF
#define RAW_DEBUG LWIP_DBG_OFF
#define MEM_DEBUG LWIP_DBG_OFF
#define MEMP_DEBUG LWIP_DBG_OFF
#define SYS_DEBUG LWIP_DBG_OFF
#define TCP_DEBUG LWIP_DBG_OFF
#define TCP_INPUT_DEBUG LWIP_DBG_OFF
#define TCP_OUTPUT_DEBUG LWIP_DBG_OFF
#define TCP_RTO_DEBUG LWIP_DBG_OFF
#define TCP_CWND_DEBUG LWIP_DBG_OFF
#define TCP_WND_DEBUG LWIP_DBG_OFF
#define TCP_FR_DEBUG LWIP_DBG_OFF
#define TCP_QLEN_DEBUG LWIP_DBG_OFF
#define TCP_RST_DEBUG LWIP_DBG_OFF
#define UDP_DEBUG LWIP_DBG_OFF
#define TCPIP_DEBUG LWIP_DBG_OFF
#define PPP_DEBUG LWIP_DBG_OFF
#define SLIP_DEBUG LWIP_DBG_OFF
#define DHCP_DEBUG LWIP_DBG_OFF

#endif /* __LWIPOPTS_H__ */
