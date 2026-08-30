from picoware.system.storage import Storage
from picoware.system.infrared import Infrared

s = Storage()
ir = Infrared(s,"infrared") 
remote = ir.load("Roku_tv.ir") # infrared/Roku_tv.ir
ir.send(remote, "Power")

# on Flipper can learn with
# ir.capture("learned/tv.ir", name="Power", display=True)
# change name to button you're pressing
# then can play it back by loading the saved file