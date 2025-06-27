#include "../../internal/system/http.hpp"
#include <ArduinoHttpClient.h>
#if defined(ARDUINO_RASPBERRY_PI_PICO_W) || defined(ARDUINO_RASPBERRY_PI_PICO_2_W)
#include <AsyncHTTPRequest_RP2040W.h>
#endif

// AsyncHTTPRequest ready states
#define readyStateUnsent 0
#define readyStateOpened 1
#define readyStateHdrsRecvd 2
#define readyStateLoading 3
#define readyStateDone 4

namespace Picoware
{
    HTTP::~HTTP()
    {
        // nothing to do
    }

    String HTTP::request(const char *method, String url, String payload, const char *headerKeys[], const char *headerValues[], int headerSize)
    {
        HTTPClient http;
        String response = "";
        http.collectHeaders(headerKeys, headerSize);
        if (http.begin(this->client, url))
        {
            for (int i = 0; i < headerSize; i++)
            {
                http.addHeader(headerKeys[i], headerValues[i]);
            }

            if (payload == "")
            {
                payload = "{}";
            }
            int statusCode = http.sendRequest(method, payload);
            char headerResponse[512];

            if (statusCode > 0)
            {
                response = http.getString();
                http.end();
                return response;
            }
            else if (statusCode == -1) // HTTPC_ERROR_CONNECTION_FAILED
            {
                // send request without SSL
                http.end();
                this->client.setInsecure();
                if (http.begin(this->client, url))
                {
                    for (int i = 0; i < headerSize; i++)
                    {
                        http.addHeader(headerKeys[i], headerValues[i]);
                    }
                    int newCode = http.sendRequest(method, payload);
                    if (newCode > 0)
                    {
                        response = http.getString();
                        http.end();
                        // this->client.setCACert(root_ca);
                        return response;
                    }
                    else
                    {
                        // this->client.setCACert(root_ca);
                    }
                }
            }
            http.end();
        }
        return response;
    }

    void HTTP::websocket(String url, int port)
    {
        // Parse the fullUrl to extract server name and path.
        // Expected format: "ws://www.jblanked.com/ws/game/new/"
        String fullUrl = url;
        String serverName;
        String path = "/";

        // Remove protocol ("ws://" or "wss://")
        if (fullUrl.startsWith("ws://"))
        {
            fullUrl = fullUrl.substring(5);
        }
        else if (fullUrl.startsWith("wss://"))
        {
            fullUrl = fullUrl.substring(6);
        }

        // Look for the first '/' that separates the server name from the path.
        int slashIndex = fullUrl.indexOf('/');
        if (slashIndex != -1)
        {
            serverName = fullUrl.substring(0, slashIndex);
            path = fullUrl.substring(slashIndex);
        }
        else
        {
            serverName = fullUrl;
            path = "/";
        }

        WiFiClient wifi_client;
        WebSocketClient ws = WebSocketClient(wifi_client, serverName.c_str(), port);
        ws.begin(path.c_str());

        if (!ws.connected())
        {
            return;
        }

        // Check if a message is available from the server:
        if (ws.parseMessage() > 0)
        {
            // Read the message from the server
            String message = ws.readString();
            //
        }

        String wsMessage = "";
        while (ws.connected())
        {
            // Check if there's incoming websocket data
            if (ws.parseMessage() > 0)
            {
                // Read the message from the server
                wsMessage = ws.readString();
                //
            }
        }

        // Close the WebSocket connection
        ws.stop();
    }
    bool HTTP::requestAsync(const char *method, String url, String payload, const char *headerKeys[], const char *headerValues[], int headerSize)
    {
#if defined(ARDUINO_RASPBERRY_PI_PICO_W) || defined(ARDUINO_RASPBERRY_PI_PICO_2_W)
        // Reset async state
        asyncResponse = "";
        asyncRequestComplete = false;

        if (asyncRequestInProgress)
        {
            return false; // Another async request is already in progress
        }

        // Check if we can send a request
        if (asyncRequest.readyState() == readyStateUnsent || asyncRequest.readyState() == readyStateDone)
        {
            // Set up the callback
            asyncRequest.onReadyStateChange(onAsyncRequestComplete, this);

            // Try to open the request
            bool openSuccess = asyncRequest.open(method, url.c_str());
            if (!openSuccess)
            {
                // Failed to open request
                state = ISSUE;
                asyncRequestInProgress = false;
                return false;
            }

            // Add headers if provided
            for (int i = 0; i < headerSize; i++)
            {
                if (headerKeys[i] && headerValues[i])
                {
                    asyncRequest.setReqHeader(headerKeys[i], headerValues[i]);
                }
            }

            // Set common headers for JSON APIs
            asyncRequest.setReqHeader("Accept", "application/json");

            asyncRequestInProgress = true;
            state = SENDING;

            // Send the request
            if (payload.length() > 0 && payload != "{}")
            {
                asyncRequest.setReqHeader("Content-Type", "application/json");
                asyncRequest.send(payload);
            }
            else
            {
                asyncRequest.send();
            }

            state = RECEIVING;
            return true;
        }
        else
        {
            // Can't send request - not in proper state
            return false;
        }
#else
        return false;
#endif
    }

#if defined(ARDUINO_RASPBERRY_PI_PICO_W) || defined(ARDUINO_RASPBERRY_PI_PICO_2_W)
    void HTTP::onAsyncRequestComplete(void *optParm, AsyncHTTPRequest *request, int readyState)
    {
        HTTP *httpInstance = static_cast<HTTP *>(optParm);

        // Check the ready state
        switch (readyState)
        {
        case readyStateUnsent:
            // Request not yet sent
            break;
        case readyStateOpened:
            // Request opened
            break;
        case readyStateHdrsRecvd:
            // Headers received
            break;
        case readyStateLoading:
            // Loading response
            httpInstance->state = RECEIVING;
            break;
        case readyStateDone:
        {
            // Request complete
            httpInstance->asyncRequestInProgress = false;

            // Check if we got a successful response
            int httpCode = request->responseHTTPcode();
            if (httpCode >= 200 && httpCode < 300)
            {
                // Success - get the response text
                httpInstance->asyncResponse = request->responseText();
                httpInstance->state = IDLE;
            }
            else
            {
                // HTTP error
                httpInstance->asyncResponse = "";
                httpInstance->state = ISSUE;
            }

            httpInstance->asyncRequestComplete = true;
            break;
        }
        default:
            // Unknown state
            break;
        }
    }
#endif
    String HTTP::getAsyncResponse()
    {
        if (asyncRequestComplete)
        {
            String response = asyncResponse;
            asyncResponse = "";
            asyncRequestComplete = false;
            return response;
        }
        return "";
    }
    bool HTTP::isAsyncComplete()
    {
        return asyncRequestComplete;
    }

    void HTTP::processAsync()
    {
        static unsigned long requestStartTime = 0;

        if (asyncRequestInProgress)
        {
            // Initialize start time on first call
            if (requestStartTime == 0)
            {
                requestStartTime = millis();
            }

            // 15 second timeout as fallback safety
            if (millis() - requestStartTime > 15000)
            {
                // Timeout - mark as failed
                asyncRequestInProgress = false;
                asyncRequestComplete = true;
                asyncResponse = "";
                state = ISSUE;
                requestStartTime = 0;
            }
        }
        else if (!asyncRequestInProgress)
        {
            // Reset timeout counter when not in progress
            requestStartTime = 0;
        }
    }
}