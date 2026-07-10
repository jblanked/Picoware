from picoware.system.js import JS

j = JS()

j.run('let settings = import("settings");')

print(f"Dark Mode: {j.run('settings.darkMode;')}")
print(f"Debug: {j.run('settings.debug;')}")
print(f"Deepseek API Key: {j.run('settings.deepseekApiKey;')}")
print(f"Exit Button: {j.run('settings.exitButton;')}")
print(f"GMT Offset: {j.run('settings.gmtOffset;')}")
print(f"LVGL Mode: {j.run('settings.lvglMode;')}")
print(f"Onscreen Keyboard: {j.run('settings.onscreenKeyboard;')}")
print(f"Open API Key: {j.run('settings.openApiKey;')}")
print(f"Server Settings: {j.run('settings.serverSettings;')}")
print(f"Theme Color: {j.run('settings.themeColor;')}")
print(f"USB Stream: {j.run('settings.usbStream;')}")
print(f"WiFi Settings: {j.run('settings.wifiSettings;')}")

