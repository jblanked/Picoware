#pragma once
#include <Arduino.h>
#include "../../internal/system/wifi_utils.hpp"
#if defined(ARDUINO_RASPBERRY_PI_PICO_W) || defined(ARDUINO_RASPBERRY_PI_PICO_2_W)
#include <AsyncHTTPRequest_RP2040W.hpp>
#endif
namespace Picoware
{
    typedef enum
    {
        INACTIVE,  // Inactive state
        IDLE,      // Default state
        RECEIVING, // Receiving data
        SENDING,   // Sending data
        ISSUE,     // Issue with connection
    } HTTPState;

    class HTTP
    {
    public:
        HTTP() : client()
        {
        }
        ~HTTP();
        HTTPState getState() const noexcept { return state; } // Get the current HTTP state
        String request(
            const char *method,                   // HTTP method
            String url,                           // URL to send the request to
            String payload = "",                  // Payload to send with the request
            const char *headerKeys[] = nullptr,   // Array of header keys
            const char *headerValues[] = nullptr, // Array of header values
            int headerSize = 0                    // Number of headers
        );
        // currently this only supprorts HTTP requests, not HTTPS..
        bool requestAsync(
            const char *method,                   // HTTP method
            String url,                           // URL to send the request to
            String payload = "",                  // Payload to send with the request
            const char *headerKeys[] = nullptr,   // Array of header keys
            const char *headerValues[] = nullptr, // Array of header values
            int headerSize = 0                    // Number of headers
        );
        void websocket(String url, int port); // Connect to a WebSocket server
        String getAsyncResponse();            // Get the response from async request
        bool isAsyncComplete();               // Check if async request is complete
        void processAsync();                  // Process async requests (call this regularly)
    private:
        HTTPState state = INACTIVE;          // Current HTTP state
        WiFiClientSecure client;             // WiFiClientSecure object for secure connections
        bool asyncRequestComplete = false;   // Track if async request is complete
        String asyncResponse = "";           // Store async response
        bool asyncRequestInProgress = false; // Track if async request is in progress
#if defined(ARDUINO_RASPBERRY_PI_PICO_W) || defined(ARDUINO_RASPBERRY_PI_PICO_2_W)
        AsyncHTTPRequest asyncRequest; // AsyncHTTPRequest object for non-blocking requests (pointer to avoid header inclusion)

        // Static callback function for async request completion
        static void onAsyncRequestComplete(void *optParm, AsyncHTTPRequest *request, int readyState);
#endif
    };
}
