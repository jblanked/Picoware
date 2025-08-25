#pragma once
#include <vector>
#include <memory>
#include <functional>

// Forward declarations
class ViewManager;
class Storage;

// Forward declarations
class DynamicApp;
class AppLoader;

// Application metadata structure
struct AppManifest
{
    char name[64];
    char description[256];
    char author[64];
    char version[16];
    char entryPoint[128]; // Path to the main app file
    char iconPath[128];   // Path to icon (optional)
    bool requiresWiFi;
    bool requiresStorage;
    uint32_t minMemory; // Minimum required memory in bytes
};

// Dynamic application interface
class DynamicApp
{
public:
    virtual ~DynamicApp() = default;
    virtual bool initialize(ViewManager *viewManager) = 0;
    virtual void run(ViewManager *viewManager) = 0;
    virtual void cleanup(ViewManager *viewManager) = 0;
    virtual const char *getName() const = 0;

    AppManifest manifest;
};

// Application factory function type
typedef std::unique_ptr<DynamicApp> (*AppCreateFunction)();

// Application loader and manager
class AppLoader
{
public:
    AppLoader(ViewManager *viewManager);
    ~AppLoader();

    // Scan SD card for applications
    bool scanForApps();

    // Load a specific application
    bool loadApp(const char *appPath);

    // Unload current application
    void unloadCurrentApp();

    // Get list of available applications
    const std::vector<AppManifest> &getAvailableApps() const { return availableApps; }

    // Launch application by index
    bool launchApp(size_t appIndex);

    // Check if an app is currently loaded
    bool hasLoadedApp() const { return currentApp != nullptr; }

    // Get current app
    DynamicApp *getCurrentApp() const { return currentApp.get(); }

private:
    ViewManager *viewManager;
    Storage *storage;
    std::vector<AppManifest> availableApps;
    std::unique_ptr<DynamicApp> currentApp;

    // Helper functions
    bool parseManifest(const char *manifestPath, AppManifest &manifest);
    bool validateManifest(const AppManifest &manifest);
    bool checkSystemRequirements(const AppManifest &manifest);

    // UF2 app functions
    void scanDirectoryForUf2Files(const char *directory);
    bool createManifestFromUf2(const char *uf2Path, AppManifest &manifest);
};

// Base class for creating dynamic applications
class BaseApp : public DynamicApp
{
protected:
    ViewManager *vm;

public:
    BaseApp() : vm(nullptr) {}

    bool initialize(ViewManager *viewManager) override
    {
        vm = viewManager;
        return onInitialize();
    }

    void run(ViewManager *viewManager) override
    {
        if (vm == nullptr)
            vm = viewManager;
        onRun();
    }

    void cleanup(ViewManager *viewManager) override
    {
        if (vm == nullptr)
            vm = viewManager;
        onCleanup();
        vm = nullptr;
    }

    // To be implemented by derived classes
    virtual bool onInitialize() = 0;
    virtual void onRun() = 0;
    virtual void onCleanup() = 0;
};

// Macro to simplify app creation
#define PICOWARE_APP(AppClass)                         \
    extern "C" std::unique_ptr<DynamicApp> createApp() \
    {                                                  \
        return std::make_unique<AppClass>();           \
    }
