#pragma once
#include "../system/helpers.hpp"
#include <stdio.h>
#include <time.h>
#include <cctype>
#include "pico/stdlib.h"

class HTTP;

#ifdef CYW43_WL_GPIO_LED_PIN

typedef struct
{
    String ssid;
    short rssi;
    uint8_t channel;
    uint8_t bssid[6];
    uint32_t auth_mode;
} WiFiScanResult;

// Maximum number of APs to record in a single scan
#define WIFI_MAX_SCAN 64

// Global scan results array and count
extern WiFiScanResult wifiScanResults[WIFI_MAX_SCAN];
extern int wifiScanCount;
extern bool wifiScanInProgress;
extern bool wifiScanReset;

#endif

// WiFi connection states for async operations
enum WiFiConnectionState
{
    WIFI_STATE_IDLE,
    WIFI_STATE_CONNECTING,
    WIFI_STATE_CONNECTED,
    WIFI_STATE_FAILED,
    WIFI_STATE_TIMEOUT
};

class WiFi
{
public:
    WiFi();
    ~WiFi();

    WiFi(const WiFi &) = delete;
    WiFi &operator=(const WiFi &) = delete;

    WiFi(WiFi &&other) noexcept;
    WiFi &operator=(WiFi &&other) noexcept;

    bool configureTime();                                                      // Configure NTP time sync
    bool connect(const char *ssid, const char *password, bool async = false);  // Connect to WiFi using the provided SSID and password
    bool connectAsync(const char *ssid, const char *password);                 // Start async WiFi connection
    String connectAP(const char *ssid);                                        // Connect to WiFi in AP mode and return the IP address
    String deviceIP();                                                         // Get IP address of the device
    void disconnect();                                                         // Disconnect from WiFi
    String getConnectedSSID() const noexcept { return connectedSSID; }         // Get the SSID of the connected network
    String getConnectedPassword() const noexcept { return connectedPassword; } // Get the password of the connected network
    WiFiConnectionState getConnectionState();                                  // Get current connection state for async operations
    bool isConnected();                                                        // Check if connected to WiFi
    void resetConnection();                                                    // Reset connection state
    String scan();                                                             // Scan for available WiFi networks
    bool setTime(tm &timeinfo, int timeoutMs = 5000);                          // Set time using NTP
    bool updateConnection();                                                   // Update async connection

private:
    bool connectHelper(const char *ssid, const char *password, bool isAP = false, bool async = false); // Helper function to connect to WiFi
    bool reinit();                                                                                     // Reinitialize class

    WiFiConnectionState currentState = WIFI_STATE_IDLE;
    unsigned long connectionStartTime = 0;
    String connectedSSID = "";
    String connectedPassword = "";
    static const unsigned long CONNECTION_TIMEOUT = 10000; // 10 seconds timeout
    String pendingSSID = "";
    String pendingPassword = "";

    // HTTP client for NTP requests
    HTTP *httpClient = nullptr;
};
