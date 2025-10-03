#pragma once
#include "../../../system/http.hpp"
#include "../../../system/view_manager.hpp"
#define FLIP_SOCIAL_DIRECTORY "picoware/flip_social"
#define FLIP_SOCIAL_SETTINGS_PATH FLIP_SOCIAL_DIRECTORY "/settings.json" // picoware/flip_social/settings.json
#define FLIP_SOCIAL_USER_PATH FLIP_SOCIAL_DIRECTORY "/username.json"     // picoware/flip_social/username.json
#define FLIP_SOCIAL_PASSWORD_PATH FLIP_SOCIAL_DIRECTORY "/password.json" // picoware/flip_social/password.json

inline String flipSocialUtilsLoadFromFlash(ViewManager *viewManager, const char *path, const char *key)
{
    auto storage = viewManager->getStorage();
    char buffer[64] = {0};
    size_t bytes_read = 0;
    if (!storage.read(path, buffer, sizeof(buffer) - 1, &bytes_read))
    {
        printf("Failed to load WiFi SSID from flash\n");
        return "";
    }
    buffer[bytes_read] = '\0'; // Ensure null termination at actual read length
    return getJsonValue(buffer, key);
}
inline String flipSocialUtilsLoadPasswordFromFlash(ViewManager *viewManager)
{
    return flipSocialUtilsLoadFromFlash(viewManager, FLIP_SOCIAL_PASSWORD_PATH, "password");
}

inline String flipSocialUtilsLoadUserFromFlash(ViewManager *viewManager)
{
    return flipSocialUtilsLoadFromFlash(viewManager, FLIP_SOCIAL_USER_PATH, "username");
}

inline bool flipSocialUtilsSaveToFlash(Storage storage, const char *path, const String &key, const String &value)
{
    std::string json = "{\"" + key + "\":\"" + value + "\"}";
    if (!storage.write(path, json.c_str(), json.size()))
    {
        printf("Failed to save %s to flash\n", key.c_str());
        return false;
    }
    return true;
}

inline bool flipSocialUtilsSavePasswordToFlash(ViewManager *viewManager, const String &password)
{
    return flipSocialUtilsSaveToFlash(viewManager->getStorage(), FLIP_SOCIAL_PASSWORD_PATH, "password", password);
}

inline bool flipSocialUtilsSaveUserToFlash(ViewManager *viewManager, const String &user)
{
    return flipSocialUtilsSaveToFlash(viewManager->getStorage(), FLIP_SOCIAL_USER_PATH, "username", user);
}
