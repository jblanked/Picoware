class View:
    """
    A class representing a view in the system.
    - name: str - the name of the view
    - run: function(ViewManager) - the function called every frame
    - start: function(ViewManager) - the function called when the view is created
    - stop: function(ViewManager) - the function called when the view is destroyed
    """

    __slots__ = ("name", "_run", "_start", "_stop", "active")

    def __init__(self, name: str, run: callable, start: callable, stop: callable):
        self.name = name
        self._run = run
        self._start = start
        self._stop = stop
        self.active = False

    def __alert(self, exception, view_manager) -> None:
        """Display an alert message."""
        import sys
        import io

        buf = io.StringIO()
        sys.print_exception(exception, buf)
        traceback_str = buf.getvalue()
        view_manager.alert(f"{traceback_str}", False) 

    def start(self, view_manager) -> bool:
        """Called when the view is created."""
        if self._start:
            try:
                if self._start(view_manager):
                    self.active = True
                    return True
            except Exception as e:
                self.__alert(f"Error starting view: {e}", view_manager)
                self.active = False
                return False
        return False

    def stop(self, view_manager):
        """Called when the view is destroyed."""
        if self._stop:
            try:
                self._stop(view_manager)
            except Exception as e:
                self.__alert(f"Error stopping view: {e}", view_manager)
        self.active = False

    def run(self, view_manager):
        """Called every frame."""
        if self._run and self.active:
            try:
                self._run(view_manager)
            except Exception as e:
                self.__alert(f"Error running view: {e}", view_manager)
                self.active = False
                view_manager.back()
