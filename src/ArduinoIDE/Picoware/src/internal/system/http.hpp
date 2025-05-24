#pragma once
#include <Arduino.h>
#include "../../internal/system/wifi_utils.hpp"
namespace Picoware
{
    class HTTP
    {
    public:
        HTTP() : client()
        {
        }
        String request(
            const char *method,                   // HTTP method
            String url,                           // URL to send the request to
            String payload = "",                  // Payload to send with the request
            const char *headerKeys[] = nullptr,   // Array of header keys
            const char *headerValues[] = nullptr, // Array of header values
            int headerSize = 0                    // Number of headers
        );
        void websocket(String url, int port); // Connect to a WebSocket server
    private:
        WiFiClientSecure client; // WiFiClientSecure object for secure connections
    };
}
