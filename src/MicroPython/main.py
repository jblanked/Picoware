def main():
    """Main function to run the application"""
    import gc

    # Initial cleanup
    gc.collect()

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
            print("run")
            vm.run()

    except Exception as e:
        print(f"Error occurred: {e}")
        if vm:
            try:
                del vm
                vm = None
                gc.collect()
            except:
                pass

    finally:
        # Final cleanup
        gc.collect()


# run the main function
if __name__ == "__main__":
    main()
