/*
Author: JBlanked
License: GPL-3.0 License
Source: https://github.com/jblanked/Picoware
*/

#include "http_mp.h"
#include "py/misc.h"
#include "py/obj.h"
#include "py/runtime.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <limits.h>
#include "../log/log_mp.h"

#ifndef PRINT
#define PRINT(...) LOG_MESSAGE(__VA_ARGS__)
#endif

#if defined(WAVESHARE_1_43) || defined(WAVESHARE_3_49) || defined(PICOCALC)
#include "../sd/fat32.h"
#define SD_AVAILABLE 1
#elif defined(CARDPUTER)
/* Cardputer uses POSIX VFS */
#include <stdio.h>
#define SD_AVAILABLE 1
#else
#define SD_AVAILABLE 0
#endif

#if defined(CARDPUTER) || (MICROPY_PY_LWIP && !defined(NO_QSTR)) || defined(WAVESHARE_2_06_ESP32S3)
/* URL / HTTP parsing helpers */

static bool parse_url(const char *url,
                      char **hostname_out, char **path_out,
                      unsigned short *port_out, bool *tls_out)
{
    *tls_out = false;
    *port_out = 80;
    *hostname_out = NULL;
    *path_out = NULL;

    const char *p = url;

    if (strncmp(p, "https://", 8) == 0)
    {
        *tls_out = true;
        *port_out = 443;
        p += 8;
    }
    else if (strncmp(p, "http://", 7) == 0)
    {
        p += 7;
    }

    const char *slash = strchr(p, '/');
    size_t host_len = slash ? (size_t)(slash - p) : strlen(p);

    /* check for explicit port */
    const char *colon = (const char *)memchr(p, ':', host_len);
    if (colon)
    {
        size_t name_len = (size_t)(colon - p);
        *hostname_out = (char *)m_malloc(name_len + 1);
        if (!*hostname_out)
            return false;
        memcpy(*hostname_out, p, name_len);
        (*hostname_out)[name_len] = '\0';
        *port_out = (unsigned short)atoi(colon + 1);
    }
    else
    {
        *hostname_out = (char *)m_malloc(host_len + 1);
        if (!*hostname_out)
            return false;
        memcpy(*hostname_out, p, host_len);
        (*hostname_out)[host_len] = '\0';
    }

    if (slash)
    {
        size_t path_len = strlen(slash);
        *path_out = (char *)m_malloc(path_len + 1);
        if (!*path_out)
        {
            m_free(*hostname_out);
            *hostname_out = NULL;
            return false;
        }
        memcpy(*path_out, slash, path_len);
        (*path_out)[path_len] = '\0';
    }
    else
    {
        *path_out = (char *)m_malloc(2);
        if (!*path_out)
        {
            m_free(*hostname_out);
            *hostname_out = NULL;
            return false;
        }
        (*path_out)[0] = '/';
        (*path_out)[1] = '\0';
    }

    return true;
}

static const char *find_body(const char *resp, size_t len, size_t *body_len)
{
    for (size_t i = 0; i + 3 < len; i++)
    {
        if (resp[i] == '\r' && resp[i + 1] == '\n' &&
            resp[i + 2] == '\r' && resp[i + 3] == '\n')
        {
            *body_len = len - (i + 4);
            return resp + i + 4;
        }
    }
    for (size_t i = 0; i + 1 < len; i++)
    {
        if (resp[i] == '\n' && resp[i + 1] == '\n')
        {
            *body_len = len - (i + 2);
            return resp + i + 2;
        }
    }
    *body_len = len;
    return resp;
}

static char *decode_chunked(const char *body, size_t body_len, size_t *out_len)
{
    char *decoded = (char *)m_malloc(body_len + 1);
    if (!decoded)
        return NULL;

    size_t decoded_len = 0;
    size_t pos = 0;

    while (pos < body_len)
    {
        size_t line_end = pos;
        while (line_end < body_len && body[line_end] != '\n')
            line_end++;

        /* parse hex chunk size */
        char size_buf[16];
        size_t slen = line_end - pos;
        if (slen > 0 && body[line_end - 1] == '\r')
            slen--;
        if (slen == 0 || slen >= sizeof(size_buf))
            break;

        memcpy(size_buf, body + pos, slen);
        size_buf[slen] = '\0';

        char *endptr;
        unsigned long chunk_size = strtoul(size_buf, &endptr, 16);
        if (endptr == size_buf || chunk_size == ULONG_MAX)
            break;
        if (chunk_size == 0)
            break;

        pos = line_end + 1;
        if (pos + chunk_size > body_len)
            break;

        memcpy(decoded + decoded_len, body + pos, chunk_size);
        decoded_len += chunk_size;
        pos += chunk_size;

        if (pos < body_len && body[pos] == '\r')
            pos++;
        if (pos < body_len && body[pos] == '\n')
            pos++;
    }

    decoded[decoded_len] = '\0';
    *out_len = decoded_len;
    return decoded;
}

static bool header_contains(const char *headers, size_t hdr_len, const char *needle)
{
    size_t nlen = strlen(needle);
    if (nlen > hdr_len)
        return false;
    for (size_t i = 0; i + nlen <= hdr_len; i++)
    {
        if (strncasecmp(headers + i, needle, nlen) == 0)
            return true;
    }
    return false;
}
#endif

#if (MICROPY_PY_LWIP && !defined(NO_QSTR)) || defined(CARDPUTER) || defined(WAVESHARE_2_06_ESP32S3)

static bool header_name_is(const char *name, size_t len, const char *needle)
{
    size_t nlen = strlen(needle);
    return len == nlen && strncasecmp(name, needle, nlen) == 0;
}

static bool append_header_line(char *buf, size_t cap, int *off,
                               const char *key, size_t key_len,
                               const char *value, size_t value_len)
{
    if (!buf || !off || !key || !value || *off < 0 || (size_t)*off >= cap || key_len == 0)
        return false;

    int n = snprintf(buf + *off, cap - (size_t)*off,
                     "%.*s: %.*s\r\n",
                     (int)key_len, key,
                     (int)value_len, value);
    if (n < 0 || (size_t)n >= cap - (size_t)*off)
        return false;

    *off += n;
    return true;
}

/* Parse JSON-style header object */
static int append_json_object_headers(const char *headers,
                                      char *buf, size_t cap, int off,
                                      bool *has_ua, bool *has_accept,
                                      bool *has_ctype, bool *has_clen,
                                      bool *has_setting)
{
    if (!headers)
        return off;

    const char *p = headers;
    while (*p && isspace((unsigned char)*p))
        p++;
    if (*p != '{')
        return -1;
    p++;

    while (*p)
    {
        while (*p && isspace((unsigned char)*p))
            p++;

        if (*p == '}')
            return off;

        if (*p != '"')
            return -1;
        const char *key = ++p;
        while (*p && *p != '"')
        {
            if (*p == '\\' && p[1] != '\0')
                p += 2;
            else
                p++;
        }
        if (*p != '"')
            return -1;
        size_t key_len = (size_t)(p - key);
        p++;

        while (*p && isspace((unsigned char)*p))
            p++;
        if (*p != ':')
            return -1;
        p++;

        while (*p && isspace((unsigned char)*p))
            p++;
        if (*p != '"')
            return -1;
        const char *value = ++p;
        while (*p && *p != '"')
        {
            if (*p == '\\' && p[1] != '\0')
                p += 2;
            else
                p++;
        }
        if (*p != '"')
            return -1;
        size_t value_len = (size_t)(p - value);
        p++;

        if (buf && !append_header_line(buf, cap, &off, key, key_len, value, value_len))
            return -1;

        if (has_ua && header_name_is(key, key_len, "User-Agent"))
            *has_ua = true;
        if (has_accept && header_name_is(key, key_len, "Accept"))
            *has_accept = true;
        if (has_ctype && header_name_is(key, key_len, "Content-Type"))
            *has_ctype = true;
        if (has_clen && header_name_is(key, key_len, "Content-Length"))
            *has_clen = true;
        if (has_setting && header_name_is(key, key_len, "Setting"))
            *has_setting = true;

        while (*p && isspace((unsigned char)*p))
            p++;
        if (*p == ',')
        {
            p++;
            continue;
        }
        if (*p == '}')
            return off;

        return -1;
    }

    return -1;
}
#endif

/* lwIP altcp implementation (RP2040 / Waveshare) */
#if MICROPY_PY_LWIP && !defined(NO_QSTR)

/* lwIP locking from mpconfigport.h */
extern void lwip_lock_acquire(void);
extern void lwip_lock_release(void);

#include "lwip/dns.h"
#include "lwip/pbuf.h"
#include "lwip/altcp.h"
#include "lwip/altcp_tcp.h"
#include "lwip/priv/altcp_priv.h"
#include "lwip/mem.h"
#include "lwip/sys.h"

#if LWIP_ALTCP_TLS
#include "lwip/altcp_tls.h"
#include "mbedtls/ssl.h"
#include "altcp_tls_mbedtls_structs.h" /* needed for altcp_mbedtls_alloc/free */
#endif

/* lwIP altcp pools not compiled, use --wrap to mem_malloc */
struct altcp_pcb *
__wrap_altcp_alloc(void)
{
    struct altcp_pcb *ret = (struct altcp_pcb *)mem_malloc(sizeof(struct altcp_pcb));
    if (ret != NULL)
    {
        memset(ret, 0, sizeof(struct altcp_pcb));
    }
    return ret;
}

void __wrap_altcp_free(struct altcp_pcb *conn)
{
    if (conn != NULL)
    {
        if (conn->fns && conn->fns->dealloc)
        {
            conn->fns->dealloc(conn);
        }
        mem_free(conn);
    }
}

/* Replace altcp_tls_mbedtls_mem.c — mbedtls uses system heap */
#if LWIP_ALTCP_TLS

void altcp_mbedtls_mem_init(void)
{
    /* mbedtls uses system calloc/free */
}

altcp_mbedtls_state_t *altcp_mbedtls_alloc(void *conf)
{
    altcp_mbedtls_state_t *ret =
        (altcp_mbedtls_state_t *)mem_calloc(1, sizeof(altcp_mbedtls_state_t));
    if (ret != NULL)
    {
        ret->conf = conf;
    }
    return ret;
}

void altcp_mbedtls_free(void *conf, altcp_mbedtls_state_t *state)
{
    LWIP_UNUSED_ARG(conf);
    if (state != NULL)
    {
        mem_free(state);
    }
}

void *altcp_mbedtls_alloc_config(size_t size)
{
    if ((mem_size_t)size != size)
    {
        return NULL; /* overflow */
    }
    return mem_calloc(1, (mem_size_t)size);
}

void altcp_mbedtls_free_config(void *item)
{
    if (item != NULL)
    {
        mem_free(item);
    }
}

#endif /* LWIP_ALTCP_TLS */

/* altcp_alloc.c excluded; provide altcp_tls_new here */
#if LWIP_ALTCP_TLS
struct altcp_pcb *
altcp_tls_new(struct altcp_tls_config *config, u8_t ip_type)
{
    struct altcp_pcb *inner_conn, *ret;
    LWIP_UNUSED_ARG(ip_type);

    inner_conn = altcp_tcp_new_ip_type(ip_type);
    if (inner_conn == NULL)
    {
        return NULL;
    }
    ret = altcp_tls_wrap(config, inner_conn);
    if (ret == NULL)
    {
        altcp_close(inner_conn);
    }
    return ret;
}
#endif /* LWIP_ALTCP_TLS */

/* tunables */
#define HTTP_POLL_INTERVAL 30 /* 30 × 0.5 s = 15 s timeout   */

/* internal state */
typedef struct
{
    struct altcp_pcb *pcb;
#if LWIP_ALTCP_TLS
    struct altcp_tls_config *tls_config;
#endif
    ip_addr_t server_ip;

    char *hostname;
    char *request_buf;
    size_t request_len;

    struct pbuf *response_pbuf; /* received pbuf chain */

    bool connected;
    bool request_sent;
    bool complete;
    bool file_saved;
    int error;

    u32_t last_recv_ms;

    unsigned short port;
    char *destination_path;

#if SD_AVAILABLE
    fat32_file_t dl_file;
    bool dl_file_open;
    bool dl_headers_done;
    bool dl_chunked;
#endif
} http_state_t;

/* Register state as GC root */
#define s_state ((http_state_t *)MP_STATE_PORT(http_state_ptr))

static err_t on_connected(void *arg, struct altcp_pcb *pcb, err_t err);
static err_t on_recv(void *arg, struct altcp_pcb *pcb, struct pbuf *p, err_t err);
static err_t on_poll(void *arg, struct altcp_pcb *pcb);
static void on_err(void *arg, err_t err);
static void on_dns(const char *name, const ip_addr_t *addr, void *arg);

static err_t http_close(http_state_t *st)
{
    err_t err = ERR_OK;
    if (!st)
        return err;

    st->complete = true;

    if (st->pcb)
    {
        altcp_arg(st->pcb, NULL);
        altcp_poll(st->pcb, NULL, 0);
        altcp_recv(st->pcb, NULL);
        altcp_err(st->pcb, NULL);

        err = altcp_close(st->pcb);
        if (err != ERR_OK)
        {
            PRINT("HTTP: close failed %d, aborting\n", err);
            altcp_abort(st->pcb);
            err = ERR_ABRT;
        }
        st->pcb = NULL;
    }

#if LWIP_ALTCP_TLS
    if (st->tls_config)
    {
        altcp_tls_free_config(st->tls_config);
        st->tls_config = NULL;
    }
#endif

    return err;
}

static void http_free_state(void)
{
    if (!s_state)
        return;

    if (s_state->pcb)
    {
        lwip_lock_acquire();
        http_close(s_state);
        lwip_lock_release();
    }

#if LWIP_ALTCP_TLS
    if (s_state->tls_config)
    {
        altcp_tls_free_config(s_state->tls_config);
        s_state->tls_config = NULL;
    }
#endif

#if SD_AVAILABLE
    if (s_state->dl_file_open)
    {
        fat32_close(&s_state->dl_file);
        s_state->dl_file_open = false;
    }
#endif
    m_free(s_state->hostname);
    m_free(s_state->request_buf);
    m_free(s_state->destination_path);
    if (s_state->response_pbuf)
    {
        pbuf_free(s_state->response_pbuf);
        s_state->response_pbuf = NULL;
    }
    m_free(s_state);
    MP_STATE_PORT(http_state_ptr) = NULL;
}

static err_t on_connected(void *arg, struct altcp_pcb *pcb, err_t err)
{
    http_state_t *st = (http_state_t *)arg;
    if (err != ERR_OK || !st)
        return err;

    st->connected = true;
    st->last_recv_ms = sys_now();

    altcp_poll(pcb, on_poll, HTTP_POLL_INTERVAL);

    err = altcp_write(st->pcb, st->request_buf, st->request_len, TCP_WRITE_FLAG_COPY);
    if (err != ERR_OK)
    {
        PRINT("HTTP: write error %d\n", err);
        return http_close(st);
    }

    altcp_output(st->pcb);
    st->request_sent = true;
    return ERR_OK;
}

static err_t on_recv(void *arg, struct altcp_pcb *pcb, struct pbuf *p, err_t err)
{
    http_state_t *st = (http_state_t *)arg;
    if (!st)
    {
        if (p)
            pbuf_free(p);
        return ERR_ARG;
    }

    if (!p)
    {
        /* remote closed, response complete */
        st->complete = true;
        st->error = ERR_OK;
        return http_close(st);
    }

    st->last_recv_ms = sys_now();

    u16_t recv_len = p->tot_len;

#if SD_AVAILABLE
    if (st->destination_path)
    {
        if (!st->dl_headers_done)
        {
            /* Accumulate pbufs until \r\n\r\n */
            if (st->response_pbuf == NULL)
                st->response_pbuf = p;
            else
                pbuf_cat(st->response_pbuf, p);

            size_t total = st->response_pbuf->tot_len;
            int32_t body_start = -1;

            for (size_t i = 0; i + 3 < total; i++)
            {
                if (pbuf_get_at(st->response_pbuf, (u16_t)i) == '\r' &&
                    pbuf_get_at(st->response_pbuf, (u16_t)(i + 1)) == '\n' &&
                    pbuf_get_at(st->response_pbuf, (u16_t)(i + 2)) == '\r' &&
                    pbuf_get_at(st->response_pbuf, (u16_t)(i + 3)) == '\n')
                {
                    body_start = (int32_t)(i + 4);
                    break;
                }
            }

            if (body_start >= 0)
            {
                /* Copy header bytes for chunked detect */
                char hdr[512];
                u16_t hdr_copy = ((u16_t)body_start < (u16_t)(sizeof(hdr) - 1))
                                     ? (u16_t)body_start
                                     : (u16_t)(sizeof(hdr) - 1);
                pbuf_copy_partial(st->response_pbuf, hdr, hdr_copy, 0);
                hdr[hdr_copy] = '\0';
                st->dl_chunked = header_contains(hdr, hdr_copy,
                                                 "transfer-encoding: chunked");

                size_t initial_body_len = total - (size_t)body_start;

                if (!st->dl_chunked)
                {
                    /* Create and open file */
                    fat32_delete(st->destination_path);
                    fat32_error_t ferr = fat32_create(&st->dl_file, st->destination_path);
                    if (ferr == FAT32_OK)
                        ferr = fat32_open(&st->dl_file, st->destination_path);

                    if (ferr != FAT32_OK)
                    {
                        PRINT("HTTP: failed to create/open dl file (err %d)\n", (int)ferr);
                    }
                    else
                    {
                        st->dl_file_open = true;

                        if (initial_body_len > 0)
                        {
                            uint8_t tmp[512];
                            size_t offset = (size_t)body_start;
                            while (offset < total)
                            {
                                u16_t to_copy = ((total - offset) < sizeof(tmp))
                                                    ? (u16_t)(total - offset)
                                                    : (u16_t)sizeof(tmp);
                                pbuf_copy_partial(st->response_pbuf, tmp,
                                                  to_copy, (u16_t)offset);
                                size_t written = 0;
                                fat32_write(&st->dl_file, tmp, to_copy, &written);
                                offset += to_copy;
                            }
                        }
                    }

                    /* Free header pbuf chain */
                    pbuf_free(st->response_pbuf);
                    st->response_pbuf = NULL;
                }
                /* Leave pbuf intact for decode */
                st->dl_headers_done = true;
            }
            /* else: \r\n\r\n not yet seen, keep accumulating. */
        }
        else if (!st->dl_chunked)
        {
            if (st->dl_file_open)
            {
                uint8_t tmp[512];
                size_t offset = 0;
                size_t total = p->tot_len;
                while (offset < total)
                {
                    u16_t to_copy = ((total - offset) < sizeof(tmp))
                                        ? (u16_t)(total - offset)
                                        : (u16_t)sizeof(tmp);
                    pbuf_copy_partial(p, tmp, to_copy, (u16_t)offset);
                    size_t written = 0;
                    fat32_write(&st->dl_file, tmp, to_copy, &written);
                    offset += to_copy;
                }
            }
            pbuf_free(p);
        }
        else
        {
            if (st->response_pbuf == NULL)
                st->response_pbuf = p;
            else
                pbuf_cat(st->response_pbuf, p);
        }

        altcp_recved(pcb, recv_len);
        return ERR_OK;
    }
#endif /* SD_AVAILABLE */

    if (st->response_pbuf == NULL)
        st->response_pbuf = p;
    else
        pbuf_cat(st->response_pbuf, p);

    altcp_recved(pcb, recv_len);

    return ERR_OK;
}

static err_t on_poll(void *arg, struct altcp_pcb *pcb)
{
    http_state_t *st = (http_state_t *)arg;

    if (!st || !st->pcb)
        return ERR_OK;

    PRINT("HTTP: on_poll st=%p pcb=%p complete=%d\n",
          (void *)st, (void *)st->pcb, (int)st->complete);

#if SD_AVAILABLE
    if (st->destination_path && st->dl_file_open && !st->dl_chunked)
    {
        u32_t idle_ms = sys_now() - st->last_recv_ms;
        u32_t timeout_ms = (u32_t)HTTP_POLL_INTERVAL * 500U;
        if (idle_ms < timeout_ms)
        {
            return ERR_OK;
        }
        st->error = ERR_OK;
        altcp_abort(st->pcb);
        st->pcb = NULL;
        st->complete = true;
        return ERR_ABRT;
    }
#endif

    u32_t idle_ms = sys_now() - st->last_recv_ms;
    u32_t timeout_ms = (u32_t)HTTP_POLL_INTERVAL * 500U;
    if (idle_ms < timeout_ms)
    {
        return ERR_OK;
    }
    PRINT("HTTP: poll timeout — no data for %u ms\n", (unsigned)idle_ms);
    st->complete = true;
    st->error = ERR_TIMEOUT;
    return http_close(st);
}

static void on_err(void *arg, err_t err)
{
    http_state_t *st = (http_state_t *)arg;
    PRINT("HTTP: error callback %d\n", err);
    if (st)
    {
        st->complete = true;
        st->error = err;
        /* PCB freed by lwIP */
        st->pcb = NULL;
#if LWIP_ALTCP_TLS
        if (st->tls_config)
        {
            altcp_tls_free_config(st->tls_config);
            st->tls_config = NULL;
        }
#endif
    }
}

static void on_dns(const char *name, const ip_addr_t *addr, void *arg)
{
    http_state_t *st = (http_state_t *)arg;
    if (!st)
        return;

    if (!addr)
    {
        PRINT("HTTP: DNS failed for %s\n", name);
        st->complete = true;
        st->error = ERR_VAL;
        return;
    }

    st->server_ip = *addr;

    if (st->port == 443)
    {
#if LWIP_ALTCP_TLS
        st->pcb = altcp_tls_new(st->tls_config, IPADDR_TYPE_ANY);
        if (!st->pcb)
        {
            PRINT("HTTP: TLS PCB alloc failed\n");
            st->complete = true;
            st->error = ERR_MEM;
            return;
        }
        /* Set SNI for server cert */
        mbedtls_ssl_context *ssl =
            (mbedtls_ssl_context *)altcp_tls_context(st->pcb);
        if (ssl)
            mbedtls_ssl_set_hostname(ssl, st->hostname);
#else
        PRINT("HTTP: HTTPS not supported in this build\n");
        st->complete = true;
        st->error = ERR_VAL;
        return;
#endif
    }
    else
    {
        st->pcb = altcp_tcp_new();
        if (!st->pcb)
        {
            PRINT("HTTP: TCP PCB alloc failed\n");
            st->complete = true;
            st->error = ERR_MEM;
            return;
        }
    }

    /* Wire callbacks */
    altcp_arg(st->pcb, st);
    altcp_err(st->pcb, on_err);
    altcp_recv(st->pcb, on_recv);

    err_t cerr = altcp_connect(st->pcb, addr, st->port, on_connected);
    if (cerr != ERR_OK)
    {
        PRINT("HTTP: connect error %d\n", cerr);
        http_close(st);
        st->complete = true;
        st->error = cerr;
    }
}

bool http_send_request(const char *url, const char *method,
                       const char *headers, const char *payload)
{
    /* clean up any previous request */
    if (s_state)
        http_free_state();

    char *hostname = NULL;
    char *path = NULL;
    unsigned short port;
    bool use_tls;

    if (!parse_url(url, &hostname, &path, &port, &use_tls))
    {
        PRINT("HTTP: URL parse failed\n");
        return false;
    }

    MP_STATE_PORT(http_state_ptr) = m_malloc0(sizeof(http_state_t));
    if (!s_state)
    {
        m_free(hostname);
        m_free(path);
        PRINT("HTTP: state alloc failed\n");
        return false;
    }

    s_state->hostname = hostname;
    s_state->port = port;

    /* TLS config (HTTPS) */
    if (use_tls)
    {
#if LWIP_ALTCP_TLS
        /* NULL cert, hold lwIP lock for entropy */
        lwip_lock_acquire();
        s_state->tls_config = altcp_tls_create_config_client(NULL, 0);
        lwip_lock_release();
        if (!s_state->tls_config)
        {
            PRINT("HTTP: TLS config failed\n");
            m_free(path);
            http_free_state();
            return false;
        }
#else
        PRINT("HTTP: HTTPS not supported in this build\n");
        m_free(path);
        http_free_state();
        return false;
#endif
    }

    /* Build raw HTTP request */
    size_t method_len = strlen(method);
    size_t path_len = strlen(path);
    size_t host_len = strlen(hostname);
    size_t headers_len = headers ? strlen(headers) : 0;
    size_t payload_len = payload ? strlen(payload) : 0;

    size_t req_cap = method_len + path_len + host_len +
                     headers_len + payload_len + 512;

    s_state->request_buf = (char *)m_malloc(req_cap);
    if (!s_state->request_buf)
    {
        m_free(path);
        http_free_state();
        PRINT("HTTP: request buffer alloc failed\n");
        return false;
    }

    int off = snprintf(s_state->request_buf, req_cap,
                       "%s %s HTTP/1.1\r\n"
                       "Host: %s\r\n"
                       "Connection: close\r\n",
                       method, path, hostname);
    m_free(path);

    /* Detect JSON object headers */
    bool headers_is_json_object = false;
    if (headers_len > 0)
    {
        const char *h = headers;
        while (*h && isspace((unsigned char)*h))
            h++;
        headers_is_json_object = (*h == '{');
    }

    /* Default headers unless caller provides */
    bool has_ua = false;
    bool has_accept = false;
    bool has_ctype = false;
    bool has_clen = false;
    bool has_setting = false;

    if (headers_len > 0)
    {
        if (headers_is_json_object)
        {
            int parse_ret = append_json_object_headers(headers,
                                                       NULL,
                                                       0,
                                                       0,
                                                       &has_ua,
                                                       &has_accept,
                                                       &has_ctype,
                                                       &has_clen,
                                                       &has_setting);
            if (parse_ret < 0)
            {
                has_ua = header_contains(headers, headers_len, "User-Agent:");
                has_accept = header_contains(headers, headers_len, "Accept:");
                has_ctype = header_contains(headers, headers_len, "Content-Type:");
                has_clen = header_contains(headers, headers_len, "Content-Length:");
                has_setting = header_contains(headers, headers_len, "Setting:");
            }
        }
        else
        {
            has_ua = header_contains(headers, headers_len, "User-Agent:");
            has_accept = header_contains(headers, headers_len, "Accept:");
            has_ctype = header_contains(headers, headers_len, "Content-Type:");
            has_clen = header_contains(headers, headers_len, "Content-Length:");
            has_setting = header_contains(headers, headers_len, "Setting:");
        }
    }

    if (!has_ua)
        off += snprintf(s_state->request_buf + off, req_cap - off,
                        "User-Agent: Raspberry Pi Pico W\r\n");
    if (!has_accept)
        off += snprintf(s_state->request_buf + off, req_cap - off,
                        "Accept: application/json, text/plain, */*\r\n");
    if (!has_setting)
        off += snprintf(s_state->request_buf + off, req_cap - off,
                        "Setting: X-Flipper-Redirect\r\n");

    if (headers_len > 0)
    {
        if (headers_is_json_object)
        {
            int parsed_off = append_json_object_headers(headers,
                                                        s_state->request_buf,
                                                        req_cap,
                                                        off,
                                                        NULL,
                                                        NULL,
                                                        NULL,
                                                        NULL,
                                                        NULL);
            if (parsed_off >= 0)
            {
                off = parsed_off;
            }
            else
            {
                PRINT("HTTP: invalid JSON-style headers, using raw headers\n");
                memcpy(s_state->request_buf + off, headers, headers_len);
                off += (int)headers_len;
                if (off >= 2 &&
                    !(s_state->request_buf[off - 2] == '\r' &&
                      s_state->request_buf[off - 1] == '\n'))
                {
                    off += snprintf(s_state->request_buf + off, req_cap - off, "\r\n");
                }
            }
        }
        else
        {
            memcpy(s_state->request_buf + off, headers, headers_len);
            off += (int)headers_len;
            /* Ensure \r\n termination */
            if (off >= 2 &&
                !(s_state->request_buf[off - 2] == '\r' &&
                  s_state->request_buf[off - 1] == '\n'))
            {
                off += snprintf(s_state->request_buf + off, req_cap - off, "\r\n");
            }
        }
    }

    /* body */
    if (payload_len > 0)
    {
        if (!has_ctype)
            off += snprintf(s_state->request_buf + off, req_cap - off,
                            "Content-Type: application/json\r\n");
        if (!has_clen)
            off += snprintf(s_state->request_buf + off, req_cap - off,
                            "Content-Length: %u\r\n", (unsigned)payload_len);
        off += snprintf(s_state->request_buf + off, req_cap - off, "\r\n");
        memcpy(s_state->request_buf + off, payload, payload_len);
        off += (int)payload_len;
    }
    else
    {
        off += snprintf(s_state->request_buf + off, req_cap - off, "\r\n");
    }

    s_state->request_len = (size_t)off;

    lwip_lock_acquire();

    ip_addr_t resolved;
    err_t err = dns_gethostbyname(hostname, &resolved, on_dns, s_state);

    if (err == ERR_OK)
    {
        /* already cached */
        on_dns(hostname, &resolved, s_state);
    }
    else if (err != ERR_INPROGRESS)
    {
        PRINT("HTTP: DNS error %d\n", err);
        lwip_lock_release();
        http_free_state();
        return false;
    }

    lwip_lock_release();
    return true;
}

bool http_is_finished(void)
{
    if (!s_state)
        return true; /* no request in progress */
    if (!s_state->complete)
        return false;

#if SD_AVAILABLE
    if (s_state->destination_path && !s_state->file_saved)
    {
        s_state->file_saved = true;

        if (s_state->error != ERR_OK)
        {
            PRINT("HTTP: file download error %d\n", s_state->error);
            http_free_state();
            return true;
        }

        if (!s_state->dl_chunked && s_state->dl_file_open)
        {
            PRINT("HTTP: file download complete, %u bytes written\n",
                  (unsigned)s_state->dl_file.position);
            fat32_close(&s_state->dl_file);
            s_state->dl_file_open = false;
            http_free_state();
            return true;
        }

        if (!s_state->response_pbuf)
        {
            PRINT("HTTP: file download: no response data\n");
            http_free_state();
            return true;
        }

        size_t total_len = s_state->response_pbuf->tot_len;
        char *raw = (char *)m_malloc(total_len + 1);
        if (!raw)
        {
            PRINT("HTTP: file download alloc failed\n");
            http_free_state();
            return true;
        }
        pbuf_copy_partial(s_state->response_pbuf, raw, total_len, 0);
        raw[total_len] = '\0';

        size_t body_len;
        const char *body = find_body(raw, total_len, &body_len);
        size_t hdr_len = (size_t)(body - raw);
        bool chunked = header_contains(raw, hdr_len, "transfer-encoding: chunked");

        const char *write_data = body;
        size_t write_len = body_len;
        char *decoded = NULL;

        if (chunked)
        {
            size_t decoded_len = 0;
            decoded = decode_chunked(body, body_len, &decoded_len);
            if (decoded)
            {
                write_data = decoded;
                write_len = decoded_len;
            }
        }

        fat32_delete(s_state->destination_path);

        fat32_file_t file;
        fat32_error_t ferr = fat32_create(&file, s_state->destination_path);
        if (ferr != FAT32_OK)
        {
            PRINT("HTTP: failed to create file '%s' (err %d)\n",
                  s_state->destination_path, (int)ferr);
        }
        else if ((ferr = fat32_open(&file, s_state->destination_path)) != FAT32_OK)
        {
            PRINT("HTTP: failed to open file '%s' after create (err %d)\n",
                  s_state->destination_path, (int)ferr);
        }
        else
        {
            size_t written = 0;
            const size_t chunk_size = (1024 * 4);
            while (written < write_len)
            {
                size_t to_write = write_len - written;
                if (to_write > chunk_size)
                    to_write = chunk_size;
                size_t bytes_written = 0;
                ferr = fat32_write(&file, write_data + written, to_write, &bytes_written);
                if (ferr != FAT32_OK || bytes_written == 0)
                {
                    PRINT("HTTP: file write error %d at offset %u\n",
                          (int)ferr, (unsigned)written);
                    break;
                }
                written += bytes_written;
            }
            fat32_close(&file);
        }

        m_free(decoded);
        m_free(raw);
        http_free_state();
    }
#endif /* SD_AVAILABLE */

    return true;
}

bool http_get_http_response(char *buffer, size_t buffer_size)
{
    if (!s_state || !s_state->complete)
        return false;

    if (!s_state->response_pbuf || s_state->error != ERR_OK)
    {
        PRINT("HTTP: no response or error %d\n", s_state ? s_state->error : -1);
        http_free_state();
        return false;
    }

    /* Flatten pbuf chain */
    size_t total_len = s_state->response_pbuf->tot_len;
    char *raw = (char *)m_malloc(total_len + 1);
    if (!raw)
    {
        http_free_state();
        return false;
    }
    pbuf_copy_partial(s_state->response_pbuf, raw, total_len, 0);
    raw[total_len] = '\0';

    /* Locate body after headers */
    size_t body_len;
    const char *body = find_body(raw, total_len, &body_len);

    /* detect chunked transfer-encoding */
    size_t hdr_len = (size_t)(body - raw);
    bool chunked = header_contains(raw, hdr_len, "transfer-encoding: chunked");

    if (chunked)
    {
        size_t decoded_len;
        char *decoded = decode_chunked(body, body_len, &decoded_len);
        if (decoded)
        {
            size_t copy_len = decoded_len < buffer_size - 1 ? decoded_len : buffer_size - 1;
            memcpy(buffer, decoded, copy_len);
            buffer[copy_len] = '\0';
            m_free(decoded);
        }
        else
        {
            size_t copy_len = body_len < buffer_size - 1 ? body_len : buffer_size - 1;
            memcpy(buffer, body, copy_len);
            buffer[copy_len] = '\0';
        }
    }
    else
    {
        size_t copy_len = body_len < buffer_size - 1 ? body_len : buffer_size - 1;
        memcpy(buffer, body, copy_len);
        buffer[copy_len] = '\0';
    }

    m_free(raw);
    http_free_state();
    return true;
}

bool http_file_download(const char *url, const char *destination_path)
{
#if !SD_AVAILABLE
    PRINT("HTTP: SD not available, cannot download file\n");
    (void)url;
    (void)destination_path;
    return false;
#else
    if (!url || !destination_path)
        return false;

    if (!http_send_request(url, "GET",
                           "Accept: application/octet-stream, */*\r\n"
                           "Content-Type: application/octet-stream\r\n",
                           NULL))
    {
        PRINT("HTTP: file download request failed to start\n");
        return false;
    }

    size_t path_len = strlen(destination_path);
    s_state->destination_path = (char *)m_malloc(path_len + 1);
    if (!s_state->destination_path)
    {
        PRINT("HTTP: destination_path alloc failed\n");
        http_free_state();
        return false;
    }
    memcpy(s_state->destination_path, destination_path, path_len + 1);

    return true;
#endif /* SD_AVAILABLE */
}

/* Cardputer BSD sockets + FreeRTOS */
#elif defined(CARDPUTER)

#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "lwip/dns.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

/* mbedtls over BSD socket */
#include "mbedtls/ssl.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/error.h"
#include "mbedtls/net_sockets.h"
#include "mbedtls/platform.h"

#define HTTP_RESPONSE_INITIAL_SIZE (4 * 1024)
#define HTTP_RESPONSE_MAX_SIZE (64 * 1024)
#define HTTP_TASK_ERR_NO_RESPONSE (-0x7000)

/* Avoid MicroPython heap in task logs */
#define HTTP_TASK_LOG(...)   \
    do                       \
    {                        \
        printf(__VA_ARGS__); \
    } while (0)

/* mbedtls objects for TLS */
typedef struct
{
    mbedtls_net_context net;
    mbedtls_ssl_context ssl;
    mbedtls_ssl_config conf;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context ctr_drbg;
} http_tls_ctx_t;

typedef struct
{
    char *hostname;
    unsigned short port;
    bool use_tls;

    char *request_buf;
    size_t request_len;

    char *response_data;
    size_t response_data_len;
    size_t response_data_cap;

    volatile bool complete;
    volatile bool success;
    volatile int task_error;

    int sock;
    http_tls_ctx_t *tls_ctx;
    TaskHandle_t task_handle;

    char *destination_path;

#if SD_AVAILABLE
    bool dl_headers_done;
    bool dl_chunked;
    FILE *dl_file;
#endif
} http_state_cardputer_t;

#define s_state ((http_state_cardputer_t *)MP_STATE_PORT(http_state_ptr))

static void http_task_finish(http_state_cardputer_t *st, bool success)
{
    if (st)
    {
        st->success = success;
        st->task_handle = NULL;
        st->complete = true;
    }
    vTaskDelete(NULL);
}

static void http_tls_cleanup(http_state_cardputer_t *st)
{
    if (!st || !st->tls_ctx)
        return;

    /* mbedtls_net_free closes fd */
    st->sock = -1;
    mbedtls_ssl_free(&st->tls_ctx->ssl);
    mbedtls_ssl_config_free(&st->tls_ctx->conf);
    mbedtls_ctr_drbg_free(&st->tls_ctx->ctr_drbg);
    mbedtls_entropy_free(&st->tls_ctx->entropy);
    mbedtls_net_free(&st->tls_ctx->net);
    free(st->tls_ctx);
    st->tls_ctx = NULL;
}

static bool http_alloc_response_buffer(http_state_cardputer_t *st)
{
    if (!st)
        return false;
    if (st->response_data)
        return true;

    st->response_data_cap = HTTP_RESPONSE_INITIAL_SIZE + 1;
    st->response_data = (char *)malloc(st->response_data_cap);
    if (!st->response_data)
    {
        st->response_data_cap = 0;
        return false;
    }
    st->response_data[0] = '\0';
    return true;
}

static bool http_resolve_ipv4(const char *hostname, unsigned short port,
                              struct sockaddr_in *out_addr, int *err_out)
{
    if (err_out)
        *err_out = EAI_FAIL;

    if (!hostname || !out_addr)
        return false;

    memset(out_addr, 0, sizeof(*out_addr));
    out_addr->sin_family = AF_INET;
    out_addr->sin_port = htons(port);

    struct addrinfo hints, *res = NULL;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;

    int ret = EAI_FAIL;
    for (int attempt = 0; attempt < 3; attempt++)
    {
        ret = getaddrinfo(hostname, NULL, &hints, &res);
        if (ret == 0 && res && res->ai_addr)
        {
            out_addr->sin_addr = ((struct sockaddr_in *)res->ai_addr)->sin_addr;
            freeaddrinfo(res);
            if (err_out)
                *err_out = 0;
            return true;
        }
        if (res)
        {
            freeaddrinfo(res);
            res = NULL;
        }
        if (attempt < 2)
            vTaskDelay(pdMS_TO_TICKS(250));
    }

    /* Fallback when getaddrinfo is flaky */
    struct hostent *he = gethostbyname(hostname);
    if (he && he->h_addr_list && he->h_addr_list[0] && he->h_length == sizeof(out_addr->sin_addr))
    {
        memcpy(&out_addr->sin_addr, he->h_addr_list[0], (size_t)he->h_length);
        if (err_out)
            *err_out = 0;
        return true;
    }

    if (err_out)
        *err_out = ret;
    return false;
}

/* FreeRTOS blocking I/O task */
static void http_task_fn(void *arg)
{
    http_state_cardputer_t *st = (http_state_cardputer_t *)arg;
    if (!st)
    {
        vTaskDelete(NULL);
        return;
    }

    size_t total = 0;
    ssize_t n;
    int ret;
    char chunk[2048];

    if (st->use_tls)
    {
        /* HTTPS via mbedtls */
        /* Resolve DNS and connect */
        struct sockaddr_in dest_addr;
        int dns_err = 0;
        if (!http_resolve_ipv4(st->hostname, st->port, &dest_addr, &dns_err))
        {
            st->task_error = dns_err;
            HTTP_TASK_LOG("HTTP: DNS failed for '%s' (err %d)\n", st->hostname, dns_err);
            http_task_finish(st, false);
            return;
        }

        st->sock = socket(AF_INET, SOCK_STREAM, 0);
        if (st->sock < 0)
        {
            st->task_error = st->sock;
            http_task_finish(st, false);
            return;
        }

        struct timeval timeout = {.tv_sec = 10, .tv_usec = 0};
        setsockopt(st->sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
        setsockopt(st->sock, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));

        ret = connect(st->sock, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
        if (ret != 0)
        {
            st->task_error = ret;
            close(st->sock);
            st->sock = -1;
            http_task_finish(st, false);
            return;
        }

        /* Init mbedtls over socket */
        st->tls_ctx = (http_tls_ctx_t *)calloc(1, sizeof(http_tls_ctx_t));
        if (!st->tls_ctx)
        {
            st->task_error = -1;
            close(st->sock);
            st->sock = -1;
            http_task_finish(st, false);
            return;
        }

        mbedtls_net_init(&st->tls_ctx->net);
        st->tls_ctx->net.fd = st->sock;

        mbedtls_ssl_init(&st->tls_ctx->ssl);
        mbedtls_ssl_config_init(&st->tls_ctx->conf);
        mbedtls_entropy_init(&st->tls_ctx->entropy);
        mbedtls_ctr_drbg_init(&st->tls_ctx->ctr_drbg);

        ret = mbedtls_ctr_drbg_seed(&st->tls_ctx->ctr_drbg,
                                    mbedtls_entropy_func,
                                    &st->tls_ctx->entropy, NULL, 0);
        if (ret != 0)
        {
            st->task_error = ret;
            HTTP_TASK_LOG("HTTP: mbedtls_ctr_drbg_seed failed (%d)\n", ret);
            goto tls_cleanup;
        }

        ret = mbedtls_ssl_config_defaults(&st->tls_ctx->conf,
                                          MBEDTLS_SSL_IS_CLIENT,
                                          MBEDTLS_SSL_TRANSPORT_STREAM,
                                          MBEDTLS_SSL_PRESET_DEFAULT);
        if (ret != 0)
        {
            st->task_error = ret;
            HTTP_TASK_LOG("HTTP: mbedtls_ssl_config_defaults failed (%d)\n", ret);
            goto tls_cleanup;
        }

        /* No cert verification (same as RP2040) */
        mbedtls_ssl_conf_authmode(&st->tls_ctx->conf, MBEDTLS_SSL_VERIFY_NONE);
        mbedtls_ssl_conf_rng(&st->tls_ctx->conf,
                             mbedtls_ctr_drbg_random,
                             &st->tls_ctx->ctr_drbg);

        ret = mbedtls_ssl_setup(&st->tls_ctx->ssl, &st->tls_ctx->conf);
        if (ret != 0)
        {
            st->task_error = ret;
            HTTP_TASK_LOG("HTTP: mbedtls_ssl_setup failed (%d)\n", ret);
            goto tls_cleanup;
        }

        ret = mbedtls_ssl_set_hostname(&st->tls_ctx->ssl, st->hostname);
        if (ret != 0)
        {
            st->task_error = ret;
            HTTP_TASK_LOG("HTTP: mbedtls_ssl_set_hostname failed (%d)\n", ret);
            goto tls_cleanup;
        }

        mbedtls_ssl_set_bio(&st->tls_ctx->ssl, &st->tls_ctx->net,
                            mbedtls_net_send, mbedtls_net_recv, NULL);

        /* TLS handshake */
        while ((ret = mbedtls_ssl_handshake(&st->tls_ctx->ssl)) != 0)
        {
            if (ret != MBEDTLS_ERR_SSL_WANT_READ &&
                ret != MBEDTLS_ERR_SSL_WANT_WRITE)
            {
                st->task_error = ret;
                HTTP_TASK_LOG("HTTP: TLS handshake failed (%d)\n", ret);
                goto tls_cleanup;
            }
        }

        /* Send full request (may be partial) */
        size_t sent_total = 0;
        while (sent_total < st->request_len)
        {
            ret = mbedtls_ssl_write(&st->tls_ctx->ssl,
                                    (const unsigned char *)st->request_buf + sent_total,
                                    st->request_len - sent_total);
            if (ret > 0)
            {
                sent_total += (size_t)ret;
                continue;
            }
            if (ret == 0)
            {
                st->task_error = MBEDTLS_ERR_SSL_CONN_EOF;
                HTTP_TASK_LOG("HTTP: TLS write returned 0\n");
                goto tls_cleanup;
            }
            if (ret != MBEDTLS_ERR_SSL_WANT_READ &&
                ret != MBEDTLS_ERR_SSL_WANT_WRITE)
            {
                st->task_error = ret;
                HTTP_TASK_LOG("HTTP: TLS write failed (%d)\n", ret);
                goto tls_cleanup;
            }
        }

        if (!http_alloc_response_buffer(st))
        {
            st->task_error = -1;
            HTTP_TASK_LOG("HTTP: response buffer alloc failed\n");
            goto tls_cleanup;
        }

        /* Receive response.
         * Retry WANT_READ/WANT_WRITE briefly */
        TickType_t no_data_start = xTaskGetTickCount();
        const TickType_t no_data_timeout_ticks = pdMS_TO_TICKS(12000);

        for (;;)
        {
            n = mbedtls_ssl_read(&st->tls_ctx->ssl,
                                 (unsigned char *)chunk, sizeof(chunk));

            if (n > 0)
            {
                no_data_start = xTaskGetTickCount();
                if (total + (size_t)n + 1 > st->response_data_cap)
                {
                    size_t new_cap = st->response_data_cap * 2;
                    if (new_cap < total + (size_t)n + 1)
                        new_cap = total + (size_t)n + 1;
                    if (new_cap > HTTP_RESPONSE_MAX_SIZE + 1)
                        break;
                    char *new_buf = (char *)realloc(st->response_data, new_cap);
                    if (!new_buf)
                        break;
                    st->response_data = new_buf;
                    st->response_data_cap = new_cap;
                }
                memcpy(st->response_data + total, chunk, (size_t)n);
                total += (size_t)n;
                continue;
            }

            if (n == 0 || n == MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY)
            {
                break;
            }

            if (n == MBEDTLS_ERR_SSL_WANT_READ ||
                n == MBEDTLS_ERR_SSL_WANT_WRITE)
            {
                if (total > 0)
                {
                    /* Have bytes, skip WANT */
                    break;
                }
                if ((xTaskGetTickCount() - no_data_start) >= no_data_timeout_ticks)
                {
                    st->task_error = (int)n;
                    HTTP_TASK_LOG("HTTP: TLS read no-data timeout (%d)\n", (int)n);
                    goto tls_cleanup;
                }
                vTaskDelay(pdMS_TO_TICKS(10));
                continue;
            }

            if (n == MBEDTLS_ERR_SSL_TIMEOUT)
            {
                if (total > 0)
                    break;
                if ((xTaskGetTickCount() - no_data_start) >= no_data_timeout_ticks)
                {
                    st->task_error = (int)n;
                    HTTP_TASK_LOG("HTTP: TLS read timeout with no data\n");
                    goto tls_cleanup;
                }
                continue;
            }

            st->task_error = (int)n;
            HTTP_TASK_LOG("HTTP: TLS read failed (%d)\n", (int)n);
            goto tls_cleanup;
        }

        if (total == 0)
        {
            st->task_error = HTTP_TASK_ERR_NO_RESPONSE;
            HTTP_TASK_LOG("HTTP: TLS no response data\n");
            goto tls_cleanup;
        }

        if (st->response_data)
            st->response_data[total] = '\0';
        st->response_data_len = total;
        st->success = true;
        st->task_error = 0;

    tls_cleanup:
        http_tls_cleanup(st);
        http_task_finish(st, st->success);
        return;
    }

    /* plain HTTP via BSD sockets */
    struct sockaddr_in dest_addr;
    int dns_err = 0;
    if (!http_resolve_ipv4(st->hostname, st->port, &dest_addr, &dns_err))
    {
        st->task_error = dns_err;
        HTTP_TASK_LOG("HTTP: DNS resolution failed for '%s' (err %d)\n",
                      st->hostname, dns_err);
        http_task_finish(st, false);
        return;
    }

    st->sock = socket(AF_INET, SOCK_STREAM, 0);
    if (st->sock < 0)
    {
        st->task_error = st->sock;
        HTTP_TASK_LOG("HTTP: socket() failed\n");
        http_task_finish(st, false);
        return;
    }

    struct timeval timeout = {
        .tv_sec = 10,
        .tv_usec = 0,
    };
    setsockopt(st->sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    setsockopt(st->sock, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));

    ret = connect(st->sock, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
    if (ret != 0)
    {
        st->task_error = ret;
        HTTP_TASK_LOG("HTTP: connect() to %s:%u failed (err %d)\n",
                      st->hostname, st->port, ret);
        close(st->sock);
        st->sock = -1;
        http_task_finish(st, false);
        return;
    }

    size_t sent_total = 0;
    while (sent_total < st->request_len)
    {
        n = send(st->sock, st->request_buf + sent_total,
                 st->request_len - sent_total, 0);
        if (n > 0)
        {
            sent_total += (size_t)n;
            continue;
        }
        if (n == 0)
        {
            st->task_error = HTTP_TASK_ERR_NO_RESPONSE;
            HTTP_TASK_LOG("HTTP: send() returned 0\n");
            close(st->sock);
            st->sock = -1;
            http_task_finish(st, false);
            return;
        }
        st->task_error = (int)n;
        HTTP_TASK_LOG("HTTP: send() failed (err %d)\n", (int)n);
        close(st->sock);
        st->sock = -1;
        http_task_finish(st, false);
        return;
    }

    if (!http_alloc_response_buffer(st))
    {
        st->task_error = -1;
        HTTP_TASK_LOG("HTTP: response buffer alloc failed\n");
        close(st->sock);
        st->sock = -1;
        http_task_finish(st, false);
        return;
    }

    while ((n = recv(st->sock, chunk, sizeof(chunk), 0)) > 0)
    {
        if (total + (size_t)n + 1 > st->response_data_cap)
        {
            size_t new_cap = st->response_data_cap * 2;
            if (new_cap < total + (size_t)n + 1)
                new_cap = total + (size_t)n + 1;
            if (new_cap > HTTP_RESPONSE_MAX_SIZE + 1)
            {
                HTTP_TASK_LOG("HTTP: response exceeds max size (%u)\n",
                              HTTP_RESPONSE_MAX_SIZE);
                break;
            }
            char *new_buf = (char *)realloc(st->response_data, new_cap);
            if (!new_buf)
                break;
            st->response_data = new_buf;
            st->response_data_cap = new_cap;
        }
        memcpy(st->response_data + total, chunk, (size_t)n);
        total += (size_t)n;
    }

    if (n < 0)
    {
        st->task_error = (int)n;
        HTTP_TASK_LOG("HTTP: recv() failed (err %d)\n", (int)n);
        close(st->sock);
        st->sock = -1;
        http_task_finish(st, false);
        return;
    }

    if (total == 0)
    {
        st->task_error = HTTP_TASK_ERR_NO_RESPONSE;
        HTTP_TASK_LOG("HTTP: no response data\n");
        close(st->sock);
        st->sock = -1;
        http_task_finish(st, false);
        return;
    }

    if (st->response_data)
        st->response_data[total] = '\0';
    st->response_data_len = total;
    st->task_error = 0;

    close(st->sock);
    st->sock = -1;
    http_task_finish(st, true);
}

static void http_free_state(void)
{
    if (!s_state)
        return;
    if (s_state->task_handle)
    {
        if (s_state->task_handle != xTaskGetCurrentTaskHandle())
            vTaskDelete(s_state->task_handle);
        s_state->task_handle = NULL;
    }
    http_tls_cleanup(s_state);
    if (s_state->sock >= 0)
    {
        close(s_state->sock);
        s_state->sock = -1;
    }
    m_free(s_state->hostname);
    m_free(s_state->request_buf);
    free(s_state->response_data);
    m_free(s_state->destination_path);
    m_free(s_state);
    MP_STATE_PORT(http_state_ptr) = NULL;
}

bool http_send_request(const char *url, const char *method,
                       const char *headers, const char *payload)
{
    /* Clean up any previous request */
    http_free_state();

    char *hostname = NULL;
    char *path = NULL;
    unsigned short port;
    bool use_tls;

    if (!parse_url(url, &hostname, &path, &port, &use_tls))
    {
        PRINT("HTTP: URL parse failed\n");
        return false;
    }

    MP_STATE_PORT(http_state_ptr) =
        (http_state_cardputer_t *)m_malloc0(sizeof(http_state_cardputer_t));
    if (!s_state)
    {
        m_free(hostname);
        m_free(path);
        return false;
    }

    s_state->hostname = hostname;
    s_state->port = port;
    s_state->use_tls = use_tls;
    s_state->sock = -1;
    s_state->tls_ctx = NULL;
    s_state->response_data = NULL;
    s_state->response_data_cap = 0;
    s_state->response_data_len = 0;

    /* Build HTTP request */
    size_t method_len = strlen(method);
    size_t path_len = strlen(path);
    size_t host_len = strlen(hostname);
    size_t headers_len = headers ? strlen(headers) : 0;
    size_t payload_len = payload ? strlen(payload) : 0;
    size_t req_cap = method_len + path_len + host_len +
                     headers_len + payload_len + 512;

    bool headers_is_json_object = false;
    if (headers_len > 0)
    {
        const char *h = headers;
        while (*h && isspace((unsigned char)*h))
            h++;
        headers_is_json_object = (*h == '{');
    }

    s_state->request_buf = (char *)m_malloc(req_cap);
    if (!s_state->request_buf)
    {
        m_free(path);
        m_free(hostname);
        m_free(s_state);
        MP_STATE_PORT(http_state_ptr) = NULL;
        return false;
    }

    int off = snprintf(s_state->request_buf, req_cap,
                       "%s %s HTTP/1.1\r\n"
                       "Host: %s\r\n"
                       "Connection: close\r\n",
                       method, path, hostname);
    m_free(path);

    bool has_ua = false;
    bool has_accept = false;
    bool has_ctype = false;
    bool has_clen = false;
    bool has_setting = false;

    if (headers_len > 0)
    {
        if (headers_is_json_object)
        {
            int parse_ret = append_json_object_headers(headers,
                                                       NULL,
                                                       0,
                                                       0,
                                                       &has_ua,
                                                       &has_accept,
                                                       &has_ctype,
                                                       &has_clen,
                                                       &has_setting);
            if (parse_ret < 0)
            {
                has_ua = header_contains(headers, headers_len, "User-Agent:");
                has_accept = header_contains(headers, headers_len, "Accept:");
                has_ctype = header_contains(headers, headers_len, "Content-Type:");
                has_clen = header_contains(headers, headers_len, "Content-Length:");
                has_setting = header_contains(headers, headers_len, "Setting:");
            }
        }
        else
        {
            has_ua = header_contains(headers, headers_len, "User-Agent:");
            has_accept = header_contains(headers, headers_len, "Accept:");
            has_ctype = header_contains(headers, headers_len, "Content-Type:");
            has_clen = header_contains(headers, headers_len, "Content-Length:");
            has_setting = header_contains(headers, headers_len, "Setting:");
        }
    }

    if (!has_ua)
        off += snprintf(s_state->request_buf + off, req_cap - off,
                        "User-Agent: Raspberry Pi Pico W\r\n");
    if (!has_accept)
        off += snprintf(s_state->request_buf + off, req_cap - off,
                        "Accept: application/json, text/plain, */*\r\n");
    if (!has_setting)
        off += snprintf(s_state->request_buf + off, req_cap - off,
                        "Setting: X-Flipper-Redirect\r\n");

    if (headers_len > 0)
    {
        if (headers_is_json_object)
        {
            int parsed_off = append_json_object_headers(headers,
                                                        s_state->request_buf,
                                                        req_cap,
                                                        off,
                                                        NULL,
                                                        NULL,
                                                        NULL,
                                                        NULL,
                                                        NULL);
            if (parsed_off >= 0)
            {
                off = parsed_off;
            }
            else
            {
                PRINT("HTTP: invalid JSON-style headers, using raw headers\n");
                memcpy(s_state->request_buf + off, headers, headers_len);
                off += (int)headers_len;
                if (off >= 2 &&
                    !(s_state->request_buf[off - 2] == '\r' &&
                      s_state->request_buf[off - 1] == '\n'))
                {
                    off += snprintf(s_state->request_buf + off, req_cap - off, "\r\n");
                }
            }
        }
        else
        {
            memcpy(s_state->request_buf + off, headers, headers_len);
            off += (int)headers_len;
            if (off >= 2 &&
                !(s_state->request_buf[off - 2] == '\r' &&
                  s_state->request_buf[off - 1] == '\n'))
            {
                off += snprintf(s_state->request_buf + off, req_cap - off, "\r\n");
            }
        }
    }

    if (payload_len > 0)
    {
        if (!has_ctype)
            off += snprintf(s_state->request_buf + off, req_cap - off,
                            "Content-Type: application/json\r\n");
        if (!has_clen)
            off += snprintf(s_state->request_buf + off, req_cap - off,
                            "Content-Length: %u\r\n", (unsigned)payload_len);
        off += snprintf(s_state->request_buf + off, req_cap - off, "\r\n");
        memcpy(s_state->request_buf + off, payload, payload_len);
        off += (int)payload_len;
    }
    else
    {
        off += snprintf(s_state->request_buf + off, req_cap - off, "\r\n");
    }
    s_state->request_len = (size_t)off;

    /* Spawn FreeRTOS task for blocking I/O
     * 16 KB stack — mbedtls TLS handshake needs significant stack
     * for entropy collection, certificate parsing, and key exchange.
     * 4 KB was not enough and caused silent reboots during HTTPS. */
    BaseType_t task_ret = xTaskCreate(
        http_task_fn,
        "http_task",
        16384,
        s_state,
        2,
        &s_state->task_handle);

    if (task_ret != pdPASS)
    {
        PRINT("HTTP: failed to create task\n");
        m_free(s_state->request_buf);
        m_free(s_state->hostname);
        m_free(s_state);
        MP_STATE_PORT(http_state_ptr) = NULL;
        return false;
    }

    return true;
}

bool http_is_finished(void)
{
    if (!s_state)
        return true;

    if (!s_state->complete)
        return false;

#if SD_AVAILABLE
    if (s_state->destination_path && s_state->success)
    {
        /* Write response body to file */
        size_t hdr_len;
        const char *body_start = find_body(s_state->response_data,
                                           s_state->response_data_len,
                                           &hdr_len);
        size_t body_len = s_state->response_data_len - (size_t)(body_start - s_state->response_data);
        bool chunked = header_contains(s_state->response_data,
                                       (size_t)(body_start - s_state->response_data),
                                       "transfer-encoding: chunked");

        const char *write_data = body_start;
        size_t write_len = body_len;
        char *decoded = NULL;

        if (chunked)
        {
            size_t decoded_len;
            decoded = decode_chunked(body_start, body_len, &decoded_len);
            if (decoded)
            {
                write_data = decoded;
                write_len = decoded_len;
            }
        }

        FILE *f = fopen(s_state->destination_path, "wb");
        if (f)
        {
            size_t written = fwrite(write_data, 1, write_len, f);
            fclose(f);
            PRINT("HTTP: file download complete, %u bytes written to '%s'\n",
                  (unsigned)written, s_state->destination_path);
        }
        else
        {
            PRINT("HTTP: failed to open '%s' for writing\n",
                  s_state->destination_path);
        }

        m_free(decoded);
    }
#endif /* SD_AVAILABLE */

    return true;
}

bool http_get_http_response(char *buffer, size_t buffer_size)
{
    if (!s_state || !s_state->complete)
        return false;

    if (buffer_size == 0)
        return false;

    buffer[0] = '\0';

    if (!s_state->success || !s_state->response_data || s_state->response_data_len == 0)
    {
        if (!s_state->success)
        {
            if (s_state->task_error == EAI_FAIL)
            {
                PRINT("HTTP: request failed (DNS resolution failed, err %d)\n",
                      (int)s_state->task_error);
            }
            else
            {
                char err_buf[96] = {0};
                mbedtls_strerror((int)s_state->task_error, err_buf, sizeof(err_buf));
                PRINT("HTTP: request failed (task err %d, %s)\n",
                      (int)s_state->task_error,
                      err_buf[0] ? err_buf : "unknown");
            }
        }
        http_free_state();
        return false;
    }

    /* Extract body from full HTTP response */
    size_t body_offset;
    const char *body = find_body(s_state->response_data,
                                 s_state->response_data_len,
                                 &body_offset);
    size_t body_len = s_state->response_data_len - (size_t)(body - s_state->response_data);

    /* Handle chunked transfer-encoding */
    size_t hdr_len = (size_t)(body - s_state->response_data);
    bool chunked = header_contains(s_state->response_data, hdr_len,
                                   "transfer-encoding: chunked");

    if (chunked)
    {
        size_t decoded_len;
        char *decoded = decode_chunked(body, body_len, &decoded_len);
        if (decoded)
        {
            size_t copy_len = decoded_len < buffer_size - 1 ? decoded_len : buffer_size - 1;
            memcpy(buffer, decoded, copy_len);
            buffer[copy_len] = '\0';
            m_free(decoded);
        }
        else
        {
            size_t copy_len = body_len < buffer_size - 1 ? body_len : buffer_size - 1;
            memcpy(buffer, body, copy_len);
            buffer[copy_len] = '\0';
        }
    }
    else
    {
        size_t copy_len = body_len < buffer_size - 1 ? body_len : buffer_size - 1;
        memcpy(buffer, body, copy_len);
        buffer[copy_len] = '\0';
    }

    /* Free state after retrieving response */
    http_free_state();

    return true;
}

bool http_file_download(const char *url, const char *destination_path)
{
#if !SD_AVAILABLE
    PRINT("HTTP: SD not available, cannot download file\n");
    (void)url;
    (void)destination_path;
    return false;
#else
    if (!url || !destination_path)
        return false;

    if (!http_send_request(url, "GET",
                           "Accept: application/octet-stream, */*\r\n",
                           NULL))
    {
        PRINT("HTTP: file download request failed to start\n");
        return false;
    }

    size_t path_len = strlen(destination_path);
    s_state->destination_path = (char *)m_malloc(path_len + 1);
    if (!s_state->destination_path)
    {
        http_free_state();
        return false;
    }
    memcpy(s_state->destination_path, destination_path, path_len + 1);

    return true;
#endif /* SD_AVAILABLE */
}

/* fallback: stubs for boards without networking */
#else

bool http_send_request(const char *url, const char *method,
                       const char *headers, const char *payload)
{
    (void)url;
    (void)method;
    (void)headers;
    (void)payload;
    PRINT("HTTP: networking not enabled, cannot send request\n");
    return false;
}

bool http_file_download(const char *url, const char *destination_path)
{
    (void)url;
    (void)destination_path;
    PRINT("HTTP: networking not enabled, cannot download file\n");
    return false;
}

bool http_is_finished(void)
{
    PRINT("HTTP: networking not enabled, no request in progress\n");
    return true;
}

bool http_get_http_response(char *buffer, size_t buffer_size)
{
    (void)buffer;
    (void)buffer_size;
    PRINT("HTTP: networking not enabled, no response available\n");
    return false;
}

#endif

/* Register our state pointer as a GC root (scanned by all builds). */
MP_REGISTER_ROOT_POINTER(void *http_state_ptr);
