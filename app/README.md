# Picoware App
A desktop application for interacting with Picoware-compatible boards.

## Requirements
- Python 3.9+
- Windows, macOS, or Linux
- Any Picoware-compatible board flashed with Picoware firmware

## Installation
Run the following commands:

Mac/Linux
```bash
git clone https://github.com/jblanked/Picoware.git
cd Picoware/app
python3 -m venv venv 
source venv/bin/activate 
pip install -r requirements.txt
pyinstaller PicowareApp.spec
./dist/Picoware/Picoware
```

Windows (via Windows PowerShell)
```bash
git clone https://github.com/jblanked/Picoware.git
cd Picoware/app
python -m venv venv
./venv/Scripts/activate
pip install -r requirements.txt
pyinstaller PicowareApp.spec
./dist/Picoware/Picoware
```

Afterwards, you can navigate to the `~/Picoware/app/dist` directory and run the executable or application directly.