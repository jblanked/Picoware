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
let success = storage.write('test.txt', 'Hello World');
let data = '';
if (success) {
    data = storage.read('test.txt');
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
    log('IP: ' + JSON.stringify(wifi.deviceIp));
} else {
    log('State: ' + JSON.stringify(wifi.state));
    log('Error: ' + JSON.stringify(wifi.lastError));
    wifi.reset();
}
```

**Async connect** (`tests/js-wifi-connect-async.py`):

```javascript
// In start():
this.wifi = import('wifi');
if (!this.wifi.connectAsync('my-ssid', 'my-pass')) {
    log('Failed to start wifi connection');
}
```

```javascript
// In run() (poll each frame):
let state = this.wifi.state;
if (state === 2) {
    log('Connected: ' + JSON.stringify(this.wifi.deviceIp));
} else if (state > 2) {
    log('Failed: ' + JSON.stringify(this.wifi.lastError));
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
uart.clear();
uart.flush();
uart.println('Hello World');
uart.write('Bye\n');
if (uart.isSending) {
    log('Sending data..');
}
if (uart.hasData) {
    log(uart.readLine);
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

function frameUpdate() {
    let t = time.ticksMs();
    draw.clear();
    draw.text(10, 10, 'Time: ' + JSON.stringify(t));
    let fps = math.floor(1000 / 30);
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
let http = import('http');
let response = http.request('https://catfact.ninja/fact', 'GET');
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
