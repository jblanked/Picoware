"""Host shim for Picoware's optional on-device C execution module."""


class C:
    """Represent the C engine without executing native C in the simulator."""

    def __init__(self):
        self.is_initialized = True

    def __del__(self):
        self.is_initialized = False

    def exec(self, path):
        """Reject C-file execution because it requires the device toolchain."""
        raise RuntimeError("C execution is not available in the simulator: " + str(path))

    def run(self, c_code):
        """Reject C-source execution because it requires the device toolchain."""
        raise RuntimeError("C execution is not available in the simulator")
