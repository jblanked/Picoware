from picoware.system.js import JS

js = JS()

js.run("""
let time = import('time');
let websocket = import('websocket');
let draw = import('draw');

let timeout = 5000;
let now = time.ticksMs();
let received = false;

if(!websocket.start('wss://echo.websocket.org', 443)) {
    draw.clear();
    draw.text(0, 10, 'Failed to start websocket connection.');
    draw.swap();
} else {
    while(!websocket.isConnected() && time.ticksMs() - now < timeout) {
        draw.clear();
        draw.text(0, 10, 'Connecting to websocket..');
        draw.swap();
    }

    if(websocket.isConnected()) {
        draw.clear();
        draw.text(0, 10, 'Connected');
        draw.text(0, 20, 'Sending hello..');
        draw.swap();

        if(websocket.send('Hello, WebSocket!')) {
            draw.clear();
            draw.text(0, 10, 'Sent hello');
            draw.swap();

            now = time.ticksMs();
            while(time.ticksMs() - now < timeout) {
                let resp = websocket.getResponse(64);
                if(resp !== null) {
                    draw.clear();
                    draw.text(0, 10, 'Received: ' + JSON.stringify(resp));
                    draw.swap();
                    received = true;
                    break;
                }
                draw.clear();
                draw.text(0, 10, 'Waiting for response..');
                draw.swap();
            }

            if(!received) {
                draw.clear();
                draw.text(0, 10, 'Failed to receive response');
                draw.swap();
            }
        } else {
            draw.clear();
            draw.text(0, 10, 'Failed to send websocket message');
            draw.swap();
        }
    } else {
        draw.clear();
        draw.text(0, 10, 'Connection timed out.. failed to connect.');
        draw.swap();
    }

    websocket.stop();
}
""")

del js
js = None
