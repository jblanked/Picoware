from picoware.system.js import JS
from picoware.system.view_manager import ViewManager

vm = ViewManager()
js = JS()

# replace sample.mp4 with vid on your SD
js.run('let video = import("video", "sample.mp4");')
js.run("""
if (video.start()) {
    while (video.run()) {
        log('Frame ' + JSON.stringify(video.frame) + ' of ' + JSON.stringify(video.frames) + ' at ' + JSON.stringify(video.fps) + ' fps\n');
    }
    video.stop();
}
else {
    log('Failed to start video');
}
""")