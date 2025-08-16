#include "../system/helpers.hpp"
#include "../system/drivers/jsmn/jsmn.h"

std::string getJsonValue(const char *json, const char *key)
{
    char *value = get_json_value(key, json);
    std::string result = value ? value : "";
    free(value);
    return result;
}

std::string getJsonArrayValue(const char *json, const char *key, uint32_t index)
{
    char *value = get_json_array_value(key, index, json);
    std::string result = value ? value : "";
    free(value);
    return result;
}
