#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include "../../../../internal/system/http.hpp"
#include "../../../../internal/system/view_manager.hpp"

#define FLIP_SOCIAL_SETTINGS_PATH "/flip_social_settings.json"
#define FLIP_SOCIAL_USER_PATH "/flip_social_user.json"
#define FLIP_SOCIAL_PASSWORD_PATH "/flip_social_password.json"
using namespace Picoware;

String flipSocialUtilsLoadFromFlash(ViewManager *viewManager, const char *path, const char *key)
{
    JsonDocument doc;
    auto storage = viewManager->getStorage();
    if (!storage.deserialize(doc, path))
    {
        return "";
    }
    if (!doc[key])
    {
        return "";
    }
    return doc[key].as<String>();
}
String flipSocialUtilsLoadPasswordFromFlash(ViewManager *viewManager)
{
    return flipSocialUtilsLoadFromFlash(viewManager, FLIP_SOCIAL_PASSWORD_PATH, "password");
}

String flipSocialUtilsLoadUserFromFlash(ViewManager *viewManager)
{
    return flipSocialUtilsLoadFromFlash(viewManager, FLIP_SOCIAL_USER_PATH, "user");
}

String flipSocialHttpRequest(ViewManager *viewManager, const char *method, String url = "", String payload = "")
{
    if (method == nullptr || url == "")
    {
        return "";
    }
    HTTP flipSocialHttp;
    String response = "";
    String user = flipSocialUtilsLoadUserFromFlash(viewManager);
    String password = flipSocialUtilsLoadPasswordFromFlash(viewManager);
    auto LED = viewManager->getLED();
    LED.on();
    if (user != "" && password != "")
    {

        const char *headerKeys[] = {"Content-Type", "HTTP_USER_AGENT", "HTTP_ACCEPT", "username", "password"};
        const char *headerValues[] = {"application/json", "Pico", "X-Flipper-Redirect", user.c_str(), password.c_str()};
        const int headerSize = 5;
        response = flipSocialHttp.request(method, url, payload, headerKeys, headerValues, headerSize);
    }
    else
    {
        const char *headerKeys[] = {"Content-Type", "HTTP_USER_AGENT", "HTTP_ACCEPT"};
        const char *headerValues[] = {"application/json", "Pico", "X-Flipper-Redirect"};
        const int headerSize = 3;
        response = flipSocialHttp.request(method, url, payload, headerKeys, headerValues, headerSize);
    }
    LED.off();
    return response;
}

bool flipSocialUtilsSaveToFlash(Storage storage, const char *path, const String &key, const String &value)
{
    JsonDocument doc;
    doc[key] = value;
    return storage.serialize(doc, path);
}

bool flipSocialUtilsSavePasswordToFlash(ViewManager *viewManager, const String &password)
{
    return flipSocialUtilsSaveToFlash(viewManager->getStorage(), FLIP_SOCIAL_PASSWORD_PATH, "password", password);
}

bool flipSocialUtilsSaveUserToFlash(ViewManager *viewManager, const String &user)
{
    return flipSocialUtilsSaveToFlash(viewManager->getStorage(), FLIP_SOCIAL_USER_PATH, "user", user);
}
