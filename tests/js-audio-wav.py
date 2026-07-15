from picoware.system.js import JS
from picoware.system.view_manager import ViewManager

vm = ViewManager()
js = JS()

js.run('let audio = import("audio");')
js.run("""
if (audio.isPlaying()) {
    audio.stop();
}
if (audio.playWAV('test.wav')) {
    let time = import("time");

    // check if interval has elapsed and fire callback
    function timerUpdate(timer) {
        let now = time.ticksMs();
        if (now - timer.lastFire >= timer.ms) {
            timer.callback(timer.index);
            timer.index++;
            timer.lastFire = now;
        }
    }

    function createTimer(ms, callback) {
        return {
            lastFire: time.ticksMs(),
            index: 0,
            ms: ms,
            callback: callback
        };
    }

    let Timer = {};
    Timer.setInterval = createTimer;

    let pollTimer = Timer.setInterval(1000, function(i) {
        if (audio.isPlaying()) {
            log("Audio is playing, index: " + JSON.stringify(i) + "\n");
        }
    });

    let start = time.ticksMs();
    while (time.ticksMs() - start < 10000) {
        timerUpdate(pollTimer);
    }

    audio.stop();
}
""")