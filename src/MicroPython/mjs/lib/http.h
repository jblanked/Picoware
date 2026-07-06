#pragma once
#include "mjs.h"

void http_js_get_response(struct mjs *mjs);
void http_js_is_finished(struct mjs *mjs);
void http_js_request(struct mjs *mjs);
void http_js_request_start(struct mjs *mjs);
//
void http_register(struct mjs *mjs);