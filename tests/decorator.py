from picoware.system.decorator import wifi_required, native, viper, storage_required, audio_required, psram_required
from picoware.system.view_manager import ViewManager
from gc import collect

vm = ViewManager()

def catch(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception as e:
        print(e)
        
@viper
def test():
    n = 1
    i = 1
    while n < 1000:
        x = 2
        while x < 1000:
            i *= 3.14159
            x += 1
        i *= x
        n += 1
    return i

def testt():
    from utime import ticks_ms as t
    current = t()
    print(test())
    print(f"Test took {t() - current} ms")
    
    
@wifi_required
def check(view_manager):
    print("You have been promoted lol")
    print(vm)

@audio_required
def check2():
    print("You have been promoted to audio leader :D")

@storage_required
def check3():
    print("You have been promoted to storage manager :D")

@psram_required
def check4(t):
    print("You have been promoted to psram control :D")

@native
@audio_required
@storage_required
@psram_required
def finalcheck(view_manager):
    print("You own the company...")

catch(check, vm)
catch(check2)
catch(check3)
catch(check4, 4)
finalcheck(vm)
testt()

del vm
vm = None

collect()