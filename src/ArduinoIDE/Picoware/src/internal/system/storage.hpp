#pragma once
#include <LittleFS.h>
#include <ArduinoJson.h>
namespace Picoware
{
    class Storage
    {
    public:
        Storage()
        {
        }
        /// Mount (and format if needed) the LittleFS filesystem.
        bool begin() noexcept
        {
            if (!LittleFS.begin())
            {
                if (LittleFS.format())
                {
                    return LittleFS.begin();
                }
                else
                {
                    rp2040.reboot();
                }
                return false;
            }
            return true;
        }

        /// Load JSON from a file into `doc`. Returns true on success.
        bool deserialize(JsonDocument &doc, const char *filename) const noexcept
        {
            File file = LittleFS.open(filename, "r");
            if (!file)
                return false;
            auto err = deserializeJson(doc, file);
            file.close();
            return !err;
        }

        /// How much heap is still free?
        size_t freeHeap() const noexcept
        {
            return rp2040.getFreeHeap();
        }

        /// Read the entire contents of a text file into a String.
        String read(const char *filename) const
        {
            String result;
            File file = LittleFS.open(filename, "r");
            if (file)
            {
                result = file.readString();
                file.close();
            }
            return result;
        }

        /// Write a JSON document to a file. Returns true on success.
        bool serialize(const JsonDocument &doc, const char *filename) const noexcept
        {
            File file = LittleFS.open(filename, "w");
            if (!file)
                return false;
            serializeJson(doc, file);
            file.close();
            return true;
        }

        /// Write raw C‑string data to a file. Returns true on success.
        bool write(const char *filename, const char *data) const noexcept
        {
            File file = LittleFS.open(filename, "w");
            if (!file)
                return false;
            file.print(data);
            file.close();
            return true;
        }
    };
}