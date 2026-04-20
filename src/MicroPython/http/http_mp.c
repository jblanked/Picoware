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

#ifndef PRINT
#define PRINT(...) mp_printf(&mp_plat_print, __VA_ARGS__)
#endif

#if MICROPY_PY_LWIP && !defined(NO_QSTR)

/* MicroPython lwIP locking (declared in mpconfigport.h) */
extern void lwip_lock_acquire(void);
extern void lwip_lock_release(void);

#include "lwip/dns.h"
#include "lwip/pbuf.h"
#include "lwip/altcp.h"
#include "lwip/altcp_tcp.h"
#include "lwip/priv/altcp_priv.h"
#include "lwip/mem.h"

#if LWIP_ALTCP_TLS
#include "lwip/altcp_tls.h"
#include "mbedtls/ssl.h"
#include "altcp_tls_mbedtls_structs.h" /* needed for altcp_mbedtls_alloc/free */
#endif

/*
 * lwIP's default altcp_alloc / altcp_free use memp pools
 * (MEMP_ALTCP_PCB).  Those pools are only created when LWIP_ALTCP=1
 * was set at the time memp.c was compiled, which is NOT the case in the
 * stock MicroPython build.  We use the --wrap linker option to redirect
 * the calls in altcp.c to our mem_malloc-based versions.
 */
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

/*
 * Replacements for altcp_tls_mbedtls_mem.c (excluded from the build because
 * its default tls_malloc / tls_free route mbedtls allocations through lwIP's
 * mem_malloc pool, which is only 8 KB — far too small for a TLS handshake).
 *
 * By NOT calling mbedtls_platform_set_calloc_free() in mem_init(), mbedtls
 * keeps its default calloc/free → system heap → plenty of room.
 * The small lwIP-internal structs still go through mem_calloc / mem_free.
 */
#if LWIP_ALTCP_TLS

void altcp_mbedtls_mem_init(void)
{
    /* intentionally empty – let mbedtls use system calloc / free */
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

/*
 * altcp_alloc.c is excluded from the build (QSTR scanner can't handle
 * its mbedtls includes).  Provide altcp_tls_new here instead.
 */
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

/* ── tunables ─────────────────────────────────────────────────── */
#define HTTP_POLL_INTERVAL 30 /* 30 × 0.5 s = 15 s timeout   */

/* ── internal state ───────────────────────────────────────────── */
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

    struct pbuf *response_pbuf; /* chain of received pbufs */

    bool connected;
    bool request_sent;
    bool complete;
    int error;

    unsigned short port;
} http_state_t;

/*
 * Register the state pointer as a GC root so the garbage collector
 * won't free our async state between http_send_request() returning
 * and the lwIP callbacks completing.
 */
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

    m_free(s_state->hostname);
    m_free(s_state->request_buf);
    if (s_state->response_pbuf)
    {
        pbuf_free(s_state->response_pbuf);
        s_state->response_pbuf = NULL;
    }
    m_free(s_state);
    MP_STATE_PORT(http_state_ptr) = NULL;
}

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

static err_t on_connected(void *arg, struct altcp_pcb *pcb, err_t err)
{
    http_state_t *st = (http_state_t *)arg;
    if (err != ERR_OK || !st)
        return err;

    st->connected = true;

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
        /* remote closed the connection — response is complete */
        st->complete = true;
        st->error = ERR_OK;
        return http_close(st);
    }

    /* chain pbufs — no heap allocation in this callback */
    if (st->response_pbuf == NULL)
    {
        st->response_pbuf = p;
    }
    else
    {
        pbuf_cat(st->response_pbuf, p);
    }
    altcp_recved(pcb, p->tot_len);

    return ERR_OK;
}

static err_t on_poll(void *arg, struct altcp_pcb *pcb)
{
    http_state_t *st = (http_state_t *)arg;
    if (st)
    {
        PRINT("HTTP: poll timeout\n");
        st->complete = true;
        st->error = ERR_TIMEOUT;
        return http_close(st);
    }
    return ERR_OK;
}

static void on_err(void *arg, err_t err)
{
    http_state_t *st = (http_state_t *)arg;
    PRINT("HTTP: error callback %d\n", err);
    if (st)
    {
        st->complete = true;
        st->error = err;
        /* PCB is already freed by lwIP when the error callback fires */
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

    /* create PCB — TLS or plain TCP */
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
        /* set SNI so the server sends the right certificate */
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

    /* wire up callbacks */
    altcp_arg(st->pcb, st);
    altcp_err(st->pcb, on_err);
    altcp_recv(st->pcb, on_recv);
    altcp_poll(st->pcb, on_poll, HTTP_POLL_INTERVAL);

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
        /* NULL cert = no server-certificate verification.
         * Must hold the lwIP lock — altcp_mbedtls_ref_entropy asserts it. */
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

    /* ── build the raw HTTP request ─────────────────────────── */
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

    /* default headers (skip if caller already provides them) */
    bool has_ua = headers_len > 0 && header_contains(headers, headers_len, "User-Agent:");
    bool has_accept = headers_len > 0 && header_contains(headers, headers_len, "Accept:");
    bool has_ctype = headers_len > 0 && header_contains(headers, headers_len, "Content-Type:");
    bool has_clen = headers_len > 0 && header_contains(headers, headers_len, "Content-Length:");
    bool has_http_ua = headers_len > 0 && header_contains(headers, headers_len, "HTTP_USER_AGENT:");
    bool has_setting = headers_len > 0 && header_contains(headers, headers_len, "Setting:");

    if (!has_ua)
        off += snprintf(s_state->request_buf + off, req_cap - off,
                        "User-Agent: Raspberry Pi Pico W\r\n");
    if (!has_accept)
        off += snprintf(s_state->request_buf + off, req_cap - off,
                        "Accept: application/json, text/plain, */*\r\n");
    if (!has_http_ua)
        off += snprintf(s_state->request_buf + off, req_cap - off,
                        "HTTP_USER_AGENT: Pico\r\n");
    if (!has_setting)
        off += snprintf(s_state->request_buf + off, req_cap - off,
                        "Setting: X-Flipper-Redirect\r\n");

    if (headers_len > 0)
    {
        memcpy(s_state->request_buf + off, headers, headers_len);
        off += (int)headers_len;
        /* make sure they end with \r\n */
        if (off >= 2 &&
            !(s_state->request_buf[off - 2] == '\r' &&
              s_state->request_buf[off - 1] == '\n'))
        {
            off += snprintf(s_state->request_buf + off, req_cap - off, "\r\n");
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
    return s_state->complete;
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

    /* flatten the pbuf chain into a contiguous buffer */
    size_t total_len = s_state->response_pbuf->tot_len;
    char *raw = (char *)m_malloc(total_len + 1);
    if (!raw)
    {
        http_free_state();
        return false;
    }
    pbuf_copy_partial(s_state->response_pbuf, raw, total_len, 0);
    raw[total_len] = '\0';

    /* locate body after HTTP headers */
    size_t body_len;
    const char *body = find_body(raw, total_len, &body_len);

    /* detect chunked transfer-encoding */
    size_t hdr_len = (size_t)(body - raw);
    bool chunked = header_contains(raw, hdr_len,
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

    m_free(raw);
    http_free_state();
    return true;
}

#else

bool http_send_request(const char *url, const char *method,
                       const char *headers, const char *payload)
{
    (void)url;
    (void)method;
    (void)headers;
    (void)payload;
    PRINT("HTTP: lwIP support not enabled, cannot send request\n");
    return false;
}

bool http_is_finished(void)
{
    PRINT("HTTP: lwIP support not enabled, no request in progress\n");
    return true;
}

bool http_get_http_response(char *buffer, size_t buffer_size)
{
    (void)buffer;
    (void)buffer_size;
    PRINT("HTTP: lwIP support not enabled, no response available\n");
    return false;
}

#endif

/* Register our state pointer as a GC root (scanned by all builds). */
MP_REGISTER_ROOT_POINTER(void *http_state_ptr);