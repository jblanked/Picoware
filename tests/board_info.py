import picoware_boards

_id = (picoware_boards.BOARD_ID)
_name = (picoware_boards.get_current_name())

print(f'You are currently using a {_name} with id "{_id}"')