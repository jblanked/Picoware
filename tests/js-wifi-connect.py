from micropython import const
from picoware.system.js import JS

js = JS()

your_ssid = const("your_ssid")
your_pass = const("your_pass")

js.run(f"""
let wifi = import('wifi');

if (wifi.connect('{your_ssid}', '{your_pass}') && wifi.isConnected()) {{
    log(' WiFi connected, mac address: ' + JSON.stringify(wifi.macAddress) + ', device_ip: ' + JSON.stringify(wifi.deviceIp));
}}
else {{
    if(wifi.state === 0) {{
        log('Failed to connect to {your_ssid}, state is idle..');
    }}
    else {{
        log('Failed to connect to {your_ssid}, state: ' + JSON.stringify(wifi.state) + ', error: ' + JSON.stringify(wifi.lastError));
    }}
    wifi.reset();
}}

""")


del js
js = None
