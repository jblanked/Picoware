# download from: http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4
# then convert to png frames with: mkdir big-buck-bunny && ffmpeg -i ~/Downloads/BigBuckBunny.mp4 -vf "fps=10,scale=320:320:force_original_aspect_ratio=decrease,pad=320:320:(ow-iw)/2:(oh-ih)/2" big-buck-bunny/frame_%04d.png
# then convert to .bin using the png2fb.py script in tools: python png2fb.py <folder> --8bit
# then rename to  `big-buck-bunny.bin` and copy to the root of your SD card
from micropython import const
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_BACK
from picoware_sd import fat32_file

FRAME_START = const(1)
FRAME_STOP = const(5965)
FRAME_WIDTH = const(320)
FRAME_HEIGHT = const(320)
CHUNK_SIZE = const(FRAME_WIDTH * FRAME_HEIGHT)

current_frame = 0
position = None
size = None
file_obj = None
frame_data = None


def start(view_manager) -> bool:
    """Start the app"""
    if not view_manager.has_sd_card:
        view_manager.alert("App requires an SD card.", False)
        return False

    global position, size, current_frame, file_obj, frame_data
    current_frame = FRAME_START
    position = Vector(0, 0)
    size = Vector(FRAME_WIDTH, FRAME_HEIGHT)

    storage = view_manager.storage
    if not storage.exists("big-buck-bunny.bin"):
        view_manager.alert("big-buck-bunny.bin not found on SD card.", False)
        return False

    # Use C module directly
    storage.mount()
    file_obj: fat32_file = storage.file_open("big-buck-bunny.bin")
    print(file_obj)

    # Pre-allocate frame buffer once
    frame_data = bytearray(CHUNK_SIZE)

    return True


def run(view_manager) -> None:
    """Run the app"""
    global current_frame

    inp = view_manager.input_manager
    storage = view_manager.storage
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
    else:
        # Direct read into pre-allocated buffer
        bytes_read = storage.file_readinto(file_obj, frame_data)

        # Check if we need to loop
        if bytes_read < CHUNK_SIZE:
            storage.file_seek(file_obj, 0)
            current_frame = FRAME_START
            storage.file_readinto(file_obj, frame_data)

        # Draw the frame
        draw = view_manager.draw
        draw.image_bytearray(position, size, frame_data)
        draw.swap()

        # Advance to next frame
        current_frame += 1
        if current_frame > FRAME_STOP:
            current_frame = FRAME_START
            storage.file_seek(file_obj, 0)


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global position, size, file_obj, frame_data
    storage = view_manager.storage

    if file_obj:
        storage.file_close(file_obj)
        file_obj = None

    storage.unmount()

    del position
    position = None
    del size
    size = None
    del frame_data
    frame_data = None

    collect()
