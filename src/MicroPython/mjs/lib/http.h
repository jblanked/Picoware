#pragma once
#include "mjs.h"

#define HTTP_JS_DEFAULT_BUFFER_SIZE 1024 * 4

void http_js_get_response(struct mjs *mjs);
void http_js_is_finished(struct mjs *mjs);
void http_js_request(struct mjs *mjs);
void http_js_request_start(struct mjs *mjs);
//
void http_create(struct mjs *mjs, mjs_val_t *http_obj);