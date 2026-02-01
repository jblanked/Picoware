# Maze Runner - Navigate through a randomly generated maze
from random import randint, choice
from picoware.system.buttons import (
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_BACK,
    BUTTON_CENTER,
)
from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_GREEN, TFT_RED, TFT_YELLOW
from picoware.system.vector import Vector

# Game state
screen_size = None
maze = []
player_x = 1
player_y = 1
exit_x = 0
exit_y = 0
cell_size = 0
maze_width = 0
maze_height = 0
moves = 0
game_won = False
offset_x = 0
offset_y = 0
pos = None
size = None
player_pos = None
player_size = None


def generate_maze(width: int, height: int):
    """Generate a random maze using iterative backtracking with a stack"""
    # Initialize maze with all walls
    _maze = [[1 for _ in range(width)] for _ in range(height)]

    stack = [(1, 1)]
    _maze[1][1] = 0

    while stack:
        x, y = stack[-1]
        directions = [(0, -2), (0, 2), (-2, 0), (2, 0)]

        # Shuffle directions
        for i in range(len(directions) - 1, 0, -1):
            j = randint(0, i)
            directions[i], directions[j] = directions[j], directions[i]

        found = False
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and _maze[ny][nx] == 1:
                # Carve wall between current cell and next cell
                _maze[y + dy // 2][x + dx // 2] = 0
                _maze[ny][nx] = 0
                stack.append((nx, ny))
                found = True
                break

        if not found:
            stack.pop()

    # Ensure start and exit are clear
    _maze[1][1] = 0
    _maze[height - 2][width - 2] = 0

    return _maze


def reset_game():
    """Reset the game with a new maze"""
    global maze, player_x, player_y, exit_x, exit_y, moves, game_won

    # Generate new maze
    maze = generate_maze(maze_width, maze_height)

    # Set player position
    player_x = 1
    player_y = 1

    # Set exit position
    exit_x = maze_width - 2
    exit_y = maze_height - 2

    moves = 0
    game_won = False


def start(view_manager) -> bool:
    """Start the app"""
    global screen_size, maze, player_x, player_y, exit_x, exit_y, cell_size
    global maze_width, maze_height, moves, game_won, offset_x, offset_y
    global pos, size, player_pos, player_size

    draw = view_manager.draw
    screen_size = draw.size

    # Calculate maze dimensions
    cell_size = screen_size.x // 20
    maze_width = (screen_size.x // cell_size) | 1
    maze_height = (screen_size.y // cell_size) | 1

    # Ensure minimum size
    maze_width = max(maze_width, 9)
    maze_height = max(maze_height, 9)

    # Calculate offset to center the maze
    offset_x = (screen_size.x - maze_width * cell_size) // 2
    offset_y = (screen_size.y - maze_height * cell_size) // 2

    pos = Vector(0, 0)
    size = Vector(cell_size, cell_size)
    player_pos = Vector(0, 0)
    player_size = Vector(cell_size - 4, cell_size - 4)

    # Initialize game
    reset_game()

    return True


def run(view_manager) -> None:
    """Run the app"""
    global player_x, player_y, moves, game_won, maze, offset_x, offset_y, pos, size

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    draw = view_manager.draw

    if game_won:
        # If game is won, wait for button press
        if button == BUTTON_CENTER:
            inp.reset()
            reset_game()
            return
    else:
        # Player movement
        new_x, new_y = player_x, player_y

        if button == BUTTON_UP:
            inp.reset()
            new_y -= 1
        elif button == BUTTON_DOWN:
            inp.reset()
            new_y += 1
        elif button == BUTTON_LEFT:
            inp.reset()
            new_x -= 1
        elif button == BUTTON_RIGHT:
            inp.reset()
            new_x += 1

        # Check if move is valid
        if (
            0 <= new_x < maze_width
            and 0 <= new_y < maze_height
            and maze[new_y][new_x] == 0
        ):
            player_x = new_x
            player_y = new_y
            moves += 1

        # Check if player reached exit
        if player_x == exit_x and player_y == exit_y:
            game_won = True

    # Draw maze
    draw.fill_screen(TFT_BLACK)
    for y in range(maze_height):
        for x in range(maze_width):
            pos.x, pos.y = offset_x + x * cell_size, offset_y + y * cell_size

            if maze[y][x] == 1:
                # Wall
                draw.fill_rectangle(pos, size, TFT_WHITE)
            elif x == exit_x and y == exit_y:
                # Exit
                draw.fill_rectangle(pos, size, TFT_GREEN)

    # Draw player
    player_pos.x, player_pos.y = (
        offset_x + player_x * cell_size + 2,
        offset_y + player_y * cell_size + 2,
    )
    player_size.x, player_size.y = (cell_size - 4, cell_size - 4)
    draw.fill_rectangle(player_pos, player_size, TFT_RED)

    # Draw moves counter
    moves_pos = Vector(5, 5)
    draw.text(moves_pos, f"Moves:{moves}", TFT_YELLOW)

    # Draw win message
    if game_won:
        msg_bg_pos = Vector(screen_size.x // 2 - 70, screen_size.y // 2 - 30)
        msg_bg_size = Vector(140, 60)
        draw.fill_rectangle(msg_bg_pos, msg_bg_size, TFT_BLACK)
        draw.rect(msg_bg_pos, msg_bg_size, TFT_WHITE)

        msg_pos = Vector(screen_size.x // 2 - 50, screen_size.y // 2 - 20)
        draw.text(msg_pos, "YOU WIN!", TFT_GREEN)
        moves_msg_pos = Vector(screen_size.x // 2 - 40, screen_size.y // 2 - 5)
        draw.text(moves_msg_pos, f"Moves:{moves}", TFT_WHITE)
        restart_msg_pos = Vector(screen_size.x // 2 - 60, screen_size.y // 2 + 10)
        draw.text(restart_msg_pos, "Press to Enter play", TFT_YELLOW)

    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global screen_size, maze, player_x, player_y, exit_x, exit_y, cell_size
    global maze_width, maze_height, moves, game_won, offset_x, offset_y
    global pos, size, player_pos, player_size
    screen_size = None
    maze = []
    player_x = 1
    player_y = 1
    exit_x = 0
    exit_y = 0
    cell_size = 0
    maze_width = 0
    maze_height = 0
    moves = 0
    game_won = False
    offset_x = 0
    offset_y = 0
    del pos
    del size
    del player_pos
    del player_size
    pos = None
    size = None
    player_pos = None
    player_size = None

    collect()
