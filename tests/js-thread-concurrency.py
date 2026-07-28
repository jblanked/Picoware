from picoware.system.js import JS

j = JS()

j.run('''
let time = import('time');
let math = import('math');

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

function doMath(id, i) {
    log('Timer ' + id + ': ' + JSON.stringify(i) +
        ' (floor ' + JSON.stringify(math.floor(3.7)) +
        ', ceil ' + JSON.stringify(math.ceil(3.2)) +
        ', sqrt ' + JSON.stringify(math.sqrt(144)) +
        ', pow ' + JSON.stringify(math.pow(2, 8)) +
        ', sin ' + JSON.stringify(math.sin(0)) +
        ', cos ' + JSON.stringify(math.cos(0)) + ')\n');
}

let timerA = Timer.setInterval(500, function(i) {
    doMath('A', i);
});

let timerB = Timer.setInterval(700, function(i) {
    doMath('B', i);
});

let start = time.ticksMs();
while(time.ticksMs() - start < 5000) {
    timerUpdate(timerA);
    timerUpdate(timerB);
}
''')

del j
j = None
