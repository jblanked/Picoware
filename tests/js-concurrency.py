from picoware.system.js import JS

j = JS()

j.run('''
let draw = import('draw');
let time = import('time');

let Timer = {};
function timerUpdate(timer) {
    let now = time.ticksMs();
    if(now - timer.lastFire >= timer.ms) {
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

Timer.setInterval = createTimer;

let t1 = Timer.setInterval(100, function(i) {
    draw.clear();
    draw.text(0, 0, 'Fast: ' + JSON.stringify(i));
    draw.swap();
});

let t2 = Timer.setInterval(500, function(i) {
    draw.text(0, 20, 'Slow: ' + JSON.stringify(i));
    draw.swap();
});

let start = time.ticksMs();
while(time.ticksMs() - start < 3000) {
    timerUpdate(t1);
    timerUpdate(t2);
}
''')