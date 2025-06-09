#include "../../internal/system/http.hpp"
#include <ArduinoHttpClient.h>
namespace Picoware
{
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
}