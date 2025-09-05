import gc

# Initial cleanup
gc.collect()
print(f"Initial memory: {gc.mem_free()}")


def main():
    """Main function to run the application"""
    from picoware.system.view_manager import ViewManager
    from picoware.system.view import View
    from picoware.applications import loading

    # Initialize the view manager
    vm: ViewManager = None
    try:
        vm: ViewManager = ViewManager()

        # Add views to the view manager
        vm.add(View("loading_view", loading.run, loading.start, loading.stop))

        # Switch views
        vm.switch_to("loading_view")

        # Main loop
        while True:
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
