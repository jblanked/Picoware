from picogui.draw import Draw
from .view import View
from .storage import Storage
from .boards import Board
from .input_manager import InputManager
from .buttons import BUTTON_BACK


class ViewManager:
    """
    A class to manage views in the system.
    - current_view: View - the currently active view
    - storage: Storage - a storage object for managing data
    - draw: Draw - a draw object for rendering
    - views: list - an ordered list of all registered views
    - view_stack: list - a stack of views for managing navigation history
    - view_stack_limit: int - the maximum number of views in the stack
    """

    def __init__(
        self, board: Board, background_color: int = 0xFFFFFF, debug: bool = False
    ):
        self.board = board
        self.draw = Draw(board, debug=debug)
        self.storage = Storage()
        self.input_manager = InputManager(board)
        self.current_view = None
        self.views = []
        self.view_stack = []
        self.view_stack_limit = 3
        self.background_color = background_color

    def add(self, view: View):
        """
        Add a view to the view manager.
        :param view: The view to be added.
        """
        if not isinstance(view, View):
            raise TypeError("view must be an instance of View")
        if any(v.name == view.name for v in self.views):
            raise ValueError(f"View '{view.name}' already registered")
        self.views.append(view)

    def back(self, delete: bool = False):
        """
        Go back to the previous view in the stack.
        If there's no previous view, this method will do nothing.
        :param delete: Whether to remove the current view from the manager.
        """
        if self.view_stack:
            if self.current_view:
                self.current_view.stop(self)
                if delete:
                    self.remove(self.current_view.name)
            self.current_view = self.view_stack.pop()
            self.__clear()
            self.current_view.start(self)
            self.__status()

    def run(self):
        """
        Run the current view.
        """
        if self.input_manager.input == BUTTON_BACK:
            self.back()
            self.input_manager.reset()
        self.input_manager.run()
        if self.current_view:
            self.current_view.run(self)

    def set(self, view_name: str):
        """
        Set the current view to a new view and clear the view stack.
        This is typically used for the initial view or resetting navigation.
        :param view_name: The name of the view to set.
        """
        # Micropython doesn't support next(..., default), so use a loop
        view = None
        for v in self.views:
            if v.name == view_name:
                view = v
                break
        if not view:
            raise ValueError(f"View '{view_name}' not found")

        if self.current_view:
            self.current_view.stop(self)
        self.view_stack.clear()
        self.current_view = view
        self.storage.free()
        self.__clear()
        self.current_view.start(self)
        self.__status()

    def switch(self, view_name: str):
        """
        Switch to a new view and add the current view to the stack.
        This allows proper back navigation through the view history.
        :param view_name: The name of the view to switch to.
        """
        # Replace next(..., default) with a loop
        view = None
        for v in self.views:
            if v.name == view_name:
                view = v
                break
        if not view:
            raise ValueError(f"View '{view_name}' not found")

        self.__clear()
        if self.current_view:
            self.current_view.stop(self)
            if len(self.view_stack) >= self.view_stack_limit:
                self.view_stack.pop(0)
            self.view_stack.append(self.current_view)

        self.current_view = view
        self.current_view.start(self)
        self.__status()

    def remove(self, view_name: str):
        """
        Remove a view from the view manager.
        :param view_name: The name of the view to be removed.
        """
        for v in self.views:
            if v.name == view_name:
                self.views.remove(v)
                return
        raise ValueError(f"View '{view_name}' not found")

    def __clear(self):
        """
        Clear the current view and free up memory.
        This is typically used when switching views.
        """
        self.draw.deinit()
        del self.draw
        self.draw = None
        self.draw = Draw(self.board)
        self.storage.free()

    def __status(self):
        """
        Run garbage collection then print the name, heap memory usage, and free space.
        """
        self.storage.free()
        print(
            f"{self.current_view.name}: {self.storage.heap_used()} bytes used, {self.storage.heap_free()} bytes free"
        )
