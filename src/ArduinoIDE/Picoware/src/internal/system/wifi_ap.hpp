#pragma once
#include <Arduino.h>
#include <DNSServer.h>
#include "../../internal/system/wifi_utils.hpp"
namespace Picoware
{
    class WiFiAP
    {
    public:
        WiFiAP();
        String getInputs() const noexcept { return lastInputs; } // Get the last inputs received
        void run();
        void runAsync();
        bool start(const char *ssid);
        void stop();                                // Stop the AP mode
        void updateHTML(const String &htmlContent); // Update the HTML content to be served

    private:
        void fetchInputs(const String &request); // Get inputs from the request
        bool isRunning;                          // Flag to indicate if the AP mode is running
        String html;                             // HTML content to be served
        DNSServer dnsServer;                     // DNS server to redirect all domains to AP IP
        IPAddress apIP;                          // AP mode IP address
        String lastInputs;                       // Last inputs received from the request
        WiFiServer server;                       // Server to handle incoming requests
    };
}