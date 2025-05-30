#include "../../internal/system/wifi_utils.hpp"
namespace Picoware
{
    WiFiScanResult wifiScanResults[WIFI_MAX_SCAN];
    int wifiScanCount = 0;
    bool wifiScanInProgress = false;
    bool wifiScanReset = false;
    static uint8_t wifiTries = 0;

    bool WiFiUtils::connectHelper(const char *ssid, const char *password, bool isAP, bool async)
    {
        if (!wifiScanInProgress)
        {
            if (isAP && strlen(ssid) == 0)
            {
                return false;
            }
            if (!isAP && (strlen(ssid) == 0 || strlen(password) == 0))
            {
                return false;
            }

            WiFi.disconnect(true);

            if (isAP)
            {
                WiFi.mode(WIFI_AP);
                WiFi.softAP(ssid);
            }
            else
            {
                WiFi.mode(WIFI_STA);
                WiFi.begin(ssid, password);
            }
            wifiScanInProgress = true;
        }
        if (!isAP)
        {
            if (!async)
            {
                while (!this->isConnected() && wifiTries < 20)
                {
                    delay(500);
                    wifiTries++;
                }
                wifiScanInProgress = false;
                if (this->isConnected())
                {
                    connectedSSID = String(ssid);
                    connectedPassword = String(password);
                    wifiTries = 0;
                    return true;
                }
                else
                {
                    wifiTries = 0;
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
            if (WiFi.status() == WL_CONNECTED)
            {
                wifiScanInProgress = false;
                connectedSSID = String(ssid);
                connectedPassword = String(password);
                return true;
            }
            return true;
        }
        return true;
    }

    bool WiFiUtils::connect(const char *ssid, const char *password, bool async)
    {
        if (async)
        {
            // Use the new async method when async flag is true
            return this->connectAsync(ssid, password);
        }

        wifiTries = 0;
        wifiScanInProgress = false;
        if (this->connectHelper(ssid, password, false, false))
        {
            return this->configureTime();
        }
        return false;
    }

    bool WiFiUtils::connectAsync(const char *ssid, const char *password)
    {
        // Reset any previous connection attempt
        this->resetConnection();

        // Store credentials for the connection attempt
        pendingSSID = String(ssid);
        pendingPassword = String(password);

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
            currentState = WIFI_STATE_FAILED;
            return false;
        }
    }

    WiFiConnectionState WiFiUtils::getConnectionState()
    {
        return currentState;
    }

    bool WiFiUtils::updateConnection()
    {
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

        // Continue the connection attempt using the helper
        if (this->connectHelper(pendingSSID.c_str(), pendingPassword.c_str(), false, true))
        {
            if (WiFi.status() == WL_CONNECTED)
            {
                currentState = WIFI_STATE_CONNECTED;
                wifiScanInProgress = false;
                wifiTries = 0;
                connectedSSID = pendingSSID;
                connectedPassword = pendingPassword;
                this->configureTime(); // Configure time when connected
                return true;
            }
            // Still connecting
            return false;
        }
        else
        {
            // Connection failed
            currentState = WIFI_STATE_FAILED;
            wifiScanInProgress = false;
            wifiTries = 0;
            return false;
        }
    }

    void WiFiUtils::resetConnection()
    {
        currentState = WIFI_STATE_IDLE;
        wifiScanInProgress = false;
        wifiTries = 0;
        pendingSSID = "";
        pendingPassword = "";
        connectionStartTime = 0;
    }

    String WiFiUtils::connectAP(const char *ssid)
    {
        if (!this->connectHelper(ssid, "", true, false))
        {
            return "";
        }
        return WiFi.softAPIP().toString();
    }

    bool WiFiUtils::configureTime()
    {
        if (WiFi.status() != WL_CONNECTED)
        {
            return false;
        }
        configTime(0, 0, "pool.ntp.org", "time.nist.gov");
        return true;
    }

    String WiFiUtils::deviceIP()
    {
        return WiFi.localIP().toString();
    }

    void WiFiUtils::disconnect()
    {
        WiFi.disconnect(true);
        this->resetConnection();
    }

    bool WiFiUtils::isConnected()
    {
        return WiFi.status() == WL_CONNECTED;
    }

    String WiFiUtils::scan()
    {
        WiFi.scanDelete();
        wifiScanCount = 0;
        for (int i = 0; i < WIFI_MAX_SCAN; i++)
        {
            wifiScanResults[i].ssid = "";
            wifiScanResults[i].rssi = 0;
            wifiScanResults[i].channel = 0;
        }
        int n = WiFi.scanNetworks();

        // Store scan results in our array
        int validNetworks = 0;
        for (int i = 0; i < n && validNetworks < WIFI_MAX_SCAN; ++i)
        {
            String ssid = WiFi.SSID(i);
            ssid.trim();
            if (ssid.length() == 0)
            {
                continue;
            }
            wifiScanResults[validNetworks].ssid = ssid;
            wifiScanResults[validNetworks].rssi = WiFi.RSSI(i);
            wifiScanResults[validNetworks].channel = WiFi.channel(i);
            validNetworks++;
        }

        // Sort our array by RSSI
        for (int i = 0; i < validNetworks - 1; ++i)
            wifiScanCount = validNetworks;

        String json = "{\"networks\":[";
        for (int i = 0; i < validNetworks; ++i)
        {
            json += "\"";
            json += wifiScanResults[i].ssid;
            json += "\"";
            if (i < validNetworks - 1)
            {
                json += ",";
            }
        }
        json += "]}";
        return json;
    }

    // may take seconds to minutes for the system time to be updated by NTP, depending on the server
    bool WiFiUtils::setTime(tm &timeinfo, int timeoutMs)
    {
        if (WiFi.status() != WL_CONNECTED)
        {
            return false;
        }
        static bool ntpInitialized = false;
        if (!ntpInitialized)
        {
            NTP.begin("pool.ntp.org", "time.nist.gov");
            NTP.waitSet(timeoutMs);
            ntpInitialized = true;
        }
        time_t now = time(nullptr);
        gmtime_r(&now, &timeinfo);
        return true; // Current Time: asctime(&timeinfo) or sprintf(buffer,"%02d:%02d:%02d", timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
    }
}