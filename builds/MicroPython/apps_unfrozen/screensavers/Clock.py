radius: int = 0


def start(view_manager) -> bool:
    """Start the app"""
    global radius
    screen_size = view_manager.draw.size
    radius = min(screen_size.x, screen_size.y) // 2 - 60
    return True


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK
    from picoware.system.vector import Vector
    from picoware.system.colors import TFT_WHITE, TFT_RED, TFT_GREEN, TFT_ORANGE
    from math import sin, cos, pi

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    draw = view_manager.draw
    time_obj = view_manager.time

    # Get current time
    time_str = time_obj.time  # Returns "HH:MM:SS"
    time_parts = time_str.split(":")
    hours = int(time_parts[0])
    minutes = int(time_parts[1])
    seconds = int(time_parts[2])

    # Clear screen
    draw.erase()

    # Calculate center and radius for the clock
    screen_size = draw.size
    center_x = screen_size.x // 2
    center_y = screen_size.y // 2 - 20  # Offset up to make room for digital display

    # Draw clock face
    circ_vec = Vector(center_x, center_y)
    draw.circle(circ_vec, radius, TFT_WHITE)

    # Draw hour markers
    line_vec_pos = Vector(0, 0)
    line_vec_size = Vector(0, 0)
    rad = pi / 180
    for i in range(12):
        angle = (i * 30 - 90) * rad  # Convert to radians, -90 to start at top
        marker_start = radius - 10
        marker_end = radius - 5
        line_vec_pos.x, line_vec_pos.y = int(center_x + marker_start * cos(angle)), int(
            center_y + marker_start * sin(angle)
        )
        line_vec_size.x, line_vec_size.y = int(center_x + marker_end * cos(angle)), int(
            center_y + marker_end * sin(angle)
        )
        draw.line_custom(line_vec_pos, line_vec_size, TFT_WHITE)

    # Draw center dot
    draw.fill_circle(circ_vec, 4, TFT_WHITE)

    # Calculate angles for clock hands (in radians)
    # Convert 12-hour format
    hours_12 = hours % 12
    hour_angle = ((hours_12 * 30 + minutes * 0.5) - 90) * rad
    minute_angle = ((minutes * 6) - 90) * rad
    second_angle = ((seconds * 6) - 90) * rad

    # Draw hour hand (shortest, thickest)
    hour_length = radius * 0.5
    hour_x = int(center_x + hour_length * cos(hour_angle))
    hour_y = int(center_y + hour_length * sin(hour_angle))
    line_vec_pos.x, line_vec_pos.y = center_x, center_y
    line_vec_size.x, line_vec_size.y = hour_x, hour_y
    draw.line_custom(line_vec_pos, line_vec_size, TFT_WHITE)
    # Make it thicker by drawing parallel lines
    line_vec_pos.x, line_vec_pos.y = center_x - 1, center_y
    line_vec_size.x, line_vec_size.y = hour_x - 1, hour_y
    draw.line_custom(line_vec_pos, line_vec_size, TFT_WHITE)
    line_vec_pos.x, line_vec_pos.y = center_x + 1, center_y
    line_vec_size.x, line_vec_size.y = hour_x + 1, hour_y
    draw.line_custom(line_vec_pos, line_vec_size, TFT_WHITE)

    # Draw minute hand (medium length)
    minute_length = radius * 0.75
    minute_x = int(center_x + minute_length * cos(minute_angle))
    minute_y = int(center_y + minute_length * sin(minute_angle))
    line_vec_pos.x, line_vec_pos.y = center_x, center_y
    line_vec_size.x, line_vec_size.y = minute_x, minute_y
    draw.line_custom(line_vec_pos, line_vec_size, TFT_GREEN)

    # Draw second hand (longest, thinnest)
    second_length = radius * 0.85
    second_x = int(center_x + second_length * cos(second_angle))
    second_y = int(center_y + second_length * sin(second_angle))
    line_vec_pos.x, line_vec_pos.y = center_x, center_y
    line_vec_size.x, line_vec_size.y = second_x, second_y
    draw.line_custom(line_vec_pos, line_vec_size, TFT_RED)

    # Draw digital time display below the clock
    digital_y = center_y + radius + 20

    # Calculate text centering
    font_width = draw.font_size.x
    time_display = time_str
    text_width = len(time_display) * font_width
    text_x = (screen_size.x - text_width) // 2
    text_vec = Vector(text_x, digital_y)
    draw.text(text_vec, time_display, TFT_WHITE)

    # Draw date below time
    date_str = time_obj.date
    date_width = len(date_str) * font_width
    date_x = (screen_size.x - date_width) // 2
    text_vec.x, text_vec.y = date_x, digital_y + 20
    draw.text(text_vec, date_str, TFT_ORANGE)

    # Swap buffers to display
    draw.swap()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global radius

    radius = 0

    collect()
