class View:
    """
    A class representing a view in the system.
    - name: str - the name of the view
    - run: function(ViewManager) - the function called every frame
    - start: function(ViewManager) - the function called when the view is created
    - stop: function(ViewManager) - the function called when the view is destroyed
    """

    def __init__(self, name: str, run: callable, start: callable, stop: callable):
        self.name = name
        self._run = run
        self._start = start
        self._stop = stop
        self.active = False
        self.should_stop = False

    def __alert(self, message: str, view_manager) -> None:
        """Display an alert message."""
        from picoware.gui.alert import Alert
        from time import sleep

        draw = view_manager.draw
        draw.clear()
        alert = Alert(
            draw,
            message,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
        )
        alert.draw("Error")
        draw.swap()
        sleep(2)

    def start(self, view_manager) -> bool:
        """Called when the view is created."""
        self.should_stop = False
        if self._start:
            try:
                if self._start(view_manager):
                    self.active = True
                    return True
            except Exception as e:
                print("Error starting view:", e)
                self.__alert(f"Error starting view:\n{e}", view_manager)
                self.active = False
                return False
        return False

    def stop(self, view_manager):
        """Called when the view is destroyed."""
        if self._stop:
            try:
                self._stop(view_manager)
            except Exception as e:
                print("Error stopping view:", e)
                self.__alert(f"Error stopping view:\n{e}", view_manager)
        self.active = False
        self.should_stop = True

    def run(self, view_manager):
        """Called every frame."""
        if self.should_stop:
            self.stop(view_manager)
            self.should_stop = False
        elif self._run and self.active:
            try:
                self._run(view_manager)
            except Exception as e:
                print("Error running view:", e)
                self.__alert(f"Error running view:\n{e}", view_manager)
                self.active = False
                self.should_stop = True
                view_manager.back()
