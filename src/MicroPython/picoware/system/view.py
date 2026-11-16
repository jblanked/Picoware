"""View - Base class for managed views."""

import view


class View(view.View):
    """A view managed by the ViewManager.

    Attributes:
        name (str): The name of the view.
        run (callable): Function called every frame.
        start (callable): Function called when the view is created.
        stop (callable): Function called when the view is destroyed.
        active (bool): Whether the view is currently active.
    """

    __slots__ = ("name", "_run", "_start", "_stop", "active")

    def __init__(self, name: str, run: callable, start: callable, stop: callable):
        """Initialize the view with its name and callbacks.

        Args:
            name (str): The name of the view.
            run (callable): Function called every frame.
            start (callable): Function called when the view is created.
            stop (callable): Function called when the view is destroyed.
        """
        self._run = run
        self._start = start
        self._stop = stop
        super().__init__(name, self.__start, self.__run, self.__stop)

    def __alert(self, exception, view_manager) -> None:
        """Display an alert message.

        Args:
            exception (Exception): The exception to display.
            view_manager (ViewManager): The manager to show the alert on.
        """
        import sys
        import io

        buf = io.StringIO()
        sys.print_exception(exception, buf)
        view_manager.alert(buf.getvalue(), False)

    def __start(self, view_manager) -> bool:
        """Start the view and mark it active.

        Args:
            view_manager (ViewManager): The manager that owns this view.

        Returns:
            bool: True if the view started successfully, False otherwise.
        """
        if self._start:
            try:
                if self._start(view_manager):
                    self.active = True
                    return True
            except Exception as e:
                self.__alert("Error starting view: %s" % str(e), view_manager)
                self.active = False
                return False
        return False

    def __stop(self, view_manager):
        """Stop the view and mark it inactive.

        Args:
            view_manager (ViewManager): The manager that owns this view.
        """
        if self._stop:
            try:
                self._stop(view_manager)
            except Exception as e:
                self.__alert("Error stopping view: %s" % str(e), view_manager)
        self.active = False

    def __run(self, view_manager):
        """Run the view's per-frame callback.

        Args:
            view_manager (ViewManager): The manager that owns this view.
        """
        if self._run and self.active:
            try:
                self._run(view_manager)
            except Exception as e:
                self.__alert("Error running view: %s" % str(e), view_manager)
                self.active = False
                view_manager.back()
