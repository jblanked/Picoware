"""Picoware CSI Radar: amplitude-based motion and spatial-change monitor."""

from math import sqrt

TARGET_SUBCARRIERS = 12
HAMPEL_WINDOW = 7
CALIBRATION_SAMPLES = 100

_MIN_VARIANCE_MARGIN = 0.00001
_MIN_CV_CHANGE = 0.02

# CSI is produced per received frame, so an idle connection yields almost none.
# Querying the gateway's DNS forwarder makes it send a reply at a steady rate.
_PROBE_INTERVAL_MS = 50
_DNS_QUERY = (
    b"\x50\x43\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    b"\x07example\x03com\x00\x00\x01\x00\x01"
)

_processor = None
_latest_metrics = None
_capture_enabled = False
_csi_enabled = False
_connecting = False
_recalibrate_requested = False
_error_message = ""
_capture_error = ""
_frame_count = 0
_fps = 0
_fps_mark = 0
_fps_frames = 0
_dropped = 0
_last_draw = 0
_probe_socket = None
_probe_address = None
_last_probe = 0


def _component_count(data):
    if data is None:
        raise ValueError("CSI data is missing")

    try:
        data_length = len(data)
    except TypeError:
        raise ValueError("CSI data must be a byte sequence")

    if data_length == 0:
        raise ValueError("CSI data is empty")
    if data_length % 2:
        raise ValueError("CSI data contains an incomplete I/Q pair")

    count = data_length // 2
    if count < TARGET_SUBCARRIERS:
        raise ValueError("CSI data contains fewer than 12 subcarriers")
    return count


def _target_indices(component_count):
    return tuple(
        index * (component_count - 1) // (TARGET_SUBCARRIERS - 1)
        for index in range(TARGET_SUBCARRIERS)
    )


def _signed_component(value):
    if not isinstance(value, int) or value < -128 or value > 255:
        raise ValueError("CSI components must be signed or unsigned 8-bit integers")
    if value > 127:
        return value - 256
    return value


def extract_target_amplitudes(data, target_indices=None):
    """Return magnitudes for 12 evenly spaced raw I/Q subcarriers."""
    count = _component_count(data)
    if target_indices is None:
        target_indices = _target_indices(count)
    if len(target_indices) != TARGET_SUBCARRIERS:
        raise ValueError("Exactly 12 target subcarriers are required")

    amplitudes = []
    for index in target_indices:
        if index < 0 or index >= count:
            raise ValueError("CSI target subcarrier index is out of range")
        real = _signed_component(data[index * 2])
        imag = _signed_component(data[index * 2 + 1])
        amplitudes.append(sqrt(real * real + imag * imag))
    return tuple(amplitudes)


def coefficient_of_variation(values):
    """Return population standard deviation divided by mean amplitude."""
    if not values:
        raise ValueError("At least one amplitude is required")

    mean = sum(values) / len(values)
    if mean <= 0:
        raise ValueError("CSI amplitudes have no measurable signal")

    squared_differences = 0.0
    for value in values:
        difference = value - mean
        squared_differences += difference * difference
    return sqrt(squared_differences / len(values)) / mean


def _mean(values):
    return sum(values) / len(values)


def _variance(values):
    mean = _mean(values)
    squared_differences = 0.0
    for value in values:
        difference = value - mean
        squared_differences += difference * difference
    return squared_differences / len(values)


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


class CSIRadarProcessor:
    """Extract 12 amplitudes and calculate filtered CV and calibrated variance."""

    def __init__(self):
        self.reset()

    def reset(self):
        self._component_count = 0
        self._target_indices = None
        self._hampel_samples = []
        self._variance_samples = []
        self.sample_count = 0
        self.baseline_cv = None
        self.baseline_variance = None
        self.change_threshold = None
        self.variance_threshold = None

    def _filter_cv(self, value):
        window = self._hampel_samples + [value]
        median = _median(window)
        deviations = [abs(sample - median) for sample in window]
        mad = _median(deviations)
        threshold = 3.0 * 1.4826 * mad

        if (mad == 0 and value != median) or abs(value - median) > threshold:
            filtered = median
        else:
            filtered = value

        if len(self._hampel_samples) >= HAMPEL_WINDOW - 1:
            self._hampel_samples.pop(0)
        self._hampel_samples.append(value)
        return filtered

    def process(self, data):
        """Process one raw CSI I/Q byte sequence and return current metrics."""
        component_count = _component_count(data)
        if self._component_count and component_count != self._component_count:
            self.reset()
        self._component_count = component_count
        if self._target_indices is None:
            self._target_indices = _target_indices(component_count)

        amplitudes = extract_target_amplitudes(data, self._target_indices)
        raw_cv = coefficient_of_variation(amplitudes)
        filtered_cv = self._filter_cv(raw_cv)

        if len(self._variance_samples) >= CALIBRATION_SAMPLES:
            self._variance_samples.pop(0)
        self._variance_samples.append(filtered_cv)
        self.sample_count += 1

        moving_variance = None
        motion = False
        spatial_change = False
        if len(self._variance_samples) == CALIBRATION_SAMPLES:
            moving_variance = _variance(self._variance_samples)
            if self.baseline_cv is None:
                self.baseline_cv = _mean(self._variance_samples)
                self.baseline_variance = moving_variance
                self.variance_threshold = self.baseline_variance + max(
                    self.baseline_variance * 3.0, _MIN_VARIANCE_MARGIN
                )
                self.change_threshold = max(
                    sqrt(self.baseline_variance) * 3.0, _MIN_CV_CHANGE
                )
            else:
                motion = moving_variance > self.variance_threshold
                spatial_change = (
                    abs(filtered_cv - self.baseline_cv) > self.change_threshold
                )

        return (
            amplitudes,
            raw_cv,
            filtered_cv,
            min(self.sample_count, CALIBRATION_SAMPLES),
            self.baseline_cv is not None,
            moving_variance,
            self.baseline_cv,
            self.variance_threshold,
            motion,
            spatial_change,
        )


def _csi_callback(record, _available, dropped):
    """Process one CSI frame and retain only the latest display metrics."""
    global _latest_metrics, _capture_error, _frame_count, _dropped
    global _recalibrate_requested

    if not _capture_enabled:
        return

    processor = _processor
    if processor is None:
        return

    _frame_count += 1
    _dropped = dropped
    if _recalibrate_requested:
        processor.reset()
        _latest_metrics = None
        _capture_error = ""
        _recalibrate_requested = False

    try:
        _latest_metrics = processor.process(record[5])
        _capture_error = ""
    except (IndexError, TypeError, ValueError) as error:
        _capture_error = str(error)


def _open_probe(wifi):
    """Open a non-blocking UDP socket aimed at the gateway's DNS port."""
    global _probe_socket, _probe_address

    _close_probe()
    try:
        import socket

        gateway = wifi.wlan.ifconfig()[2]
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        _probe_socket = sock
        _probe_address = (gateway, 53)
    except Exception:
        _close_probe()


def _close_probe():
    global _probe_socket, _probe_address

    if _probe_socket is not None:
        try:
            _probe_socket.close()
        except Exception:
            pass
    _probe_socket = None
    _probe_address = None


def _send_probe():
    """Send one gateway query and drain replies so lwIP does not queue them."""
    sock = _probe_socket
    if sock is None:
        return

    try:
        sock.sendto(_DNS_QUERY, _probe_address)
    except OSError:
        pass
    for _ in range(8):
        try:
            sock.recv(128)
        except OSError:
            break


def _start_capture(view_manager):
    global _capture_enabled, _csi_enabled, _connecting, _error_message

    wifi = view_manager.wifi
    if wifi is None:
        _error_message = "WiFi is not available"
        _connecting = False
        return False

    _capture_enabled = True
    if not wifi.csi(True, buffer_size=32, callback=_csi_callback):
        _capture_enabled = False
        _csi_enabled = False
        _connecting = False
        _error_message = wifi.error or "Could not start CSI capture"
        return False

    _csi_enabled = True
    _connecting = False
    _error_message = ""
    _open_probe(wifi)
    return True


def _connect_or_start(view_manager):
    global _connecting, _error_message

    wifi = view_manager.wifi
    if wifi is None:
        _error_message = "WiFi is not available"
        return False
    if wifi.is_connected():
        return _start_capture(view_manager)

    from picoware.applications.wifi.utils import connect_to_saved_wifi

    if connect_to_saved_wifi(view_manager):
        _connecting = True
        _error_message = ""
        return True

    _connecting = False
    _error_message = wifi.error or "Connect to WiFi and save credentials first"
    return False


def start(view_manager):
    """Start CSI capture, connecting to the saved network if necessary."""
    global _processor, _latest_metrics, _capture_enabled, _csi_enabled
    global _connecting, _recalibrate_requested, _error_message, _capture_error
    global _frame_count, _fps, _fps_mark, _fps_frames, _dropped, _last_draw
    global _last_probe

    if view_manager.wifi is None:
        view_manager.alert("WiFi is not available")
        return False

    _processor = CSIRadarProcessor()
    _latest_metrics = None
    _capture_enabled = False
    _csi_enabled = False
    _connecting = False
    _recalibrate_requested = False
    _error_message = ""
    _capture_error = ""
    _frame_count = 0
    _fps = 0
    _fps_mark = 0
    _fps_frames = 0
    _dropped = 0
    _last_draw = 0
    _last_probe = 0

    if not _connect_or_start(view_manager):
        view_manager.alert(_error_message, True)
        _processor = None
        return False
    return True


def _draw(view_manager):
    from picoware.system.colors import (
        TFT_GREEN,
        TFT_ORANGE,
        TFT_RED,
        TFT_WHITE,
        TFT_YELLOW,
    )
    from picoware.system.vector import Vector

    draw = view_manager.draw
    draw.erase()
    width = draw.size.x
    font_width = max(1, draw.font_size.x)
    line_height = max(1, draw.font_size.y + 1)
    footer_y = max(0, draw.size.y - draw.font_size.y - 2)
    y = 2

    title = "CSI RADAR - 12 SUBCARRIERS"
    draw.text(Vector(max(0, (width - draw.len(title)) // 2), y), title)
    y += line_height

    metrics = _latest_metrics
    if _error_message:
        status = "ERROR: " + _error_message
        status_color = TFT_RED
    elif _connecting:
        status = "CONNECTING TO WIFI"
        status_color = TFT_YELLOW
    elif _capture_error:
        status = "CSI DATA ERROR: " + _capture_error
        status_color = TFT_RED
    elif _recalibrate_requested:
        status = "CALIBRATING 0/100"
        status_color = TFT_YELLOW
    elif not _csi_enabled or metrics is None:
        status = "WAITING FOR CSI TRAFFIC"
        status_color = TFT_YELLOW
    else:
        sample_count = metrics[3]
        calibrated = metrics[4]
        motion = metrics[8]
        spatial_change = metrics[9]
        if not calibrated:
            status = "CALIBRATING %d/100" % sample_count
            status_color = TFT_YELLOW
        elif motion:
            status = "MOTION DETECTED"
            status_color = TFT_ORANGE
        elif spatial_change:
            status = (
                "PRESENT / SPACE CHANGE"
                if width < 220
                else "PRESENCE / SPATIAL CHANGE"
            )
            status_color = TFT_GREEN
        else:
            status = "QUIET"
            status_color = TFT_WHITE

    while draw.len(status) > width - 4 and len(status) > 4:
        status = status[:-1]
    draw.text(Vector(2, y), status, status_color)
    y += line_height

    if width < 180:
        traffic_text = "%d/s D%d" % (_fps, _dropped)
    else:
        traffic_text = "CSI %d frames/s DROP:%d" % (_fps, _dropped)
    draw.text(Vector(2, y), traffic_text)
    y += line_height

    if metrics is not None:
        amplitudes = metrics[0]
        raw_cv = metrics[1]
        filtered_cv = metrics[2]
        calibrated = metrics[4]
        moving_variance = metrics[5]
        variance_threshold = metrics[7]

        if width < 180:
            cv_text = "C%.3f H%.3f" % (raw_cv, filtered_cv)
        else:
            cv_text = "CV %.4f HAMP %.4f" % (raw_cv, filtered_cv)
        draw.text(Vector(2, y), cv_text)
        y += line_height

        if calibrated:
            if width < 180:
                variance_text = "V%.5f T%.5f" % (
                    moving_variance,
                    variance_threshold,
                )
            else:
                variance_text = "VAR100 %.6f THR %.6f" % (
                    moving_variance,
                    variance_threshold,
                )
        else:
            variance_text = "VAR100: calibrating"
        draw.text(Vector(2, y), variance_text)
        y += line_height

        chars_per_line = max(1, width // font_width)
        group_size = max(1, min(12, (chars_per_line - 5) // 4))
        for first in range(0, len(amplitudes), group_size):
            last = min(len(amplitudes), first + group_size)
            values = " ".join(
                "%d" % int(amplitudes[index]) for index in range(first, last)
            )
            text = "A%d-%d %s" % (first, last - 1, values)
            if y + draw.font_size.y > footer_y:
                break
            draw.text(Vector(2, y), text)
            y += line_height

    if width < 180:
        footer = "CTR:CAL B:EXIT"
    elif width < 240:
        footer = "CENTER:CAL BACK:EXIT"
    else:
        footer = "CENTER:RECALIBRATE BACK:EXIT"
    draw.text(Vector(max(0, (width - draw.len(footer)) // 2), footer_y), footer)
    draw.swap()


def run(view_manager):
    """Update CSI state, render current readings, and handle controls."""
    from utime import ticks_ms, ticks_diff
    from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER
    from picoware.system.wifi import WIFI_STATE_ISSUE, WIFI_STATE_TIMEOUT

    global _connecting, _error_message, _last_draw, _recalibrate_requested
    global _last_probe, _fps, _fps_mark, _fps_frames

    button = view_manager.button
    if button == BUTTON_BACK:
        view_manager.back()
        return
    if button == BUTTON_CENTER:
        if _csi_enabled:
            _recalibrate_requested = True
        elif not _connect_or_start(view_manager):
            _error_message = _error_message or "Could not start CSI radar"

    wifi = view_manager.wifi
    if _connecting and wifi is not None:
        if wifi.is_connected():
            _start_capture(view_manager)
        elif wifi.status() in (WIFI_STATE_ISSUE, WIFI_STATE_TIMEOUT):
            _connecting = False
            _error_message = wifi.error or "WiFi connection failed"

    now = ticks_ms()
    if _csi_enabled:
        if ticks_diff(now, _last_probe) >= _PROBE_INTERVAL_MS:
            _last_probe = now
            _send_probe()
        if ticks_diff(now, _fps_mark) >= 1000:
            elapsed = ticks_diff(now, _fps_mark)
            _fps = (_frame_count - _fps_frames) * 1000 // elapsed if _fps_mark else 0
            _fps_frames = _frame_count
            _fps_mark = now

    if ticks_diff(now, _last_draw) < 200:
        return
    _last_draw = now
    _draw(view_manager)


def stop(view_manager):
    """Stop CSI capture and release app state."""
    from gc import collect

    global _processor, _latest_metrics, _capture_enabled, _csi_enabled
    global _connecting, _recalibrate_requested, _error_message, _capture_error
    global _frame_count, _fps, _fps_mark, _fps_frames, _dropped, _last_draw
    global _last_probe

    _capture_enabled = False
    _close_probe()
    wifi = view_manager.wifi
    if _csi_enabled and wifi is not None and not wifi.csi(False):
        view_manager.log("[CSI Radar] Failed to stop CSI capture: %s" % wifi.error, 2)

    _processor = None
    _latest_metrics = None
    _csi_enabled = False
    _connecting = False
    _recalibrate_requested = False
    _error_message = ""
    _capture_error = ""
    _frame_count = 0
    _fps = 0
    _fps_mark = 0
    _fps_frames = 0
    _dropped = 0
    _last_draw = 0
    _last_probe = 0
    collect()
