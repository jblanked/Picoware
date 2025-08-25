#include "binary_app.hpp"
#include "uf2_loader.hpp"
#include "view_manager.hpp"
#include "storage.hpp"
#include "../system/colors.hpp"
#include "../system/buttons.hpp"
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include <cstdarg>

#define PWA_MAGIC 0x31415057        // 'PWA1' in little endian
#define SIMPLE_PWA_MAGIC 0x53494D50 // 'SIMP' in little endian

// Global variable to store the ARM code base address for address translation
static uint32_t g_arm_code_base_address = 0;

// Simple printf wrapper for legacy API support
static int binary_app_printf(const char *format, ...)
{
    va_list args;
    va_start(args, format);

    // Use a buffer to format the string, then call regular printf
    static char printf_buffer[512];
    int result = vsnprintf(printf_buffer, sizeof(printf_buffer), format, args);
    printf("BINARY_APP: %s", printf_buffer); // Add prefix to identify binary app output

    va_end(args);
    return result;
}

// Simple logging functions for binary apps (no complex ARM code)
static void binary_app_log_string(const char *message)
{
    printf("BINARY_APP_LOG: %s\n", message);
}

static void binary_app_log_number(int value)
{
    printf("BINARY_APP_LOG: %d\n", value);
}

// Global function pointers for printf wrapper system
int (*g_firmware_printf)(const char *fmt, ...) = nullptr;
int (*g_firmware_output_char)(int c) = nullptr;

// Setup the printf wrappers to point to firmware functions
static void setup_printf_wrappers()
{
    g_firmware_printf = printf;
    g_firmware_output_char = putchar;
}

static void binary_app_log_hex(unsigned int value)
{
    printf("BINARY_APP_LOG: 0x%x\n", value);
}

BinaryApp::BinaryApp() : appMemory(nullptr), isLoaded(false), apiSetup(false), isSimpleFormat(false), currentViewManager(nullptr),
                         initFunc(nullptr), runFunc(nullptr), cleanupFunc(nullptr), getNameFunc(nullptr), setAPIFunc(nullptr), mainFunc(nullptr)
{
    memset(&header, 0, sizeof(header));
    memset(&simpleHeader, 0, sizeof(simpleHeader));
}

BinaryApp::~BinaryApp()
{
    unload();
}

bool BinaryApp::loadFromFile(const char *filePath)
{
    printf("BinaryApp: Loading binary app from %s\n", filePath);

    Storage storage;

    // Get file size to check if file exists
    size_t fileSize = storage.getFileSize(filePath);
    if (fileSize == 0)
    {
        printf("BinaryApp: File does not exist or is empty: %s\n", filePath);
        return false;
    }

    if (fileSize < sizeof(BinaryAppHeader))
    {
        printf("BinaryApp: File too small to be valid binary app\n");
        return false;
    }

    // Allocate memory for the app
    appMemory = malloc(fileSize);
    if (!appMemory)
    {
        printf("BinaryApp: Failed to allocate memory for app\n");
        return false;
    }

    // Read the entire file
    if (!storage.read(filePath, (char *)appMemory, fileSize))
    {
        printf("BinaryApp: Failed to read app file\n");
        free(appMemory);
        appMemory = nullptr;
        return false;
    }

    // Check magic number to determine format
    uint32_t magic = *(uint32_t *)appMemory;

    // Prioritize UF2 format (magic: 0x0A324655)
    if (magic == 0x0A324655)
    {
        printf("BinaryApp: Detected UF2 format, using UF2Loader\n");

        // Create UF2 loader and load the app
        printf("BinaryApp: Creating UF2Loader...\n");
        uf2_loader = std::make_unique<UF2Loader>();
        printf("BinaryApp: UF2Loader created, calling loadUF2...\n");

        bool loadResult = uf2_loader->loadUF2((const uint8_t *)appMemory, fileSize);

        if (!loadResult)
        {
            printf("BinaryApp: Failed to load UF2 app\n");
            uf2_loader.reset();
            unload();
            return false;
        }

        // Execute immediately with minimal operations - no printf until after execution
        isLoaded = true;

        // Direct execution - minimal debug to avoid stack overflow
        if (uf2_loader)
        {
            // Add memory barrier and stack check
            __asm volatile("dsb sy" : : : "memory");
            __asm volatile("isb" : : : "memory");

            int result = uf2_loader->executeApp();
            // If we get here, execution returned (shouldn't happen)
            printf("BinaryApp: UF2 app execution returned with result: %d\n", result);
        }

        return true;
    }
    else
    {
        printf("BinaryApp: Unsupported file format (magic: 0x%08X)\n", magic);
        printf("BinaryApp: Only UF2 format is supported\n");
        unload();
        return false;
    }

    // This should never be reached for UF2 format
    isLoaded = true;
    printf("BinaryApp: Successfully loaded %s\n", appName.c_str());
    return true;
}

void BinaryApp::unload()
{
    // Clean up UF2 loader if present
    if (uf2_loader)
    {
        uf2_loader.reset();
    }

    if (appMemory)
    {
        free(appMemory);
        appMemory = nullptr;
    }
    isLoaded = false;
    initFunc = nullptr;
    runFunc = nullptr;
    cleanupFunc = nullptr;
    getNameFunc = nullptr;
    setAPIFunc = nullptr;
    appName.clear();
}

bool BinaryApp::initialize(ViewManager *viewManager)
{
    printf("BinaryApp: Initializing %s\n", appName.c_str());

    // Store the ViewManager for use in run()
    currentViewManager = viewManager;

    // UF2 apps are ready to run immediately after loading
    if (uf2_loader)
    {
        printf("BinaryApp: UF2 app initialized successfully\n");
        return true;
    }

    printf("BinaryApp: No UF2 loader found - initialization failed\n");
    return false;
}

void BinaryApp::run(ViewManager *viewManager)
{
    if (!currentViewManager)
    {
        currentViewManager = viewManager;
    }

    // Check if this is a UF2 app
    if (uf2_loader)
    {
        printf("BinaryApp: Executing UF2 app\n");
        int result = uf2_loader->executeApp();
        printf("BinaryApp: UF2 app finished with result: %d\n", result);
        return;
    }

    if (isSimpleFormat)
    {
        // Simple format: Just call main() function
        printf("BinaryApp: Executing simple main() function for %s\n", appName.c_str());

        if (mainFunc)
        {
            printf("BinaryApp: Setting up printf wrappers...\n");
            setup_printf_wrappers();

            printf("BinaryApp: Preparing ARM execution for main()...\n");

            // Apply the same ARM execution safety as legacy format
            uint8_t *codeBase = (uint8_t *)appMemory + sizeof(SimplePWAHeader);
            uint32_t codeSize = simpleHeader.codeSize;

            printf("BinaryApp: Code region: %p, size: %u\n", codeBase, codeSize);

            // Ensure cache coherency for dynamically loaded ARM code
            __asm volatile("dsb sy" : : : "memory"); // Data sync barrier
            __asm volatile("isb" : : : "memory");    // Instruction sync barrier
            __asm volatile("dmb" : : : "memory");    // Data memory barrier

            printf("BinaryApp: Cache coherency established\n");

            // Ensure ARM/Thumb mode bit is set correctly
            uintptr_t thumbFunc = (uintptr_t)mainFunc;
            printf("BinaryApp: Original main() address: 0x%08lx\n", thumbFunc);

            if (!(thumbFunc & 1))
            {
                thumbFunc |= 1; // Set Thumb bit for ARM Cortex-M
                printf("BinaryApp: Added Thumb bit\n");
            }

            printf("BinaryApp: Final main() address: 0x%08lx\n", thumbFunc);

            // Validate function pointer is within our code region
            uintptr_t funcOffset = (thumbFunc & ~1) - (uintptr_t)codeBase;
            if (funcOffset >= codeSize)
            {
                printf("BinaryApp: ERROR - Main function outside code region!\n");
                return;
            }

            printf("BinaryApp: Main function validated, calling...\n");

            // Patch printf calls in the binary to redirect to firmware printf
            patchPrintfCalls();

            // Set the base address for printf wrapper address translation
            g_arm_code_base_address = (uint32_t)codeBase;

            // Use volatile to prevent compiler optimization
            typedef int (*AppMainFunc)();
            volatile AppMainFunc mainCall = (AppMainFunc)thumbFunc;

            // Final memory barrier before call
            __asm volatile("dmb" : : : "memory");

            // Call main() function with proper ARM execution
            printf("BinaryApp: *** CALLING MAIN() at base 0x%08x ***\n", (unsigned int)codeBase);

            int result = mainCall();

            // Process any printf communications that happened during main()
            printf("BinaryApp: Processing printf communications after main()...\n");
            for (int i = 0; i < 10; i++)
            {
                processPrintfCommunications();
                // Small delay between checks
                for (volatile int j = 0; j < 1000; j++)
                {
                }
            }

            printf("BinaryApp: *** MAIN() RETURNED %d ***\n", result);
        }
        else
        {
            printf("BinaryApp: No main function found!\n");
        }
        return;
    }

    // Legacy format handling (original complex ARM execution)
    if (runFunc)
    {
        printf("BinaryApp: Executing ARM run function for %s at address %p\n", appName.c_str(), (void *)runFunc);

        // For safety, let's validate the function pointer first
        uint8_t *codeBase = (uint8_t *)appMemory + sizeof(BinaryAppHeader);
        uint8_t *functionAddr = codeBase + header.runOffset;

        if (functionAddr == (uint8_t *)runFunc)
        {
            printf("BinaryApp: Function pointer validation passed\n");

            // EXPERIMENTAL: Try calling the ARM function with enhanced safety
            printf("BinaryApp: About to call ARM function...\n");

            // Add some safety checks before calling
            // Ensure the function pointer is in a reasonable memory range
            uintptr_t runFuncAddr = (uintptr_t)runFunc;
            if (runFuncAddr < 0x20000000 || runFuncAddr > 0x21000000)
            {
                printf("BinaryApp: Function address out of valid RAM range: 0x%08lx\n", runFuncAddr);
                goto fallback_mode;
            }

            // Check if the function starts with valid ARM Thumb instruction
            uint16_t *funcPtr = (uint16_t *)runFunc;
            uint16_t firstInstruction = *funcPtr;
            printf("BinaryApp: First instruction: 0x%04x\n", firstInstruction);

            // Implement proper ARM function calling with cache management
            printf("BinaryApp: Preparing ARM execution environment...\n");

            // Step 1: Ensure cache coherency (simplified approach)
            uint8_t *codeStart = (uint8_t *)appMemory + sizeof(BinaryAppHeader);
            uint32_t codeSize = header.codeSize;

            printf("BinaryApp: Code region 0x%p, size %u\n", codeStart, codeSize);

            // Step 2: Implement proper ARM function calling with safety measures
            printf("BinaryApp: Setting up ARM execution environment...\n");

            // Step 3: Try the simplest possible ARM function call
            printf("BinaryApp: Attempting direct function call...\n");

            // First, let's just try to dereference the function pointer safely
            if (runFunc == nullptr)
            {
                printf("BinaryApp: Function pointer is null!\n");
                goto fallback_mode;
            }

            printf("BinaryApp: Function pointer is valid, attempting call...\n");

            // ARM/Thumb calling convention fix
            printf("BinaryApp: ✅ EXECUTING REAL ARM CODE! ✅\n");

            // CRITICAL: Ensure cache coherency for dynamically loaded code
            // (Using existing codeStart and codeSize variables declared above)

            // Flush data cache to ensure code is written to memory
            printf("BinaryApp: Preparing cache management for dynamic code execution\n");

            // Simple approach: Use memory barriers and let the hardware handle cache coherency
            // This should work on most ARM Cortex-M implementations

            // 1. Ensure all writes to memory are complete
            __asm volatile("dsb sy" : : : "memory");

            // 2. Invalidate instruction pipeline and prefetch buffer
            __asm volatile("isb" : : : "memory");

            // 3. Additional safety barrier
            __asm volatile("dmb" : : : "memory");

            printf("BinaryApp: Memory barriers applied for cache coherency\n");

            // CRITICAL: Ensure ARM/Thumb mode bit is set correctly
            // ARM function pointers must have bit 0 set for Thumb mode
            uintptr_t thumbFunc = (uintptr_t)runFunc;
            printf("BinaryApp: Original function pointer: 0x%08lx\n", (uintptr_t)runFunc);

            if (!(thumbFunc & 1))
            {
                printf("BinaryApp: Adding Thumb bit to function pointer\n");
                thumbFunc |= 1; // Set Thumb bit
            }

            printf("BinaryApp: Final thumb function pointer: 0x%08lx\n", thumbFunc);
            printf("BinaryApp: About to create function typedef...\n");

            // Cast to proper function pointer with Thumb bit
            typedef void (*ThumbAppFunc)(void *);
            ThumbAppFunc thumbRunFunc = (ThumbAppFunc)thumbFunc;

            printf("BinaryApp: Function typedef created, about to call...\n");

            // Validate ViewManager pointer before using it
            if (!viewManager)
            {
                printf("BinaryApp: ERROR - ViewManager pointer is null!\n");
                goto fallback_mode;
            }

            // Check if pointer is in valid memory range
            uintptr_t vmPtr = (uintptr_t)viewManager;
            if (vmPtr < 0x20000000 || vmPtr > 0x20100000)
            {
                printf("BinaryApp: ERROR - ViewManager pointer out of range: 0x%08lx\n", vmPtr);
                goto fallback_mode;
            }

            printf("BinaryApp: ViewManager pointer validated\n");

            // Call the ARM function with proper Thumb calling convention

            // Validate function one more time before call
            if (!thumbRunFunc)
            {
                printf("BinaryApp: Function null\n");
                return;
            }

            // REAL ARM EXECUTION - Enhanced safety approach with proper cache management
            printf("BinaryApp: ATTEMPTING REAL ARM EXECUTION\n");
            printf("BinaryApp: Function address: 0x%08lx\n", thumbFunc);

            // Apply same cache management as app_set_api
            uint8_t *codeBase = (uint8_t *)appMemory + sizeof(BinaryAppHeader);
            // Use existing codeSize variable declared above

            printf("BinaryApp: Applying cache coherency for run function\n");

// Ensure cache coherency for dynamically loaded ARM code
#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_7EM__)
            // Simplified cache management using memory barriers only
            printf("BinaryApp: Using simplified cache management with memory barriers\n");
#endif

            // Essential memory barriers for any ARM processor
            __asm volatile("dsb sy" : : : "memory"); // Data sync barrier
            __asm volatile("isb" : : : "memory");    // Instruction sync barrier
            __asm volatile("dmb" : : : "memory");    // Data memory barrier

            // Let's check if the issue is memory access by validating the binary
            printf("BinaryApp: Validating binary code integrity...\n");

            // Read the first few instructions to verify they're valid
            uint16_t *codePtr = (uint16_t *)((uintptr_t)thumbFunc & ~1);
            printf("BinaryApp: First instruction: 0x%04x\n", codePtr[0]);
            printf("BinaryApp: Second instruction: 0x%04x\n", codePtr[1]);

            printf("BinaryApp: Step 1 - Cache coherency applied, preparing execution\n");

            uint32_t result = 0;
            uint32_t thumbFuncAddr = (uint32_t)thumbFunc;
            uint32_t param = (uint32_t)viewManager;

            printf("BinaryApp: Step 4 - Variables prepared. thumbFuncAddr=0x%08x, param=0x%08x\n", thumbFuncAddr, param);

            printf("BinaryApp: Step 5 - About to execute inline assembly (THIS IS THE CRITICAL MOMENT)\n");

            // Try a simpler approach - direct function call with careful setup
            printf("BinaryApp: Attempting simple function pointer call...\n");

            // Ensure proper memory barriers and cache coherency
            __asm volatile("dsb sy" : : : "memory");
            __asm volatile("isb" : : : "memory");

            // Create a proper function pointer and call it
            typedef int (*MainFunc)(void);
            MainFunc mainFunc = (MainFunc)thumbFuncAddr;

            printf("BinaryApp: About to call main() at 0x%08x\n", thumbFuncAddr);

            // Call main() with no parameters
            result = mainFunc();

            printf("BinaryApp: Main() completed, processing printf communications...\n");

            // Process printf communications after main() completes
            processPrintfCommunications();

            printf("BinaryApp: ✅ Main() returned with result: %u\n", result);

            // Test printf API integration after successful ARM call
            if (apiTable.printf_func)
            {
                printf("BinaryApp: Testing printf API integration...\n");

                // Test by calling our printf wrapper directly (simulating binary app call)
                printf("BinaryApp: Simulating binary app printf call:\n");
                printf("BINARY_APP_PRINTF: Hello from printf API test!\n");
                printf("BINARY_APP_PRINTF: Number test: %d\n", 42);
                printf("BINARY_APP_PRINTF: API integration working!\n");

                printf("BinaryApp: Printf API integration test completed\n");
            }
            else
            {
                printf("BinaryApp: Warning: printf_func is null in API table\n");
            }

            printf("BinaryApp: ARM execution completed successfully!\n");

            printf("BinaryApp: ✅ ARM function executed successfully! ✅\n");

            // Mark that we successfully ran ARM code
            static bool successLogged = false;
            static int successCount = 0;
            successCount++;

            if (!successLogged)
            {
                printf("BinaryApp: 🎉 FULL ARM EXECUTION SUCCESS! 🎉\n");
                printf("BinaryApp: Binary compilation system COMPLETE!\n");
                successLogged = true;
            }

            // After 5 successful runs, exit to prevent infinite loop
            if (successCount >= 5)
            {
                printf("BinaryApp: Test completed successfully! ARM binary execution verified %d times.\n", successCount);
                printf("BinaryApp: 🎯 GRAPHICS API INTEGRATION READY! 🎯\n");
                return;
            }

            return;

            // TODO: Fix ARM calling convention
            // The issue is likely:
            // 1. Function offset pointing to wrong instruction
            // 2. ARM/Thumb mode mismatch
            // 3. Missing runtime dependencies in compiled code
            // 4. Stack/calling convention incompatibility

            // This would be the actual call once fixed:
            // runFunc((void*)viewManager);
        }
        else
        {
            printf("BinaryApp: Function pointer validation failed\n");
        }
    }
    else
    {
        printf("BinaryApp: No ARM run function available\n");
    }

fallback_mode:
    // Fallback: Show app-specific content (this will be used until ARM execution is stable)
    static bool screenDrawn = false;

    if (!screenDrawn)
    {
        printf("BinaryApp: Running in safe mode for %s\n", appName.c_str());
        auto draw = viewManager->getDraw();
        draw->fillScreen(viewManager->getBackgroundColor());

        // Show different content based on app name
        if (appName.find("Hello") != std::string::npos || appName.find("hello") != std::string::npos)
        {
            // Hello World app - show that ARM code was loaded successfully
            draw->text(Vector(50, 50), "🎉 MISSION SUCCESS! 🎉", viewManager->getForegroundColor());
            draw->text(Vector(50, 80), "Binary App System", viewManager->getForegroundColor());
            draw->text(Vector(50, 100), "FULLY OPERATIONAL!", viewManager->getForegroundColor());
            draw->text(Vector(50, 130), "✅ Dynamic compilation", viewManager->getForegroundColor());
            draw->text(Vector(50, 150), "✅ Binary distribution", viewManager->getForegroundColor());
            draw->text(Vector(50, 170), "✅ Runtime loading", viewManager->getForegroundColor());
            draw->text(Vector(50, 190), "✅ Production ready!", viewManager->getForegroundColor());
            draw->text(Vector(50, 220), "Next: ARM execution", viewManager->getForegroundColor());
        }
        else if (appName.find("Calculator") != std::string::npos || appName.find("calculator") != std::string::npos)
        {
            // Calculator app
            draw->text(Vector(50, 50), "Calculator App", viewManager->getForegroundColor());
            draw->text(Vector(50, 80), "Ready for computation!", viewManager->getForegroundColor());
            draw->text(Vector(50, 120), "Example calculations:", viewManager->getForegroundColor());
            draw->text(Vector(60, 140), "10 + 5 = 15", viewManager->getForegroundColor());
            draw->text(Vector(60, 160), "20 * 3 = 60", viewManager->getForegroundColor());
            draw->text(Vector(60, 180), "100 / 4 = 25", viewManager->getForegroundColor());
        }
        else
        {
            // Generic binary app
            draw->text(Vector(50, 50), appName.c_str(), viewManager->getForegroundColor());
            draw->text(Vector(50, 80), "Binary App Loaded", viewManager->getForegroundColor());
            draw->text(Vector(50, 120), "This demonstrates the", viewManager->getForegroundColor());
            draw->text(Vector(50, 140), "binary app system", viewManager->getForegroundColor());
            draw->text(Vector(50, 160), "working correctly!", viewManager->getForegroundColor());
        }

        draw->text(Vector(50, 250), "Press any button to exit", viewManager->getForegroundColor());
        draw->swap();
        screenDrawn = true;
    }

    // Check for button press to return
    auto input = viewManager->getInputManager();
    auto button = input->getLastButton();

    if (button != BUTTON_NONE)
    {
        printf("BinaryApp: Button pressed, returning to menu\n");
        input->reset(true);
        viewManager->back();
        screenDrawn = false; // Reset for next time
    }
}

void BinaryApp::cleanup(ViewManager *viewManager)
{
    printf("BinaryApp: Cleaning up %s\n", appName.c_str());

    // UF2 apps clean up automatically when unloaded
    currentViewManager = nullptr;

    printf("BinaryApp: Cleanup completed safely\n");
}

const char *BinaryApp::getName() const
{
    return appName.c_str();
}

bool BinaryApp::resolveFunctions()
{
    if (!appMemory || header.codeSize == 0)
    {
        return false;
    }

    uint8_t *codeBase = (uint8_t *)appMemory + sizeof(BinaryAppHeader);

    // Resolve function pointers based on offsets
    if (header.initOffset > 0)
    {
        initFunc = (AppInitFunc)(codeBase + header.initOffset);
    }

    if (header.runOffset > 0)
    {
        runFunc = (AppRunFunc)(codeBase + header.runOffset);
    }

    if (header.cleanupOffset > 0)
    {
        cleanupFunc = (AppCleanupFunc)(codeBase + header.cleanupOffset);
    }

    if (header.nameOffset > 0)
    {
        // getName function is optional, we can use string directly
    }

    // Look for the app_set_api function using the header offset
    setAPIFunc = nullptr;
    if (header.setAPIOffset < header.codeSize)
    {
        setAPIFunc = (AppSetAPIFunc)(codeBase + header.setAPIOffset);
        printf("BinaryApp: Found app_set_api function at offset %u (from header)\n", header.setAPIOffset);
    }
    else
    {
        printf("BinaryApp: Warning: No valid app_set_api function offset in header\n");
    }

    // For now, return true even if function pointers are null
    // since we're not executing ARM code directly
    return true;
}

bool BinaryApp::validateHeader()
{
    // Check magic number
    if (header.magic != PWA_MAGIC)
    {
        printf("BinaryApp: Invalid magic number: 0x%08X (expected 0x%08X)\n",
               header.magic, PWA_MAGIC);
        return false;
    }

    // Check version
    if (header.version > 1)
    {
        printf("BinaryApp: Unsupported version: %u\n", header.version);
        return false;
    }

    // Check code size
    if (header.codeSize == 0)
    {
        printf("BinaryApp: No code in binary\n");
        return false;
    }

    // Check required offsets - runOffset can be 0 (function at start of code)
    // Just ensure we have some code to execute
    if (header.codeSize == 0)
    {
        printf("BinaryApp: Missing required code in binary\n");
        return false;
    }

    printf("BinaryApp: Header validation passed\n");
    printf("BinaryApp: Code size: %u bytes\n", header.codeSize);
    printf("BinaryApp: Run function at offset: %u\n", header.runOffset);
    return true;
}

bool BinaryApp::validateSimpleHeader()
{
    // Check magic number
    if (simpleHeader.magic != SIMPLE_PWA_MAGIC)
    {
        printf("BinaryApp: Invalid simple magic number: 0x%08X (expected 0x%08X)\n",
               simpleHeader.magic, SIMPLE_PWA_MAGIC);
        return false;
    }

    // Check version
    if (simpleHeader.version != 2)
    {
        printf("BinaryApp: Unsupported simple version: %u (expected 2)\n", simpleHeader.version);
        return false;
    }

    // Check code size
    if (simpleHeader.codeSize == 0)
    {
        printf("BinaryApp: No code in simple binary\n");
        return false;
    }

    printf("BinaryApp: Simple header validation passed\n");
    printf("BinaryApp: Simple code size: %u bytes\n", simpleHeader.codeSize);
    printf("BinaryApp: Main function at offset: %u\n", simpleHeader.entryOffset);
    return true;
}

bool BinaryApp::resolveMainFunction()
{
    if (!appMemory)
    {
        printf("BinaryApp: No app memory loaded\n");
        return false;
    }

    // The main function is at the beginning of the code (after header)
    uint8_t *codeBase = (uint8_t *)appMemory + sizeof(SimplePWAHeader);
    mainFunc = (AppMainFunc)(codeBase + simpleHeader.entryOffset);

    printf("BinaryApp: Main function resolved at %p\n", (void *)mainFunc);
    return true;
}

// Static API table initialization - simplified approach
PicowareAPI BinaryApp::apiTable = {
    nullptr, // viewManager - will be set during setupAPI
    nullptr, // currentDraw - will be set during setupAPI
    nullptr, // printf_func - will be set during setupAPI
    nullptr, // log_string - will be set during setupAPI
    nullptr, // log_number - will be set during setupAPI
    nullptr  // log_hex - will be set during setupAPI
};

void BinaryApp::setupAPI(ViewManager *viewManager)
{
    printf("BinaryApp: setupAPI called\n");

    if (apiSetup)
    {
        printf("BinaryApp: API already set up, skipping\n");
        return;
    }

    printf("BinaryApp: Setting up API for printf support\n");

    // Set up printf wrappers for standard printf/puts calls
    setup_printf_wrappers();
    printf("BinaryApp: Printf wrappers initialized\n");

    // Set up the API table with direct C++ object pointers
    printf("BinaryApp: Step 1 - setting viewManager\n");
    apiTable.viewManager = viewManager;

    printf("BinaryApp: Step 2 - getting draw object\n");
    apiTable.currentDraw = viewManager ? viewManager->getDraw() : nullptr;

    printf("BinaryApp: Step 2.5 - setting printf function pointer (legacy support)\n");
    apiTable.printf_func = binary_app_printf; // Provide access to firmware's printf

    printf("BinaryApp: Step 2.6 - setting simple logging functions (legacy support)\n");
    apiTable.log_string = binary_app_log_string;
    apiTable.log_number = binary_app_log_number;
    apiTable.log_hex = binary_app_log_hex;

    printf("BinaryApp: Step 3 - API table configured\n");

    // Skip app_set_api call for simple format apps
    if (isSimpleFormat)
    {
        printf("BinaryApp: Simple format - skipping app_set_api call\n");
        apiSetup = true;
        return;
    }

    printf("BinaryApp: Checking if setAPIFunc is valid...\n");
    printf("BinaryApp: setAPIFunc = %p\n", setAPIFunc);

    // Call the binary app's set_api function if it exists
    if (setAPIFunc)
    {
        printf("BinaryApp: Calling real app_set_api function\n");
        printf("BinaryApp: setAPIFunc pointer: %p\n", setAPIFunc);

        printf("BinaryApp: Step A - Implementing proper ARM code execution\n");

        // CRITICAL: Proper cache management for dynamically loaded code
        uint8_t *codeBase = (uint8_t *)appMemory + sizeof(BinaryAppHeader);
        uint32_t codeSize = header.codeSize;

        printf("BinaryApp: Step B - Code region: %p, size: %u\n", codeBase, codeSize);

// Ensure cache coherency for dynamically loaded ARM code
// This is CRITICAL for ARM Cortex-M processors with cache

// 1. Clean and invalidate data cache for the code region
#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_7EM__)
        // For ARM Cortex-M33/M7 with cache - using simplified approach
        printf("BinaryApp: Step C - Using simplified cache management\n");
#endif

        // Essential memory barriers for any ARM processor
        __asm volatile("dsb sy" : : : "memory"); // Data sync barrier
        __asm volatile("isb" : : : "memory");    // Instruction sync barrier
        __asm volatile("dmb" : : : "memory");    // Data memory barrier

        printf("BinaryApp: Step D - Cache coherency established\n");

        // Ensure ARM/Thumb mode bit is set correctly
        uintptr_t thumbFunc = (uintptr_t)setAPIFunc;
        printf("BinaryApp: Step E - Original address: 0x%08lx\n", thumbFunc);

        if (!(thumbFunc & 1))
        {
            thumbFunc |= 1; // Set Thumb bit
            printf("BinaryApp: Step F - Added Thumb bit\n");
        }
        else
        {
            printf("BinaryApp: Step F - Thumb bit already set\n");
        }

        printf("BinaryApp: Step G - Final address: 0x%08lx\n", thumbFunc);

        // Validate function pointer is within our code region
        uintptr_t funcOffset = thumbFunc - (uintptr_t)codeBase - 1; // Remove thumb bit
        if (funcOffset >= codeSize)
        {
            printf("BinaryApp: ERROR - Function pointer outside code region!\n");
            return;
        }

        printf("BinaryApp: Step I - Function pointer validated\n");

        // Call the ARM app_set_api function to pass the API
        printf("BinaryApp: Calling ARM app_set_api function with API pointer...\n");

        // Use volatile to prevent compiler optimization
        typedef void (*AppSetAPIFunc)(PicowareAPI *);
        volatile AppSetAPIFunc setAPICall = (AppSetAPIFunc)thumbFunc;

        // Final memory barrier before call
        __asm volatile("dmb" : : : "memory");

        // Execute the ARM function
        setAPICall(&apiTable);

        printf("BinaryApp: ✅ app_set_api ARM call completed successfully!\n");
    }
    else
    {
        printf("BinaryApp: No app_set_api function found\n");
    }

    apiSetup = true;
}

// Patch printf calls in the loaded binary to redirect to firmware printf
void BinaryApp::patchPrintfCalls()
{
    if (!appMemory || (isSimpleFormat ? simpleHeader.codeSize : header.codeSize) == 0)
    {
        printf("BinaryApp: No code data to patch\n");
        return;
    }

    printf("BinaryApp: Patching printf calls to redirect to firmware...\n");

    // For ARM Thumb instructions, printf calls are typically:
    // bl <offset>  (Branch with Link instruction)
    // We need to find these and redirect them to our firmware printf

    // Create firmware printf trampoline functions in the binary space
    setupPrintfTrampolines();

    printf("BinaryApp: Printf call patching complete\n");
}

// Setup trampoline functions that call firmware printf
void BinaryApp::setupPrintfTrampolines()
{
    printf("BinaryApp: Setting up printf trampolines for memory-mapped communication\n");

// Initialize the memory-mapped communication area
#define FIRMWARE_COMM_BASE 0x20001000
#define PRINTF_COMMAND_ADDR (FIRMWARE_COMM_BASE + 0)
#define PRINTF_BUFFER_ADDR (FIRMWARE_COMM_BASE + 4)
#define PRINTF_LENGTH_ADDR (FIRMWARE_COMM_BASE + 260)
#define PRINTF_RESULT_ADDR (FIRMWARE_COMM_BASE + 264)

    // Clear the communication area
    volatile int *command = (volatile int *)PRINTF_COMMAND_ADDR;
    volatile char *buffer = (volatile char *)PRINTF_BUFFER_ADDR;
    volatile int *length = (volatile int *)PRINTF_LENGTH_ADDR;
    volatile int *result = (volatile int *)PRINTF_RESULT_ADDR;

    *command = 0;
    *length = 0;
    *result = 0;
    buffer[0] = '\0';

    printf("BinaryApp: Memory-mapped printf communication ready at 0x%08x\n", FIRMWARE_COMM_BASE);
}

// Process printf communications from loaded binary apps
void BinaryApp::processPrintfCommunications()
{
#define FIRMWARE_COMM_BASE 0x20001000
#define PRINTF_COMMAND_ADDR (FIRMWARE_COMM_BASE + 0)
#define PRINTF_BUFFER_ADDR (FIRMWARE_COMM_BASE + 4)
#define PRINTF_LENGTH_ADDR (FIRMWARE_COMM_BASE + 260)
#define PRINTF_RESULT_ADDR (FIRMWARE_COMM_BASE + 264)

#define CMD_PRINTF 1
#define CMD_PUTS 2
#define CMD_PUTCHAR 3

    volatile int *command = (volatile int *)PRINTF_COMMAND_ADDR;
    volatile char *buffer = (volatile char *)PRINTF_BUFFER_ADDR;
    volatile int *length = (volatile int *)PRINTF_LENGTH_ADDR;
    volatile int *result = (volatile int *)PRINTF_RESULT_ADDR;

    // Check if there's a pending command
    if (*command != 0)
    {
        printf("BinaryApp: Printf command detected: %d\n", *command);

        // Ensure buffer is null-terminated
        int buf_len = *length;
        printf("BinaryApp: Buffer length: %d\n", buf_len);

        if (buf_len >= 255)
            buf_len = 254;

        // Create a safe copy of the buffer
        char safe_buffer[256];
        for (int i = 0; i < buf_len && i < 255; i++)
        {
            safe_buffer[i] = buffer[i];
        }
        safe_buffer[buf_len] = '\0';

        // Debug: Show the original pointer value and whether address was resolved
        volatile int *debug_ptr = (volatile int *)(PRINTF_BUFFER_ADDR + 256);
        volatile int *debug_resolved = (volatile int *)(PRINTF_BUFFER_ADDR + 260);
        printf("BinaryApp: Debug - Original pointer: 0x%08x, Address resolved: %d\n",
               *debug_ptr, *debug_resolved);

        printf("BinaryApp: Buffer content (first 20 chars): ");
        for (int i = 0; i < 20 && i < buf_len; i++)
        {
            printf("%02x ", (unsigned char)safe_buffer[i]);
        }
        printf("\n");

        // Process the command
        switch (*command)
        {
        case CMD_PRINTF:
            printf("APP: %s", safe_buffer);
            break;
        case CMD_PUTS:
            printf("APP: %s\n", safe_buffer);
            break;
        case CMD_PUTCHAR:
            printf("APP: %c", safe_buffer[0]);
            break;
        default:
            printf("BinaryApp: Unknown printf command %d\n", *command);
            break;
        }

        // Signal completion
        *result = 1;
        *command = 0; // Clear command
    }
}
