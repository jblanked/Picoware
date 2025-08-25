#include "app_loader.hpp"
#include "view_manager.hpp"
#include "storage.hpp"
#include "../gui/menu.hpp"
#include "../gui/alert.hpp"
#include "binary_app.hpp"
#include <cstring>
#include <cstdio>

AppLoader::AppLoader(ViewManager *viewManager)
    : viewManager(viewManager), storage(nullptr), currentApp(nullptr)
{
    storage = new Storage();
}

AppLoader::~AppLoader()
{
    unloadCurrentApp();
    delete storage;
}

bool AppLoader::scanForApps()
{
    availableApps.clear();

    printf("AppLoader: Scanning for .uf2 applications...\n");

    // Scan for .uf2 files in known locations
    const char *searchPaths[] = {
        "apps/",
        nullptr};

    for (int i = 0; searchPaths[i] != nullptr; i++)
    {
        printf("AppLoader: Scanning directory: %s\n", searchPaths[i]);
        scanDirectoryForUf2Files(searchPaths[i]);
    }

    printf("AppLoader: Found %zu UF2 applications\n", availableApps.size());
    return !availableApps.empty();
}

void AppLoader::scanDirectoryForUf2Files(const char *directory)
{
    // Check for .uf2 files - comprehensive list of potential files
    const char *possibleUf2Files[] = {
        // Phase 3 examples
        "hello_world.uf2",
        "led_blinker.uf2",
        "button_input.uf2",
        "adc_reader.uf2",

        // Legacy/test files
        "hello_world_uf2.uf2",
        "enhanced_uf2_test.uf2",

        // Common app names
        "calculator.uf2",
        "text_editor.uf2",
        "file_browser.uf2",
        "terminal.uf2",
        "settings.uf2",
        "wifi_scanner.uf2",
        "sensor_test.uf2",
        "clock.uf2",
        "weather.uf2",
        "music_player.uf2",
        "image_viewer.uf2",
        "system_info.uf2",
        "benchmark.uf2",
        "memory_test.uf2",

        // User-defined apps (common patterns)
        "app.uf2",
        "main.uf2",
        "demo.uf2",
        "test.uf2",
        "example.uf2",

        nullptr};

    for (int i = 0; possibleUf2Files[i] != nullptr; i++)
    {
        char uf2Path[256];
        snprintf(uf2Path, sizeof(uf2Path), "%s%s", directory, possibleUf2Files[i]);

        printf("AppLoader: Checking for .uf2 file: %s\n", uf2Path);

        uint32_t fileSize = storage->getFileSize(uf2Path);
        if (fileSize > 0)
        {
            printf("AppLoader: ✅ Found .uf2 file: %s (%u bytes)\n", uf2Path, fileSize);

            // Create a manifest entry for this .uf2 file
            AppManifest manifest;
            if (createManifestFromUf2(uf2Path, manifest))
            {
                availableApps.push_back(manifest);
                printf("AppLoader: ✅ Added UF2 app: %s\n", manifest.name);
            }
            else
            {
                printf("AppLoader: ❌ Failed to create manifest for: %s\n", uf2Path);
            }
        }
    }
}

bool AppLoader::createManifestFromUf2(const char *uf2Path, AppManifest &manifest)
{
    printf("AppLoader: Creating manifest from .uf2 file: %s\n", uf2Path);

    // Initialize manifest with defaults
    memset(&manifest, 0, sizeof(manifest));

    // Derive name from filename
    const char *filename = strrchr(uf2Path, '/');
    if (filename)
    {
        filename++; // Skip the '/'
    }
    else
    {
        filename = uf2Path;
    }

    // Copy filename without .uf2 extension
    const char *extension = strrchr(filename, '.');
    size_t nameLen = extension ? (extension - filename) : strlen(filename);
    if (nameLen >= sizeof(manifest.name))
    {
        nameLen = sizeof(manifest.name) - 1;
    }

    strncpy(manifest.name, filename, nameLen);
    manifest.name[nameLen] = '\0';

    // Convert underscores to spaces and capitalize first letter
    if (manifest.name[0] >= 'a' && manifest.name[0] <= 'z')
    {
        manifest.name[0] = manifest.name[0] - 'a' + 'A';
    }
    for (char *p = manifest.name; *p; p++)
    {
        if (*p == '_')
            *p = ' ';
    }

    // Set the entry point to the .uf2 file path
    strncpy(manifest.entryPoint, uf2Path, sizeof(manifest.entryPoint) - 1);
    manifest.entryPoint[sizeof(manifest.entryPoint) - 1] = '\0';

    // Set UF2-specific defaults
    strncpy(manifest.author, "UF2 Developer", sizeof(manifest.author) - 1);
    strncpy(manifest.version, "1.0", sizeof(manifest.version) - 1);
    strncpy(manifest.description, "UF2 native application", sizeof(manifest.description) - 1);
    manifest.requiresWiFi = false;
    manifest.requiresStorage = false; // UF2 apps are self-contained
    manifest.minMemory = 256 * 1024;  // 256KB for UF2 apps

    printf("AppLoader: Created manifest for UF2 app: %s\n", manifest.name);
    return true;
}

// Legacy function - no longer used with binary apps
bool AppLoader::parseManifest(const char *manifestPath, AppManifest &manifest)
{
    // This function is deprecated in the binary app system
    // All metadata is now embedded in .pwa files or derived from filenames
    printf("AppLoader: parseManifest is deprecated - use .pwa files instead\n");
    return false;
}

bool AppLoader::validateManifest(const AppManifest &manifest)
{
    // Basic validation
    if (strlen(manifest.name) == 0)
    {
        printf("AppLoader: Validation failed - empty name\n");
        return false;
    }

    if (strlen(manifest.entryPoint) == 0)
    {
        printf("AppLoader: Validation failed - empty entry point\n");
        return false;
    }

    printf("AppLoader: Checking if UF2 file exists: %s\n", manifest.entryPoint);

    // Check if UF2 file exists and is valid
    uint32_t entrySize = storage->getFileSize(manifest.entryPoint);
    printf("AppLoader: UF2 file size: %u bytes\n", entrySize);

    if (entrySize == 0)
    {
        printf("AppLoader: UF2 file not found or empty: %s\n", manifest.entryPoint);
        return false;
    }

    // Additional validation - check if it's a UF2 file
    const char *extension = strrchr(manifest.entryPoint, '.');
    if (!extension || strcmp(extension, ".uf2") != 0)
    {
        printf("AppLoader: Entry point is not a UF2 file: %s\n", manifest.entryPoint);
        return false;
    }

    printf("AppLoader: Manifest validation passed for: %s\n", manifest.name);
    return true;
}

bool AppLoader::checkSystemRequirements(const AppManifest &manifest)
{
    // Check WiFi requirement
    if (manifest.requiresWiFi && !viewManager->getWiFi().isConnected())
    {
        return false;
    }

    // Check memory requirement (simplified)
    if (manifest.minMemory > 100000)
    { // Arbitrary limit for demo
        return false;
    }

    return true;
}

bool AppLoader::loadApp(const char *appPath)
{
    unloadCurrentApp();

    printf("AppLoader: Loading UF2 app from: %s\n", appPath);

    // Check if file exists by getting its size
    uint32_t fileSize = storage->getFileSize(appPath);
    if (fileSize == 0)
    {
        printf("AppLoader: UF2 file not found or empty: %s\n", appPath);
        return false;
    }

    // Check file extension to ensure it's a UF2 file
    const char *extension = strrchr(appPath, '.');
    if (!extension || strcmp(extension, ".uf2") != 0)
    {
        printf("AppLoader: Not a UF2 file: %s\n", appPath);
        return false;
    }

    printf("AppLoader: Loading UF2 app (%u bytes)...\n", fileSize);

    // Create and load the binary app
    auto binaryApp = std::make_unique<BinaryApp>();
    if (!binaryApp->loadFromFile(appPath))
    {
        printf("AppLoader: Failed to load binary app\n");
        return false;
    }

    // Set the current app
    currentApp = std::move(binaryApp);

    // Find and set the manifest data for this app
    for (size_t i = 0; i < availableApps.size(); i++)
    {
        if (strcmp(availableApps[i].entryPoint, appPath) == 0)
        {
            currentApp->manifest = availableApps[i];
            printf("AppLoader: Set manifest for app: %s\n", currentApp->manifest.name);
            break;
        }
    }

    printf("AppLoader: Binary app loaded successfully\n");
    return currentApp != nullptr;
}

void AppLoader::unloadCurrentApp()
{
    if (currentApp)
    {
        currentApp->cleanup(viewManager);
        currentApp.reset();
    }
}

bool AppLoader::launchApp(size_t appIndex)
{
    printf("AppLoader: Launching app at index %zu\n", appIndex);

    if (appIndex >= availableApps.size())
    {
        printf("AppLoader: Invalid app index %zu (max: %zu)\n", appIndex, availableApps.size());
        return false;
    }

    const AppManifest &manifest = availableApps[appIndex];
    printf("AppLoader: Launching app: %s\n", manifest.name);
    printf("AppLoader: Entry point: %s\n", manifest.entryPoint);

    if (!loadApp(manifest.entryPoint))
    {
        printf("AppLoader: Failed to load app: %s\n", manifest.name);
        return false;
    }

    if (!currentApp)
    {
        printf("AppLoader: currentApp is null after loading!\n");
        return false;
    }

    printf("AppLoader: Initializing app: %s\n", manifest.name);
    bool initResult = currentApp->initialize(viewManager);
    printf("AppLoader: App initialization result: %s\n", initResult ? "success" : "failed");

    return initResult;
}
