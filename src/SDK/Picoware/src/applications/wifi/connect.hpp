#pragma once
#include "../../../gui/draw.hpp"
#include "../../../gui/menu.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../system/wifi.hpp"
#include "../../../applications/wifi/utils.hpp"

static Alert *wifiConnectAlert = nullptr;
static TextBox *statusBox = nullptr;
static unsigned long lastUpdate = 0;
static unsigned long connectionStartTime = 0;
static bool connectionInitiated = false;
static bool wifiSaved = false;
static String statusMessage = "";

static String getWiFiStatusText(ViewManager *viewManager)
{
    auto &wifiUtil = viewManager->getWiFi();
    String ssid = wifiUtilsLoadWiFiSSIDFromFlash(viewManager);
    String text = "WiFi Setup\n\n";
    text += "Network: " + ssid + "\n";
    text += "Status: " + statusMessage + "\n\n";

    if (wifiUtil.isConnected())
    {
        text += "IP Address: " + wifiUtil.deviceIP() + "\n";
        text += "Connected!\n\n";
        statusMessage = "Connected successfully!";
        if (!wifiSaved)
        {
            wifiSaved = wifiUtilsSaveWiFiToFlash(viewManager->getStorage(), wifiUtil.getConnectedSSID(), wifiUtil.getConnectedPassword());
        }
    }
    else
    {
        WiFiConnectionState state = wifiUtil.getConnectionState();
        switch (state)
        {
        case WIFI_STATE_IDLE:
            text += "Ready to connect\n\n";
            break;
        case WIFI_STATE_CONNECTING:
        {
            unsigned long elapsed = (millis() - connectionStartTime) / 1000;
            text += "Connecting... (" + std::to_string(elapsed) + "s)\n\n";
        }
        break;
        case WIFI_STATE_CONNECTED:
            text += "Connected!\n\n";
            break;
        case WIFI_STATE_FAILED:
            text += "Connection failed\n\n";
            break;
        case WIFI_STATE_TIMEOUT:
            text += "Connection timeout\n\n";
            break;
        }
    }

    text += "Press RIGHT to connect\n";
    text += "Press LEFT/BACK to go back\n";
    text += "Press UP to disconnect";

    return text;
}

static bool wifiConnectStart(ViewManager *viewManager)
{
    if (wifiConnectAlert != nullptr)
    {
        delete wifiConnectAlert;
        wifiConnectAlert = nullptr;
    }

    // if wifi isn't available, return
#ifndef CYW43_WL_GPIO_LED_PIN
    wifiConnectAlert = new Alert(viewManager->getDraw(), "WiFi not available on your board.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
    wifiConnectAlert->draw();
    delay(2000);
    return false;
#endif

    // if wifi credentials are not set, return
    if (wifiUtilsLoadWiFiSSIDFromFlash(viewManager) == "" || wifiUtilsLoadWiFiPasswordFromFlash(viewManager) == "")
    {
        wifiConnectAlert = new Alert(viewManager->getDraw(), "WiFi credentials not saved yet.\nAdd them in the WiFi settings.", viewManager->getForegroundColor(), viewManager->getBackgroundColor());
        wifiConnectAlert->draw();
        delay(2000);
        return false;
    }
    // Clean up existing objects
    if (statusBox != nullptr)
    {
        delete statusBox;
        statusBox = nullptr;
    }

    // Create status text box
    statusBox = new TextBox(
        viewManager->getDraw(),
        0,
        320,
        viewManager->getForegroundColor(),
        viewManager->getBackgroundColor());

    // Reset state
    connectionInitiated = false;
    lastUpdate = 0;
    connectionStartTime = 0;
    statusMessage = viewManager->getWiFi().isConnected() ? "Connected" : "Initialized";

    // Set initial text
    statusBox->setText(getWiFiStatusText(viewManager).c_str());
    return true;
}

static void wifiConnectRun(ViewManager *viewManager)
{
    auto inputManager = viewManager->getInputManager();
    auto input = inputManager->getLastButton();
    auto &wifiUtil = viewManager->getWiFi();
    auto ssid = wifiUtilsLoadWiFiSSIDFromFlash(viewManager);
    auto password = wifiUtilsLoadWiFiPasswordFromFlash(viewManager);

    // Handle input
    switch (input)
    {
    case BUTTON_LEFT:
    case BUTTON_BACK:
        // Go back to previous view
        viewManager->back();
        inputManager->reset();
        return;

    case BUTTON_RIGHT:
        // Start WiFi connection if not already connecting/connected
        if (wifiUtil.getConnectionState() == WIFI_STATE_IDLE)
        {
            statusMessage = "Starting connection...";
            if (wifiUtil.connectAsync(ssid.c_str(), password.c_str()))
            {
                connectionInitiated = true;
                connectionStartTime = millis();
                statusMessage = "Connecting...";
            }
            else
            {
                statusMessage = "Failed to start connection";
            }
        }
        else if (wifiUtil.getConnectionState() == WIFI_STATE_FAILED ||
                 wifiUtil.getConnectionState() == WIFI_STATE_TIMEOUT)
        {
            // Retry connection
            wifiUtil.resetConnection();
            statusMessage = "Retrying...";
            if (wifiUtil.connectAsync(ssid.c_str(), password.c_str()))
            {
                connectionInitiated = true;
                connectionStartTime = millis();
                statusMessage = "Connecting...";
            }
            else
            {
                statusMessage = "Failed to start connection";
            }
        }
        inputManager->reset();
        break;

    case BUTTON_UP:
        wifiUtil.disconnect();
        statusMessage = "Disconnected";
        inputManager->reset();
        break;

    default:
        break;
    }

    if (connectionInitiated)
    {
        // Call updateConnection to advance the connection process
        wifiUtil.updateConnection();

        // Update status based on current state
        WiFiConnectionState currentState = wifiUtil.getConnectionState();
        switch (currentState)
        {
        case WIFI_STATE_CONNECTED:
        {
            statusMessage = "Connected successfully!";
            connectionInitiated = false;
            break;
        }
        case WIFI_STATE_FAILED:
        {
            statusMessage = "Connection failed";
            connectionInitiated = false;
            break;
        }
        case WIFI_STATE_TIMEOUT:
        {
            statusMessage = "Connection timed out";
            connectionInitiated = false;
            break;
        }
        case WIFI_STATE_CONNECTING:
        {
            statusMessage = "Connecting...";
            break;
        }
        default:
            break;
        }

        statusBox->setText(getWiFiStatusText(viewManager).c_str());
        lastUpdate = millis();
    }

    else
    {
        unsigned long currentTime = millis();
        if (currentTime - lastUpdate > 250)
        {
            statusBox->setText(getWiFiStatusText(viewManager).c_str());
            lastUpdate = currentTime;
        }
    }
}

static void wifiConnectStop(ViewManager *viewManager)
{
    // Clean up resources
    if (statusBox != nullptr)
    {
        delete statusBox;
        statusBox = nullptr;
    }
    if (wifiConnectAlert != nullptr)
    {
        delete wifiConnectAlert;
        wifiConnectAlert = nullptr;
    }

    connectionInitiated = false;
    lastUpdate = 0;
    connectionStartTime = 0;
}

static const View wifiConnectView = View("WiFi Connect", wifiConnectRun, wifiConnectStart, wifiConnectStop);
