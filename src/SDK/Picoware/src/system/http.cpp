#include "../system/http.hpp"
#include "../system/helpers.hpp"
#include "../system/certs.hpp"
#ifdef CYW43_WL_GPIO_LED_PIN
#include "pico/async_context.h"
#include "pico/cyw43_arch.h"
#include "lwip/dns.h"
#include "lwip/tcp.h"
#include "lwip/altcp.h"
#include "lwip/altcp_tcp.h"
#if LWIP_ALTCP_TLS
#include "lwip/altcp_tls.h"
#include "mbedtls/ssl.h"
#endif
#include "lwip/err.h"
#else
#include <limits.h>
#endif
#include <cstring>
#include <cstdio>
#include <map>

struct SimpleHTTPRequest
{
    std::string hostname;
    std::string url;
    std::string method;
    std::string payload;
    unsigned short port;
    bool complete;
    int result;
    std::string response_data;
};

struct async_context;
struct pbuf;
struct altcp_pcb;

#ifdef CYW43_WL_GPIO_LED_PIN

struct http_request_state
{
    SimpleHTTPRequest req_data;
    struct altcp_pcb *pcb;
#if LWIP_ALTCP_TLS
    struct altcp_tls_config *tls_config;
#else
    void *tls_config; // placeholder for when TLS is disabled
#endif
    ip_addr_t server_ip;
    bool connected;
    bool request_sent;
    bool complete;
    int error;
    std::string http_request;
    std::string response_data;
};

static http_request_state *current_http_state = nullptr;

static err_t http_client_close(http_request_state *state)
{
    err_t err = ERR_OK;

    if (state)
    {
        state->complete = true;

        if (state->pcb != NULL)
        {
            altcp_arg(state->pcb, NULL);
            altcp_poll(state->pcb, NULL, 0);
            altcp_recv(state->pcb, NULL);
            altcp_err(state->pcb, NULL);

            err = altcp_close(state->pcb);
            if (err != ERR_OK)
            {
                printf("HTTP: close failed %d, calling abort\n", err);
                altcp_abort(state->pcb);
                err = ERR_ABRT;
            }
            state->pcb = NULL;
        }

        if (state->tls_config != NULL)
        {
#if LWIP_ALTCP_TLS
            altcp_tls_free_config((struct altcp_tls_config *)state->tls_config);
#endif
            state->tls_config = NULL;
        }
    }

    return err;
}

static err_t http_client_connected(void *arg, struct altcp_pcb *pcb, err_t err)
{
    if (err != ERR_OK || !arg)
    {
        return err;
    }

    http_request_state *state = (http_request_state *)arg;
    state->connected = true;

    // Send HTTP request
    err = altcp_write(state->pcb, state->http_request.c_str(), state->http_request.length(), TCP_WRITE_FLAG_COPY);
    if (err != ERR_OK)
    {
        printf("HTTP: Error writing data, err=%d\n", err);
        return http_client_close(state);
    }

    state->request_sent = true;
    return ERR_OK;
}

static err_t http_client_recv(void *arg, struct altcp_pcb *pcb, struct pbuf *p, err_t err)
{
    if (!arg)
    {
        if (p)
            pbuf_free(p);
        return ERR_ARG;
    }

    http_request_state *state = (http_request_state *)arg;

    if (!p)
    {
        state->req_data.complete = true;
        state->req_data.result = ERR_OK;
        return http_client_close(state);
    }

    if (p->tot_len > 0)
    {
        // Copy data from pbuf to our response string
        char *buf = new char[p->tot_len + 1];
        if (!buf)
        {
            printf("HTTP: Failed to allocate %u bytes for response buffer\n", p->tot_len + 1);
            pbuf_free(p);
            return ERR_MEM;
        }

        pbuf_copy_partial(p, buf, p->tot_len, 0);
        buf[p->tot_len] = '\0';

        state->response_data += std::string(buf);
        // Store final response data
        state->req_data.response_data = state->response_data;

        delete[] buf;

        // Tell lwIP we processed this data
        altcp_recved(pcb, p->tot_len);
    }

    pbuf_free(p);
    return ERR_OK;
}

static err_t http_client_poll(void *arg, struct altcp_pcb *pcb)
{
    if (arg)
    {
        http_request_state *state = (http_request_state *)arg;
        printf("HTTP: Poll timeout\n");
        state->error = PICO_ERROR_TIMEOUT;
        state->req_data.complete = true;
        state->req_data.result = ERR_TIMEOUT;
        return http_client_close(state);
    }
    return ERR_OK;
}

static void http_client_err(void *arg, err_t err)
{
    printf("HTTP: Error callback, err=%d\n", err);
    if (arg)
    {
        http_request_state *state = (http_request_state *)arg;
        state->req_data.complete = true;
        state->req_data.result = err;
        state->error = err;

        // Important: When an error callback is invoked, the PCB is already freed by lwIP
        // So we must NOT call altcp_close or altcp_abort on it
        // Just mark it as NULL and clean up TLS config if needed
        state->pcb = NULL;

        if (state->tls_config != NULL)
        {
#if LWIP_ALTCP_TLS
            altcp_tls_free_config((struct altcp_tls_config *)state->tls_config);
#endif
            state->tls_config = NULL;
        }
    }
}

static void http_client_dns_found(const char *hostname, const ip_addr_t *ipaddr, void *arg)
{
    if (!arg)
        return;

    http_request_state *state = (http_request_state *)arg;

    if (!ipaddr)
    {
        printf("HTTP: DNS resolution failed\n");
        state->req_data.complete = true;
        state->req_data.result = ERR_VAL;
        return;
    }

    state->server_ip = *ipaddr;

    // Create altcp PCB (with or without TLS)
    if (state->req_data.port == 443 || state->tls_config != NULL)
    {
#if LWIP_ALTCP_TLS
        // HTTPS
        state->pcb = altcp_tls_new((struct altcp_tls_config *)state->tls_config, IPADDR_TYPE_ANY);
        if (!state->pcb)
        {
            printf("HTTP: Failed to create TLS PCB\n");
            state->req_data.complete = true;
            state->req_data.result = ERR_MEM;
            return;
        }

        // Set SNI (Server Name Indication)
        mbedtls_ssl_context *ssl = (mbedtls_ssl_context *)altcp_tls_context(state->pcb);
        if (ssl)
        {
            mbedtls_ssl_set_hostname(ssl, hostname);
        }

#else
        // TLS requested but not available
        printf("HTTP: HTTPS not supported in this build\n");
        state->req_data.complete = true;
        state->req_data.result = ERR_VAL;
        return;
#endif
    }
    else
    {
        // HTTP
        state->pcb = altcp_tcp_new();
        if (!state->pcb)
        {
            printf("HTTP: Failed to create TCP PCB\n");
            state->req_data.complete = true;
            state->req_data.result = ERR_MEM;
            return;
        }
    }

    // Set callbacks
    altcp_arg(state->pcb, state);
    altcp_err(state->pcb, http_client_err);
    altcp_recv(state->pcb, http_client_recv);
    altcp_poll(state->pcb, http_client_poll, 30); // 30 * 0.5s = 15s timeout

    // Connect
    err_t connect_err = altcp_connect(state->pcb, ipaddr, state->req_data.port, http_client_connected);
    if (connect_err != ERR_OK)
    {
        printf("HTTP: Connect failed, err=%d\n", connect_err);
        http_client_close(state);
        state->req_data.complete = true;
        state->req_data.result = connect_err;
    }
}

static bool http_client_request(const std::string &hostname, const std::string &url,
                                const std::string &method, const std::string &data,
                                unsigned short port, SimpleHTTPRequest *req,
                                const std::map<std::string, std::string> &headers = {})
{
    if (current_http_state != nullptr)
    {
        printf("HTTP: Request already in progress\n");
        return false;
    }

    // Allocate state
    current_http_state = new http_request_state();
    if (!current_http_state)
    {
        printf("HTTP: Failed to allocate state\n");
        return false;
    }

    memset(current_http_state, 0, sizeof(http_request_state));
    current_http_state->req_data = *req; // Copy the request data

    // Create TLS config for HTTPS
    if (port == 443)
    {
#if LWIP_ALTCP_TLS
        const uint8_t ca_cert[] = LETS_ENCRYPT_ROOT_CA;
        current_http_state->tls_config = altcp_tls_create_config_client(ca_cert, sizeof(ca_cert));
        if (!current_http_state->tls_config)
        {
            printf("HTTP: Failed to create TLS config with certificates\n");
            // Fallback to no certificates
            current_http_state->tls_config = altcp_tls_create_config_client(NULL, 0);
            if (!current_http_state->tls_config)
            {
                printf("HTTP: Failed to create fallback TLS config\n");
                delete current_http_state;
                current_http_state = nullptr;
                return false;
            }
        }
#else
        printf("HTTP: HTTPS requested but TLS not supported in this build\n");
        delete current_http_state;
        current_http_state = nullptr;
        return false;
#endif
    }

    // Build HTTP request
    std::string request = method + " " + url + " HTTP/1.1\r\n";
    request += "Host: " + hostname + "\r\n";
    request += "Connection: close\r\n";

    // Set default headers if not overridden by custom headers
    bool has_user_agent = headers.find("User-Agent") != headers.end();
    bool has_accept = headers.find("Accept") != headers.end();
    bool has_content_type = headers.find("Content-Type") != headers.end();
    bool has_content_length = headers.find("Content-Length") != headers.end();

    if (!has_user_agent)
    {
        request += "User-Agent: Pico/1.0\r\n";
    }
    if (!has_accept)
    {
        request += "Accept: application/json, text/plain, */*\r\n";
    }

    // Add custom headers
    for (const auto &header : headers)
    {
        request += header.first + ": " + header.second + "\r\n";
    }

    if (!data.empty())
    {
        if (!has_content_type)
        {
            request += "Content-Type: application/x-www-form-urlencoded\r\n";
        }
        if (!has_content_length)
        {
            request += "Content-Length: " + std::to_string(data.length()) + "\r\n";
        }
    }

    request += "\r\n";
    if (!data.empty())
    {
        request += data;
    }

    current_http_state->http_request = request;

    // Start DNS resolution
    cyw43_arch_lwip_begin();

    ip_addr_t server_ip;
    err_t err = dns_gethostbyname(hostname.c_str(), &server_ip, http_client_dns_found, current_http_state);

    if (err == ERR_OK)
    {
        // Host is in DNS cache
        http_client_dns_found(hostname.c_str(), &server_ip, current_http_state);
    }
    else if (err != ERR_INPROGRESS)
    {
        printf("HTTP: DNS resolution error, err=%d\n", err);
        http_client_close(current_http_state);
        delete current_http_state;
        current_http_state = nullptr;
        cyw43_arch_lwip_end();
        return false;
    }

    cyw43_arch_lwip_end();
    return true;
}

#endif

HTTP::HTTP()
{
    // nothing to do
}

HTTP::~HTTP()
{
    clearAsyncResponse();
}

void HTTP::clearAsyncResponse()
{
    async_response = "";
    async_request_complete = false;
    async_request_in_progress = false;
#ifdef CYW43_WL_GPIO_LED_PIN
    delete current_http_state;
    current_http_state = nullptr;
#endif
    state = IDLE;
}

std::string HTTP::del(const std::string &url, const std::map<std::string, std::string> &headers)
{
    return request("DELETE", url, headers);
}

bool HTTP::delAsync(const std::string &url, const std::map<std::string, std::string> &headers)
{
    return requestAsync("DELETE", url, headers);
}

std::string HTTP::extractHttpBody(const std::string &httpResponse)
{
    if (httpResponse.empty())
    {
        return "";
    }

    // Find the end of headers (empty line)
    size_t header_end = httpResponse.find("\r\n\r\n");
    if (header_end == std::string::npos)
    {
        header_end = httpResponse.find("\n\n");
        if (header_end == std::string::npos)
        {
            return httpResponse; // No headers found, return as-is
        }
        header_end += 2;
    }
    else
    {
        header_end += 4;
    }

    std::string body = httpResponse.substr(header_end);

    // Check for chunked encoding
    std::string headers = httpResponse.substr(0, header_end);
    std::transform(headers.begin(), headers.end(), headers.begin(), ::tolower);

    if (headers.find("transfer-encoding: chunked") != std::string::npos)
    {
        // Decode chunked encoding
        std::string decoded_body;
        size_t pos = 0;

        while (pos < body.length())
        {
            // Find chunk size line
            size_t size_end = body.find('\n', pos);
            if (size_end == std::string::npos)
                break;

            std::string size_line = body.substr(pos, size_end - pos);
            // Remove \r if present
            if (!size_line.empty() && size_line.back() == '\r')
            {
                size_line.pop_back();
            }

            // Parse chunk size (hexadecimal)
            size_t chunk_size = 0;
            char *endptr;
            chunk_size = strtoul(size_line.c_str(), &endptr, 16);

            // Check if conversion was successful
            if (endptr == size_line.c_str() || chunk_size == ULONG_MAX)
            {
                break; // Invalid chunk size
            }

            if (chunk_size == 0)
            {
                break; // End of chunks
            }

            pos = size_end + 1; // Move past the size line

            // Extract chunk data
            if (pos + chunk_size <= body.length())
            {
                decoded_body += body.substr(pos, chunk_size);
                pos += chunk_size;

                // Skip trailing CRLF
                if (pos < body.length() && body[pos] == '\r')
                    pos++;
                if (pos < body.length() && body[pos] == '\n')
                    pos++;
            }
            else
            {
                break; // Incomplete chunk
            }
        }

        return decoded_body;
    }

    return body;
}

bool HTTP::getAsync(const std::string &url, const std::map<std::string, std::string> &headers)
{
    return requestAsync("GET", url, headers);
}

std::string HTTP::get(const std::string &url, const std::map<std::string, std::string> &headers)
{
    return request("GET", url, headers);
}

std::string HTTP::getAsyncResponse() const
{
    return async_response;
}

HTTPState HTTP::getState() const
{
    return state;
}

std::string HTTP::getStateString() const
{
    switch (state)
    {
    case IDLE:
        return "IDLE";
    case LOADING:
        return "LOADING";
    case ISSUE:
        return "ISSUE";
    default:
        return "UNKNOWN";
    }
}

bool HTTP::isRequestComplete() const
{
    return async_request_complete;
}

bool HTTP::isRequestInProgress() const
{
    return async_request_in_progress;
}

std::string HTTP::internalRequest(const std::string &method, const std::string &url, bool async, const std::map<std::string, std::string> &headers, const std::string &data)
{
#ifdef CYW43_WL_GPIO_LED_PIN
    std::string hostname, path;
    unsigned short port;
    bool use_tls;

    if (!parseUrl(url, hostname, path, port, use_tls))
    {
        state = ISSUE;
        return "";
    }

    SimpleHTTPRequest req;
    req.hostname = hostname;
    req.url = path;
    req.method = method;
    req.payload = data;
    req.port = port;
    req.complete = false;
    req.result = 0;
    req.response_data = "";

    if (!http_client_request(hostname, path, method, data, port, &req, headers))
    {
        state = ISSUE;
        return "";
    }

    if (async)
    {
        // Store request for async processing
        async_request_in_progress = true;
        async_request_complete = false;
        state = LOADING;
        return "";
    }

    // Wait for completion
    uint32_t start_time = to_ms_since_boot(get_absolute_time());
    while (!req.complete)
    {
        cyw43_arch_poll();

        // Check if the state indicates completion
        if (current_http_state && current_http_state->req_data.complete)
        {
            req.complete = true;
            req.result = current_http_state->req_data.result;
            req.response_data = current_http_state->req_data.response_data;
            break;
        }

        uint32_t current_time = to_ms_since_boot(get_absolute_time());
        if (current_time - start_time > REQUEST_TIMEOUT_MS)
        {
            printf("HTTP: Request timeout\n");
            break;
        }

        sleep_ms(POLL_INTERVAL_MS);
    }

    // Clean up
    if (current_http_state)
    {
        http_client_close(current_http_state);
        delete current_http_state;
        current_http_state = nullptr;
    }

    std::string result = req.response_data;
    return extractHttpBody(result);
#else
    return "";
#endif
}

bool HTTP::parseUrl(const std::string &url, std::string &hostname, std::string &path, unsigned short &port, bool &use_tls)
{
    // Parse URL: https://example.com/path or http://example.com/path
    use_tls = false;
    port = 80;

    size_t protocol_end = url.find("://");
    if (protocol_end == std::string::npos)
    {
        // No protocol specified, assume http
        hostname = url;
        path = "/";
        return true;
    }

    std::string protocol = url.substr(0, protocol_end);
    std::transform(protocol.begin(), protocol.end(), protocol.begin(), ::tolower);

    if (protocol == "https")
    {
        use_tls = true;
        port = 443;
    }
    else if (protocol == "http")
    {
        use_tls = false;
        port = 80;
    }
    else
    {
        printf("HTTP: Unsupported protocol: %s\n", protocol.c_str());
        return false;
    }

    std::string remaining = url.substr(protocol_end + 3);

    // Find path
    size_t path_start = remaining.find('/');
    if (path_start == std::string::npos)
    {
        hostname = remaining;
        path = "/";
    }
    else
    {
        hostname = remaining.substr(0, path_start);
        path = remaining.substr(path_start);
    }

    // Check for port in hostname
    size_t port_start = hostname.find(':');
    if (port_start != std::string::npos)
    {
        std::string port_str = hostname.substr(port_start + 1);
        hostname = hostname.substr(0, port_start);
        port = static_cast<unsigned short>(std::atoi(port_str.c_str()));
    }

    return true;
}

std::string HTTP::post(const std::string &url, const std::map<std::string, std::string> &headers, const std::string &data)
{
    return request("POST", url, headers, data);
}

std::string HTTP::put(const std::string &url, const std::map<std::string, std::string> &headers, const std::string &data)
{
    return request("PUT", url, headers, data);
}

bool HTTP::postAsync(const std::string &url, const std::map<std::string, std::string> &headers, const std::string &data)
{
    return requestAsync("POST", url, headers, data);
}

bool HTTP::putAsync(const std::string &url, const std::map<std::string, std::string> &headers, const std::string &data)
{
    return requestAsync("PUT", url, headers, data);
}

std::string HTTP::request(const std::string &method, const std::string &url, const std::map<std::string, std::string> &headers, const std::string &data)
{
    return internalRequest(method, url, false, headers, data);
}

bool HTTP::requestAsync(const std::string &method, const std::string &url, const std::map<std::string, std::string> &headers, const std::string &data)
{
    internalRequest(method, url, true, headers, data);
    return state != ISSUE;
}

void HTTP::update()
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (async_request_in_progress && current_http_state)
    {
        if (current_http_state->req_data.complete)
        {
            async_response = extractHttpBody(current_http_state->req_data.response_data);
            async_request_complete = true;
            async_request_in_progress = false;
            state = IDLE;

            // Clean up
            http_client_close(current_http_state);
            delete current_http_state;
            current_http_state = nullptr;
        }
    }
#endif
}
