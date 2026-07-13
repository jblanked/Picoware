from picoware.system.js import JS

js = JS()

try:
    js.run('let bt = import("bluetooth");')

    # Properties
    print(f"MAC Address: {js.run('bt.macAddress;')}")
    print(f"Connected Address: {js.run('bt.connectedAddress;')}")
    print(f"Is Pairing: {js.run('bt.isPairing;')}")
    print(f"Is Scanning: {js.run('bt.isScanning;')}")
    print(f"Is Connected: {js.run('bt.isConnected;')}")
    print(f"Is Peripheral Connected: {js.run('bt.isPeripheralConnected;')}")
    print(f"Passkey: {js.run('bt.passkey;')}")
    print(f"Services: {js.run('bt.services;')}")
    print(f"Characteristics: {js.run('bt.characteristics;')}")

    # Methods
    print(f"Register: {js.run('bt.register();')}")
    print(f"Is UART Ready: {js.run('bt.isUartReady();')}")
    print(f"Stop Peripheral: {js.run('bt.stopPeripheral();')}")
    print(f"Scan Stop: {js.run('bt.scanStop();')}")

    # Start peripheral
    print(f"Start Peripheral: {js.run('bt.startPeripheral();')}")

    # Send test data
    print("Send:", js.run("bt.send('hello');"))

    # Advertise
    print(f"Advertise: {js.run('bt.advertise(500000);')}")
    print(f"Stop Advertise: {js.run('bt.advertise(null);')}")

    # Pairing
    paired_addr = "00:00:00:00:00:00"
    test_addr = "AA:BB:CC:DD:EE:FF"
    print(f"Load Paired: {js.run('bt.loadPairedDevices();')}")
    print("Is Device Paired:", js.run("bt.isDevicePaired('" + paired_addr + "');"))
    print("Save Paired:", js.run("bt.savePairedDevice('" + test_addr + "', 'TestDevice');"))
    print("Remove Paired:", js.run("bt.removePairedDevice('" + test_addr + "');"))

    # Callbacks
    js.run("bt.onWrite(function(data) { log('Received: ' + data); });")
    js.run("bt.onNotify(function(data) { log('Notified: ' + data); });")
    js.run("bt.onScan(function(addrType, addr, name, rssi) { log('Found: ' + name); });")

    print(f"Scan: {js.run('bt.scan(2000);')}")

    # Decode helpers (binary data not creatable from MJS, test existence)
    print("decodeName exists:", js.run("typeof bt.decodeName;"))
    print("decodeServices exists:", js.run("typeof bt.decodeServices;"))

except Exception as e:
    print(f"Bluetooth test error: {e}")

del js
js = None
