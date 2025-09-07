def main():
    """Main function to run the application"""
    import gc

    # Initial cleanup
    gc.collect()
    print(f"Initial memory: {gc.mem_free()}")

    from picoware.system.view_manager import ViewManager
    from picoware.system.view import View
    from picoware.applications import desktop

    print(f"After imports memory: {gc.mem_free()}")

    print("Starting ViewManager...")

    # Initialize the view manager
    vm: ViewManager = None
    try:
        vm: ViewManager = ViewManager()

        print(f"After ViewManager init memory: {gc.mem_free()}")

        # Add views to the view manager
        vm.add(View("desktop_view", desktop.run, desktop.start, desktop.stop))

        print(f"After adding views memory: {gc.mem_free()}")

        # Switch views
        vm.switch_to("desktop_view")

        print(f"After switching views memory: {gc.mem_free()}")

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
        print(f"Final memory: {gc.mem_free()}")


# run the main function
if __name__ == "__main__":
    main()
