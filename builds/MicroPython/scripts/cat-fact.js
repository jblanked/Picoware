let http = import("http");
let draw = import('draw');
let time = import('time');

let response = http.request("https://catfact.ninja/fact", "GET");

draw.clear();

if (response) {
    draw.text(10, 10, JSON.parse(response).fact);
}
else {
    draw.text(10, 10, "Failed to fetch cat fact.");
}
draw.swap();
time.sleepMs(5000);