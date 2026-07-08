from picoware.system.js import JS
from picoware.system.thread import Thread

js0 = JS()
js1 = JS()

_done = [False, False]

def run_on_core(js, thread_id):
    """Execute JavaScript on the given core."""
    result = js.run(f"""
    let math = import('math');
    let a = math.floor(3.7);
    let b = math.ceil(3.2);
    let c = math.sqrt(144);
    let d = math.pow(2, 8);
    let e = math.sin(0);
    let f = math.cos(0);
    let res = 0;
    for (let i = ({thread_id} + 1) * 100; i < ({thread_id} + 1) * 100 + 5; i++) {{
        log('Thread {thread_id}: ' + JSON.stringify(i));
        res = i;
    }}
    res;
    """)
    print(f"\nThread {thread_id}: {result}\n")
    _done[thread_id] = True

# Run on second core
t = Thread(run_on_core, (js1, 1))
t.run()

# Run on main core 
run_on_core(js0, 0)

# Wait for second core to finish (poll its flag only)
while not _done[1]:
    pass

del t
t = None