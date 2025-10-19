class AppLoader:
    """Class to manage loading and running apps dynamically"""

    def __init__(self, view_manager):
        """
        Initialize the AppLoader with a view manager

        Args:
            view_manager: The view manager instance to interact with the display and storage
        """
        self.view_manager = view_manager
        self.loaded_apps = {}
        self.current_app = None

    def __del__(self):
        """Cleanup loaded apps on deletion"""
        self.stop()
        self.cleanup_modules()

    def cleanup_modules(self):
        """Remove all app modules from sys.modules"""
        try:
            import sys
            from gc import collect

            # Clear our references first
            self.loaded_apps.clear()
            self.current_app = None

            # Remove ALL modules from the apps directory
            modules_to_delete = []
            for mod_name, mod in list(sys.modules.items()):
                if hasattr(mod, "__file__") and mod.__file__:
                    if "/sd/picoware/apps/" in mod.__file__:
                        modules_to_delete.append(mod_name)

            for mod_name in modules_to_delete:
                del sys.modules[mod_name]

            # Force garbage collection
            collect()

        except Exception as e:
            print("Error cleaning up modules: {}".format(e))

    def list_available_apps(self, subdirectory="") -> list[str]:
        """List all available apps (with .py extension) in the /sd/picoware/apps directory or subdirectory"""
        try:
            storage = self.view_manager.get_storage()
            # no need to mount because we're using auto-mount
            apps_path = "/sd/picoware/apps"
            if subdirectory:
                apps_path = f"{apps_path}/{subdirectory}"

            file_list = storage.listdir(apps_path)
            apps = [
                f[:-3] for f in file_list if f.endswith(".py") and not f.startswith(".")
            ]
            # Sort alphabetically
            apps.sort()
            return apps

        except Exception as e:
            print(f"Error listing apps: {e}")
            return []

    def list_loaded_apps(self) -> list:
        """List all loaded apps"""
        return list(self.loaded_apps.keys())

    def load_app(self, app_name, subdirectory=""):
        """
        Load an app module dynamically

        Args:
            app_name: The name of the app module to load (without .py extension)
            subdirectory: Optional subdirectory within /sd/picoware/apps
        """
        try:
            cache_key = f"{subdirectory}/{app_name}" if subdirectory else app_name
            if cache_key not in self.loaded_apps:
                # Mount the SD card first
                storage = self.view_manager.get_storage()
                storage.mount()

                # Add the SD card apps directory to sys.path
                import sys

                # Always add the base apps directory
                base_apps_path = "/sd/picoware/apps"
                if base_apps_path not in sys.path:
                    sys.path.append(base_apps_path)

                # Add subdirectory if specified
                apps_path = base_apps_path
                if subdirectory:
                    apps_path = f"{apps_path}/{subdirectory}"
                    if apps_path not in sys.path:
                        sys.path.append(apps_path)

                # Now try to import the module by name
                app_module = __import__(app_name)

                # Verify the app has required methods
                required_methods = ["start", "run", "stop"]
                for method in required_methods:
                    if not hasattr(app_module, method) or not callable(
                        getattr(app_module, method)
                    ):
                        raise AttributeError(f"App {app_name} missing {method} method")

                self.loaded_apps[cache_key] = app_module

            return self.loaded_apps[cache_key]

        except ImportError as e:
            print(f"Could not import app {app_name}: {e}")
            return None
        except Exception as e:
            print(f"Error loading app {app_name}: {type(e).__name__}: {e}")
            return None

    def run(self):
        """Run the currently loaded app"""
        if self.current_app:
            self.current_app.run(self.view_manager)
        else:
            print("No app currently loaded")

    def start(self, app_name) -> bool:
        """Start a specific app"""
        # Stop current app first
        if self.current_app:
            self.stop()

        app_module = self.load_app(app_name)
        if app_module:
            success = app_module.start(self.view_manager)
            if success:
                self.current_app = app_module
                return True
        return False

    def stop(self):
        """Stop the current app"""
        if self.current_app:
            self.current_app.stop(self.view_manager)
            self.current_app = None

    def switch_app(self, app_name):
        """Switch to a different app"""
        return self.start(app_name)
