"""
Picoware
Author: JBlanked
Github: https://github.com/jblanked/Picoware
Info: A custom firmware for the PicoCalc, Video Game Module, and other Raspberry Pi Pico devices.
Created: 2025-05-14
Updated: 2026-01-30
"""


def main():
    """Main function to run the application"""
    from gc import collect
    import storage

    storage.disable_usb_drive()

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
                # show an alert to user
                from picoware.gui.alert import Alert
                from time import sleep

                draw = vm.draw
                draw.clear()
                alert = Alert(
                    draw,
                    f"Critical Error:\n{e}\nPlease restart.",
                    vm.get_foreground_color(),
                    vm.get_background_color(),
                )
                alert.draw("Error")
                draw.swap()
                sleep(2)

                del alert
                del vm

                alert = None
                vm = None
                collect()
            except Exception:
                pass

    finally:
        # Final cleanup
        collect()


# run the main function
if __name__ == "__main__":
    main()
