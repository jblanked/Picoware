from picoware.system.mmbasic import MMBasic
from picoware.system.view_manager import ViewManager

vm = ViewManager()
mb = MMBasic(vm)

test_code = """
CLS
COLOR RGB(white)
BOX 10,10,100,100,,,RGB(red),RGB(red)
TEXT 160,160,"Picoware",cm
END
"""

if not mb.start(test_code):
    vn.log("Failed to start MMBasic interpreter")
else:
    mb.run()

del mb, vm