from picoware.system.js import JS

j = JS()

j.run('let uart = import("uart");')

print(f"TX Pin: {j.run('uart.txPin;')}")
print(f"RX Pin: {j.run('uart.rxPin;')}")
print(f"Baud Rate: {j.run('uart.baudRate;')}")
print(f"Timeout: {j.run('uart.timeout;')}")

j.run('''
uart.clear();
uart.flush();

uart.println("Hello World");
uart.write("Bye\n");

if(uart.is_sending) {{
    log("Sending data..");
}}

if(uart.has_data) {{
    log(uart.readLine);
}}

let arr = [];
let readCount = uart.readInto(arr, 2048);

for(let i = 0; i < readCount; i++) {{
    log(JSON.stringify(arr[i]));
}}

''')
