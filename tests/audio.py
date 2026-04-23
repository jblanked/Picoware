from picoware.system.view_manager import ViewManager
from picoware.system.audio import AudioNote
from gc import collect, mem_free
print(mem_free())
v = ViewManager()
a = v.audio
print(a.volume)
a.volume = 8
print(a.volume)
note = AudioNote(a.PITCH_E3, a.PITCH_E3, a.NOTE_QUARTER)
a.play_note(note)
print(mem_free())
print(dir(a))
del a
del v._audio
a = None
v._audio = None
print(dir(a))
collect()
collect()
collect()
collect()
collect()
print(mem_free())