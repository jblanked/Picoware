# Picoware App
A desktop application for interacting with Picoware-compatible boards.

## Requirements
- Python 3.9+
- Windows, macOS, or Linux
- Any Picoware-compatible board flashed with Picoware firmware

## Installation
Run the following commands:

### 1. Close the repository and setup a virtual environment:

Mac/Linux
```bash
git clone https://github.com/jblanked/Picoware.git
cd Picoware/app
python3 -m venv venv 
source venv/bin/activate 
pip install -r requirements.txt
```

Windows (via Windows PowerShell)
```bash
git clone https://github.com/jblanked/Picoware.git
cd Picoware/app
python -m venv venv
pip install -r requirements.txt
./venv/Scripts/activate
```

### 2. Build and run the application:

Either install the application using PyInstaller:
```bash
pyinstaller PicowareApp.spec
./dist/Picoware/Picoware
```

Or run the application directly using Python:
```bash
python app.py
```

### 3. Run the application:

Afterwards, you can navigate to the `~/Picoware/app/dist` directory and run the executable or application directly if you compiled it with PyInstaller. Otherwise, you can run the application directly using `python app.py` as shown above.