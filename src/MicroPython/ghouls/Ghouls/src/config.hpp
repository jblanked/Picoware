#pragma once
#include <stdint.h>
#include <string.h>
#include "engine_config.hpp"

#include ENGINE_MEM_INCLUDE

#ifdef ENGINE_LOG_INCLUDE
#include ENGINE_LOG_INCLUDE
#endif

#define GROUND_ROWS 160
#define SKY_HORIZON_ROWS 160
#define WIREFRAME_ENABLED true

#define TICKS_PER_DAY 1700
#define PLAYER_SPEED_VERTICAL SPEED_SCALE(0.4f)
#define PLAYER_SPEED_HORIZONTAL SPEED_SCALE(0.07f)

// time
#define TIME_INCLUDE "pico/time.h"
#define TIME_MILLIS to_ms_since_boot(get_absolute_time()) * 10

// buttons
#define INPUT_KEY_UP 0
#define INPUT_KEY_DOWN 1
#define INPUT_KEY_RIGHT 2
#define INPUT_KEY_LEFT 3
#define INPUT_KEY_CENTER 4
#define INPUT_KEY_BACK 5

// http
#define HTTP_INACTIVE -1
#define HTTP_IDLE 0
#define HTTP_RECEIVING 1
#define HTTP_SENDING 2
#define HTTP_ISSUE 3
#define HTTP_INCLUDE "../../http_config.hpp"
#define HTTP_REQUEST_IS_FINISHED http_is_finished               // () -> bool
#define HTTP_SEND_REQUEST http_send_request                     // (const char *url, const char *method, const char *headers, const char *payload) -> bool
#define HTTP_WEBSOCKET_IS_CONNECTED http_websocket_is_connected // () -> bool
#define HTTP_WEBSOCKET_SEND http_websocket_send                 // (const char *message) -> bool
#define HTTP_WEBSOCKET_START http_websocket_start               // (const char *url, uint16_t port) -> bool
#define HTTP_WEBSOCKET_STOP http_websocket_stop                 // () -> bool
#define HTTP_GET_RESPONSE http_get_http_response                // (char *buffer, size_t buffer_size) -> bool
#define HTTP_GET_WEBSOCKET_RESPONSE http_get_websocket_response // (char *buffer, size_t buffer_size) -> bool

// json
#define JSON_INCLUDE "../../../jsmn/jsmn.h"
#define JSON_GET_VALUE get_json_value             // (const char *key, const char *json_str) -> char* (caller must free)
#define JSON_GET_ARRAY_VALUE get_json_array_value // (const char *key, int index, const char *json_str) -> char* (caller must free)

// sound
#define SOUND_INCLUDE "../../../audio/audio.h"
// #define SOUND_PLAY_MONO_FREQUENCY sound_play_mono_frequency     // (int frequency, int duration_ms)
#define SOUND_PLAY_STEREO_FREQUENCY audio_play_sound_blocking // (int left_freq, int right_freq, int duration_ms)
#define SOUND_PLAY_PCM audio_push_samples                     // (const int16_t *samples, int count)
#define SOUND_PLAY_WAV audio_play_wav                         // (const char *path)
#define SOUND_STOP audio_stop                                 // () -> void