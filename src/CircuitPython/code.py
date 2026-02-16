"""
Picoware
Author: JBlanked
Github: https://github.com/jblanked/Picoware
Info: A custom firmware for the PicoCalc, Video Game Module, and other Raspberry Pi Pico devices.
Created: 2025-05-14
Updated: 2026-02-15
"""


def disable():
    """Disable the USB drive"""
    import storage

    try:
        storage.disable_usb_drive()
    except Exception as e:
        print(e)


def enable():
    """Enable the USB drive for file access"""
    import storage

    try:
        storage.enable_usb_drive()
    except Exception as e:
        print(e)


def freq():
    """Set the CPU frequency to 200 MHz"""
    import microcontroller

    microcontroller.cpu.frequency = 200000000


def main():
    """Main function to run the application"""
    from gc import collect

    freq()

    disable()

    # Initial cleanup
    collect()

    from picoware.system.view_manager import ViewManager
    from picoware.system.view import View
    from picoware.applications import desktop

    # Initialize the view manager
    vm: ViewManager = None
    try:
        vm: ViewManager = ViewManager()

        # Add views to the view manager
        vm.add(View("desktop_view", desktop.run, desktop.start, desktop.stop))

        # Switch views
        vm.switch_to("desktop_view")

        # Main loop
        while True:
            vm.run()

    except Exception as e:
        print(f"Error occurred: {e}")
        if vm:
            try:
                vm.alert(f"Critical Error:\n{e}\nPlease restart.")
            except Exception:
                pass

    finally:
        # Final cleanup
        collect()
        enable()


# run the main function
if __name__ == "__main__":
    main()
