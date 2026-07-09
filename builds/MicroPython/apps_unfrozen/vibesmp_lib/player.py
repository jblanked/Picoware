from gc import collect
import time
from vibesmp_lib.id3 import parse_id3
from vibesmp_lib.utils import format_time
try:
    from picoware.system.audio import decode_radio_diag
except ImportError:
    decode_radio_diag = None

class Player:
    _RADIO_DEBUG = False
    _RADIO_SERVICE_POLL_MS = 10
    _RADIO_BACKEND_POLL_MS = 2000
    _RADIO_CACHE_VERSION = 4
    _RADIO_PROFILE_CACHE_LIMIT = 12
    _RADIO_RETRY_LIMIT = 2
    _RADIO_RETRY_DELAY_MS = 1500
    _RADIO_VERIFY_GRACE_MS = 2000
    _RADIO_DIAG_POLL_MS = 1000
    _RADIO_FIFO_WARN_BYTES = 32 * 1024
    _RADIO_NET_STALL_WARN_DELTA = 20

    def _audio_has_method(self, name):
        if hasattr(self.audio, name):
            return True
        try:
            return hasattr(self.audio.__class__, name)
        except Exception:
            return False

    def _audio_call(self, name, *args):
        method = getattr(self.audio, name, None)
        if method:
            return method(*args)
        method = getattr(self.audio.__class__, name, None)
        if method:
            return method(self.audio, *args)
        raise AttributeError("Audio has no method " + name)

    def __init__(self, audio, storage=None):
        self.audio = audio
        self.storage = storage
        self.loop_mode = 0  # 0: None, 1: Loop One, 2: Loop All
        self.user_stopped = True
        self._paused_pos = 0
        self._paused = False
        self._seeking = False
        self._recovering = False
        self.current_track = ""
        self.radio_mode = False
        self.radio_name = ""
        self.radio_url = ""
        self.radio_active_id = None
        self.radio_status = "Stopped"
        self.radio_failure_reason = ""
        self.radio_failure_category = ""
        self.radio_retry_count = 0
        self.radio_retry_allowed = False
        self.radio_status_changed_ms = 0
        self._radio_started_ms = 0
        self._radio_disconnect_logged = False
        self._radio_profile_cache = None
        self._radio_profile_cache_dirty = False
        self._radio_retry_due_ms = 0
        self._radio_retry_source = ""
        self._radio_has_connected = False
        self._radio_connect_phase = ""
        self._radio_connect_runtime = False
        self._radio_connect_source = ""
        self._radio_first_profile = None
        self._radio_first_probe = None
        self._radio_candidates = None
        self._radio_candidate_idx = 0
        self._radio_profile_idx = 0
        self._radio_seen_attempts = None
        self._radio_verify_original_url = ""
        self._radio_verify_play_url = ""
        self._radio_verify_profile = None
        self._radio_verify_started_ms = 0
        self._radio_verify_fail_phase = ""
        self._radio_backend_state_cache = None
        self._radio_backend_playing_cache = False
        self._radio_service_poll_ms = 0
        self._radio_backend_poll_ms = 0
        self._radio_perf_start_ms = 0
        self._radio_perf_buffering_seen = False
        self._radio_perf_playing_seen = False
        self._radio_diag_poll_ms = 0
        self._radio_diag_last = None
        self._radio_diag_low_since_ms = 0
        self._radio_diag_warned_low = False
        self._radio_diag_warned_network = False
        self._volume = 100
        self._audio_call("set_volume", self._volume)
        self._last_dur = 0
        self._sr_ch = 88200 # Cached sample_rate * channels (stereo 44.1kHz default)
        self.current_id3 = {"title": "", "artist": ""}
        self.last_play_time = 0 # Timestamp of last play() or resume()
        self._last_pos_check = 0
        self._last_hw_pos = -1
        self._stall_count = 0
        self._io_throttled_until = 0
        self._last_hw_info = None
        self._last_info_time = 0
        self._paused_pos_resume = 0 # Saved position in seconds from previous session
        self._play_busy_until = 0

        # Performance Cache
        self._dur_str_cache = "--:--" # Cached total time string
        self._meta_pending = False
        self.pre_play_callback = None
        self.perf_counters = None
        self._perf_enabled = False

    def set_perf_counters(self, counters):
        self.perf_counters = counters
        self._perf_enabled = counters is not None
        if not self._perf_enabled:
            self._radio_perf_start_ms = 0
            self._radio_perf_buffering_seen = False
            self._radio_perf_playing_seen = False

    def _perf_inc(self, name):
        if not self._perf_enabled:
            return
        counters = self.perf_counters
        counters[name] = counters.get(name, 0) + 1

    def _perf_timing(self, prefix, elapsed):
        if not self._perf_enabled:
            return
        counters = self.perf_counters
        count_key = prefix + "_count"
        total_key = prefix + "_total_ms"
        max_key = prefix + "_max_ms"
        min_key = prefix + "_min_ms"
        counters[count_key] = counters.get(count_key, 0) + 1
        counters[total_key] = counters.get(total_key, 0) + elapsed
        if elapsed > counters.get(max_key, 0):
            counters[max_key] = elapsed
        current_min = counters.get(min_key, None)
        if current_min is None or elapsed < current_min:
            counters[min_key] = elapsed

    def _perf_radio_mark(self, status):
        if not self._perf_enabled or not self._radio_perf_start_ms:
            return
        now = time.ticks_ms()
        if status == "Buffering" and not self._radio_perf_buffering_seen:
            self._radio_perf_buffering_seen = True
            self._perf_timing("radio_start_to_buffering", time.ticks_diff(now, self._radio_perf_start_ms))
        elif status == "Playing" and not self._radio_perf_playing_seen:
            self._radio_perf_playing_seen = True
            self._perf_timing("radio_start_to_playing", time.ticks_diff(now, self._radio_perf_start_ms))

    def _radio_debug(self, message):
        if not self._RADIO_DEBUG:
            return
        print("[VIBESMP][RADIO] {}".format(message))

    def _radio_debugf(self, template, *args):
        if self._RADIO_DEBUG:
            self._radio_debug(template.format(*args))

    def _set_radio_status(self, status, reason=None, category=None):
        prev = self.radio_status
        next_reason = self.radio_failure_reason if reason is None else reason
        next_category = self.radio_failure_category if category is None else category
        changed = (
            prev != status or
            self.radio_failure_reason != next_reason or
            self.radio_failure_category != next_category
        )
        if changed:
            self.radio_status = status
            self.radio_failure_reason = next_reason
            self.radio_failure_category = next_category
            self.radio_status_changed_ms = time.ticks_ms()
            if self._perf_enabled:
                self._perf_radio_mark(status)
            if self._RADIO_DEBUG:
                msg = "radio status {} -> {}".format(prev, status)
                if reason:
                    msg += " ({})".format(reason)
                self._radio_debug(msg)
        if changed and status != "Disconnected":
            self._radio_disconnect_logged = False
        return changed

    def _reset_radio_runtime_state(self):
        self.radio_failure_reason = ""
        self.radio_failure_category = ""
        self.radio_retry_count = 0
        self.radio_retry_allowed = False
        self._radio_retry_due_ms = 0
        self._radio_retry_source = ""
        self._radio_has_connected = False
        self._radio_started_ms = 0
        self._radio_disconnect_logged = False
        self._reset_radio_connect_state()
        self.radio_status_changed_ms = time.ticks_ms()

    def _reset_radio_diag_state(self):
        self._radio_diag_poll_ms = 0
        self._radio_diag_last = None
        self._radio_diag_low_since_ms = 0
        self._radio_diag_warned_low = False
        self._radio_diag_warned_network = False

    def _reset_radio_connect_state(self):
        self._radio_connect_phase = ""
        self._radio_connect_runtime = False
        self._radio_connect_source = ""
        self._radio_first_profile = None
        self._radio_first_probe = None
        self._radio_candidates = None
        self._radio_candidate_idx = 0
        self._radio_profile_idx = 0
        self._radio_seen_attempts = None
        self._radio_backend_state_cache = None
        self._radio_backend_playing_cache = False
        self._radio_service_poll_ms = 0
        self._radio_backend_poll_ms = 0
        self._reset_radio_diag_state()
        self._radio_verify_original_url = ""
        self._radio_verify_play_url = ""
        self._radio_verify_profile = None
        self._radio_verify_started_ms = 0
        self._radio_verify_fail_phase = ""

    def _mark_radio_healthy(self):
        self.radio_retry_allowed = True
        self._radio_has_connected = True
        self.radio_failure_reason = ""
        self.radio_failure_category = ""
        self._radio_retry_due_ms = 0
        self._radio_retry_source = ""
        self._radio_disconnect_logged = False

    def _radio_normalize_url(self, url):
        if not isinstance(url, str):
            return ""
        url = url.strip()
        lower = url.lower()
        if lower.startswith("http://"):
            rest = url[7:]
        elif lower.startswith("https://"):
            rest = url[8:]
        else:
            return ""
        if not rest or rest.startswith("/") or rest.startswith("?") or rest.startswith("#"):
            return ""
        host = rest.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        if not host or any(ch.isspace() for ch in host):
            return ""
        if host == "." or host == ".." or host.startswith(".") or host.endswith("."):
            return ""
        return url

    def _schedule_radio_retry(self, source):
        self._reset_radio_connect_state()
        if not self.radio_retry_allowed or self.radio_retry_count >= self._RADIO_RETRY_LIMIT:
            self._set_radio_status("Disconnected", source, category="runtime_disconnect")
            self._radio_disconnect_logged = True
            self._radio_retry_due_ms = 0
            self._radio_retry_source = ""
            self._flush_radio_profile_cache(clear=True)
            return False
        self.radio_retry_count += 1
        self._radio_retry_source = source
        self._radio_retry_due_ms = time.ticks_add(time.ticks_ms(), self._RADIO_RETRY_DELAY_MS)
        self._audio_call("stop")
        self._set_radio_status(
            "Retrying",
            "{} retry {}/{}".format(source, self.radio_retry_count, self._RADIO_RETRY_LIMIT),
            category="runtime_disconnect",
        )
        self._radio_disconnect_logged = True
        return True

    def _retry_radio_if_due(self):
        if not self._radio_retry_due_ms:
            return False
        if time.ticks_diff(time.ticks_ms(), self._radio_retry_due_ms) < 0:
            return False
        retry_source = self._radio_retry_source or "retry"
        self._radio_retry_due_ms = 0
        self._radio_retry_source = ""
        self._radio_debugf(
            "retrying radio stream {!r} attempt {}/{}",
            self.radio_url, self.radio_retry_count, self._RADIO_RETRY_LIMIT
        )
        self._start_radio_connect(runtime=True, source=retry_source)
        return True

    def _radio_info_snapshot(self):
        return "radio info disabled backend_state={!r}".format(self._radio_backend_state())

    def _radio_diag_snapshot(self, diag):
        if decode_radio_diag:
            return decode_radio_diag(diag)
        names = (
            "underruns",
            "rebuffer_count",
            "last_fatal_error",
            "last_fatal_state",
            "min_pcm_ring_fill",
            "max_compressed_fifo_fill",
            "current_pcm_ring_fill",
            "current_compressed_fifo_fill",
            "compressed_fifo_size",
            "compressed_fifo_backend",
            "pcm_low_watermark",
            "pcm_resume_target",
            "startup_compressed_target",
            "compressed_low_watermark",
            "compressed_resume_target",
            "decode_no_data_count",
            "network_no_data_count",
        )
        try:
            if diag is None:
                return None
            return dict((names[i], diag[i]) for i in range(min(len(names), len(diag))))
        except (TypeError, IndexError):
            return diag

    def service_radio(self, force=False):
        if not self.radio_mode or not self._audio_has_method("radio_service"):
            return False
        now = time.ticks_ms()
        if (
            force
            or not self._radio_service_poll_ms
            or time.ticks_diff(now, self._radio_service_poll_ms) >= self._RADIO_SERVICE_POLL_MS
        ):
            try:
                self._audio_call("radio_service")
            except Exception:
                return False
            self._radio_service_poll_ms = now
            return True
        return False

    def _sample_radio_diag(self, force=False):
        if not self.radio_mode:
            return None
        now = time.ticks_ms()
        if (
            not force
            and self._radio_diag_poll_ms
            and time.ticks_diff(now, self._radio_diag_poll_ms) < self._RADIO_DIAG_POLL_MS
        ):
            return self._radio_diag_last
        try:
            diag = self._radio_diag_snapshot(getattr(self.audio, "radio_diag", None))
        except Exception:
            return self._radio_diag_last
        if not isinstance(diag, dict):
            self._radio_diag_last = diag
            self._radio_diag_poll_ms = now
            return diag

        previous = self._radio_diag_last if isinstance(self._radio_diag_last, dict) else None
        self._radio_diag_last = diag
        self._radio_diag_poll_ms = now
        if self._RADIO_DEBUG:
            self._radio_debugf(
                "diag state={} fifo={}/{} pcm={} underruns={} rebuf={} fatal={} net_no_data={}",
                self._radio_backend_state_cache,
                diag.get("current_compressed_fifo_fill", 0),
                diag.get("compressed_fifo_size", 0),
                diag.get("current_pcm_ring_fill", 0),
                diag.get("underruns", 0),
                diag.get("rebuffer_count", 0),
                diag.get("last_fatal_error", 0),
                diag.get("network_no_data_count", 0),
            )
        self._check_radio_health(diag, previous, now)
        return diag

    def _check_radio_health(self, diag, previous, now):
        current = int(diag.get("current_compressed_fifo_fill", 0) or 0)
        fatal = int(diag.get("last_fatal_error", 0) or 0)
        state = self._radio_backend_state_cache

        if current and current < self._RADIO_FIFO_WARN_BYTES:
            if not self._radio_diag_low_since_ms:
                self._radio_diag_low_since_ms = now
            elif (
                not self._radio_diag_warned_low
                and time.ticks_diff(now, self._radio_diag_low_since_ms) >= 2000
            ):
                self._radio_diag_warned_low = True
                self._radio_debugf("compressed FIFO low: {} bytes", current)
        else:
            self._radio_diag_low_since_ms = 0
            self._radio_diag_warned_low = False

        if previous:
            previous_fill = int(previous.get("current_compressed_fifo_fill", 0) or 0)
            current_net = int(diag.get("network_no_data_count", 0) or 0)
            previous_net = int(previous.get("network_no_data_count", 0) or 0)
            if (
                current < previous_fill
                and current < (self._RADIO_FIFO_WARN_BYTES * 2)
                and (current_net - previous_net) >= self._RADIO_NET_STALL_WARN_DELTA
                and not self._radio_diag_warned_network
            ):
                self._radio_diag_warned_network = True
                self._radio_debugf(
                    "network no-data rising while FIFO falls: fifo {}->{} net_no_data {}->{}",
                    previous_fill,
                    current,
                    previous_net,
                    current_net,
                )
            elif current >= (self._RADIO_FIFO_WARN_BYTES * 2):
                self._radio_diag_warned_network = False

        if fatal and state == "stopped" and not self.user_stopped:
            self._handle_radio_runtime_drop("diag fatal {}".format(fatal))

    def _poll_radio_backend(self, force=False):
        now = time.ticks_ms()
        self.service_radio(force=force)
        if (
            not force
            and self._radio_backend_poll_ms
            and time.ticks_diff(now, self._radio_backend_poll_ms) < self._RADIO_BACKEND_POLL_MS
        ):
            return
        try:
            state = getattr(self.audio, "radio_state", None)
        except Exception:
            state = None
        try:
            playing = bool(self.audio.is_playing)
        except Exception:
            playing = False
        self._radio_backend_state_cache = state if isinstance(state, str) else None
        self._radio_backend_playing_cache = playing
        self._radio_backend_poll_ms = now
        self._sample_radio_diag(force=force)

    def _radio_backend_state(self, force=False):
        self._poll_radio_backend(force=force)
        return self._radio_backend_state_cache

    def _radio_backend_playing(self, force=False):
        self._poll_radio_backend(force=force)
        return self._radio_backend_playing_cache

    def _radio_backend_alive(self):
        if self.radio_mode and self._radio_has_connected:
            return True
        state = self._radio_backend_state()
        return self._radio_backend_playing() or state in ("startup_buffering", "buffering", "playing")

    def _radio_backend_fatal_error(self):
        return 0

    def _radio_cache_path(self):
        return "picoware/vibesmp/radio/profile_cache.json"

    def _load_radio_profile_cache(self):
        self._radio_profile_cache = {}
        return self._radio_profile_cache

    def _radio_cache_entry_valid(self, key, entry):
        if not isinstance(key, str) or not isinstance(entry, dict):
            return False
        if self._radio_profile_key(entry.get("url", "")) != key:
            return False
        if not self._radio_normalize_url(entry.get("url", "")):
            return False
        final_url = entry.get("final_url", entry.get("url", ""))
        if not self._radio_normalize_url(final_url):
            return False
        profile = entry.get("profile")
        if not isinstance(profile, dict):
            return False
        http_version = profile.get("http_version", "1.1")
        if http_version not in ("1.0", "1.1"):
            return False
        try:
            int(profile.get("timeout_ms", 5000))
            int(profile.get("max_redirects", 0))
            ts = entry.get("timestamp", 0)
            if ts is not None:
                float(ts)
        except (TypeError, ValueError):
            return False
        return True

    def _prune_radio_profile_cache(self):
        cache = self._radio_profile_cache
        if not cache or len(cache) <= self._RADIO_PROFILE_CACHE_LIMIT:
            return
        while len(cache) > self._RADIO_PROFILE_CACHE_LIMIT:
            oldest_key = None
            oldest_ts = None
            for key, entry in cache.items():
                ts = entry.get("timestamp", 0) if isinstance(entry, dict) else 0
                if oldest_key is None or ts < oldest_ts:
                    oldest_key = key
                    oldest_ts = ts
            if oldest_key is None:
                break
            del cache[oldest_key]

    def _save_radio_profile_cache(self):
        return False

    def _flush_radio_profile_cache(self, clear=False):
        self._radio_profile_cache_dirty = False
        return False

    def _radio_profile_key(self, url):
        return url or ""

    def _radio_evict_profile_cache(self, url):
        return False

    def _radio_profile_label(self, profile):
        return "{} icy={} redirects={}".format(
            profile.get("http_version", "1.1"),
            1 if profile.get("icy") else 0,
            profile.get("max_redirects", 0),
        )

    def _radio_profile_signature(self, profile):
        return (
            profile.get("http_version", "1.1"),
            bool(profile.get("icy")),
            profile.get("user_agent", "VibesMP/1.0"),
            profile.get("timeout_ms", 5000),
            profile.get("max_redirects", 0),
            bool(profile.get("allow_http_fallback")),
        )

    def _radio_options(self, http_version="1.1", icy=False, max_redirects=0, allow_http_fallback=False):
        return {
            "http_version": http_version,
            "icy": bool(icy),
            "user_agent": "VibesMP/1.0",
            "timeout_ms": 5000,
            "max_redirects": max_redirects,
            "allow_http_fallback": bool(allow_http_fallback),
        }

    def _radio_profile_matrix(self, max_redirects=0):
        return [
            self._radio_options("1.1", False, max_redirects),
            self._radio_options("1.1", True, max_redirects),
            self._radio_options("1.0", False, max_redirects),
        ]

    def _radio_http_fallback_url(self, url):
        if isinstance(url, str) and url.startswith("https://"):
            return "http://" + url[8:]
        return None

    def _radio_tls_closed_early(self, probe):
        return bool(
            probe
            and not probe.get("ok")
            and probe.get("tls")
            and (probe.get("status") in (None, 0))
        )

    def _radio_probe_backend_unsupported(self, probe):
        if not isinstance(probe, dict) or probe.get("ok"):
            return False
        return (
            not probe.get("url")
            and not probe.get("final_url")
            and not probe.get("location")
            and not probe.get("content_type")
            and int(probe.get("status") or 0) == 0
            and int(probe.get("error") or 0) == 0
            and int(probe.get("elapsed_ms") or 0) == 0
        )

    def _radio_probe(self, url, profile):
        if not self._audio_has_method("radio_probe"):
            self._radio_debug("audio backend missing radio_probe")
            return None
        try:
            if self._RADIO_DEBUG:
                self._radio_debugf("probe url={!r} profile={}", url, self._radio_profile_label(profile))
            res = self._audio_call("radio_probe", url, profile)
            self._radio_debugf("probe result {}", res)
            return res
        except (OSError, ValueError, AttributeError, TypeError) as e:
            import sys
            print("[ERROR] player.radio_probe:", e)
            sys.print_exception(e)
            return {"ok": False, "url": url, "final_url": url, "error": repr(e)}

    def _radio_cache_success(self, original_url, final_url, profile):
        return

    def _start_radio_connect(self, runtime=False, source="play_radio start"):
        self._reset_radio_connect_state()
        self._radio_connect_runtime = bool(runtime)
        self._radio_connect_source = source
        self._radio_first_profile = self._radio_options("1.1", False, 3)
        self._radio_connect_phase = "direct"
        self._set_radio_status("Connecting", source, category="runtime_disconnect" if runtime else None)

    def _begin_radio_play_attempt(self, original_url, play_url, profile, fail_phase):
        collect()
        if self._RADIO_DEBUG:
            self._radio_debugf("play attempt url={!r} profile={}", play_url, self._radio_profile_label(profile))
        start_ms = time.ticks_ms() if self._perf_enabled else 0
        try:
            ok = self._audio_call("play_mp3_url", play_url, profile)
        except (OSError, ValueError, AttributeError, TypeError) as e:
            import sys
            print("[ERROR] player.radio play attempt:", e)
            sys.print_exception(e)
            ok = False
        if start_ms:
            self._perf_timing("radio_play_mp3_url_return", time.ticks_diff(time.ticks_ms(), start_ms))
            self._perf_inc("radio_play_mp3_url_ok" if ok else "radio_play_mp3_url_fail")
        self._radio_debugf("audio.play_mp3_url returned {}", ok)
        if not ok:
            self._audio_call("stop")
            return False
        self._radio_verify_original_url = original_url
        self._radio_verify_play_url = play_url
        self._radio_verify_profile = profile
        self._radio_verify_started_ms = time.ticks_ms()
        self._radio_verify_fail_phase = fail_phase
        self._radio_connect_phase = "verify"
        self._set_radio_status(
            "Connecting",
            "verifying playback",
            category="runtime_disconnect" if self._radio_connect_runtime else None,
        )
        return True

    def _finish_radio_connect_success(self, cache_success=False):
        self.last_play_time = time.ticks_ms()
        self._radio_started_ms = self.last_play_time
        self._play_busy_until = time.ticks_add(time.ticks_ms(), 1500)
        self._mark_radio_healthy()
        if cache_success and self._radio_verify_profile:
            self._radio_cache_success(
                self._radio_verify_original_url,
                self._radio_verify_play_url,
                self._radio_verify_profile,
            )
        self._reset_radio_connect_state()
        return True

    def _advance_radio_candidate_index(self):
        self._radio_profile_idx += 1
        candidates = self._radio_candidates or []
        while self._radio_candidate_idx < len(candidates):
            profiles = candidates[self._radio_candidate_idx][1]
            if self._radio_profile_idx < len(profiles):
                return
            self._radio_candidate_idx += 1
            self._radio_profile_idx = 0

    def _finish_radio_connect_failure(self, reason="all radio methods failed"):
        runtime = self._radio_connect_runtime
        source = self._radio_connect_source or "radio connect"
        self._reset_radio_connect_state()
        if runtime:
            if self.radio_retry_count >= self._RADIO_RETRY_LIMIT:
                self._set_radio_status("Disconnected", source, category="runtime_disconnect")
                self._radio_disconnect_logged = True
                self._flush_radio_profile_cache(clear=True)
            else:
                self._schedule_radio_retry(source)
            return False
        self.radio_retry_allowed = False
        self._set_radio_status("Unsupported Stream", reason, category="startup_failure")
        self._radio_debugf("{} for name={!r} url={!r}", reason, self.radio_name, self.radio_url)
        self._flush_radio_profile_cache(clear=True)
        return False

    def _radio_build_candidates(self):
        url = self.radio_url
        first_profile = self._radio_first_profile or self._radio_options("1.1", False, 3)
        first_probe = self._radio_first_probe
        final_url = None
        if first_probe:
            probed_final = first_probe.get("final_url") or None
            if probed_final and (probed_final != url or first_probe.get("ok")):
                final_url = probed_final

        tls_closed_early = self._radio_tls_closed_early(first_probe)
        candidates = []
        if final_url:
            reusable_final_probe = first_probe if first_probe and first_probe.get("ok") and final_url == url else None
            candidates.append((final_url, [first_profile], reusable_final_probe))
            http_url = self._radio_http_fallback_url(final_url)
            if http_url and http_url != final_url:
                candidates.append((http_url, [self._radio_options("1.1", False, 1)], None))
            candidates.append((final_url, [
                self._radio_options("1.1", True, 0),
                self._radio_options("1.0", False, 0),
            ], None))
        if first_probe and first_probe.get("ok") and final_url == url:
            candidates.append((url, [first_profile], first_probe))
        http_source = final_url or url
        http_url = self._radio_http_fallback_url(http_source)
        if http_url and http_url != http_source:
            candidates.append((http_url, self._radio_profile_matrix(1 if final_url else 3), None))
        if not final_url and not tls_closed_early:
            candidates.append((url, self._radio_profile_matrix(3), first_probe))
        elif final_url != url and not tls_closed_early:
            candidates.append((url, self._radio_profile_matrix(3), first_probe))
        self._radio_candidates = candidates
        self._radio_candidate_idx = 0
        self._radio_profile_idx = 0
        self._radio_seen_attempts = set()
        self._radio_connect_phase = "candidate"

    def _advance_radio_verify(self):
        elapsed = time.ticks_diff(time.ticks_ms(), self._radio_verify_started_ms)
        self.service_radio(force=True)
        self._mark_radio_healthy()
        if elapsed < self._RADIO_VERIFY_GRACE_MS:
            self._set_radio_status("Buffering")
            return True
        self._set_radio_status("Playing")
        return self._finish_radio_connect_success(cache_success=True)
        return True

    def _advance_radio_connect(self):
        phase = self._radio_connect_phase
        if not phase:
            return False
        if not self.radio_mode or self.user_stopped:
            self._reset_radio_connect_state()
            return False

        if phase == "cached":
            cache = self._load_radio_profile_cache()
            cached = cache.get(self._radio_profile_key(self.radio_url))
            first_profile = self._radio_first_profile or self._radio_options("1.1", False, 3)
            if cached:
                cached_url = cached.get("final_url") or self.radio_url
                cached_profile = cached.get("profile") or self._radio_options()
                skip_cached_attempt = (
                    cached_url == self.radio_url
                    and self._radio_profile_signature(cached_profile) == self._radio_profile_signature(first_profile)
                )
                if not skip_cached_attempt:
                    if self._RADIO_DEBUG:
                        self._radio_debugf("trying cached direct play url={!r} profile={}", cached_url, self._radio_profile_label(cached_profile))
                    if self._begin_radio_play_attempt(self.radio_url, cached_url, cached_profile, "cached"):
                        return True
                    self._radio_evict_profile_cache(self.radio_url)
                    self._radio_debug("cached profile failed; running full method search")
            self._radio_connect_phase = "direct"
            return True

        if phase == "direct":
            first_profile = self._radio_first_profile or self._radio_options("1.1", False, 3)
            if self._RADIO_DEBUG:
                self._radio_debugf("trying direct first play before probe profile={}", self._radio_profile_label(first_profile))
            if self._begin_radio_play_attempt(self.radio_url, self.radio_url, first_profile, "first_probe"):
                return True
            self._radio_connect_phase = "first_probe"
            return True

        if phase == "first_probe":
            first_profile = self._radio_first_profile or self._radio_options("1.1", False, 3)
            self._radio_first_probe = self._radio_probe(self.radio_url, first_profile)
            if self._radio_probe_backend_unsupported(self._radio_first_probe):
                self._finish_radio_connect_failure("backend unsupported")
                return True
            self._radio_connect_phase = "build_candidates"
            return True

        if phase == "build_candidates":
            self._radio_build_candidates()
            return True

        if phase == "candidate":
            candidates = self._radio_candidates or []
            seen = self._radio_seen_attempts
            if seen is None:
                seen = set()
                self._radio_seen_attempts = seen
            while self._radio_candidate_idx < len(candidates):
                candidate_url, profiles, reusable_probe = candidates[self._radio_candidate_idx]
                if self._radio_profile_idx >= len(profiles):
                    self._advance_radio_candidate_index()
                    continue
                profile = profiles[self._radio_profile_idx]
                key = "{}|{}|{}|{}".format(
                    candidate_url,
                    profile.get("http_version"),
                    profile.get("icy"),
                    profile.get("max_redirects"),
                )
                if key in seen:
                    self._advance_radio_candidate_index()
                    continue
                seen.add(key)
                probe = reusable_probe if self._radio_profile_idx == 0 else None
                if probe is None:
                    probe = self._radio_probe(candidate_url, profile)
                if probe is None:
                    self._radio_debug("probe unavailable; falling back to direct playback")
                    if self._begin_radio_play_attempt(self.radio_url, candidate_url, profile, "candidate"):
                        return True
                    self._advance_radio_candidate_index()
                    return True
                if not probe.get("ok"):
                    self._radio_debugf(
                        "probe failed: status={} error={} final_url={!r}",
                        probe.get("status"), probe.get("error"), probe.get("final_url")
                    )
                    if self._radio_probe_backend_unsupported(probe):
                        self._finish_radio_connect_failure("backend unsupported")
                        return True
                    self._advance_radio_candidate_index()
                    return True
                final_url = probe.get("final_url") or candidate_url
                if self._begin_radio_play_attempt(self.radio_url, final_url, profile, "candidate"):
                    return True
                self._advance_radio_candidate_index()
                return True
            self._finish_radio_connect_failure()
            return True

        if phase == "verify":
            return self._advance_radio_verify()

        self._finish_radio_connect_failure()
        return True

    def _handle_radio_runtime_drop(self, source):
        if self.user_stopped or self._radio_disconnect_logged:
            return
        self._radio_debugf(
            "{} detected drop: state={!r} is_playing={} user_stopped={} {}",
            source,
            self._radio_backend_state(),
            self._radio_backend_playing(),
            self.user_stopped,
            self._radio_info_snapshot(),
        )
        self._schedule_radio_retry(source)

    def _sync_radio_status_from_backend(self):
        if self.radio_status == "Retrying" and self._radio_retry_due_ms:
            return False
        state = self._radio_backend_state()
        if state == "buffering" or state == "startup_buffering":
            self._mark_radio_healthy()
            self._set_radio_status("Buffering")
            return True
        if state == "playing":
            self._mark_radio_healthy()
            if self.radio_status in ("Buffering", "Connecting", "Retrying"):
                self._set_radio_status("Playing")
            return True
        return False

    def _fade(self, target, start_v=None, steps=2, step_ms=10):
        current = self._volume if start_v is None else start_v
        diff = target - current
        for i in range(1, steps + 1):
            v = int(current + (diff * i / steps))
            try: self._audio_call("set_volume", v)
            except (OSError, AttributeError): pass
            time.sleep_ms(step_ms)
        try: self._audio_call("set_volume", target)
        except (OSError, AttributeError): pass

    def play(self, file_path, start_pos=0):
        if not file_path: return False

        # Ensure hardware is stopped and settled
        self._audio_call("stop")
        time.sleep_ms(10)
        collect()

        self.radio_mode = False
        self.radio_name = ""
        self.radio_url = ""
        self.radio_active_id = None
        self.radio_status = "Stopped"
        self._reset_radio_runtime_state()
        self._flush_radio_profile_cache(clear=True)
        self.user_stopped = False
        self._paused_pos = 0
        self._paused = False
        self.current_track = file_path

        skip_meta = False
        if self.pre_play_callback:
            try:
                if self.pre_play_callback(file_path):
                    skip_meta = True
            except Exception as e:
                print("[ERROR] player.play pre_play_callback:", e)

        try:
            self._audio_call("set_volume", self._volume)
            res = self._execute_play(file_path, start_pos, skip_meta=skip_meta)
            if not res:
                time.sleep_ms(10)
                res = self._execute_play(file_path, start_pos, skip_meta=skip_meta)
            return res
        except MemoryError:
            from vibesmp_lib.id3 import clear_cache
            clear_cache(); collect()
            try:
                self._audio_call("stop"); time.sleep_ms(10)
                return self._execute_play(file_path, start_pos, skip_meta=skip_meta)
            except (OSError, AttributeError): return False
        except (OSError, ValueError) as e:
            import sys
            print("[ERROR] player.play:", e)
            sys.print_exception(e)
            return False

    def play_radio(self, name, url, active_id=None):
        normalized_url = self._radio_normalize_url(url)
        if not normalized_url:
            self._radio_debugf("play_radio rejected malformed URL: {!r}", url)
            self.user_stopped = False
            self._audio_call("stop")
            self._flush_radio_profile_cache(clear=True)
            self.radio_mode = True
            self.radio_name = name or (url.strip() if isinstance(url, str) and url.strip() else "Radio")
            self.radio_url = url.strip() if isinstance(url, str) else ""
            self.radio_active_id = active_id
            self._reset_radio_runtime_state()
            self.current_track = ""
            self.current_id3 = {"title": self.radio_name, "artist": "Internet Radio", "cover": None}
            self.radio_retry_allowed = False
            self._set_radio_status("Unsupported Stream", "invalid radio URL", category="startup_failure")
            return False
        url = normalized_url

        self._radio_debugf("play_radio requested: name={!r} url={!r}", name or url, url)
        self._audio_call("stop")
        time.sleep_ms(10)
        collect()
        self._flush_radio_profile_cache(clear=True)

        self.radio_mode = True
        self.radio_name = name or url
        self.radio_url = url
        self.radio_active_id = active_id
        self._reset_radio_runtime_state()
        self._set_radio_status("Connecting", "play_radio start")
        if self._perf_enabled:
            self._radio_perf_start_ms = time.ticks_ms()
            self._radio_perf_buffering_seen = False
            self._radio_perf_playing_seen = False
        else:
            self._radio_perf_start_ms = 0
        self.current_track = ""
        self.current_id3 = {"title": self.radio_name, "artist": "Internet Radio", "cover": None}
        self._paused = False
        self._paused_pos = 0
        self._paused_pos_resume = 0
        self.user_stopped = False

        try:
            self._audio_call("set_volume", self._volume)
            if not self._audio_has_method("play_mp3_url"):
                self._radio_debug("audio backend missing play_mp3_url")
                self._set_radio_status("Unsupported Stream", "play_mp3_url missing", category="startup_failure")
                return False
            if self._audio_has_method("radio_probe"):
                self._radio_connect_runtime = False
                self._radio_connect_source = "play_radio start"
                self._radio_first_profile = self._radio_options("1.1", False, 3)
                self._radio_connect_phase = "direct"
                if self._begin_radio_play_attempt(url, url, self._radio_first_profile, "first_probe"):
                    self._perf_inc("radio_fast_path_ok")
                    return True
                self._perf_inc("radio_fast_path_fail")
                self._radio_connect_phase = "first_probe"
                self._advance_radio_connect()
                return True

            self._radio_debug("calling legacy audio.play_mp3_url")
            res = self._audio_call("play_mp3_url", url)
            self._radio_debugf("legacy audio.play_mp3_url returned {}", res)
            if res:
                self.last_play_time = time.ticks_ms()
                self._radio_started_ms = self.last_play_time
                self._play_busy_until = time.ticks_add(time.ticks_ms(), 1500)
                self._mark_radio_healthy()
                if self._RADIO_DEBUG:
                    self._radio_debug(self._radio_info_snapshot())
                self._set_radio_status("Playing")
            else:
                self._set_radio_status("Unsupported Stream", "audio.play_mp3_url returned False", category="startup_failure")
            return res
        except (OSError, ValueError, AttributeError, TypeError) as e:
            import sys
            print("[ERROR] player.play_radio:", e)
            sys.print_exception(e)
            self._set_radio_status("Disconnected", "exception during play_radio", category="startup_failure")
            if self._RADIO_DEBUG:
                self._radio_debugf("exception during play_radio; {}", self._radio_info_snapshot())
            self._radio_disconnect_logged = True
            self._flush_radio_profile_cache(clear=True)
            return False

    def stop_radio(self):
        if not self.radio_mode:
            self._radio_debug("stop_radio ignored: radio_mode is False")
            return False
        self.user_stopped = True
        self._reset_radio_connect_state()
        self._audio_call("stop")
        self._set_radio_status("Stopped", "stop_radio", category="user_stop")
        self.radio_mode = False
        self.radio_name = ""
        self.radio_url = ""
        self.radio_active_id = None
        self.current_id3 = {"title": "", "artist": ""}
        self._flush_radio_profile_cache(clear=True)
        self._reset_radio_runtime_state()
        self._radio_debug("radio stopped by user")
        return True

    def _execute_play(self, file_path, start_pos, skip_meta=False, is_seconds=False):
        sd_path = file_path
        if sd_path.startswith("/sd/"): sd_path = sd_path[4:]
        elif sd_path.startswith("sd/"): sd_path = sd_path[3:]
        if not sd_path.startswith("/"): sd_path = "/" + sd_path

        from vibesmp_lib.id3 import _id3_cache
        if file_path in _id3_cache:
            self.current_id3 = _id3_cache[file_path]
            self._meta_pending = False
        elif not skip_meta:
            self._meta_pending = True
            from vibesmp_lib.utils import get_filename
            self.current_id3 = {"title": get_filename(file_path), "artist": "Loading...", "cover": None}
            self._dur_str_cache = "--:--"

        try:
            res = self._audio_call("play_mp3", sd_path)
            self.last_play_time = time.ticks_ms()
            if res: self._play_busy_until = time.ticks_add(time.ticks_ms(), 300)

            if res and start_pos > 0:
                time.sleep_ms(10)
                target_sample = int(start_pos)
                if is_seconds:
                    info = self.audio.info
                    if info:
                        sr = info.sample_rate or 44100
                        ch = info.channels or 2
                        self._sr_ch = sr * ch
                        target_sample = int(start_pos * self._sr_ch)
                self._audio_call("seek", target_sample)
        except (OSError, ValueError) as e:
            import sys
            print(f"[ERROR] player: play_mp3: {e}")
            sys.print_exception(e)
            res = False

        if res:
            time.sleep_ms(20)
            if not self.audio.is_playing:
                self._audio_call("stop")
                time.sleep_ms(10)
                self._audio_call("play_mp3", sd_path)
                time.sleep_ms(5)
                if start_pos > 0:
                    self._audio_call("seek", int(start_pos * self._sr_ch if is_seconds else start_pos))

            info = self.audio.info
            if info:
                sr = info.sample_rate or 44100
                ch = info.channels or 2
                self._sr_ch = sr * ch
                if info.duration > 0:
                    self._last_dur = info.duration / self._sr_ch
                    self._dur_str_cache = format_time(int(self._last_dur))
        return res

    def restart_current(self):
        if self.radio_mode or not self.current_track:
            return False
        self.user_stopped = False
        self._paused = False
        self._paused_pos = 0
        self._paused_pos_resume = 0
        if self.is_playing:
            self._seeking = True
            try:
                self._audio_call("set_volume", 0)
                ok = self.seek_absolute(0)
            finally:
                self._audio_call("set_volume", self._volume)
                self._seeking = False
            if ok:
                self.last_play_time = time.ticks_ms()
                self._play_busy_until = time.ticks_add(time.ticks_ms(), 300)
                return True
        return self.play(self.current_track, 0)

    def get_info(self, force=False):
        if self.radio_mode:
            return None
        now = time.ticks_ms()
        if force or not self._last_hw_info or time.ticks_diff(now, self._last_info_time) > 500:
            self._last_hw_info = self.audio.info
            self._last_info_time = now
        return self._last_hw_info

    def monitor_and_heal(self):
        if self.radio_mode:
            if self._retry_radio_if_due():
                return True
            if self._advance_radio_connect():
                return True
            self._sync_radio_status_from_backend()
            if (
                not self._radio_retry_due_ms
                and not self._radio_connect_phase
                and self._radio_has_connected
                and not self._radio_backend_alive()
                and not self._radio_backend_playing()
                and not self.user_stopped
            ):
                self._handle_radio_runtime_drop("monitor")
            return True
        if not self.is_playing or self.user_stopped or self._seeking or self._recovering:
            self._stall_count = 0; return True

        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_pos_check) < 500: return True

        self._last_pos_check = now
        info = self.get_info(force=True)
        curr_pos = info.position if info else -1

        if curr_pos != -1:
            if curr_pos == self._last_hw_pos:
                self._stall_count += 1
                if self._stall_count >= 10:
                    print(f"[ERROR] Player: Stall healing at {curr_pos}")
                    self._stall_count = 0; self._recovering = True
                    self._io_throttled_until = time.ticks_add(now, 15000)
                    try:
                        self._audio_call("stop"); time.sleep_ms(20)
                        self._execute_play(self.current_track, start_pos=curr_pos, skip_meta=True)
                    finally: self._recovering = False
                    return False
            else:
                self._stall_count = 0; self._last_hw_pos = curr_pos
        return True

    def load_pending_meta(self):
        if not self._meta_pending or not self.current_track or not self.can_load_heavy_assets:
            return False

        collect()
        file_path = self.current_track
        try:
            from vibesmp_lib.metadata_engine import get_track_hash
            file_hash = get_track_hash(file_path)
            meta_path = "picoware/vibesmp/library/meta/" + file_hash + ".json"

            temp_meta = None
            if self.storage and self.storage.exists(meta_path):
                data = self.storage.read(meta_path)
                import json
                temp_meta = json.loads(data); del data
            else:
                temp_meta = parse_id3(self.storage, file_path)

            if temp_meta:
                self.current_id3 = temp_meta
                from vibesmp_lib.id3 import _id3_cache
                if len(_id3_cache) > 50: _id3_cache.clear()
                _id3_cache[file_path] = temp_meta
        except (OSError, ValueError) as e:
            import sys
            print(f"[ERROR] Player: Meta load failed: {e}")
            sys.print_exception(e)

        self._meta_pending = False; collect()
        return True

    def stop(self):
        self._paused_pos = 0; self.user_stopped = True
        self._paused = False
        if self.radio_mode:
            self.stop_radio()
            return
        if self.is_playing: self._fade(0)
        self._audio_call("stop")
        from gc import collect; collect()

    def pause(self):
        if self.radio_mode:
            return False
        if self.is_playing:
            info = self.audio.info
            self._paused_pos = info.position if info else 0
            self._paused = True
            self._fade(0); self._audio_call("stop")
            from gc import collect; collect()
            return True
        return False

    def resume(self):
        if self.radio_mode:
            return False
        if self.current_track and not self.is_playing:
            pos = self._paused_pos
            is_sec = False
            if pos == 0 and self._paused_pos_resume > 0:
                pos = self._paused_pos_resume; is_sec = True
                self._paused_pos_resume = 0

            meta = self.current_id3 if isinstance(self.current_id3, dict) else {}
            has_meta = bool(meta.get("title") or meta.get("artist") or meta.get("cover"))
            skip_meta = True

            # A fresh session can resume a preselected track before any metadata or
            # cover art has been primed. Reuse the pre-play warmup path so the first
            # visible playback render has the same metadata state as a direct play().
            if self.last_play_time <= 0 or not has_meta:
                skip_meta = False
                if self.pre_play_callback:
                    try:
                        if self.pre_play_callback(self.current_track):
                            skip_meta = True
                    except Exception as e:
                        print("[ERROR] player.resume pre_play_callback:", e)

            res = self._execute_play(self.current_track, pos, skip_meta=skip_meta, is_seconds=is_sec)
            if res:
                self._fade(self._volume, start_v=0)
                self._paused_pos = 0
                self._paused = False
            return res
        return False

    @property
    def volume(self): return self._volume
    @volume.setter
    def volume(self, val):
        self._volume = max(0, min(100, val))
        self._audio_call("set_volume", self._volume)

    def check_end(self, playlist, shuffle=False):
        if self.radio_mode:
            if self._retry_radio_if_due():
                return False
            if self._advance_radio_connect():
                return False
            self._sync_radio_status_from_backend()
            if (
                not self._radio_retry_due_ms
                and not self._radio_connect_phase
                and self._radio_has_connected
                and not self._radio_backend_alive()
                and not self._radio_backend_playing()
                and not self.user_stopped
            ):
                self._handle_radio_runtime_drop("check_end")
            return False
        if self.user_stopped or self.is_paused(): return False
        if time.ticks_diff(time.ticks_ms(), self.last_play_time) < 2000: return False

        if not self.is_playing:
            curr = playlist.get_current()
            if curr:
                if self.current_track != curr:
                    return self.play(curr)
                next_t = playlist.next_track(self.loop_mode, shuffle, auto_advance=True)
                if next_t: return self.play(next_t)
        return False

    def seek(self, seconds):
        if self.radio_mode:
            return False
        if self._seeking: return False

        if self.is_paused():
            if self._sr_ch <= 0:
                self._sr_ch = 88200

            delta_samples = int(seconds * self._sr_ch)
            new_pos = self._paused_pos + delta_samples
            if new_pos < 0:
                new_pos = 0
            dur = self.get_duration_seconds()
            if dur > 0:
                max_samples = int(dur * self._sr_ch)
                if new_pos >= max_samples:
                    new_pos = int(max_samples - (self._sr_ch // 10))

            self._paused_pos = new_pos
            return True

        info = self.audio.info
        if not info: return False

        self._sr_ch = (info.sample_rate or 44100) * (info.channels or 1)
        current_sec = info.position / self._sr_ch
        self._seeking = True
        try:
            self._audio_call("set_volume", 0)  # Mute before seek to eliminate pre-seek PCM pop
            res = self.seek_absolute(current_sec + seconds)
        finally:
            self._audio_call("set_volume", self._volume)  # Restore volume after seek command queued
            self._seeking = False
        if res: self._play_busy_until = time.ticks_add(time.ticks_ms(), 300)
        return res

    def seek_absolute(self, seconds):
        if self.radio_mode:
            return False
        info = self.audio.info
        if not info: return False

        self._sr_ch = (info.sample_rate or 44100) * (info.channels or 1)
        target_sample = int(seconds * self._sr_ch)
        dur_samples = info.duration

        if target_sample < 0: target_sample = 0
        if dur_samples > 0 and target_sample >= dur_samples:
            target_sample = int(dur_samples - (self._sr_ch // 10))

        try:
            return self._audio_call("seek", target_sample)
        except (OSError, ValueError) as e:
            import sys
            print(f"[ERROR] Player.seek_absolute: {e}")
            sys.print_exception(e)
            return False

    def get_pos_seconds(self):
        if self.radio_mode:
            if self._radio_started_ms:
                return time.ticks_diff(time.ticks_ms(), self._radio_started_ms) // 1000
            return 0
        info = self.audio.info
        if not info: return self._paused_pos / self._sr_ch if self._sr_ch > 0 else 0
        if self._sr_ch <= 0:
            self._sr_ch = (info.sample_rate or 44100) * (info.channels or 2)
        return info.position / self._sr_ch

    def get_duration_seconds(self):
        if self.radio_mode:
            return 0
        info = self.audio.info
        if not info: return self._last_dur
        if self._sr_ch <= 0:
            self._sr_ch = (info.sample_rate or 44100) * (info.channels or 2)
        if info.duration > 0: self._last_dur = info.duration / self._sr_ch
        return self._last_dur

    def get_timing_seconds(self):
        if self.radio_mode:
            return self.get_pos_seconds(), 0
        info = self.audio.info
        if not info:
            pos = self._paused_pos / self._sr_ch if self._sr_ch > 0 else 0
            return pos, self._last_dur
        if self._sr_ch <= 0:
            self._sr_ch = (info.sample_rate or 44100) * (info.channels or 2)
        pos = info.position / self._sr_ch
        if info.duration > 0:
            self._last_dur = info.duration / self._sr_ch
        return pos, self._last_dur

    @property
    def can_load_heavy_assets(self):
        if self.radio_mode: return False
        if not self.current_track: return False
        if self._seeking or self._recovering: return False
        if self.user_stopped: return True
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_play_time) < 1500: return False
        if self._io_throttled_until > 0:
            if time.ticks_diff(self._io_throttled_until, now) > 0: return False
            else: self._io_throttled_until = 0
        return not self.is_playing or time.ticks_diff(now, self.last_play_time) > 2000

    @property
    def is_busy(self):
        return time.ticks_diff(self._play_busy_until, time.ticks_ms()) > 0

    @property
    def is_playing(self):
        if self.radio_mode:
            return (not self.user_stopped) and self.radio_status in ("Connecting", "Buffering", "Playing", "Retrying")
        return self.audio.is_playing

    def is_paused(self, is_playing=None):
        if self._paused:
            return True
        if self._paused_pos_resume <= 0:
            return False
        if is_playing is None:
            is_playing = self.is_playing
        return not is_playing
