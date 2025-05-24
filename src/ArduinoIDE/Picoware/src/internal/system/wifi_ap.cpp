#include "../../internal/system/wifi_ap.hpp"
namespace Picoware
{
    WiFiAP::WiFiAP()
        : dnsServer(), isRunning(false), lastInputs(""), server(80)
    {
        html = "HTTP/1.1 200 OK\r\n";
        html += "Content-type:text/html\r\n";
        html += "\r\n";
        html += "<!DOCTYPE html><html>\r\n";
        html += "<head><title>Picoware</title></head>\r\n";
        html += "<body><h1>Welcome to Picoware AP Mode</h1></body>\r\n";
        html += "</html>";
    }

    void WiFiAP::fetchInputs(const String &request)
    {
        auto getIdx = request.indexOf("get?");
        if (getIdx != -1 && request.startsWith("GET"))
        {
            int startPos = getIdx;
            int endPos = request.indexOf("HTTP/1.1", startPos);
            if (startPos > 0 && endPos > startPos)
            {
                String path = request.substring(startPos, endPos);
                int start = getIdx - 1;
                int end = path.indexOf('&', start);
                this->lastInputs = "";
                while (end != -1)
                {
                    String part = path.substring(start, end);
                    this->lastInputs += part;
                    start = end + 1;
                    end = path.indexOf('&', start);
                }
                String part = path.substring(start, end);
                this->lastInputs += part;
            }
        }
    }

    bool WiFiAP::start(const char *ssid)
    {
        WiFi.disconnect(true);
        WiFi.mode(WIFI_AP);
        WiFi.softAP(ssid);
        String ipStr = WiFi.softAPIP().toString();
        if (ipStr.length() == 0)
        {
            return false;
        }
        apIP = IPAddress();
        apIP.fromString(ipStr);
        dnsServer.start(53, "*", apIP);
        isRunning = true;
        server.begin();
        return true;
    }

    void WiFiAP::run()
    {
        if (!isRunning)
        {
            return;
        }

        while (true)
        {
            dnsServer.processNextRequest();
            WiFiClient client = server.accept();
            if (client)
            {
                String request = "";
                unsigned long timeout = millis() + 5000;
                while (client.connected() && millis() < timeout)
                {
                    if (request.indexOf("\r\n\r\n") > 0)
                    {
                        break;
                    }

                    // Read available data
                    while (client.available() && millis() < timeout)
                    {
                        char c = client.read();
                        request += c;
                        timeout = millis() + 1000; // Reset timeout on data received
                    }
                    delay(1);
                }
                fetchInputs(request);
                client.println(html);
                delay(10);
                client.stop();
            }
            delay(10);
        }

        this->stop();
    }

    void WiFiAP::runAsync()
    {
        if (!isRunning)
        {
            return;
        }

        dnsServer.processNextRequest();
        WiFiClient client = server.accept();
        if (client)
        {
            String request = "";
            unsigned long timeout = millis() + 5000;
            while (client.connected() && millis() < timeout)
            {
                if (request.indexOf("\r\n\r\n") > 0)
                {
                    break;
                }

                // Read available data
                while (client.available() && millis() < timeout)
                {
                    char c = client.read();
                    request += c;
                    timeout = millis() + 1000; // Reset timeout on data received
                }
                delay(1);
            }
            fetchInputs(request);
            client.println(html);
            delay(10);
            client.stop();
        }
    }

    void WiFiAP::stop()
    {
        if (isRunning)
        {
            server.end();
            WiFi.disconnect(true);
            dnsServer.stop();
            isRunning = false;
        }
    }

    void WiFiAP::updateHTML(const String &htmlContent)
    {
        html = "HTTP/1.1 200 OK\r\n";
        html += "Content-type:text/html\r\n";
        html += "\r\n";
        html += htmlContent;
    }
}