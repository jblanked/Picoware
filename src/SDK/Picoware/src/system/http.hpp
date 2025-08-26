#pragma once
#include "../system/wifi.hpp"
#include "../system/helpers.hpp"
#include <map>

typedef enum
{
    IDLE,    // Default state
    LOADING, // Loading/requesting data
    ISSUE,   // Issue with connection
} HTTPState;

class HTTP
{
public:
    HTTP();
    ~HTTP();

    void clearAsyncResponse();
    std::string getAsyncResponse() const;
    HTTPState getState() const;
    std::string getStateString() const;
    bool isRequestComplete() const;
    bool isRequestInProgress() const;
    void update(); // poll async requests

    std::string request(const std::string &method, const std::string &url, const std::map<std::string, std::string> &headers = {}, const std::string &data = "");
    bool requestAsync(const std::string &method, const std::string &url, const std::map<std::string, std::string> &headers = {}, const std::string &data = "");

    // quick sync requests
    std::string del(const std::string &url, const std::map<std::string, std::string> &headers = {});
    std::string get(const std::string &url, const std::map<std::string, std::string> &headers = {});
    std::string post(const std::string &url, const std::map<std::string, std::string> &headers = {}, const std::string &data = "");
    std::string put(const std::string &url, const std::map<std::string, std::string> &headers = {}, const std::string &data = "");

    // quick async requests
    bool delAsync(const std::string &url, const std::map<std::string, std::string> &headers = {});
    bool getAsync(const std::string &url, const std::map<std::string, std::string> &headers = {});
    bool postAsync(const std::string &url, const std::map<std::string, std::string> &headers = {}, const std::string &data = "");
    bool putAsync(const std::string &url, const std::map<std::string, std::string> &headers = {}, const std::string &data = "");

private:
    std::string async_response = "";
    bool async_request_complete = false;
    bool async_request_in_progress = false;
    static const uint32_t REQUEST_TIMEOUT_MS = 15000;
    HTTPState state = IDLE;
    static const uint32_t POLL_INTERVAL_MS = 10;
    //
    std::string extractHttpBody(const std::string &httpResponse);
    std::string internalRequest(const std::string &method, const std::string &url, bool async, const std::map<std::string, std::string> &headers = {}, const std::string &data = "");
    bool parseUrl(const std::string &url, std::string &hostname, std::string &path, unsigned short &port, bool &use_tls);

private:
};
