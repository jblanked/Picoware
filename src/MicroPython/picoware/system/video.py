"""Video - Video output for Picoware."""

import video


class Video(video.Video):
    """Handle video output on the device.

    Args:
        path (str): Path to the video file.
        x (int): X-coordinate for video display. Default is 0.
        y (int): Y-coordinate for video display. Default is 0.
        scale (float): Scale factor for the video display. Default is 1.0.

    Methods:
        - play(): Blocking video playback.
        - start(): Start video playback asynchronously.
        - run(): Run a video playback frame.
    
    Attributes:
        - path (str): Path to the video file.
        - active (bool): Indicates if the video is currently active.
        - width (int): Width of the video display.
        - height (int): Height of the video display.
        - frames (int): Total number of frames in the video.
        - frame (int): Current frame index of the video.
        - fps (float): Frames per second of the video.
    
    """
    