_weather_alert = None
_weather_http = None
_location_request_sent = False
_location_request_in_progress = False
_weather_request_sent = False
_weather_request_in_progress = False
_displaying_result_w = False
_ip_address = ""
_location_last_update = 0
_location_dot_count = 0
_weather_last_update = 0
_weather_dot_count = 0


def __filter_degree_symbol(input_str: str) -> str:
    """Filter out degree symbols from the input string"""
    result = ""
    i = 0
    while i < len(input_str):
        # Skip the degree symbol (° is 0xC2 0xB0 in UTF-8)
        if (
            i < len(input_str) - 1
            and ord(input_str[i]) == 0xC2
            and ord(input_str[i + 1]) == 0xB0
        ):
            i += 2  # Skip both bytes of the degree symbol
            continue
        result += input_str[i]
        i += 1
    return result


def __reset_weather_state() -> None:
    """Reset all weather state flags"""
    global _location_request_sent, _location_request_in_progress
    global _weather_request_sent, _weather_request_in_progress
    global _displaying_result_w, _ip_address

    _location_request_sent = False
    _location_request_in_progress = False
    _weather_request_sent = False
    _weather_request_in_progress = False
    _displaying_result_w = False
    _ip_address = ""


def __weather_alert_and_return(view_manager, message: str) -> None:
    """Show alert and return to previous view"""
    global _weather_alert

    if _weather_alert:
        del _weather_alert
        _weather_alert = None

    from picoware.gui.alert import Alert
    from time import sleep

    _weather_alert = Alert(
        view_manager.get_draw(),
        message,
        view_manager.get_foreground_color(),
        view_manager.get_background_color(),
    )
    _weather_alert.draw("Error")
    sleep(2)


def start(view_manager) -> bool:
    """Start the weather app"""
    global _weather_alert, _weather_http

    if _weather_alert:
        del _weather_alert
        _weather_alert = None
    if _weather_http:
        del _weather_http
        _weather_http = None

    draw = view_manager.get_draw()
    
    wifi = view_manager.get_wifi()
    
    # if not a wifi device, return
    if not wifi:
        from picoware.gui.alert import Alert
        from time import sleep

        _weather_alert = Alert(
            draw,
            "WiFi not available..",
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
        )
        _weather_alert.draw("Error")
        sleep(2)
        return False

    # Check if WiFi is connected
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi
        __weather_alert_and_return(view_manager, "WiFi not connected yet.")
        connect_to_saved_wifi(view_manager)
        return False

    from picoware.system.vector import Vector
    from picoware.system.http import HTTP

    draw.text(Vector(5, 5), "Fetching location data...")
    draw.swap()

    _weather_http = HTTP()

    # Reset weather state for fresh start
    __reset_weather_state()

    return True


def run(view_manager) -> None:
    """Run the weather app"""
    from picoware.system.vector import Vector
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    global _weather_alert, _weather_http
    global _location_request_sent, _location_request_in_progress
    global _weather_request_sent, _weather_request_in_progress
    global _displaying_result_w, _ip_address
    global _location_last_update, _location_dot_count
    global _weather_last_update, _weather_dot_count

    input_manager = view_manager.get_input_manager()
    button = input_manager.get_last_button()
    draw = view_manager.get_draw()

    if button in (BUTTON_LEFT, BUTTON_BACK):
        input_manager.reset()
        __reset_weather_state()
        view_manager.back()
        return

    if button in (BUTTON_RIGHT, BUTTON_CENTER):
        input_manager.reset()
        __reset_weather_state()
        draw.clear(Vector(0, 0), draw.size, view_manager.get_background_color())
        draw.text(Vector(5, 5), "Fetching location data...")
        draw.swap()

    if _displaying_result_w:
        return

    # Step 1: Get location data if not already requested
    if not _location_request_sent and not _location_request_in_progress:
        _location_request_sent = True
        _location_request_in_progress = True

        if not _weather_http:
            from picoware.system.http import HTTP

            _weather_http = HTTP()

        _weather_http.clear_async_response()
        if not _weather_http.get_async("https://ipwhois.app/json/"):
            __weather_alert_and_return(view_manager, "Failed to start location request")
            view_manager.back()
            return

        draw.clear(Vector(0, 0), draw.size, view_manager.get_background_color())
        draw.text(Vector(5, 5), "Getting your location...")
        draw.swap()

    # Process async location request
    if _location_request_in_progress:
        if _weather_http.is_request_complete():
            _location_request_in_progress = False

            location_response = _weather_http.response

            if location_response:
                try:
                    from ujson import loads

                    data = loads(location_response)
                    _ip_address = data.get("ip", "")

                    if _ip_address:
                        draw.clear(
                            Vector(0, 0), draw.size, view_manager.get_background_color()
                        )
                        draw.text(Vector(5, 5), "Fetching Weather data...")
                        draw.swap()

                        del _weather_http
                        _weather_http = None

                        return
                    else:
                        __weather_alert_and_return(
                            view_manager, "Failed to get location coordinates."
                        )
                        view_manager.back()
                        return

                except Exception as e:
                    print(f"Error parsing location data: {e}")
                    __weather_alert_and_return(
                        view_manager, "Failed to parse location data."
                    )
                    return
            else:
                error_msg = "Failed to fetch location data."
                if _weather_http.state == 2:  # HTTP_ISSUE
                    error_msg += "\nNetwork error or timeout."
                __weather_alert_and_return(view_manager, error_msg)
                view_manager.back()
                return
        else:
            # Show loading indicator for location
            from utime import ticks_ms

            millis = int(ticks_ms())

            if millis - _location_last_update > 500:
                _location_last_update = millis
                _location_dot_count = (_location_dot_count + 1) % 4

                loading_text = "Getting your location" + ("." * _location_dot_count)
                draw.clear(Vector(0, 0), draw.size, view_manager.get_background_color())
                draw.text(
                    Vector(5, 5), loading_text, view_manager.get_foreground_color()
                )
                draw.swap()
        return

    # Step 2: Get weather data if we have IP address but haven't requested weather yet
    if _ip_address and not _weather_request_sent and not _weather_request_in_progress:
        _weather_request_sent = True
        _weather_request_in_progress = True

        weather_url = f"https://wttr.in/@{_ip_address}?format=%C,%t,%h"

        if not _weather_http:
            from picoware.system.http import HTTP

            _weather_http = HTTP()

        if not _weather_http.get_async(weather_url):
            __weather_alert_and_return(view_manager, "Failed to start weather request")
            view_manager.back()
            return

        draw.clear(Vector(0, 0), draw.size, view_manager.get_background_color())
        draw.text(Vector(5, 5), "Getting weather data...")
        draw.swap()

    # Process async weather request
    if _weather_request_in_progress:
        if _weather_http.is_request_complete():
            _weather_request_in_progress = False

            weather_response = _weather_http.response

            if weather_response:
                # wttr.in has each value separated by a comma
                values = weather_response.split(",")

                # Extract individual values (condition, temperature, humidity)
                condition = values[0] if len(values) > 0 else "N/A"
                temperature = (
                    __filter_degree_symbol(values[1]) if len(values) > 1 else "N/A"
                )
                humidity = values[2] if len(values) > 2 else "N/A"

                total_data = "Current Weather:\n\n"
                total_data += f"Condition: {condition}\n"
                total_data += f"Temperature: {temperature}\n"
                total_data += f"Humidity: {humidity}\n\n"
                total_data += "Press CENTER to refresh\nPress LEFT to go back"

                draw.clear(Vector(0, 0), draw.size, view_manager.get_background_color())
                draw.text(Vector(0, 5), total_data, view_manager.get_foreground_color())
                draw.swap()
                _displaying_result_w = True

                # Cleanup resources for next iteration
                del _weather_http
                _weather_http = None
                return
            else:
                error_msg = "Failed to fetch weather data."
                if _weather_http.state == 2:  # HTTP_ISSUE
                    error_msg += "\nNetwork error or timeout."
                __weather_alert_and_return(view_manager, error_msg)
                view_manager.back()
                return
        else:
            # Show loading indicator for weather
            from utime import ticks_ms

            millis = int(ticks_ms())

            if millis - _weather_last_update > 500:
                _weather_last_update = millis
                _weather_dot_count = (_weather_dot_count + 1) % 4

                loading_text = "Getting weather data" + ("." * _weather_dot_count)
                draw.clear(Vector(0, 0), draw.size, view_manager.get_background_color())
                draw.text(
                    Vector(5, 5), loading_text, view_manager.get_foreground_color()
                )
                draw.swap()


def stop(view_manager) -> None:
    """Stop the weather app"""
    from gc import collect

    __reset_weather_state()

    global _weather_alert, _weather_http
    global _location_last_update, _location_dot_count
    global _weather_last_update, _weather_dot_count

    if _weather_alert:
        del _weather_alert
        _weather_alert = None
    if _weather_http:
        del _weather_http
        _weather_http = None

    _location_last_update = 0
    _location_dot_count = 0
    _weather_last_update = 0
    _weather_dot_count = 0

    collect()
