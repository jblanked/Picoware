_gps_alert = None
_gps_http = None
_gps_request_sent = False
_gps_request_in_progress = False
_gps_displaying_result = False
_gps_last_update = 0
_gps_dot_count = 0


def __reset_gps_state() -> None:
    """Reset flags"""
    global _gps_request_sent, _gps_request_in_progress, _gps_displaying_result

    _gps_request_sent = False
    _gps_request_in_progress = False
    _gps_displaying_result = False


def __parse_location_data(response: str) -> str:
    """Parse the location data and return a formatted response"""
    try:
        from ujson import loads

        data: dict = loads(response)

        city = data.get("city", "Unknown")
        region = data.get("region", "Unknown")
        country = data.get("country", "Unknown")
        lat = data.get("latitude", "Unknown")
        lon = data.get("longitude", "Unknown")
        ip = data.get("ip", "Unknown")

        location_text = "Your Location:\n\n"
        location_text += f"City: {city}\n"
        location_text += f"Region: {region}\n"
        location_text += f"Country: {country}\n\n"
        location_text += "Coordinates:\n"
        location_text += f"Latitude: {lat}\n"
        location_text += f"Longitude: {lon}\n\n"
        location_text += f"IP: {ip}\n\n"

        location_text += "Press CENTER to refresh\nPress LEFT to go back"

        return location_text

    except Exception as e:
        print(f"Error parsing location data: {e}")
        return ""


def start(view_manager) -> bool:
    """Start the app"""

    global _gps_alert, _gps_http

    if _gps_alert:
        del _gps_alert
        _gps_alert = None
    if _gps_http:
        del _gps_http
        _gps_http = None

    draw = view_manager.draw

    wifi = view_manager.wifi

    # if not a wifi device, return
    if not wifi:
        view_manager.alert("WiFi not available...", False)
        return False

    # if wifi isn't connected, return
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        view_manager.alert("WiFi not connected yet...", False)
        connect_to_saved_wifi(view_manager)
        return False

    from picoware.system.vector import Vector
    from picoware.system.http import HTTP

    draw.text(Vector(5, 5), "Starting GPS lookup...")
    draw.swap()

    _gps_http = HTTP()

    # reset GPS state for fresh start
    __reset_gps_state()

    return True


def run(view_manager) -> None:
    """Run the app"""

    from picoware.system.vector import Vector
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_CENTER,
    )

    global _gps_alert, _gps_http
    global _gps_request_sent, _gps_request_in_progress, _gps_displaying_result

    input_manager = view_manager.input_manager
    button = input_manager.button
    draw = view_manager.draw

    if button in (BUTTON_LEFT, BUTTON_BACK):
        input_manager.reset()
        __reset_gps_state()
        view_manager.back()
        return

    if button in (BUTTON_RIGHT, BUTTON_CENTER):
        input_manager.reset()
        __reset_gps_state()

        draw.clear(Vector(0, 0), draw.size, view_manager.background_color)
        draw.text(Vector(5, 5), "Starting GPS lookup...")
        draw.swap()

    if _gps_displaying_result:
        return

    if not _gps_request_sent and not _gps_request_in_progress:
        _gps_request_sent = True
        _gps_request_in_progress = True

        # start async request for location data
        if not _gps_http:
            from picoware.system.http import HTTP

            _gps_http = HTTP()

        _gps_http.clear_async_response()
        if not _gps_http.get_async("https://ipwhois.app/json"):
            view_manager.alert("Failed to start location request...")
            _gps_request_sent = False
            _gps_request_in_progress = False
            return

        draw.clear(Vector(0, 0), draw.size, view_manager.background_color)
        draw.text(Vector(5, 5), "Getting your location...")
        draw.swap()

    # check if the async request is complete
    if _gps_request_in_progress:

        # check if request completed (either success or failure)
        if _gps_http.is_request_complete():
            _gps_request_in_progress = False

            gps_response: str = _gps_http.response.text if _gps_http.response else ""

            if gps_response:
                # parse the location data
                location_text = __parse_location_data(gps_response)

                if location_text:
                    draw.clear(Vector(0, 0), draw.size, view_manager.background_color)
                    draw.text(
                        Vector(0, 5), location_text, view_manager.foreground_color
                    )
                else:
                    draw.clear(Vector(0, 0), draw.size, view_manager.background_color)
                    error_msg = f"Unable to parse location data.\n\nRaw Response:\n{location_text}\n\nPress LEFT to go back"
                    draw.text(Vector(5, 5), error_msg, view_manager.foreground_color)

                draw.swap()
                _gps_displaying_result = True

                # delete to cleanup resources
                # also necessary for next iteration
                del _gps_http
                _gps_http = None
            else:
                draw.clear(Vector(0, 0), draw.size, view_manager.background_color)
                error_msg = "Failed to get location data."
                if _gps_http.state == 2:  # HTTP_ISSUE
                    error_msg += "\nNetwork error or timeout."
                view_manager.alert(error_msg, True)
                return
        else:

            # show loading indicator while request is in progress
            global _gps_last_update, _gps_dot_count

            from utime import ticks_ms

            millis = int(ticks_ms())

            if millis - _gps_last_update > 500:
                _gps_last_update = millis
                _gps_dot_count = (_gps_dot_count + 1) % 4  # Cycle through 0-3

                loading_text = "Getting your location" + ("." * _gps_dot_count)
                draw.clear(Vector(0, 0), draw.size, view_manager.background_color)
                draw.text(Vector(5, 5), loading_text, view_manager.foreground_color)
                draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""

    __reset_gps_state()

    global _gps_alert, _gps_http, _gps_last_update, _gps_dot_count

    if _gps_alert:
        del _gps_alert
        _gps_alert = None
    if _gps_http:
        del _gps_http
        _gps_http = None

    _gps_last_update = 0
    _gps_dot_count = 0
