from picoware.system.js import JS
from picoware.system.view_manager import ViewManager

vm = ViewManager()
js = JS()

js.run('let audio = import("audio");')
js.run("""
if (audio.isPlaying()) {
    audio.stop();
}
audio.playSound({
    leftFrequency: "165",
    rightFrequency: "165",
    duration: "500"
});
""")