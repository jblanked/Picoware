# translated from https://github.com/lazerduck/PicoCalc_Dashboard/blob/main/sudoku.py
# Sudoku.py - Sudoku game for PicoCalc
def shuffle(lst):
    """Fisher-Yates shuffle for MicroPython."""
    from random import randint

    for i in range(len(lst) - 1, 0, -1):
        j = randint(0, i)
        lst[i], lst[j] = lst[j], lst[i]


class SudokuGame:
    """Class to manage Sudoku game state."""

    def __init__(self, difficulty="medium"):
        from time import time

        self.grid = [[0 for _ in range(9)] for _ in range(9)]
        self.given = [[False for _ in range(9)] for _ in range(9)]
        self.cursor_row = 0
        self.cursor_col = 0
        self.difficulty = difficulty
        self.start_time = time()
        self.completed = False

    def __del__(self):
        del self.grid
        self.grid = None
        del self.given
        self.given = None
        self.difficulty = None

    def generate_puzzle(self):
        """Generate a new Sudoku puzzle."""
        from random import randint

        # Try up to 3 times to generate a valid puzzle
        for _ in range(3):
            # Reset grid
            self.grid = [[0 for _ in range(9)] for _ in range(9)]

            # First, generate a complete valid solution
            self._fill_diagonal_boxes()
            if not self._solve():
                continue  # Retry if solve failed

            # Successfully generated, break out
            break

        # Remove numbers based on difficulty
        clues = {"easy": 40, "medium": 32, "hard": 26}
        num_clues = clues.get(self.difficulty, 32)
        cells_to_remove = 81 - num_clues

        # Randomly remove cells
        removed = 0
        attempts = 0
        max_attempts = 200

        while removed < cells_to_remove and attempts < max_attempts:
            row = randint(0, 8)
            col = randint(0, 8)

            if self.grid[row][col] != 0:
                backup = self.grid[row][col]
                self.grid[row][col] = 0

                # Simple check: just remove it (proper unique solution check is complex)
                removed += 1

            attempts += 1

        # Mark given cells
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] != 0:
                    self.given[r][c] = True

    def _fill_diagonal_boxes(self):
        """Fill the three diagonal 3x3 boxes with random valid numbers."""
        for box in range(0, 9, 3):
            nums = list(range(1, 10))
            shuffle(nums)
            idx = 0
            for r in range(3):
                for c in range(3):
                    self.grid[box + r][box + c] = nums[idx]
                    idx += 1

    def _solve(self):
        """Solve the Sudoku using iterative backtracking (no recursion)."""
        # Find all empty cells
        empty_cells = []
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] == 0:
                    empty_cells.append((r, c))

        if not empty_cells:
            return True

        # Iterative backtracking using a stack
        cell_idx = 0
        attempts = [0] * len(
            empty_cells
        )  # Track which number we're trying for each cell

        while 0 <= cell_idx < len(empty_cells):
            row, col = empty_cells[cell_idx]

            # Clear current cell
            self.grid[row][col] = 0

            # Try numbers from attempts[cell_idx] + 1 to 9
            found = False
            for num in range(attempts[cell_idx] + 1, 10):
                if self._is_valid(row, col, num):
                    self.grid[row][col] = num
                    attempts[cell_idx] = num
                    found = True
                    break

            if found:
                # Move to next cell
                cell_idx += 1
            else:
                # Backtrack
                attempts[cell_idx] = 0
                cell_idx -= 1

                # Safety check - if we backtracked too far, give up
                if cell_idx < 0:
                    return False

        return True

    def _find_empty(self):
        """Find an empty cell (0)."""
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] == 0:
                    return (r, c)
        return None

    def _is_valid(self, row, col, num):
        """Check if placing num at (row, col) is valid."""
        # Check row
        if num in self.grid[row]:
            return False

        # Check column
        for r in range(9):
            if self.grid[r][col] == num:
                return False

        # Check 3x3 box
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for r in range(box_row, box_row + 3):
            for c in range(box_col, box_col + 3):
                if self.grid[r][c] == num:
                    return False

        return True

    def get_conflicts(self, row, col):
        """Get list of conflicting cells for the cell at (row, col)."""
        if self.grid[row][col] == 0:
            return []

        num = self.grid[row][col]
        conflicts = []

        # Check row
        for c in range(9):
            if c != col and self.grid[row][c] == num:
                conflicts.append((row, c))

        # Check column
        for r in range(9):
            if r != row and self.grid[r][col] == num:
                conflicts.append((r, col))

        # Check 3x3 box
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for r in range(box_row, box_row + 3):
            for c in range(box_col, box_col + 3):
                if (r, c) != (row, col) and self.grid[r][c] == num:
                    conflicts.append((r, c))

        return conflicts

    def is_complete(self):
        """Check if puzzle is complete and valid."""
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] == 0:
                    return False
                if self.get_conflicts(r, c):
                    return False
        return True

    def set_cell(self, row, col, num):
        """Set a cell value if it's not a given cell."""
        if not self.given[row][col]:
            self.grid[row][col] = num


global game


def center_text(display, text, y, color):
    """Helper to center text on screen."""
    from picoware.system.vector import Vector

    text_width = display.font_size.x * len(text)
    x = (display.size.x - text_width) // 2
    display.text(Vector(x, y), text, color)


def draw_sudoku(display):
    """Draw the Sudoku grid and numbers."""
    from time import time
    from picoware.system.colors import (
        TFT_BLUE,
        TFT_CYAN,
        TFT_RED,
        TFT_YELLOW,
        TFT_WHITE,
        TFT_BLACK,
    )
    from picoware.system.vector import Vector

    display.fill_screen(TFT_BLACK)

    # Pre-calculate conflicts for all cells (only once per frame)
    conflicts_cache = {}
    for r in range(9):
        for c in range(9):
            if game.grid[r][c] != 0:
                conflicts_cache[(r, c)] = game.get_conflicts(r, c)

    # Grid parameters - centered on screen
    grid_size = 315
    cell_size = 35
    grid_x = 2
    grid_y = 2  # Start at top of screen

    # Highlight selected cell's row, column, and box
    sel_row, sel_col = game.cursor_row, game.cursor_col

    # Highlight row
    y = grid_y + sel_row * cell_size + 1
    display.fill_rectangle(
        Vector(grid_x + 1, y), Vector(grid_size - 2, cell_size - 1), TFT_BLUE
    )

    # Highlight column
    x = grid_x + sel_col * cell_size + 1
    display.fill_rectangle(
        Vector(x, grid_y + 1), Vector(cell_size - 1, grid_size - 2), TFT_BLUE
    )
    # Highlight 3x3 box
    box_row, box_col = 3 * (sel_row // 3), 3 * (sel_col // 3)
    bx = grid_x + box_col * cell_size + 1
    by = grid_y + box_row * cell_size + 1
    display.fill_rectangle(
        Vector(bx, by), Vector(3 * cell_size - 1, 3 * cell_size - 1), TFT_BLUE
    )

    # Draw numbers
    text_vec = Vector(0, 0)
    for r in range(9):
        for c in range(9):
            num = game.grid[r][c]
            if num != 0:
                text_vec.x = grid_x + c * cell_size + 12
                text_vec.y = grid_y + r * cell_size + 12

                # Determine color
                if game.given[r][c]:
                    color = TFT_WHITE  # Given numbers: light gray/white
                elif conflicts_cache.get((r, c)):
                    color = TFT_RED  # Conflicts: red
                else:
                    color = TFT_CYAN  # Player numbers: cyan

                display.text(text_vec, str(num), color)

    # Highlight selected cell
    x = grid_x + sel_col * cell_size
    y = grid_y + sel_row * cell_size
    display.rect(Vector(x + 1, y + 1), Vector(cell_size - 2, cell_size - 2), TFT_YELLOW)
    display.rect(Vector(x + 2, y + 2), Vector(cell_size - 4, cell_size - 4), TFT_YELLOW)

    # Draw grid lines
    vline_vec = Vector(0, grid_y)
    vline_vec_size = Vector(0, grid_size)
    hline_vec = Vector(grid_x, 0)
    hline_vec_size = Vector(grid_size, 0)
    for i in range(10):
        thickness = 2 if i % 3 == 0 else 1
        color = TFT_WHITE

        # Vertical lines
        x = grid_x + i * cell_size
        for t in range(thickness):
            vline_vec.x = x + t
            vline_vec_size.x = x + t
            vline_vec_size.y = grid_y + grid_size
            display.line_custom(
                vline_vec,
                vline_vec_size,
                color,
            )

        # Horizontal lines
        y = grid_y + i * cell_size
        for t in range(thickness):
            hline_vec.y = y + t
            hline_vec_size.x = grid_x + grid_size
            hline_vec_size.y = y + t
            display.line_custom(
                hline_vec,
                hline_vec_size,
                color,
            )

    # Show info below grid
    info_y = grid_y + grid_size + 2

    # Show timer and difficulty on one line
    elapsed = int(time() - game.start_time)
    mins = elapsed // 60
    secs = elapsed % 60
    timer_text = f"{mins:02d}:{secs:02d}"
    diff_text = f"{game.difficulty[0].upper()}{game.difficulty[1:]}"

    display.text(Vector(4, info_y), diff_text, TFT_CYAN)  # Bright green
    display.text(Vector(280, info_y), timer_text, TFT_CYAN)  # Bright green

    display.swap()


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_CENTER,
        BUTTON_DOWN,
        BUTTON_UP,
    )
    from picoware.system.colors import TFT_BLUE
    from picoware.gui.menu import Menu

    inp = view_manager.input_manager
    draw = view_manager.draw
    bg = view_manager.background_color
    fg = view_manager.foreground_color

    # set menu
    _menu = Menu(
        draw,  # draw instance
        "Select Difficulty",  # title
        0,  # y position
        draw.size.y,  # height
        fg,  # text color
        bg,  # background color
        TFT_BLUE,  # selected item color
        fg,  # border color
    )

    # add items
    _menu.add_item("Easy")
    _menu.add_item("Medium")
    _menu.add_item("Hard")

    global game

    _menu.set_selected(1)  # Default to medium

    # select difficulty
    while True:
        key = inp.button
        if key == BUTTON_UP:
            inp.reset()
            _menu.scroll_up()
        elif key == BUTTON_DOWN:
            inp.reset()
            _menu.scroll_down()
        elif key == BUTTON_CENTER:
            inp.reset()

            # Show generating message
            draw.fill_screen(bg)
            center_text(draw, "Generating puzzle...", 140, fg)
            center_text(draw, "Please wait...", 160, fg)
            draw.swap()

            # Create and generate puzzle
            options = {
                0: "easy",
                1: "medium",
                2: "hard",
            }
            game = SudokuGame(options.get(_menu.selected_index))
            game.generate_puzzle()
            return True
        elif key == BUTTON_BACK:
            return False


def run(view_manager) -> None:
    """Run the app"""
    from time import time
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_RIGHT,
        BUTTON_UP,
        BUTTON_0,
        BUTTON_BACKSPACE,
    )
    from picoware.system.colors import (
        TFT_CYAN,
        TFT_GREEN,
        TFT_YELLOW,
    )
    from picoware.system.vector import Vector

    global game

    inp = view_manager.input_manager
    key = inp.button
    draw = view_manager.draw

    if key == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    # Check if completed
    if game.is_complete() and not game.completed:
        game.completed = True
        elapsed = int(time() - game.start_time)
        mins = elapsed // 60
        secs = elapsed % 60

        draw.fill_screen(view_manager.background_color)
        center_text(draw, "Congratulations!", 120, TFT_GREEN)
        center_text(draw, "Puzzle Complete!", 150, TFT_GREEN)
        center_text(draw, f"Time: {mins:02d}:{secs:02d}", 180, TFT_CYAN)
        draw.text(Vector(8, 290), "Press any key to continue...", TFT_YELLOW)
        view_manager.back()
        return

    if key == BUTTON_UP:  # Up
        inp.reset()
        game.cursor_row = (game.cursor_row - 1) % 9
    elif key == BUTTON_DOWN:  # Down
        inp.reset()
        game.cursor_row = (game.cursor_row + 1) % 9
    elif key == BUTTON_LEFT:  # Left
        inp.reset()
        game.cursor_col = (game.cursor_col - 1) % 9
    elif key == BUTTON_RIGHT:  # Right
        inp.reset()
        game.cursor_col = (game.cursor_col + 1) % 9
    elif key in (BUTTON_0, BUTTON_BACKSPACE):
        inp.reset()
        game.set_cell(game.cursor_row, game.cursor_col, 0)
    else:
        from picoware.system.buttons import (
            BUTTON_1,
            BUTTON_2,
            BUTTON_3,
            BUTTON_4,
            BUTTON_5,
            BUTTON_6,
            BUTTON_7,
            BUTTON_8,
            BUTTON_9,
        )

        button_map = {
            BUTTON_1: "1",
            BUTTON_2: "2",
            BUTTON_3: "3",
            BUTTON_4: "4",
            BUTTON_5: "5",
            BUTTON_6: "6",
            BUTTON_7: "7",
            BUTTON_8: "8",
            BUTTON_9: "9",
        }
        num = button_map.get(key)
        if num:
            inp.reset()
            game.set_cell(game.cursor_row, game.cursor_col, num)

    # Game loop
    draw_sudoku(view_manager.draw)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global game

    if game:
        del game
        game = None

    collect()
