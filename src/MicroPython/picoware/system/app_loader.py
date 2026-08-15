import sys
from gc import collect, mem_free

class AppLoader:
    """Class to manage loading and running apps dynamically.
    
    Attributes:
        view_manager (ViewManager): The view manager instance for display and storage access.
        loaded_apps (dict): Dictionary to cache loaded app modules, keyed by app name.
        current_app (object): Reference to the currently running app module.
        _vfs_ready (bool): Flag indicating whether the VFS is ready for app loading.
    """

    def __init__(self, view_manager, mount_vfs:bool=False):
        """Initialize the AppLoader with a view manager.

        Args:
            view_manager (ViewManager): The view manager instance for display and storage access.
            mount_vfs (bool): Whether to mount the VFS for app loading. Defaults to False.
        """
        self.view_manager = view_manager
        self.loaded_apps = {}
        self.current_app = None
        self._vfs_ready = False
        if mount_vfs and view_manager.storage.mount_vfs("/sd"):
            self._vfs_ready = True

    def __del__(self):
        """Cleanup loaded apps on deletion"""
        self.stop()
        self.cleanup_modules()
        if self._vfs_ready:
            self.view_manager.storage.unmount_vfs("/sd")
        self._vfs_ready = False

    def cleanup_modules(self):
        """Remove all app modules from sys.modules"""
        try:
            # Clear our references first
            self.loaded_apps.clear()
            self.current_app = None

            # Remove ALL modules from the apps directory
            modules_to_delete = []
            path_str = "/picoware/apps/"
            # Also check for VFS-mounted paths
            sd_path_str = "/sd/picoware/apps/"
            for mod_name, mod in list(sys.modules.items()):
                if hasattr(mod, "__file__") and mod.__file__:
                    if path_str in mod.__file__ or sd_path_str in mod.__file__:
                        modules_to_delete.append(mod_name)

            for mod_name in modules_to_delete:
                del sys.modules[mod_name]

            # Force garbage collection
            collect()

            self.view_manager.log(
                f"[AppLoader]: Cleaned up modules, free memory: {mem_free()} bytes"
            )

        except Exception as e:
            self.view_manager.log("Error cleaning up modules: {}".format(e), 2)

    def list_available_apps(self, subdirectory="") -> list[str]:
        """List available apps in the picoware/apps directory or subdirectory.

        Args:
            subdirectory (str): Optional subdirectory within picoware/apps. Defaults to "".

        Returns:
            list[str]: Names of apps with .py or .mpy extensions, sorted alphabetically.
        """
        try:
            storage = self.view_manager.storage
            # no need to mount because we're using auto-mount
            apps_path = "/picoware/apps"
            if subdirectory:
                apps_path = f"{apps_path}/{subdirectory}"
            file_list = storage.listdir(apps_path)
            _py_apps = []
            for f in file_list:
                if f.startswith("."):
                    continue
                if f.endswith(".py"):
                    _py_apps.append(f[:-3])
                if f.endswith(".mpy"):
                    _py_apps.append(f[:-4])
            # Sort alphabetically
            _py_apps.sort()
            return _py_apps

        except Exception as e:
            self.view_manager.log(f"Error listing apps: {e}", 2)
            return []

    def list_loaded_apps(self) -> list:
        """List all loaded apps.

        Returns:
            list: Names of the currently loaded app modules.
        """
        return list(self.loaded_apps.keys())

    def load_module(self, module_path: str) -> bool:
        """Add a VFS path to sys.path so modules can be imported directly.

        Mounts the SD card and adds the given VFS path so modules can be
        imported with a bare import statement. Useful for testing in Thonny
        or when manually importing from a specific location.

        Args:
            module_path (str): Path relative to the VFS root, e.g. ``"/picoware/apps"``.

        Returns:
            bool: True if the path was added to ``sys.path``, False otherwise.
        """
        try:
            storage = self.view_manager.storage
            storage.mount()

            if not storage.vfs_mounted:
                self.view_manager.log("[AppLoader]: VFS not mounted, cannot add path", 2)
                return False

            full_path = f"{storage.vfs_prefix}{module_path}"

            if full_path not in sys.path:
                sys.path.append(full_path)

            self.view_manager.log(
                f"[AppLoader]: Added {full_path} to sys.path, free memory: {mem_free()} bytes"
            )
            return True

        except Exception as e:
            self.view_manager.log(
                f"[AppLoader]: Error adding path {module_path}: {type(e).__name__}: {e}", 2
            )
            return False

    def load_app(self, app_name, subdirectory=""):
        """Load an app module dynamically and verify its required methods.

        Args:
            app_name (str): Name of the app module to load (without extension).
            subdirectory (str): Optional subdirectory within picoware/apps. Defaults to "".

        Returns:
            object or None: The loaded app module, or None if loading failed.

        Raises:
            RuntimeError: If the VFS is not ready or not mounted.
            AttributeError: If the app module is missing a required method.
        """
        if not self._vfs_ready:
            self._vfs_ready = self.view_manager.storage.mount_vfs("/sd")
            if not self._vfs_ready:
                raise RuntimeError("VFS not ready, cannot load apps.")

        from utime import ticks_ms

        start_time = ticks_ms()
        try:
            cache_key = f"{subdirectory}/{app_name}" if subdirectory else app_name
            if cache_key not in self.loaded_apps:
                # Mount the SD card first
                storage = self.view_manager.storage
                storage.mount()

                # Determine the base path based on VFS mode
                if not storage.vfs_mounted:
                    raise RuntimeError("Storage VFS not mounted, cannot load apps.")

                # Use the board-specific VFS prefix (/sdcard on Cardputer, /sd elsewhere)
                base_apps_path = f"{storage.vfs_prefix}/picoware/apps"

                # Always add the base apps directory to sys.path
                if base_apps_path not in sys.path:
                    sys.path.append(base_apps_path)

                # Add subdirectory if specified
                apps_path = base_apps_path
                if subdirectory:
                    apps_path = f"{apps_path}/{subdirectory}"
                    if apps_path not in sys.path:
                        sys.path.append(apps_path)

                # Check if module is already in sys.modules
                app_module = (
                    __import__(app_name)
                    if app_name not in sys.modules
                    else sys.modules[app_name]
                )

                self.view_manager.log(
                    f"[AppLoader]: Imported {app_name} after {ticks_ms() - start_time} ms, free memory: {mem_free()} bytes"
                )

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
            self.view_manager.log(f"Could not import app {app_name}: {e}", 2)
            return None
        except Exception as e:
            self.view_manager.log(
                f"Error loading app {app_name}: {type(e).__name__}: {e}", 2
            )
            return None

    def run(self):
        """Run the currently loaded app"""
        if self.current_app:
            self.current_app.run(self.view_manager)

    def start(self, app_name) -> bool:
        """Start a specific app.

        Args:
            app_name (str): Name of the app module to start.

        Returns:
            bool: True if the app started successfully, False otherwise.
        """
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
        """Switch to a different app.

        Args:
            app_name (str): Name of the app module to switch to.

        Returns:
            bool: True if the switch succeeded, False otherwise.
        """
        return self.start(app_name)
