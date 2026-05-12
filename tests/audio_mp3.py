from picoware.system.view_manager import ViewManager
from utime import sleep_ms
from gc import collect, mem_free
print(mem_free())
v = ViewManager()
a = v.audio

file_name = "storm-demo.mp3"

try:
    if not a.play_mp3(file_name):
        print("failed to play mp3")
    
    while a.is_playing:
        sleep_ms(1)

finally:
    a.stop()
    
    del v._audio
    v._audio = None
    
    del v
    v = None

    collect()
    collect()
    collect()


