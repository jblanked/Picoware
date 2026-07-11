import os


def mount(mount_point="/sd"):
    """Mount the simulated SD card directory as a real VFS at *mount_point*
    so that __import__ and open() can resolve paths like /sd/picoware/apps."""
    # Already mounted?
    try:
        os.stat(mount_point)
        return True
    except OSError:
        pass

    import sim_runtime

    sd_path = sim_runtime.sd_root
    # Ensure an absolute path – sim_runtime.root is the repo root
    if not sd_path.startswith("/"):
        sd_path = sim_runtime.root.rstrip("/") + "/" + sd_path

    # Create backing dir if missing
    try:
        os.stat(sd_path)
    except OSError:
        sim_runtime.mkdir_p(sd_path)

    os.mount(os.VfsPosix(sd_path), mount_point)
    return True


def umount(mount_point="/sd"):
    try:
        os.umount(mount_point)
    except Exception:
        pass
    return True
