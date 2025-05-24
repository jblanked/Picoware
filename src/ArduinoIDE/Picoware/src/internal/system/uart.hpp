#pragma once
#include <Arduino.h>
namespace Picoware
{
    class UART
    {
    public:
        /// Construct and begin at `baudrate` on pins TX=0, RX=1 by default.
        explicit UART(uint32_t baudrate,
                      uint8_t txPin = 0,
                      uint8_t rxPin = 1) noexcept
            : serial(new SerialPIO(txPin, rxPin))
        {
            serial->begin(baudrate);
        }

        /// Clean up SerialPIO
        ~UART() noexcept
        {
            delete serial;
        }

        /// How many bytes are waiting?
        size_t available() const noexcept
        {
            return serial->available();
        }

        /// (Re‑)initialize baud rate.
        void begin(uint32_t baudrate) noexcept
        {
            serial->begin(baudrate);
        }

        /// Wait until outgoing data is sent.
        void flush() noexcept
        {
            serial->flush();
        }

        /// Discard any incoming data.
        void clearBuffer() noexcept
        {
            while (available() > 0)
            {
                read();
            }
        }

        /// Print a string (no newline).
        void print(const String &str) const
        {
            serial->print(str);
        }

        /// printf‑style formatted output.
        void printf(const char *format, ...) const
        {
            va_list args;
            va_start(args, format);
            serial->printf(format, args);
            va_end(args);
        }

        /// Print a string with newline.
        void println(const String &str = "") const
        {
            serial->println(str);
        }

        /// Read one byte (or 0 if none).
        uint8_t read() noexcept
        {
            return serial->read();
        }

        /// Read up to `size` bytes into `buffer`.
        size_t readBytes(uint8_t *buffer, size_t size)
        {
            return serial->readBytes(buffer, size);
        }

        /// Read one line (up to `\n`), trimmed.
        String readSerialLine() const
        {
            String s = serial->readStringUntil('\n');
            s.trim();
            return s;
        }

        /// Read until the given terminator string or timeout (ms), trimmed.
        String readStringUntilString(const String &terminator,
                                     uint32_t timeout = 5000)
        {
            String result;
            unsigned long start = millis();
            while (millis() - start < timeout)
            {
                if (available() > 0)
                {
                    char c = static_cast<char>(read());
                    result += c;
                    if (result.endsWith(terminator))
                    {
                        result.remove(result.length() - terminator.length());
                        break;
                    }
                }
                else
                {
                    delay(1);
                }
            }
            result.trim();
            return result;
        }

        /// Change the inter‑byte timeout for readStringUntil(), etc.
        void setTimeout(uint32_t timeout) noexcept
        {
            serial->setTimeout(timeout);
        }

        /// Write raw bytes out.
        size_t write(const uint8_t *buffer, size_t size)
        {
            return serial->write(buffer, size);
        }

    private:
        SerialPIO *serial;
    };

} // namespace Picoware
