#include "../system/wifi.hpp"
#include "../system/http.hpp"
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <sys/time.h>

#ifdef CYW43_WL_GPIO_LED_PIN
#include "pico/cyw43_arch.h"
WiFiScanResult wifiScanResults[WIFI_MAX_SCAN];
int wifiScanCount = 0;
bool wifiScanInProgress = false;
bool wifiScanReset = false;
static uint8_t wifiTries = 0;
#endif

static bool wifiInitialized = false;

WiFi::WiFi()
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (wifiInitialized)
    {
        return;
    }

    if (cyw43_arch_init())
    {
        printf("[WiFi]: Failed to initialize WiFi\n");
        return;
    }

    wifiInitialized = true;

    // Initialize HTTP client for NTP requests
    httpClient = new HTTP();
#endif
}

WiFi::~WiFi()
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (httpClient)
    {
        delete httpClient;
        httpClient = nullptr;
    }

    if (wifiInitialized)
    {
        cyw43_arch_deinit();
        wifiInitialized = false;
        printf("[WiFi]: WiFi deinitialized\n");
    }
#endif
}

WiFi::WiFi(WiFi &&other) noexcept
    : currentState(other.currentState),
      connectionStartTime(other.connectionStartTime),
      connectedSSID(std::move(other.connectedSSID)),
      connectedPassword(std::move(other.connectedPassword)),
      pendingSSID(std::move(other.pendingSSID)),
      pendingPassword(std::move(other.pendingPassword)),
      httpClient(other.httpClient)
{
    other.currentState = WIFI_STATE_IDLE;
    other.connectionStartTime = 0;
    other.httpClient = nullptr;
}

WiFi &WiFi::operator=(WiFi &&other) noexcept
{
    if (this != &other)
    {
        // Clean up existing HTTP client
        if (httpClient)
        {
            delete httpClient;
        }

        currentState = other.currentState;
        connectionStartTime = other.connectionStartTime;
        connectedSSID = std::move(other.connectedSSID);
        connectedPassword = std::move(other.connectedPassword);
        pendingSSID = std::move(other.pendingSSID);
        pendingPassword = std::move(other.pendingPassword);
        httpClient = other.httpClient;

        // Reset other object
        other.currentState = WIFI_STATE_IDLE;
        other.connectionStartTime = 0;
        other.httpClient = nullptr;
    }
    return *this;
}

bool WiFi::connectHelper(const char *ssid, const char *password, bool isAP, bool async)
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (!wifiInitialized && !reinit())
    {
        printf("[WiFi:connectHelper]: WiFi not initialized\n");
        return false;
    }

    if (!wifiScanInProgress)
    {
        if (isAP && strlen(ssid) == 0)
        {
            return false;
        }
        if (!isAP && (strlen(ssid) == 0 || strlen(password) == 0))
        {
            printf("SSID or password is empty\n");
            return false;
        }

        // Disconnect any existing connection
        if (cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA) == CYW43_LINK_UP)
        {
            cyw43_wifi_leave(&cyw43_state, CYW43_ITF_STA);
        }

        if (isAP)
        {
            cyw43_arch_enable_ap_mode(ssid, password ? password : NULL, CYW43_AUTH_WPA2_AES_PSK);
        }
        else
        {
            cyw43_arch_enable_sta_mode();
            int err = cyw43_arch_wifi_connect_async(ssid, password, CYW43_AUTH_WPA2_AES_PSK);
            if (err != 0)
            {
                printf("WiFi connect failed: %d\n", err);
                return false;
            }
        }
        wifiScanInProgress = true;
    }

    if (!isAP)
    {
        if (!async)
        {
            while (!this->isConnected() && wifiTries < 20)
            {
                sleep_ms(500);
                wifiTries++;
#if PICO_CYW43_ARCH_POLL
                cyw43_arch_poll();
#endif
            }
            wifiScanInProgress = false;
            if (this->isConnected())
            {
                connectedSSID = std::string(ssid);
                connectedPassword = std::string(password);
                wifiTries = 0;
                return true;
            }
            else
            {
                wifiTries = 0;
                printf("WiFi connection failed...\n");
                return false;
            }
        }
        wifiTries++;
        if (wifiTries > 20)
        {
            wifiTries = 0;
            wifiScanInProgress = false;
            return false;
        }
        if (cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA) == CYW43_LINK_UP)
        {
            wifiScanInProgress = false;
            connectedSSID = std::string(ssid);
            connectedPassword = std::string(password);
            currentState = WIFI_STATE_CONNECTED;
            return true;
        }
        return true;
    }
    return true;
#else
    return false;
#endif
}

bool WiFi::connect(const char *ssid, const char *password, bool async)
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (async)
    {
        return this->connectAsync(ssid, password);
    }

    wifiTries = 0;
    wifiScanInProgress = false;
    if (this->connectHelper(ssid, password, false, false))
    {
        return this->configureTime();
    }
    return false;
#else
    return false;
#endif
}

bool WiFi::connectAsync(const char *ssid, const char *password)
{
#ifdef CYW43_WL_GPIO_LED_PIN
    // Reset any previous connection attempt
    this->resetConnection();

    // Store credentials for the connection attempt
    pendingSSID = std::string(ssid);
    pendingPassword = std::string(password);

    // Start the connection
    wifiTries = 0;
    wifiScanInProgress = false;
    currentState = WIFI_STATE_CONNECTING;
    connectionStartTime = millis();

    // Start the actual connection using the helper
    if (this->connectHelper(ssid, password, false, true))
    {
        return true; // Connection initiated successfully
    }
    else
    {
        printf("Failed to initiate connection\n");
        currentState = WIFI_STATE_FAILED;
        return false;
    }
#else
    return false;
#endif
}

WiFiConnectionState WiFi::getConnectionState()
{
    return currentState;
}

bool WiFi::updateConnection()
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (currentState != WIFI_STATE_CONNECTING)
    {
        return currentState == WIFI_STATE_CONNECTED;
    }

    // Check for timeout
    if (millis() - connectionStartTime > CONNECTION_TIMEOUT)
    {
        currentState = WIFI_STATE_TIMEOUT;
        wifiScanInProgress = false;
        wifiTries = 0;
        return false;
    }

#if PICO_CYW43_ARCH_POLL
    cyw43_arch_poll();
#endif

    // Check if we're already connected
    if (cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA) == CYW43_LINK_UP)
    {
        currentState = WIFI_STATE_CONNECTED;
        wifiScanInProgress = false;
        wifiTries = 0;
        connectedSSID = pendingSSID;
        connectedPassword = pendingPassword;
        this->configureTime();
        return true;
    }
    return false;
#else
    return false;
#endif
}

bool WiFi::reinit()
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (wifiInitialized)
    {
        cyw43_arch_deinit();
    }

    if (cyw43_arch_init())
    {
        printf("[WiFi]: Failed to re-initialize WiFi\n");
        return false;
    }

    wifiInitialized = true;

    // Reinitialize HTTP client if needed
    if (!httpClient)
    {
        httpClient = new HTTP();
    }

    return true;
#endif
}

void WiFi::resetConnection()
{
#ifdef CYW43_WL_GPIO_LED_PIN
    currentState = WIFI_STATE_IDLE;
    wifiScanInProgress = false;
    wifiTries = 0;
    pendingSSID = "";
    pendingPassword = "";
    connectionStartTime = 0;
#endif
}

String WiFi::connectAP(const char *ssid)
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (!this->connectHelper(ssid, "", true, false))
    {
        return "";
    }
    // arduino ide sends the soft AP.. not sure how to get that
    return std::string("192.168.4.1");
#else
    return "";
#endif
}

bool WiFi::configureTime()
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (!this->isConnected() || !httpClient)
    {
        return false;
    }

    std::string response = httpClient->get("http://worldtimeapi.org/api/ip");

    if (response.empty())
    {
        printf("[WiFi]: Failed to get timezone-aware time, trying UTC...\n");
        response = httpClient->get("http://worldtimeapi.org/api/timezone/Etc/UTC");

        if (response.empty())
        {
            printf("[WiFi]: Failed to get time from WorldTimeAPI\n");
            return false;
        }
    }

    // Parse JSON response to extract Unix timestamp
    std::string unixtime_str = getJsonValue(response.c_str(), "unixtime");

    if (unixtime_str.empty())
    {
        printf("[WiFi]: Failed to parse time response\n");
        return false;
    }

    time_t timestamp = (time_t)atol(unixtime_str.c_str());

    // Try to get timezone offset information
    std::string raw_offset_str = getJsonValue(response.c_str(), "raw_offset");
    std::string dst_offset_str = getJsonValue(response.c_str(), "dst_offset");
    std::string timezone_str = getJsonValue(response.c_str(), "timezone");

    int timezone_offset = 0; // Default to UTC

    if (!raw_offset_str.empty())
    {
        int raw_offset = atoi(raw_offset_str.c_str());
        int dst_offset = 0;

        if (!dst_offset_str.empty())
        {
            dst_offset = atoi(dst_offset_str.c_str());
        }

        timezone_offset = raw_offset + dst_offset;
        timestamp += timezone_offset;
    }
    else
    {
        printf("[WiFi]: No timezone offset available, using UTC\n");
    }

    // ensure timestamp is reasonable (after year 2000)
    if (timestamp < 946684800)
    {
        printf("[WiFi]: Invalid timestamp received: %ld\n", (long)timestamp);
        return false;
    }

    // Set system time
    struct timeval tv;
    tv.tv_sec = timestamp;
    tv.tv_usec = 0;

    if (settimeofday(&tv, NULL) == 0)
    {
        return true;
    }
    else
    {
        printf("[WiFi]: Failed to set system time\n");
        return false;
    }
#else
    return false;
#endif
}

String WiFi::deviceIP()
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if ((!wifiInitialized && !reinit()) || !this->isConnected())
    {
        return std::string("");
    }

    // arduino ide has a method for this, we'll just return a placeholder now
    return std::string("192.168.1.100");
#else
    return "";
#endif
}

void WiFi::disconnect()
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (wifiInitialized)
    {
        if (cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA) == CYW43_LINK_UP)
        {
            cyw43_wifi_leave(&cyw43_state, CYW43_ITF_STA);
        }
    }
    this->resetConnection();
#endif
}

bool WiFi::isConnected()
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (!wifiInitialized && !reinit())
    {
        return false;
    }
    return cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA) == CYW43_LINK_UP;
#else
    return false;
#endif
}

#ifdef CYW43_WL_GPIO_LED_PIN
static int scanResultCallback(void *env, const cyw43_ev_scan_result_t *result)
{
    if (result && wifiScanCount < WIFI_MAX_SCAN)
    {
        std::string ssid_str = std::string((const char *)result->ssid);
        trim(ssid_str);

        if (ssid_str.length() > 0)
        {
            wifiScanResults[wifiScanCount].ssid = ssid_str;
            wifiScanResults[wifiScanCount].rssi = result->rssi;
            wifiScanResults[wifiScanCount].channel = result->channel;
            memcpy(wifiScanResults[wifiScanCount].bssid, result->bssid, 6);
            wifiScanResults[wifiScanCount].auth_mode = result->auth_mode;
            wifiScanCount++;
        }
    }
    return 0;
}
#endif

String WiFi::scan()
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (!wifiInitialized && !reinit())
    {
        return std::string("{\"networks\":[]}");
    }

    // Clear previous results
    wifiScanCount = 0;
    for (int i = 0; i < WIFI_MAX_SCAN; i++)
    {
        wifiScanResults[i].ssid = "";
        wifiScanResults[i].rssi = 0;
        wifiScanResults[i].channel = 0;
    }

    cyw43_arch_enable_sta_mode();

    cyw43_wifi_scan_options_t scan_options = {0};
    int err = cyw43_wifi_scan(&cyw43_state, &scan_options, NULL, scanResultCallback);

    if (err != 0)
    {
        return std::string("{\"networks\":[]}");
    }

    // Wait for scan to complete
    int timeout = 0;
    while (cyw43_wifi_scan_active(&cyw43_state) && timeout < 100)
    {
        sleep_ms(100);
        timeout++;
#if PICO_CYW43_ARCH_POLL
        cyw43_arch_poll();
#endif
    }

    // Sort results by RSSI (strongest first)
    for (int i = 0; i < wifiScanCount - 1; i++)
    {
        for (int j = i + 1; j < wifiScanCount; j++)
        {
            if (wifiScanResults[i].rssi < wifiScanResults[j].rssi)
            {
                WiFiScanResult temp = wifiScanResults[i];
                wifiScanResults[i] = wifiScanResults[j];
                wifiScanResults[j] = temp;
            }
        }
    }

    std::string json = std::string("{\"networks\":[");
    for (int i = 0; i < wifiScanCount; ++i)
    {
        json += "\"";
        json += wifiScanResults[i].ssid.c_str();
        json += "\"";
        if (i < wifiScanCount - 1)
        {
            json += ",";
        }
    }
    json += "]}";
    return json;
#else
    return "";
#endif
}

bool WiFi::setTime(tm &timeinfo, int timeoutMs)
{
#ifdef CYW43_WL_GPIO_LED_PIN
    if (!this->isConnected())
    {
        return false;
    }

    static bool timeInitialized = false;
    if (!timeInitialized)
    {
        // Try to configure time from internet
        if (this->configureTime())
        {
            timeInitialized = true;
        }
        else
        {
            // If internet time sync fails, check if we have a valid system time
            time_t now = time(nullptr);
            if (now > 24 * 3600)
            {
                timeInitialized = true;
            }
            else
            {
                printf("[WiFi]: Failed to synchronize time\n");
                return false;
            }
        }
    }

    // Get current time and populate timeinfo structure
    time_t now = time(nullptr);
    localtime_r(&now, &timeinfo);

    // Verify that we have a reasonable time (after year 2000)
    bool timeValid = (now > 946684800); // Jan 1, 2000 00:00:00 UTC

    if (!timeValid)
    {
        printf("[WiFi]: System time appears invalid: %ld\n", (long)now);
        timeInitialized = false; // Reset so we try again next time
        return false;
    }
    return true;
#else
    return false;
#endif
}
