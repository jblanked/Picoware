#!/bin/sh
set -u

sim_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root_dir=$(CDPATH= cd -- "$sim_dir/.." && pwd)
stamp="/tmp/picoware-sim-dev.$$"
child=""

cleanup() {
    if [ -n "$child" ] && kill -0 "$child" 2>/dev/null; then
        kill "$child" 2>/dev/null
        wait "$child" 2>/dev/null
    fi
    rm -f "$stamp"
}

trap cleanup INT TERM EXIT

touch "$stamp"

if ! sh "$sim_dir/build.sh" --check; then
    echo "sim native helpers are missing or stale; run: sh sim_mp/build.sh" >&2
    exit 1
fi

watch_changed() {
    for path in \
        "$root_dir/builds/MicroPython/apps_unfrozen" \
        "$root_dir/src/MicroPython/picoware" \
        "$root_dir/sim_mp/hardware"
    do
        [ -d "$path" ] || continue
        if find "$path" -type f -newer "$stamp" -print -quit | grep . >/dev/null 2>&1; then
            return 0
        fi
    done
    return 1
}

while :; do
    touch "$stamp"
    micropython "$sim_dir/run.py" --viewer "$@" &
    child=$!
    restarted=0
    while kill -0 "$child" 2>/dev/null; do
        sleep 1
        if watch_changed; then
            echo "[sim-dev] source change detected; restarting simulator"
            kill "$child" 2>/dev/null
            wait "$child" 2>/dev/null
            child=""
            restarted=1
            break
        fi
    done
    if [ "$restarted" -eq 0 ]; then
        wait "$child" 2>/dev/null
        child=""
        break
    fi
done

cleanup
