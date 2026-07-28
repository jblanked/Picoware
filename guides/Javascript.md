# JavaScript (MJS) Guide
[MJS](https://github.com/cesanta/mjs) is an embedded JavaScript engine which implements a strict subset of ES6 (JavaScript version 6). It is used in Picoware to allow users to execute JavaScript code/scripts on the device. It has known limitations, such as no `var`, only `let`, and others described [here](https://github.com/cesanta/mjs#restrictions).

Picoware users can write scripts and add them to the SD card (in `picoware/scripts/`) and they will appear in `Library` -> `Scripts`, and when clicked, they will be executed. The scripts can also be run from Python using the `JS` class (`picoware.system.js`) in a custom python app or the REPL. Unlike our python apps, these scripts do not have to have lifetime methods (`start()`, `run()`, `stop()`), and are executed in a single run. The scripts can use the built-in libraries (see below) to access the device's hardware and features.

## Globals

These functions and objects are available without any import.

### `log(message)`

Print a message to the debug console.

```javascript
log('Hello World');
```

### `JSON`

Standard JSON stringify/parse — see `tests/js-json.py`.

```javascript
JSON.stringify({name: 'test', value: 42});
JSON.parse('{"name":"test","value":42}');
```

## Libraries

All libraries are loaded via `import('name')`. The returned object
provides methods and properties for that library.

---

### time

`import('time')` — millisecond timing.

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `ticksMs()` | number | Milliseconds since boot |
| `ticksDiff(t1, t2)` | number | Difference between two tick values |
| `sleepMs(ms)` | void | Block for N milliseconds |

**Example** (`tests/js-time.py`):

```javascript
let time = import('time');
let ticks = time.ticksMs();
```

---

### math

`import('math')` — basic math functions.

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `floor(x)` | number | Round down |
| `ceil(x)` | number | Round up |
| `sqrt(x)` | number | Square root |
| `pow(x, y)` | number | Power |
| `sin(x)` | number | Sine (radians) |
| `cos(x)` | number | Cosine (radians) |
| `random()` | number | Random float [0, 1) |

**Example** (`tests/js-math.py`):

```javascript
let math = import('math');
let a = math.floor(3.7);
let b = math.ceil(3.2);
let c = math.sqrt(144);
let d = math.pow(2, 8);
let e = math.sin(0);
let f = math.cos(0);
```

---

### system

`import('system')` — board and runtime information.

**Properties** (read-only)

| Name | Type | Description |
|------|------|-------------|
| `boardId` | string | Board identifier |
| `boardName` | string | Board display name |
| `deviceName` | string | Device hostname |
| `freePsram` | number | Free PSRAM bytes |
| `freeHeap` | number | Free heap bytes |
| `freq` | number | CPU frequency (MHz) |
| `hasAudio` | boolean | Audio hardware present |
| `hasPsram` | boolean | PSRAM present |
| `hasSdCard` | boolean | SD card present |
| `hasTouch` | boolean | Touch screen present |
| `hasWifi` | boolean | WiFi hardware present |
| `isCircular` | boolean | Circular display |
| `freeFlash` | number | Free flash bytes |
| `totalFlash` | number | Total flash bytes |
| `totalHeap` | number | Total heap bytes |
| `totalPsram` | number | Total PSRAM bytes |
| `usedHeap` | number | Used heap bytes |
| `usedPsram` | number | Used PSRAM bytes |
| `version` | string | Firmware version |

**Methods**

| Name | Description |
|------|-------------|
| `softReset()` | Soft reset the device |
| `hardReset()` | Hard reset the device |
| `bootloaderMode()` | Reboot into bootloader |

**Example** (`tests/js-system.py`):

```javascript
let system = import('system');
log('Board: ' + system.boardName);
log('Free RAM: ' + system.freeHeap);
log('Has WiFi: ' + system.hasWifi);
```

---

### pin

`import('pin', pinNumber, direction, pull)` — GPIO pin control.

The `direction` is a string: `'IN'`, `'OUT'`, or `'OPEN_DRAIN'`.
The `pull` is a string: `'PULL_UP'` or `'PULL_DOWN'`.

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `on()` | void | Set pin high |
| `off()` | void | Set pin low |
| `high()` | void | Set pin high |
| `low()` | void | Set pin low |
| `toggle()` | void | Toggle pin state |
| `value([v])` | number | Get or set pin value |

**Example** (`tests/js-pin.py`):

```javascript
let time = import('time');
let pin = import('pin', 28, 'OUT');

pin.on();
time.sleepMs(100);
pin.value(); // 1

pin.off();
time.sleepMs(100);
pin.value(); // 0

pin.toggle();
pin.value(); // 1

pin.value(0);
pin.value(); // 0
```

---

### input

`import('input')` — button and keyboard input.

**Properties** (read-only)

| Name | Type | Description |
|------|------|-------------|
| `button` | number | Current button code |
| `battery` | number | Battery level |
| `wasCapitalized` | boolean | Shift was active |

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `buttonToChar(code)` | string | Map button code to character |
| `read()` | number | Blocking key read |
| `readNonBlocking()` | number | Non-blocking key read (-1 if none) |
| `reset()` | void | Reset input state |

**Example** (`tests/js-input.py`):

```javascript
let input = import('input');
let code = input.button;
let char = input.buttonToChar(code);
input.reset();
```

---

### storage

`import('storage')` — SD card file operations.

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `read(path)` | string | Read entire file |
| `readChunk(path, offset, size)` | string | Read file chunk |
| `size(path)` | number | File size in bytes |
| `write(path, data)` | boolean | Write data (string or ArrayBuffer) |

**Example** (`tests/js-storage.py`):

```javascript
let storage = import('storage');
let success = storage.write("test.txt", "Hello World");
let data = "";
if(success) {
    data = storage.read("test.txt");
}
```

---

### wifi

`import('wifi')` — WiFi connectivity.

**Properties** (read-only except `timeout`)

| Name | Type | Description |
|------|------|-------------|
| `deviceIp` | string | Assigned IP address |
| `lastError` | string | Last error message |
| `macAddress` | string | MAC address |
| `state` | number | 0=idle, 1=connecting, 2=connected, 3=issue, 4=timeout |
| `timeout` | number | Connection timeout (seconds), read/write |

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `connect(ssid, pass, staMode)` | boolean | Sync connect (blocks until done) |
| `connectAsync(ssid, pass, staMode)` | boolean | Start async connect in background thread |
| `disconnect()` | void | Disconnect from network |
| `isConnected()` | boolean | Check connection status |
| `reset()` | void | Reset WiFi configuration |
| `scan()` | array | Scan for networks |

**Sync connect** (`tests/js-wifi-connect.py`):

```javascript
let wifi = import('wifi');

if (wifi.connect('my-ssid', 'my-pass') && wifi.isConnected()) {
    log(' WiFi connected, mac address: ' + JSON.stringify(wifi.macAddress) + ', device_ip: ' + JSON.stringify(wifi.deviceIp));
}
else {
    if(wifi.state === 0) {
        log('Failed to connect to my-ssid, state is idle..');
    }
    else {
        log('Failed to connect to my-ssid, state: ' + JSON.stringify(wifi.state) + ', error: ' + JSON.stringify(wifi.lastError));
    }
    wifi.reset();
}
```

**Async connect** (`tests/js-wifi-connect-async.py`):

```javascript
// In start():
let wifi = import('wifi');
if (!wifi.connectAsync('my-ssid', 'my-pass')) {
    log('Failed to start wifi connection');
}
```

```javascript
// In run() (poll each frame):
let state = wifi.state;
if (state === 1) {
    // WIFI_STATE_CONNECTING
} else if (state === 2) {
    // WIFI_STATE_CONNECTED
    let info = JSON.stringify({ip: wifi.deviceIp, mac: wifi.macAddress});
    log('WiFi connected: ' + info);
} else if (state === 0) {
    // WIFI_STATE_IDLE
    log('Connection failed — state is idle');
} else {
    // WIFI_STATE_ISSUE (3) or WIFI_STATE_TIMEOUT (4)
    let info = JSON.stringify({state: wifi.state, error: wifi.lastError});
    log('Connection failed: ' + info);
}
```

---

### uart

`import('uart', uartId, txPin, rxPin, baudRate, timeout)` — serial
communication. All parameters are optional with defaults (id=0, tx=0,
rx=1, baud=115000, timeout=2000ms).

**Properties** (read-only)

| Name | Type | Description |
|------|------|-------------|
| `txPin` | number | TX pin number |
| `rxPin` | number | RX pin number |
| `baudRate` | number | Baud rate |
| `timeout` | number | Read timeout (ms) |
| `isSending` | boolean | Transmit in progress |
| `hasData` | boolean | Data available to read |

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `clear()` | void | Clear buffers |
| `flush()` | void | Wait for transmit completion |
| `println(data)` | void | Write string with newline |
| `write(data)` | void | Write raw data |
| `readLine()` | string | Read line |
| `readSerialLine()` | string | Read serial line |
| `readInto(buffer, length)` | number | Read bytes into array |

**Example** (`tests/js-uart.py`):

```javascript
let uart = import('uart');

// Properties
uart.txPin;
uart.rxPin;
uart.baudRate;
uart.timeout;

uart.clear();
uart.flush();

uart.println("Hello World");
uart.write("Bye\n");

if(uart.isSending) {
    log("Sending data..");
}

if(uart.hasData) {
    log(uart.readLine);
}

let arr = [];
let readCount = uart.readInto(arr, 2048);

for(let i = 0; i < readCount; i++) {
    log(JSON.stringify(arr[i]));
}
```

---

### draw

`import('draw')` — display drawing primitives.

Color values must be hex strings (`'#FF0000'`) or raw numbers. Default color is white (0xFFFF), default
background is black (0x0000).

Font sizes (optional last parameter): use `1` or omit for default.

**Methods**

| Name | Description |
|------|-------------|
| `clear([color])` | Clear screen |
| `pixel(x, y, [color])` | Draw a pixel |
| `line(x1, y1, x2, y2, [color])` | Draw a line |
| `rectangle(x, y, w, h, [color])` | Draw rectangle outline |
| `fillRectangle(x, y, w, h, [color])` | Draw filled rectangle |
| `fillRoundRectangle(x, y, w, h, r, [color])` | Rounded filled rect |
| `circle(cx, cy, r, [color])` | Draw circle outline |
| `fillCircle(cx, cy, r, [color])` | Draw filled circle |
| `triangle(x1, y1, x2, y2, x3, y3, [color])` | Draw triangle outline |
| `fillTriangle(x1, y1, x2, y2, x3, y3, [color])` | Draw filled triangle |
| `char(x, y, c, [color, fontSize])` | Draw a single character |
| `text(x, y, str, [color, fontSize])` | Draw a text string |
| `swap()` | Swap display buffers |

**Example** (`tests/js-app.py`):

```javascript
let draw = import('draw');
let time = import('time');
let math = import('math');

draw.clear();
draw.text(10, 10, 'JS Frame Rate Test');
draw.swap();
let frame = 0;
let lastTime = time.ticksMs();
function frameUpdate() {
    let t = time.ticksMs();
    let dt = time.ticksDiff(t, lastTime);
    lastTime = t;
    frame++;
    draw.clear();
    draw.text(10, 10, 'Frame: ' + JSON.stringify(frame));
    draw.text(10, 30, 'Time: ' + JSON.stringify(t));
    let fps = dt > 0 ? math.floor(1000 / dt) : 0;
    draw.text(10, 50, 'FPS: ' + JSON.stringify(fps));
    draw.swap();
}
```

---

### http

`import('http')` — HTTP client.

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `request(url, method, headers, payload, bufSize)` | string | Sync HTTP request |
| `requestStart(url, method, headers, payload)` | boolean | Start async request |
| `isFinished()` | boolean | Async request done |
| `getResponse(bufSize)` | string | Get async response |

**Sync request** (`tests/js-http-get.py`):

```javascript
let http = import('http'); let response = http.request("https://catfact.ninja/fact", "GET");
```

---

### audio

`import('audio')` — audio playback (MP3, WAV, and tone generation).

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `isPlaying()` | boolean | Whether audio is currently playing |
| `playMP3(filename)` | boolean | Play an MP3 file from SD card |
| `playWAV(filename)` | boolean | Play a WAV file from SD card |
| `playSound(soundObj)` | void | Play a tone (blocking) |
| `stop()` | void | Stop audio playback |

**Tone example** (`tests/js-audio.py`):

```javascript
let audio = import('audio');

if (audio.isPlaying()) {
    audio.stop();
}
audio.playSound({
    leftFrequency: "165",
    rightFrequency: "165",
    duration: "500"
});
```

**MP3 example** (`tests/js-audio-mp3.py`):

```javascript
let audio = import('audio');

if (audio.isPlaying()) {
    audio.stop();
}
if (audio.playMP3('test.mp3')) {
    let time = import("time");

    // check if interval has elapsed and fire callback
    function timerUpdate(timer) {
        let now = time.ticksMs();
        if (now - timer.lastFire >= timer.ms) {
            timer.callback(timer.index);
            timer.index++;
            timer.lastFire = now;
        }
    }

    function createTimer(ms, callback) {
        return {
            lastFire: time.ticksMs(),
            index: 0,
            ms: ms,
            callback: callback
        };
    }

    let Timer = {};
    Timer.setInterval = createTimer;

    let pollTimer = Timer.setInterval(1000, function(i) {
        if (audio.isPlaying()) {
            log("Audio is playing, index: " + JSON.stringify(i) + "\n");
        }
    });

    let start = time.ticksMs();
    while (time.ticksMs() - start < 10000) {
        timerUpdate(pollTimer);
    }

    audio.stop();
}
```

---

### bluetooth

`import('bluetooth')` — BLE central and peripheral operations.

**Properties** (read-only)

| Name | Type | Description |
|------|------|-------------|
| `macAddress` | string | Local MAC address |
| `connectedAddress` | string | Connected peer address |
| `isPairing` | boolean | Pairing in progress |
| `isScanning` | boolean | Scan in progress |
| `isConnected` | boolean | Connected as central |
| `isPeripheralConnected` | boolean | Connected as peripheral |
| `passkey` | number | Current passkey |
| `services` | array | Discovered services |
| `characteristics` | array | Discovered characteristics |

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `advertise(duration, [name])` | void | Start/stop advertising |
| `connect(type, addr, [timeout], [autoReconnect])` | boolean | Connect to a device |
| `decodeName(data)` | string | Decode device name from raw data |
| `decodeServices(data)` | array | Decode services from raw data |
| `disconnect([addr])` | void | Disconnect from a device |
| `discoverCharacteristics(connHandle, startHandle)` | void | Discover characteristics |
| `discoverServices()` | void | Discover services |
| `isDevicePaired(addr)` | boolean | Check if a device is paired |
| `isUartReady()` | boolean | UART service ready |
| `loadPairedDevices()` | void | Load paired device list |
| `onNotify(callback)` | void | Register notify callback |
| `onScan(callback)` | void | Register scan result callback |
| `onWrite(callback)` | void | Register write callback |
| `pair()` | void | Start pairing |
| `passkeyReply(accept, [passkey])` | void | Reply to passkey request |
| `read(connHandle)` | string | Read data from connection |
| `register()` | void | Register BLE service |
| `removePairedDevice(addr)` | void | Remove a paired device |
| `savePairedDevice(addr, [name])` | void | Save a paired device |
| `scan([duration], [interval], [window], [active])` | void | Start BLE scan |
| `scanForUartDevices([callback], [timeout])` | void | Scan for UART devices |
| `scanStop()` | void | Stop scanning |
| `send(data)` | void | Send data over UART |
| `startPeripheral([name], [interval])` | void | Start peripheral mode |
| `stopPeripheral()` | void | Stop peripheral mode |
| `subscribe(connHandle, [enable])` | void | Subscribe to notifications |
| `write(data, [connHandle], [response])` | void | Write data to connection |

**Example** (`tests/js-bluetooth.py`):

```javascript
let bt = import('bluetooth');

// Properties
bt.macAddress;
bt.connectedAddress;
bt.isPairing;
bt.isScanning;
bt.isConnected;
bt.isPeripheralConnected;
bt.passkey;
bt.services;
bt.characteristics;

// Methods
bt.register();
bt.isUartReady();
bt.stopPeripheral();
bt.scanStop();

// Start peripheral
bt.startPeripheral();

// Send test data
bt.send('hello');

// Advertise
bt.advertise(500000);
bt.advertise(null);

// Pairing
bt.loadPairedDevices();
bt.isDevicePaired('00:00:00:00:00:00');
bt.savePairedDevice('AA:BB:CC:DD:EE:FF', 'TestDevice');
bt.removePairedDevice('AA:BB:CC:DD:EE:FF');

// Callbacks
bt.onWrite(function(data) { log('Received: ' + data); });
bt.onNotify(function(data) { log('Notified: ' + data); });
bt.onScan(function(addrType, addr, name, rssi) { log('Found: ' + name); });

bt.scan(2000);
```

---

### buttons

`import('buttons')` — button code constants. Use these constants to identify
buttons from `input.button`.

**Properties** (read-only constants)

| Name | Value | Description |
|------|-------|-------------|
| `BUTTON_NONE` | -1 | No button pressed |
| `BUTTON_UART` | -2 | UART input |
| `BUTTON_PICO_CALC` | -3 | PicoCalc keyboard |
| `BUTTON_UP` | 0 | D-pad up |
| `BUTTON_DOWN` | 1 | D-pad down |
| `BUTTON_RIGHT` | 2 | D-pad right |
| `BUTTON_LEFT` | 3 | D-pad left |
| `BUTTON_CENTER` / `BUTTON_OK` | 4 | Center/OK |
| `BUTTON_BACK` | 5 | Back |
| `BUTTON_START` | 6 | Start |
| `BUTTON_A` – `BUTTON_Z` | 7–32 | Letter keys |
| `BUTTON_0` – `BUTTON_9` | 33–42 | Number keys |
| `BUTTON_SPACE` | 43 | Space |
| `BUTTON_ENTER` | 74 | Enter |
| `BUTTON_BACKSPACE` | 73 | Backspace |
| `BUTTON_SHIFT` | 75 | Shift |
| `BUTTON_ESCAPE` | 77 | Escape |
| `BUTTON_TAB` | 82 | Tab |
| `BUTTON_F1` – `BUTTON_F10` | 87–96 | Function keys |

Also includes symbols (`BUTTON_EXCLAMATION`, `BUTTON_AT`, `BUTTON_HASH`, etc.),
modifiers (`BUTTON_CONTROL`, `BUTTON_ALT`, `BUTTON_CAPS_LOCK`, `BUTTON_DELETE`,
`BUTTON_HOME`, `BUTTON_END`), and keyboard modifiers (`KEY_MOD_ALT`,
`KEY_MOD_SHL`, `KEY_MOD_SHR`, `KEY_MOD_SYM`).

**Example**:

```javascript
let btns = import('buttons');
let input = import('input');

if (input.button === btns.BUTTON_A) {
    log('A pressed');
}
if (input.button === btns.BUTTON_ENTER) {
    log('Enter pressed');
}
```

---

### psram

`import('psram')` — PSRAM (pseudo-static RAM) direct memory access.

**Properties** (read-only)

| Name | Type | Description |
|------|------|-------------|
| `freeHeapSize` | number | Free heap bytes |
| `nextFreeAddr` | number | Next free address |
| `totalHeapSize` | number | Total heap bytes |
| `usedHeapSize` | number | Used heap bytes |

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `isReady()` | boolean | PSRAM initialized |
| `size()` | number | PSRAM size in bytes |
| `test()` | boolean | Run self-test |
| `read8(addr)` | number | Read 8-bit value |
| `read16(addr)` | number | Read 16-bit value |
| `read32(addr)` | number | Read 32-bit value |
| `read(addr, length)` | string | Read bytes |
| `read32Bulk(addr, buffer)` | number | Bulk read 32-bit values |
| `write8(addr, value)` | void | Write 8-bit value |
| `write16(addr, value)` | void | Write 16-bit value |
| `write32(addr, value)` | void | Write 32-bit value |
| `write(addr, data)` | void | Write string or binary data |
| `write32Bulk(addr, data)` | number | Bulk write 32-bit values |
| `fill(addr, value, length)` | void | Fill memory region |
| `memset(addr, value, length)` | void | Alias for fill |
| `copy(src, dst, length)` | void | Copy within PSRAM |
| `memcpy(dst, src, length)` | void | Alias for copy |
| `malloc(data)` | object | Allocate and store data |
| `allocObject(data)` | object | Allocate and store an object |
| `collect()` | void | Garbage collect |
| `getNextFree()` | number | Get next free address |
| `memFree()` | void | Free all allocations |

Addresses and values accept hex strings (`'0x00'`, `'0x42'`) or numbers.

**Example** (`tests/js-psram.py`):

```javascript
let psram = import('psram');

// Properties
psram.freeHeapSize;
psram.nextFreeAddr;
psram.totalHeapSize;
psram.usedHeapSize;

// Status
psram.isReady();
psram.size();
psram.test();

// Read/write 8-bit
psram.write8('0x00', '0x42');
psram.read8("0x00");

// Read/write 16-bit
psram.write16('0x04', '0x1234');
psram.read16("0x04");

// Read/write 32-bit
psram.write32('0x08', '0xDEADBEEF');
psram.read32("0x08");

// Fill
psram.fill('0x64', '0xFF', '0x10');
psram.read8("0x64");

// Memset
psram.memset('0xC8', '0xAA', '0x08');
psram.read8("0xC8");

// Copy within PSRAM
psram.write32('0x12C', '0xCAFEBABE');
psram.copy('0x12C', '0x190', '0x04');
psram.read32("0x190");

// Memcpy
psram.write32('0x1F4', '0x12345678');
psram.memcpy('0x258', '0x1F4', '0x04');
psram.read32("0x258");

// Memory management
psram.memFree();
psram.getNextFree();

// String write/read
psram.write('0x3E8', 'Hello PSRAM');
psram.read("0x3E8", 11);

// Allocate objects
psram.malloc('test data');
psram.allocObject(42);

psram.collect();
```

---

### settings

`import('settings')` — read device settings from `picoware/settings/picoware.json`
on the SD card.

**Properties** (read-only)

| Name | Type | Description |
|------|------|-------------|
| `darkMode` | boolean | Dark mode enabled |
| `debug` | boolean | Debug mode enabled |
| `deepseekApiKey` | string | DeepSeek API key |
| `exitButton` | string | Exit button preference |
| `gmtOffset` | number | GMT timezone offset |
| `lvglMode` | boolean | LVGL rendering mode |
| `onscreenKeyboard` | boolean | On-screen keyboard enabled |
| `openaiApiKey` | string | OpenAI API key |
| `serverSettings` | object | Server config (`{username, password}`) |
| `themeColor` | string | UI theme color |
| `usbStream` | boolean | USB streaming enabled |
| `wifiSettings` | object | WiFi config (`{ssid, password}`) |

**Example** (`tests/js-settings.py`):

```javascript
let settings = import('settings');

log('Dark mode: ' + settings.darkMode);
log('Theme color: ' + settings.themeColor);

let wifi = settings.wifiSettings;
log('SSID: ' + wifi.ssid);

let server = settings.serverSettings;
log('Server user: ' + server.username);
```

---

### websocket

`import('websocket')` — WebSocket client.

**Methods**

| Name | Returns | Description |
|------|---------|-------------|
| `start(url, port)` | boolean | Open WebSocket connection |
| `stop()` | boolean | Close connection |
| `isConnected()` | boolean | Connection status |
| `send(message)` | boolean | Send a text message |
| `getResponse([bufSize])` | string | Receive a message (null if none) |

**Example** (`tests/js-websocket.py`):

```javascript
let time = import('time');
let websocket = import('websocket');
let draw = import('draw');

let timeout = 5000;
let now = time.ticksMs();
let received = false;

if(!websocket.start('wss://echo.websocket.org', 443)) {
    draw.clear();
    draw.text(0, 10, 'Failed to start websocket connection.');
    draw.swap();
} else {
    while(!websocket.isConnected() && time.ticksMs() - now < timeout) {
        draw.clear();
        draw.text(0, 10, 'Connecting to websocket..');
        draw.swap();
    }

    if(websocket.isConnected()) {
        draw.clear();
        draw.text(0, 10, 'Connected');
        draw.text(0, 20, 'Sending hello..');
        draw.swap();

        if(websocket.send('Hello, WebSocket!')) {
            draw.clear();
            draw.text(0, 10, 'Sent hello');
            draw.swap();

            now = time.ticksMs();
            while(time.ticksMs() - now < timeout) {
                let resp = websocket.getResponse(64);
                if(resp !== null) {
                    draw.clear();
                    draw.text(0, 10, 'Received: ' + JSON.stringify(resp));
                    draw.swap();
                    received = true;
                    break;
                }
                draw.clear();
                draw.text(0, 10, 'Waiting for response..');
                draw.swap();
            }

            if(!received) {
                draw.clear();
                draw.text(0, 10, 'Failed to receive response');
                draw.swap();
            }
        } else {
            draw.clear();
            draw.text(0, 10, 'Failed to send websocket message');
            draw.swap();
        }
    } else {
        draw.clear();
        draw.text(0, 10, 'Connection timed out.. failed to connect.');
        draw.swap();
    }

    websocket.stop();
}
```

---

### Array and String

Arrays and strings are native MJS types with standard methods.

**Array**

| Method | Description |
|--------|-------------|
| `push(...items)` | Append items, returns new length |
| `splice(start, count)` | Remove and return items |
| `length` | Array length (property) |

**Example** (`tests/js-array.py`):

```javascript
let arr = [1, 2, 3];
let len = arr.push(4, 5);
let first = arr[0];
let third = arr[2];
let spliced = arr.splice(1, 2);
```

**String**

| Method | Description |
|--------|-------------|
| `length` | String length (property) |
| `slice(start, end)` | Extract substring |
| `indexOf(substr)` | Find substring position |
| `charCodeAt(pos)` | Get character code |

**Example** (`tests/js-string.py`):

```javascript
let s = 'Hello World';
let len = s.length;
let sl = s.slice(0, 5);
let idx = s.indexOf('World');
let code = s.charCodeAt(0);
let char = s[6];
```

---

## Running JavaScript

### From Python (test files)

Use the `JS` class from `picoware.system.js`:

```python
from picoware.system.js import JS

js = JS()
result = js.run("let math = import('math'); math.sqrt(144);")
print(result)  # 12.0

del js
```

### From a file on SD card

Use `js.exec()` instead of `js.run()`:

```python
js = JS()
result = js.exec('scripts/test.js')
del js
```

The file loader is only available on boards with SD card support.
