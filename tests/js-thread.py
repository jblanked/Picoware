from picoware.system.js import JS
from picoware.system.thread import ThreadTask
from picoware.system.view_manager import ViewManager

v = ViewManager()

js0 = JS()
js1 = JS()

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
        log('\nThread {thread_id}: ' + JSON.stringify(i));
        res = i;
    }}
    res;
    """)
    print(f"\nThread {thread_id}: {result}\n")

# Run on second core
task = ThreadTask(
    "JS",
    function=run_on_core,
    args=(js1, 1),
)
v._thread_manager.add_task(task)
v._thread_manager.run()
            

# Run on main core 
run_on_core(js0, 0)

# Wait for second core to finish (poll its flag only)
while v is not None and isinstance(v, ViewManager) and not v._thread_manager.task.should_stop:
    v._thread_manager.run()

del js0, js1, v