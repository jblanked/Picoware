from picoware.system.audio import Audio
from utime import sleep_ms
from gc import collect, mem_free
print(mem_free())

a = Audio()

file_name = "picoware/apps/games/ghouls/assets/ghouls-growling.wav"
file_name_2 = "picoware/apps/games/ghouls/assets/ambience.wav"

try:
    if not a.play_wav(file_name):
        print("failed to play first wav")
    
    if not a.play_wav(file_name_2):
        print("failed to play second wav")
    
    while a.is_playing:
        sleep_ms(1)

finally:
    a.stop()
    
    del a
    a = None

    collect()
    collect()
    collect()