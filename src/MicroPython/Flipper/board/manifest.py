include("$(PORT_DIR)/boards/manifest.py")

# Only SD bootstrap is frozen.
freeze("$(PORT_DIR)/modules/Flipper", script="_boot.py")
