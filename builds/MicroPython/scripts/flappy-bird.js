let input = import('input');
let buttons = import('buttons');
let draw = import('draw');

let W = draw.size.width;
let H = draw.size.height;
let UP = buttons.BUTTON_UP;
let CENTER = buttons.BUTTON_CENTER;
let BACK = buttons.BUTTON_BACK;

let SWAP = true;

let CYAN = '0x07FF';
let WHITE = '0xFFFF';
let GREEN = '0x07E0';
let DARKGREEN = '0x03E0';
let BLACK = '0x0000';
let YELLOW = '0xFFE0';

let BIRD_W = 20;
let BIRD_H = 16;
let PILAR_MAX = 15;
let GRAVITY_JUMP = -6.0;
let GRAVITY_TICK = 0.7;
let STATE_LIFE = 0;
let STATE_OVER = 1;

let bird_pixels = [
    "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF6", "0xED", "0xED", "0xF2", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF6", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF6", "0xE9",
    "0xC0", "0xC0", "0xE4", "0xF6", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF6", "0xC4", "0xFB", "0x1F", "0x1F", "0x1F", "0xFB", "0xC4", "0xE5", "0xE9", "0xEA", "0xE9", "0xC4", "0xF6", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF6",
    "0xC0", "0xC4", "0xF6", "0x1F", "0xF6", "0xC4", "0xE5", "0xE9", "0xF2", "0x1F", "0xFB", "0xFB", "0xE9", "0xF2", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF6", "0xC0", "0xE5", "0xE9", "0xF6", "0xF6", "0xC0", "0xE5", "0xF2", "0x1F", "0xDB", "0x6D", "0xFB",
    "0xC9", "0xF2", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF6", "0xC0", "0xE5", "0xE5", "0xE9", "0xE9", "0xC0", "0xE9", "0xFB", "0x1F", "0xD6", "0x92", "0x1F", "0xF1", "0xF1", "0xFE", "0x1F", "0x1F", "0x1F", "0x1F", "0xF6", "0xC0", "0xE5", "0xEA", "0xE5",
    "0xC0", "0xC0", "0xE9", "0xFB", "0xFB", "0xFB", "0x1F", "0xF6", "0xF5", "0xF9", "0xFA", "0x1F", "0x1F", "0x1F", "0x1F", "0xF6", "0xC0", "0xE5", "0xEA", "0xE5", "0xE5", "0xC0", "0xE9", "0xF7", "0x1F", "0xFB", "0xF6", "0xC9", "0xF6", "0x1F", "0x1F", "0x1F",
    "0x1F", "0x1F", "0x1F", "0xF6", "0xC4", "0xE5", "0xE5", "0xE5", "0xE5", "0xE5", "0xE9", "0xEA", "0xE9", "0xC4", "0xC9", "0xFB", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF6", "0xE4", "0xC0", "0xE5", "0xEA", "0xE9", "0xED", "0xF0",
    "0xEC", "0xEC", "0xF0", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF2", "0xC4", "0xE0", "0xE9", "0xED", "0xF4", "0xF4", "0xF4", "0xF4", "0xF5", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xFB", "0xF6",
    "0xF6", "0xF6", "0xC4", "0xE0", "0xED", "0xF4", "0xF4", "0xF4", "0xF4", "0xF4", "0xF9", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF2", "0xC0", "0xC0", "0xC0", "0xC0", "0xE0", "0xE9", "0xF4", "0xF4", "0xF4", "0xF4", "0xF9", "0x1F", "0x1F",
    "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF2", "0xC0", "0xE5", "0xE5", "0xE5", "0xE5", "0xE8", "0xF4", "0xF4", "0xF4", "0xFA", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xF2", "0xC0", "0xC0", "0xC0", "0xC0", "0xED",
    "0xFB", "0xFE", "0xFE", "0xFE", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0xFB", "0xED", "0xED", "0xED", "0xED", "0xF6", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F", "0x1F"
];

// scale factors (base 320x240)
let SX = W / 320;
let SY = H / 240;
let S = (W < H ? W : H) / 240;

let GAB_W = 16 * SX;
let GAB_H = 140 * SY;
let PILAR_DIST = W * 0.35;
let GROUND_H = (20 * S > 8) ? 20 * S : 8;

function str(n) { return JSON.stringify(n); }

// seeded random generator
let seed = 12345;
function rand(lo, hi) {
    seed = (seed * 16807) % 2147483647;
    let r = seed / 2147483647;
    let v = lo + r * (hi - lo + 1);
    return v - (v % 1);
}

let bird = { 'x': 15 * SX, 'y': H / 2, 'gravity': 0.0 };
let pilars = [];
let pilars_count = 0;
let points = 0;
let state = STATE_LIFE;
let cloud_y = [SY * 20, SY * 50, SY * 80, SY * 110];

for (let i = 0; i < PILAR_MAX; i++) {
    pilars[i] = { 'x': 0, 'h': 0, 'visible': 0, 'passed': false, 'spawned': false };
}

function random_pilar() {
    pilars_count += 1;
    pilars[pilars_count % PILAR_MAX] = {
        'x': W + GAB_W + 1,
        'h': rand(1, H - GAB_H - 21),
        'visible': 1,
        'passed': false,
        'spawned': false
    };
}

function state_init() {
    bird.gravity = 0.0;
    bird.x = 15 * SX;
    bird.y = H / 2;
    pilars_count = 0;
    points = 0;
    state = STATE_LIFE;
    for (let i = 0; i < PILAR_MAX; i++) {
        pilars[i].visible = 0;
    }
    random_pilar();
}

function game_tick() {
    if (state !== STATE_LIFE) { return; }

    bird.gravity += GRAVITY_TICK;
    bird.y += bird.gravity;

    // spawn next pillar
    let lead = pilars[pilars_count % PILAR_MAX];
    let spawn_x = (W - PILAR_DIST) + 3;
    if (lead.visible && !lead.spawned && lead.x <= spawn_x) {
        lead.spawned = true;
        random_pilar();
    }

    if (bird.y <= 0) {
        bird.y = 0;
        state = STATE_OVER;
    }
    if (bird.y + BIRD_H >= H) {
        bird.y = H - BIRD_H;
        state = STATE_OVER;
    }

    for (let i = 0; i < PILAR_MAX; i++) {
        let p = pilars[i];
        if (p.visible && state === STATE_LIFE) {
            p.x -= 4;

            if (bird.x >= p.x + GAB_W && !p.passed) {
                p.passed = true;
                points += 1;
            }
            if (p.x < -GAB_W) {
                p.visible = 0;
            }

            if (bird.x + BIRD_H >= p.x && bird.x <= p.x + GAB_W) {
                if (bird.y + BIRD_W - 2 >= p.h + GAB_H) {
                    state = STATE_OVER;
                    break;
                }
                if (bird.y < p.h) {
                    state = STATE_OVER;
                    break;
                }
            }
        }
    }
}

function draw_scene() {
    draw.fillRectangle(0, 0, W, H, CYAN);

    // clouds
    let off = (points * 2) % W;
    let m = W + 80 * S;
    for (let i = 0; i < 4; i++) {
        let t = (i * 80 * S - off) % m;
        if (t < 0) { t += m; }
        let x = t - 40 * S;
        let y = cloud_y[i];
        if (x >= 12 * S && x < W) {
            draw.fillCircle(x, y, 12 * S, WHITE);
            draw.fillCircle(x + 10 * S, y - 5 * S, 10 * S, WHITE);
            draw.fillCircle(x - 8 * S, y - 3 * S, 8 * S, WHITE);
        }
    }

    // ground
    draw.fillRectangle(0, H - GROUND_H, W, GROUND_H, GREEN);
    let step = (15 * S > 5) ? 15 * S : 5;
    for (let gx = 0; gx < W; gx += step) {
        draw.line(gx, H - GROUND_H, gx, H - GROUND_H + 5 * S, DARKGREEN);
    }

    if (state !== STATE_LIFE) { return; }

    // pillars
    for (let i = 0; i < PILAR_MAX; i++) {
        let p = pilars[i];
        if (p.visible === 1 && p.x >= 0 && p.x < W) {
            draw.fillRectangle(p.x, 0, GAB_W, p.h, GREEN);
            draw.rectangle(p.x, 0, GAB_W, p.h, DARKGREEN);

            let by = p.h + GAB_H;
            let bh = H - by - GROUND_H;
            if (bh > 0) {
                draw.fillRectangle(p.x, by, GAB_W, bh, GREEN);
                draw.rectangle(p.x, by, GAB_W, bh, DARKGREEN);
            }
        }
    }
}

function draw_overlay() {
    if (state === STATE_LIFE) {
        draw.text(140 * SX, 12 * SY, 'Score: ' + str(points), BLACK);
    } else {
        draw.fillRectangle(120 * S, 100 * S, 100 * S, 60 * S, YELLOW);
        draw.rectangle(120 * S, 100 * S, 100 * S, 60 * S, BLACK);
        draw.text(130 * S, 110 * S, 'Game Over!', BLACK);
        draw.text(125 * S, 125 * S, 'Score: ' + str(points), BLACK);
        draw.text(125 * S, 140 * S, 'Press to Retry', BLACK);
    }
}

let game = import('game', 'Flappy Bird', { 'x': W, 'y': H, 'z': 0 }, '0x0000', '0xFFFF');
let level = import('level', 'Level', { 'x': W, 'y': H, 'z': 0 }, game);
level.set('clearAllowed', false);
let sprite = import('image', { 'width': BIRD_W, 'height': BIRD_H }, true, bird_pixels);
let sprite_left = import('image', { 'width': BIRD_W, 'height': BIRD_H }, true, bird_pixels);
let sprite_right = import('image', { 'width': BIRD_W, 'height': BIRD_H }, true, bird_pixels);
let player = import('entity', 'Player', 0, { 'x': -100, 'y': -100, 'z': 0 }, { 'x': BIRD_W, 'y': BIRD_H, 'z': 0 }, sprite, sprite_left, sprite_right);
level.entityAdd(player);
let engine = import('engine', game, 240, false);

state_init();

function tick(button) {
    engine.updateGameInput(button);

    if (button === UP || button === CENTER) {
        if (state === STATE_OVER) {
            state_init();
        } else if (state === STATE_LIFE) {
            bird.gravity = GRAVITY_JUMP;
        }
    }

    game_tick();
    draw_scene();

    if (state === STATE_LIFE) {
        player.set('position', { 'x': bird.x, 'y': bird.y, 'z': 0 });
    } else {
        player.set('position', { 'x': -100, 'y': -100, 'z': 0 });
    }
    player.updatePosition();

    engine.runAsync(true);
    draw_overlay();
    if (SWAP) { draw.swap(); }
}

while (true) {
    let button = input.button;
    input.reset();
    if (button === BACK) { break; }
    tick(button);
}

input.reset();
engine.stop();
engine.destroy();