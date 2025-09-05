class View:
    """
    A class representing a view in the system.
    - name: str - the name of the view
    - run: function(ViewManager) - the function called every frame
    - start: function(ViewManager) - the function called when the view is created
    - stop: function(ViewManager) - the function called when the view is destroyed
    """

    def __init__(self, name: str, run, start, stop):
        self.name = name
        self._run = run
        self._start = start
        self._stop = stop
        self.active = False
        self.should_stop = False

    def start(self, view_manager) -> bool:
        """Called when the view is created."""
        if self._start:
            if self._start(view_manager):
                self.active = True
        return False

    def stop(self, view_manager):
        """Called when the view is destroyed."""
        if self._stop:
            self._stop(view_manager)
        self.active = False
        self.should_stop = True

    def run(self, view_manager):
        """Called every frame."""
        if self.should_stop:
            self.stop(view_manager)
            self.should_stop = False
        elif self._run and self.active:
            self._run(view_manager)
