#pragma once

#include "app_loader.hpp"
#include "uf2_loader.hpp"
#include <string>
#include <memory>
#include <cstdarg>

// Use the existing Vector class from gui/vector.hpp
#include "../gui/vector.hpp"

// Forward declarations
class ViewManager;
class Draw;

// Function table structure for binary app API - simplified C++ approach
struct PicowareAPI
{
    // Direct C++ object pointers - no function wrappers needed
    ViewManager *viewManager; // Direct access to ViewManager object
    Draw *currentDraw;        // Direct access to current Draw object

    // External function pointers for binary apps
    int (*printf_func)(const char *format, ...); // printf function pointer (variadic)

    // Simple logging functions for easy ARM code generation
    void (*log_string)(const char *message); // Simple string logging
    void (*log_number)(int value);           // Simple number logging
    void (*log_hex)(unsigned int value);     // Simple hex logging
};

// Binary app structure for compiled .pwa files
struct BinaryAppHeader
{
    uint32_t magic;         // 'PWA1' magic number
    uint32_t version;       // App format version
    uint32_t codeSize;      // Size of executable code
    uint32_t entryOffset;   // Offset to main entry point
    uint32_t initOffset;    // Offset to initialize function
    uint32_t runOffset;     // Offset to run function
    uint32_t cleanupOffset; // Offset to cleanup function
    uint32_t nameOffset;    // Offset to app name string
    uint32_t setAPIOffset;  // Offset to app_set_api function
    uint32_t apiVersion;    // Required API version
    uint8_t reserved[28];   // Reserved for future use (reduced by 4 bytes)
};

// Simple PWA header for main() function approach
struct SimplePWAHeader
{
    uint32_t magic;       // 'SIMP' magic number (0x53494D50)
    uint32_t version;     // Format version (2)
    uint32_t codeSize;    // Size of executable code
    uint32_t entryOffset; // Offset to main function (always 0)
    uint8_t reserved[48]; // Reserved for future use (64 - 16 = 48)
};

// Function pointer types for app entry points
typedef bool (*AppInitFunc)(void *viewManager);
typedef void (*AppRunFunc)(void *viewManager);
typedef void (*AppCleanupFunc)(void *viewManager);
typedef const char *(*AppGetNameFunc)();
typedef void (*AppSetAPIFunc)(PicowareAPI *api);
typedef int (*AppMainFunc)(); // Simple main() function type

class BinaryApp : public DynamicApp
{
private:
    void *appMemory;                 // Loaded app binary in memory
    BinaryAppHeader header;          // App header information (legacy)
    SimplePWAHeader simpleHeader;    // Simple header information (new)
    std::string appName;             // App name from binary
    bool isLoaded;                   // Whether app is loaded in memory
    bool apiSetup;                   // Whether API has been set up
    bool isSimpleFormat;             // Whether using simple main() format
    ViewManager *currentViewManager; // Current view manager instance

    // UF2 loader for UF2 format apps
    std::unique_ptr<UF2Loader> uf2_loader;

    // Function pointers to app code (legacy format)
    AppInitFunc initFunc;
    AppRunFunc runFunc;
    AppCleanupFunc cleanupFunc;
    AppGetNameFunc getNameFunc;
    AppSetAPIFunc setAPIFunc;

    // Simple format function pointer
    AppMainFunc mainFunc;

    // API function table for binary apps
    static PicowareAPI apiTable;

public:
    BinaryApp();
    ~BinaryApp();

    // Load binary app from file
    bool loadFromFile(const char *filePath);

    // Unload app from memory
    void unload();

    // DynamicApp interface
    bool initialize(ViewManager *viewManager) override;
    void run(ViewManager *viewManager) override;
    void cleanup(ViewManager *viewManager) override;
    const char *getName() const override;

private:
    // Resolve function pointers from loaded binary
    bool resolveFunctions();

    // Validate binary format
    bool validateHeader();

    // Simple format validation and resolution
    bool validateSimpleHeader();
    bool resolveMainFunction();

    // Setup API function table for the binary app
    void setupAPI(ViewManager *viewManager);

    // Printf call patching for firmware redirection
    void patchPrintfCalls();
    void setupPrintfTrampolines();
    void processPrintfCommunications();
};
