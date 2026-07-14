# Picoware App
A desktop application for interacting with Picoware-compatible boards.

## Requirements
- Python 3.9+
- Windows, macOS, or Linux
- Any Picoware-compatible board flashed with Picoware firmware

## Installation
Use the provided installer for your operating system, or clone the repository and install dependencies manually.

To clone the repository, install dependencies and compile the application, run the following commands:

```bash
git clone https://github.com/jblanked/Picoware.git
cd Picoware/app
python3 -m venv venv # on Windows use `python -m venv venv`
source venv/bin/activate # on Windows use `./venv/Scripts/activate`
pip install -r requirements.txt
pyinstaller PicowareApp.spec
```

Then run the application with:

```bash
./dist/Picoware/Picoware
```

Or navigate to the `dist/Picoware` directory and run the executable directly.