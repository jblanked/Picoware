import sys
import pyb


def main():
    """Mount SD card and set the main script to /sd/firmware/main.py."""
    try:
        import sd_mp

        sd_mp.init()
        if sd_mp.mount():
            if "/sd/firmware" not in sys.path:
                sys.path.insert(0, "/sd/firmware")
            pyb.main("/sd/firmware/main.py")
    except Exception as e:
        print("SD boot failed:", e)


main()
