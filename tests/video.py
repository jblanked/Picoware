"""
1. Download sample-320x240.mp4 from https://mp4.to/samples/mp4/
2. Open up Terminal and use: cd ~/Downloads && ffmpeg -i sample-320x240.mp4 -c:v mjpeg -q:v 3 -c:a mp3 sample.mp4
3. Add sample.mp4 to the root of your SD card
"""

from picoware.system.view_manager import ViewManager
from picoware.system.video import Video

vm = ViewManager()

_path = "sample.mp4"
if not vm.storage.exists(_path):
    raise Exception("Test file not found..")

v = Video("sample.mp4")

# blocking approach..
# v.play()

# non-blocking
if v.start():
    while v.run():
        pass
    v.stop()
else:
    vm.log("Failed to start")

del vm, v

