from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_BACKSPACE, BUTTON_DELETE

class SearchMixin:
    """Mixin to add real-time search and unified navigation to a view."""
    
    def init_search(self):
        self._search_query = ""
        self.filtered_indices = []
        self._filter_items()

    def _filter_items(self):
        """Must be implemented by the view to update self.filtered_indices."""
        raise NotImplementedError

    def handle_search_navigation(self, btn, total_rows, page_size=5):
        """Standardized Up/Down navigation for search-enabled lists."""
        if total_rows <= 0: return False
        
        if btn == BUTTON_UP:
            self._selected_index = (self._selected_index - 1) % total_rows
            return True
        elif btn == BUTTON_DOWN:
            self._selected_index = (self._selected_index + 1) % total_rows
            return True
        elif btn == 58: # BUTTON_LEFT_BRACKET
            self._selected_index = max(0, self._selected_index - page_size)
            return True
        elif btn == 59: # BUTTON_RIGHT_BRACKET
            self._selected_index = min(total_rows - 1, self._selected_index + page_size)
            return True
        return False

    def get_filtered_data_index(self, show_add_row=True):
        """Returns the actual data index for current selection, or None if invalid."""
        offset = 1 if show_add_row else 0
        idx = self._selected_index - offset
        if 0 <= idx < len(self.filtered_indices):
            return self.filtered_indices[idx]
        return None

    def handle_search_input(self, btn, input_manager):
        """Handles typing and backspace. Returns True if search changed."""
        if btn in (127, BUTTON_BACKSPACE, BUTTON_DELETE):
            if self._search_query:
                self._search_query = self._search_query[:-1]
                self._filter_items_reset()
                return True
        elif btn != -1 and btn not in (BUTTON_UP, BUTTON_DOWN):
            char = input_manager.button_to_char(btn)
            if char and char != "\n":
                self._search_query += char
                self._filter_items_reset()
                return True
        return False

    def _filter_items_reset(self):
        self._filter_items()
        self._selected_index = 0
        self._scroll_offset = 0
        self._dirty = True

    def clear_search(self):
        self._search_query = ""
        self._filter_items_reset()

    @property
    def is_searching(self):
        return len(self._search_query) > 0

    @property
    def search_title(self):
        return f"Search: {self._search_query}_" if self.is_searching else None
