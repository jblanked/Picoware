from picoware.system.js import JS

j = JS()

j.run('let battery = import("battery");')

print(f"battery: {j.run('battery.battery;')}")
print(f"has_voltage: {j.run('battery.hasVoltage;')}")
print(f"voltage: {j.run('battery.voltage;')}")