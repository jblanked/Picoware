#include <stdio.h>
#include "pico/stdlib.h"
#include "src/system/drivers/southbridge.h"
#include "src/system/led.hpp"
#include "src/system/wifi.hpp"
#include "src/gui/draw.hpp"

#ifdef CYW43_WL_GPIO_LED_PIN
// WiFi-specific code for Pico W or Pico 2W
#include "pico/cyw43_arch.h"
#define WIFI_SSID "your_ssid"
#define WIFI_PASSWORD "your_password"
#endif

int main()
{
    stdio_init_all();
    sb_init();

    LED led;
    Draw draw;

    draw.clearBuffer(0);
    draw.setFont(1); // 8x10 font
    draw.setTextBackground(TFT_BLACK);
#ifdef CYW43_WL_GPIO_LED_PIN
    printf("Initializing WiFi...\n");
    WiFi wifi;

    printf("Connecting to WiFi...\n");
    draw.clearBuffer(0);
    draw.text(Vector(10, 10), "Connecting to WiFi...");
    draw.swap(false);

    int retryCount = 0;
    const int MAX_RETRIES = 3;
    bool connected = false;

    while (retryCount < MAX_RETRIES && !connected)
    {
        if (retryCount > 0)
        {
            printf("Retrying WiFi connection (attempt %d/%d)...\n", retryCount + 1, MAX_RETRIES);
            draw.clearBuffer(0);
            char retryMsg[50];
            snprintf(retryMsg, sizeof(retryMsg), "Retry %d/%d...", retryCount + 1, MAX_RETRIES);
            draw.text(Vector(10, 10), retryMsg);
            draw.swap(false);
            sleep_ms(1000);
        }

        if (wifi.connectAsync(WIFI_SSID, WIFI_PASSWORD))
        {
            printf("WiFi async connection initiated (attempt %d)\n", retryCount + 1);
            int connectionAttempts = 0;
            const int MAX_CONNECTION_ATTEMPTS = 25;
            bool attemptComplete = false;

            while (connectionAttempts < MAX_CONNECTION_ATTEMPTS && !attemptComplete)
            {
                wifi.updateConnection();
                WiFiConnectionState state = wifi.getConnectionState();

                switch (state)
                {
                case WIFI_STATE_CONNECTED:
                    connected = true;
                    attemptComplete = true;
                    printf("WiFi connected successfully on attempt %d\n", retryCount + 1);
                    draw.clearBuffer(0);
                    draw.text(Vector(10, 10), "WiFi connected!");
                    led.blink();
                    led.blink();
                    led.blink();
                    draw.swap(false);
                    sleep_ms(2000);
                    break;

                case WIFI_STATE_FAILED:
                    printf("WiFi connection failed (state: %d), will retry\n", state);
                    attemptComplete = true;
                    break;

                case WIFI_STATE_TIMEOUT:
                    printf("WiFi connection timed out (state: %d), will retry\n", state);
                    attemptComplete = true;
                    wifi.resetConnection(); // Reset for next attempt
                    break;

                case WIFI_STATE_CONNECTING:
                    if (connectionAttempts % 5 == 0)
                    {
                        printf("Still connecting... %d/%d (attempt %d/%d)\n",
                               connectionAttempts, MAX_CONNECTION_ATTEMPTS, retryCount + 1, MAX_RETRIES);
                        draw.clearBuffer(0);
                        char progress[60];
                        snprintf(progress, sizeof(progress), "Connecting %d/%d",
                                 connectionAttempts / 5 + 1, MAX_CONNECTION_ATTEMPTS / 5);
                        draw.text(Vector(10, 10), progress);

                        if (retryCount > 0)
                        {
                            char attemptMsg[30];
                            snprintf(attemptMsg, sizeof(attemptMsg), "Attempt %d/%d", retryCount + 1, MAX_RETRIES);
                            draw.text(Vector(10, 30), attemptMsg);
                        }
                        draw.swap(false);
                    }
                    break;

                default:
                    break;
                }

                connectionAttempts++;
                sleep_ms(500);
            }

            if (!connected && !attemptComplete)
            {
                printf("Connection attempt %d timed out after %d seconds\n", retryCount + 1, MAX_CONNECTION_ATTEMPTS / 2);
                wifi.resetConnection();
            }
        }
        else
        {
            printf("Failed to initiate WiFi connection on attempt %d\n", retryCount + 1);
        }

        retryCount++;
    }

    if (connected && wifi.isConnected())
    {
        printf("Connected to SSID: %s\n", wifi.getConnectedSSID().c_str());
        draw.clearBuffer(0);
        draw.text(Vector(10, 10), "Scanning networks...");
        draw.swap(false);
        String networks = wifi.scan();
        draw.clearBuffer(0);
        draw.text(Vector(10, 10), "WiFi connected!");
        draw.text(Vector(10, 30), networks.c_str());
        draw.swap(false);
    }
    else
    {
        printf("WiFi connection failed after %d attempts\n", retryCount);
        draw.clearBuffer(0);
        draw.text(Vector(10, 10), "Connection failed");
        draw.text(Vector(10, 30), "Check network");
        draw.swap(false);
        led.blink();
    }
    sleep_ms(2000);
#endif

    while (true)
    {
        // Test 1: Simple text positioning demo
        printf("Testing cursor positioning...\n");

        draw.clearBuffer(0);
        draw.setCursor(Vector(10, 10));
        draw.text(draw.getCursor(), "Position: (10,10)");

        draw.setCursor(Vector(10, 30));
        draw.text(draw.getCursor(), "Position: (10,30)");

        draw.setCursor(Vector(50, 50));
        draw.text(draw.getCursor(), "Offset text");

        draw.swap(false);
        sleep_ms(2000);

        // Test 2: Word wrapping demo
        printf("Testing word wrapping...\n");

        draw.clearBuffer(0);
        draw.setFont(2); // 5x10 font for more text
        draw.text(Vector(0, 0), "This is a very long line that should wrap around to the next line automatically when it reaches the edge of the screen!");

        draw.swap(false);
        sleep_ms(2000);

        // Test 3: Mixed graphics and text
        printf("Testing mixed graphics...\n");

        draw.clearBuffer(0);
        draw.setFont(1);

        // Draw some graphics
        draw.fillRect(Vector(10, 10), Vector(100, 60), TFT_BLUE);
        draw.fillCircle(Vector(200, 50), 30, TFT_RED);

        // Add text over graphics
        draw.setTextBackground(TFT_BLUE);
        draw.text(Vector(15, 20), "Text on");
        draw.text(Vector(15, 35), "Blue Box", TFT_YELLOW);

        draw.setTextBackground(TFT_BLACK);
        draw.text(Vector(180, 45), "Circle!", TFT_WHITE);

        draw.swap(false);
        sleep_ms(2000);

        led.blink();
    }
}