from picoware.system.uf2loader import UF2Loader

# change path to file path of uf2 located on SD card
path = "Picoware-PicoCalcPico2W.uf2"

uf2 = UF2Loader()
uf2.flash(path)
