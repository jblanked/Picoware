def main():
    """Main function to run the application"""
    from gc import collect, threshold, mem_free, mem_alloc

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
        del vm
        vm = None
        # Final cleanup
        collect()
        threshold(mem_free() // 4 + mem_alloc())


# run the main function
if __name__ == "__main__":
    main()
