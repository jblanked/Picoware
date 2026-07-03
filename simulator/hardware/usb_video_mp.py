USB_VIDEO_MAGIC = 0x50494356
USB_VIDEO_HDR_SIZE = 10
USB_VIDEO_FORMAT_RGB332 = 0
USB_VIDEO_FORMAT_RGB565 = 1


class USBVideoStream:
    def __init__(self):
        self.active = False
        self.pixel_format = USB_VIDEO_FORMAT_RGB332
        self.frames_sent = 0
        self.last_frame = None

    def __repr__(self):
        return "USBVideoStream(active=%s, pixel_format=%d)" % (
            self.active,
            self.pixel_format,
        )

    def __del__(self):
        self.stop()

    def start(self):
        self.active = True

    def stop(self):
        self.active = False

    def send_frame(self, frame=None, width=0, height=0):
        if not self.active:
            return False

        self.frames_sent += 1
        self.last_frame = {
            "magic": USB_VIDEO_MAGIC,
            "width": int(width),
            "height": int(height),
            "pixel_format": self.pixel_format,
            "data": bytes(frame) if frame is not None else b"",
        }
        return True
