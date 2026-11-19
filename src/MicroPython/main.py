def main():
    """Main function to run the application"""
    from micropython import alloc_emergency_exception_buf
    from gc import collect, threshold, mem_free, mem_alloc
    from time import sleep
    from picoware.system.boards import BOARD_HAS_ESP32

    if BOARD_HAS_ESP32 == 1:
        # added this for ThonnyIDE connecting/stopping
        sleep(1)

    alloc_emergency_exception_buf(100)

    # Initial cleanup
    collect()
    threshold(mem_free() // 4 + mem_alloc())

    from picoware.system.view_manager import ViewManager
    from picoware.system.view import View
    from picoware.applications import desktop

    # Initialize the view manager
    vm: ViewManager = None
    try:
        vm: ViewManager = ViewManager()

        vm.add(View("desktop_view", desktop.run, desktop.start, desktop.stop), True)

        collect()
        threshold(mem_free() // 4 + mem_alloc())
        
        while vm.run():
            pass

    except Exception as e:
        if vm is not None:
            vm.alert("Critical Error:\n%s\nPlease restart." % str(e))
        else:
            print("Error occurred: %s" % str(e))

    finally:
        if vm is not None:
            vm.__cleanup()
            del vm
        vm = None
        # Final cleanup
        collect()
        threshold(mem_free() // 4 + mem_alloc())

# run the main function
if __name__ == "__main__":
    main()
