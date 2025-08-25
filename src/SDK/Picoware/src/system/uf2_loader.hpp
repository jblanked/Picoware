#pragma once

// after trying my own .pwa format, pelrun mentioned his uf2 loader project from https://github.com/pelrun/uf2loader
// after spending many many hours debugging and optimizing to edit the memory management, I had Claude make some edits
// I'll likely return to this once the project is finished
// more information can be found in the project documentation (/src/tools/application_loader.md)

#include <stdint.h>
#include <stddef.h>

// UF2 Block structure (512 bytes)
struct UF2Block
{
    uint32_t magicStart0; // 0x0A324655 "UF2\n"
    uint32_t magicStart1; // 0x9E5D5157
    uint32_t flags;       // Board family flags
    uint32_t targetAddr;  // Address to load this block
    uint32_t payloadSize; // Number of bytes in data (max 476)
    uint32_t blockNo;     // Block number (0-based)
    uint32_t numBlocks;   // Total number of blocks
    uint32_t fileSize;    // File size or board family ID
    uint8_t data[476];    // Actual data
    uint32_t magicEnd;    // 0x0AB16F30
} __attribute__((packed));

// UF2 Family IDs
#define UF2_FAMILY_RP2040 0xe48bff56
#define UF2_FAMILY_RP2350 0xe48bff57
#define UF2_FAMILY_RP2350_ARM_S 0xe48bff59 // RP2350 ARM Secure
#define ABSOLUTE_FAMILY_ID 0xe48bff59      // Used in RP2350-E10 workaround

// Forward declarations for Picoware objects
class ViewManager;
class Draw;
class Storage;
class WifiManager;

/**
 * Shared Memory Interface Structure
 * This is mapped at 0x20080000 and provides function pointers to firmware services
 */
struct PicowareSharedInterface
{
    // Interface version and validation
    uint32_t version; // Interface version number
    uint32_t magic;   // Magic number for validation (0x50575346 - "PWSF")
    uint32_t size;    // Size of this structure

    // Core firmware services
    struct
    {
        // Display and GUI
        void (*update_display)(void);
        void (*clear_screen)(void);
        void (*draw_pixel)(int x, int y, uint32_t color);
        void (*draw_line)(int x1, int y1, int x2, int y2, uint32_t color);
        void (*draw_rect)(int x, int y, int w, int h, uint32_t color);
        void (*draw_text)(int x, int y, const char *text, uint32_t color);

        // Storage system
        bool (*storage_read)(const char *path, void *buffer, size_t size);
        bool (*storage_write)(const char *path, const void *buffer, size_t size);
        bool (*storage_exists)(const char *path);
        bool (*storage_delete)(const char *path);
        size_t (*storage_get_size)(const char *path);

        // Input handling
        bool (*button_pressed)(int button_id);
        bool (*button_released)(int button_id);
        bool (*button_held)(int button_id);
        void (*get_input_state)(void *input_state);

        // WiFi services
        bool (*wifi_connect)(const char *ssid, const char *password);
        bool (*wifi_disconnect)(void);
        bool (*wifi_is_connected)(void);
        const char *(*wifi_get_ip)(void);

        // HTTP client
        bool (*http_get)(const char *url, void *response_buffer, size_t buffer_size);
        bool (*http_post)(const char *url, const void *data, size_t data_size, void *response_buffer, size_t buffer_size);

        // System utilities
        uint32_t (*get_time_ms)(void);
        void (*delay_ms)(uint32_t ms);
        void (*delay_us)(uint32_t us);

        // Logging and debug
        void (*log_info)(const char *message);
        void (*log_warning)(const char *message);
        void (*log_error)(const char *message);
        void (*log_debug)(const char *message);

    } firmware;

    // Direct object access (advanced usage)
    struct
    {
        ViewManager *view_manager;
        Draw *current_draw;
        Storage *storage;
        WifiManager *wifi_manager;
    } objects;

    // Reserved space for future expansion
    uint8_t reserved[512];
};

// Global shared interface pointer (initialized by UF2Loader)
extern PicowareSharedInterface *g_picoware_interface;

class UF2Loader
{
public:
    UF2Loader();
    ~UF2Loader();

    // Load UF2 file from memory buffer
    bool loadUF2(const uint8_t *uf2_data, size_t size);

    // Execute loaded binary
    int executeApp();

    // Cleanup loaded app
    void unloadApp();

    // Get app info
    const char *getAppName() const { return app_name; }
    bool isLoaded() const { return loaded; }

private:
    bool parseUF2Blocks(const uint8_t *data, size_t size);
    bool validateBlock(const UF2Block *block);
    bool loadELFSection(uint32_t addr, const uint8_t *data, size_t size);
    void setupSharedInterface();

    uint8_t *app_memory;  // Loaded app memory
    size_t app_size;      // Size of loaded app
    uint32_t entry_point; // App entry point address
    uint32_t min_addr;    // Minimum address of loaded app (for relocation)
    char app_name[64];    // App name
    bool loaded;          // Is app loaded?

    // Memory management
    static constexpr uint32_t APP_LOAD_BASE = 0x20040000;
    static constexpr size_t MAX_APP_SIZE = 256 * 1024; // 256KB
    static constexpr uint32_t SHARED_INTERFACE_ADDR = 0x20080000;
};
