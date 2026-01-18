def main():
    """Main function to run the application"""
    from gc import collect
    from machine import freq
    from picoware.system.boards import (
        BOARD_ID,
        BOARD_PICOCALC_PICO,
        BOARD_PICOCALC_PICOW,
    )

    if BOARD_ID in (BOARD_PICOCALC_PICO, BOARD_PICOCALC_PICOW):
        # if pico, pico w set at 210
        freq(210000000)
    else:
        # if pico2, pico2 w set at 230
        freq(230000000)

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
