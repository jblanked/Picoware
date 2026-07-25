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

    def __alert(self, action, exception, view_manager) -> None:
        """Display an alert message."""
        import sys
        import io

        prefix = "Error {} view '{}':".format(action, self.name)
        try:
            buf = io.StringIO()
            sys.print_exception(exception, buf)
            message = "{}\n{}".format(prefix, buf.getvalue())
        except Exception:
            print(prefix)
            sys.print_exception(exception)
            message = "{}\n{}".format(prefix, exception)

        print(message)
        try:
            view_manager.alert(message, False)
        except Exception as alert_error:
            print("Unable to display view exception alert:", alert_error)

    def start(self, view_manager) -> bool:
        """Called when the view is created."""
        if self._start:
            try:
                if self._start(view_manager):
                    self.active = True
                    return True
            except Exception as e:
                self.__alert("starting", e, view_manager)
                self.active = False
                return False
        return False

    def stop(self, view_manager):
        """Called when the view is destroyed."""
        if self._stop:
            try:
                self._stop(view_manager)
            except Exception as e:
                self.__alert("stopping", e, view_manager)
        self.active = False

    def run(self, view_manager):
        """Called every frame."""
        if self._run and self.active:
            try:
                self._run(view_manager)
            except Exception as e:
                self.__alert("running", e, view_manager)
                self.active = False
                view_manager.back()
