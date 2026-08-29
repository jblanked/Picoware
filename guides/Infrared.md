# Infrared
Picoware exposes the IR hardware through `picoware.system.infrared`. The
protocol folders under `picoware.system.drivers.ir_rx` and `picoware.system.drivers.ir_tx` are
the lower-level decoders and encoders. They support NEC, NEC-ext, Samsung32,
Sony SIRC 12/15/20, Philips RC-5/RC-6 mode 0, and Microsoft MCE.

Currently the Flipper Zero supports both IR transmission and reception, the Cardputer-Adv only supports transmission, and the other boards need external IR hardware for either function.

## SD layout

Put `.ir` files below the SD card's `infrared` directory:

```text
infrared/
  Roku_tv.ir
  TVs/
    Example.ir
  assets/
    Roku_Standalone.ir
```

The file format is Flipper's `IR signals file` or `IR library file` version 1. Parsed signals store
the protocol, address, and command. Raw signals store the carrier frequency,
duty cycle, and positive alternating mark/space timings. Raw signals preserve
unknown protocols and are the recommended capture format when no encoder is
available. `RemoteLibrary.load()` indexes a file's signal names and byte ranges;
raw timing data is read only when a signal is selected.

## Use

```python
from picoware.system.storage import Storage
from picoware.system.infrared import Infrared

s = Storage()
ir = Infrared(s,"infrared") 
remote = ir.load("Roku_tv.ir") # infrared/Roku_tv.ir
ir.send(remote, "Power")
```

Capture a signal on Flipper and save it as a raw `.ir` file:

```python
saved = ir.capture(
    path="learned/Example.ir",
    name="Power",
    display=True,
)
```

For low-level use, `InfraredTransmitter.send(signal)` handles either a parsed
or raw `Signal`, while `Infrared.receiver("NEC", callback)` creates the
existing edge-based decoder. A decoder callback receives `(command, address,
extended_or_control)` and repeat commands use the decoder's existing negative
repeat value.

Known parsed protocols use the compact encoders. Any protocol not in
that table can still be sent when the file contains `type: raw`. 
