#pragma once
#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include "WiFi.h"
namespace Picoware
{
    typedef struct
    {
        String ssid;
        short rssi;
        uint8_t channel;
    } WiFiScanResult;

// Maximum number of APs to record in a single scan
#define WIFI_MAX_SCAN 64

    // Global scan results array and count
    extern WiFiScanResult wifiScanResults[WIFI_MAX_SCAN];
    extern int wifiScanCount;
    extern bool wifiScanInProgress;
    extern bool wifiScanReset;

    // WiFi connection states for async operations
    enum WiFiConnectionState
    {
        WIFI_STATE_IDLE,
        WIFI_STATE_CONNECTING,
        WIFI_STATE_CONNECTED,
        WIFI_STATE_FAILED,
        WIFI_STATE_TIMEOUT
    };

    class WiFiUtils
    {
    public:
        WiFiUtils()
        {
        }
        bool connect(const char *ssid, const char *password, bool async = false);  // Connect to WiFi using the provided SSID and password
        bool connectAsync(const char *ssid, const char *password);                 // Start async WiFi connection
        String getConnectedSSID() const noexcept { return connectedSSID; }         // Get the SSID of the connected network
        String getConnectedPassword() const noexcept { return connectedPassword; } // Get the password of the connected network
        WiFiConnectionState getConnectionState();                                  // Get current connection state for async operations
        bool updateConnection();                                                   // Update async connection - call this in your main loop
        bool configureTime();                                                      // Configure time using NTP
        String connectAP(const char *ssid);                                        // Connect to WiFi in AP mode and return the IP address
        String deviceIP();                                                         // Get IP address of the device
        void disconnect();                                                         // Disconnect from WiFi
        bool isConnected();                                                        // Check if connected to WiFi
        bool setTime(tm &timeinfo, int timeoutMs = 5000);                          // Set time to a tm structure
        String scan();                                                             // Scan for available WiFi networks
        void resetConnection();                                                    // Reset connection state

    private:
        bool connectHelper(
            const char *ssid,
            const char *password,
            bool isAP = false,
            bool async = false); // Helper function to connect to WiFi
        WiFiConnectionState currentState = WIFI_STATE_IDLE;
        String pendingSSID = "";
        String pendingPassword = "";
        unsigned long connectionStartTime = 0;
        static const unsigned long CONNECTION_TIMEOUT = 10000; // 10 seconds timeout
        String connectedSSID = "";
        String connectedPassword = "";
    };
}