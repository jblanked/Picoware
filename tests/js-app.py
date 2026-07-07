import micropython
js = None

@micropython.native
def start(view_manager) -> bool:
    """Start the app"""
    from picoware.system.js import JS
    global js
    js = JS()
    js.run(f"""
        let width = {view_manager.draw.size.x};
        let height = {view_manager.draw.size.y};
        draw.clear();
        draw.text(10, 10, 'JS Frame Rate Test');
        draw.swap();
        let frame = 0;
        let lastTime = time.ticksMs();
        function frameUpdate() {{
            let t = time.ticksMs();
            let dt = time.ticksDiff(t, lastTime);
            lastTime = t;
            frame++;
            draw.clear();
            draw.text(10, 10, 'Frame: ' + JSON.stringify(frame));
            draw.text(10, 30, 'Time: ' + JSON.stringify(t));
            let fps = dt > 0 ? math.floor(1000 / dt) : 0;
            draw.text(10, 50, 'FPS: ' + JSON.stringify(fps));
            draw.swap();
        }}
    """)
    return True

@micropython.native
def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_BACK:
        inp.reset()
        view_manager.back()
        return

    js.run("frameUpdate();")

@micropython.native
def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global js

    del js
    js = None

    collect()

from picoware.system.view_manager import ViewManager
from picoware.system.view import View

vm = None

try:
    vm = ViewManager()
    vm.add(
        View(
            "app_tester",
            run,
            start,
            stop,
        )
    )
    vm.switch_to("app_tester")
    while True:
        vm.run()
finally:
    del vm
    vm = None