#!/bin/sh
set -u

sim_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root_dir=$(CDPATH= cd -- "$sim_dir/.." && pwd)
baseline_file="$sim_dir/native_review.baseline"

mode=build
force=0
update_baseline=0
targets=""
status=0
review_status=0

usage() {
    cat <<EOF
usage: sh sim_mp/build.sh [--force] [--clean] [--check] [--update-baseline] [target...]

targets:
  all              build/check every simulator native helper
  viewer           sim_mp/viewer/sdl_fb_viewer
  audio            both local audio and radio audio sidecars
  audio-player     sim_mp/audio/sdl_audio_player
  radio-player     sim_mp/audio/sdl_radio_player
  frame-sidecar    sim_mp/native/sim_frame_sidecar
EOF
}

log() {
    printf '%s\n' "$*"
}

die() {
    printf '%s\n' "$*" >&2
    exit 2
}

file_exists() {
    [ -e "$1" ]
}

needs_rebuild() {
    binary=$1
    shift
    if [ "$force" -eq 1 ]; then
        return 0
    fi
    if [ ! -x "$binary" ]; then
        return 0
    fi
    for dep in "$@"; do
        if [ -e "$dep" ] && [ "$dep" -nt "$binary" ]; then
            return 0
        fi
    done
    return 1
}

require_sdl2() {
    pkg-config --exists sdl2 || die "SDL2 development files not found: pkg-config --exists sdl2 failed"
}

compile_sdl() {
    binary=$1
    source=$2
    require_sdl2
    log "[sim-build] cc $binary"
    cc -O2 -o "$binary" "$source" $(pkg-config --cflags --libs sdl2)
}

compile_plain() {
    binary=$1
    source=$2
    log "[sim-build] cc $binary"
    cc -O2 -o "$binary" "$source"
}

check_or_build() {
    name=$1
    binary=$2
    build_kind=$3
    source=$4
    shift 4

    if needs_rebuild "$binary" "$source" "$@"; then
        if [ "$mode" = "check" ]; then
            if [ ! -e "$binary" ]; then
                log "[sim-build:missing] $name -> $binary"
            else
                log "[sim-build:stale] $name -> $binary"
            fi
            status=1
            return
        fi
        if [ "$build_kind" = "sdl" ]; then
            compile_sdl "$binary" "$source" || status=1
        else
            compile_plain "$binary" "$source" || status=1
        fi
    else
        log "[sim-build:ok] $name"
    fi
}

build_viewer() {
    check_or_build \
        "viewer" \
        "$sim_dir/viewer/sdl_fb_viewer" \
        "sdl" \
        "$sim_dir/viewer/sdl_fb_viewer.c"
}

build_audio_player() {
    check_or_build \
        "audio-player" \
        "$sim_dir/audio/sdl_audio_player" \
        "sdl" \
        "$sim_dir/audio/sdl_audio_player.c" \
        "$root_dir"/src/MicroPython/audio/minimp3/*.h
}

build_radio_player() {
    check_or_build \
        "radio-player" \
        "$sim_dir/audio/sdl_radio_player" \
        "sdl" \
        "$sim_dir/audio/sdl_radio_player.c" \
        "$root_dir"/src/MicroPython/audio/minimp3/*.h
}

build_frame_sidecar() {
    check_or_build \
        "frame-sidecar" \
        "$sim_dir/native/sim_frame_sidecar" \
        "plain" \
        "$sim_dir/native/sim_frame_sidecar.c"
}

review_inputs() {
    cat <<EOF
src/MicroPython/audio/audio.c
src/MicroPython/audio/audio.h
src/MicroPython/audio/audio_mp.c
src/MicroPython/audio/audio_mp.h
EOF
}

write_review_baseline() {
    tmp="$baseline_file.tmp"
    : > "$tmp" || die "could not write $tmp"
    review_inputs | while IFS= read -r rel; do
        file="$root_dir/$rel"
        if [ -e "$file" ]; then
            mtime=$(stat -c %Y "$file" 2>/dev/null || printf '0')
            set -- $(cksum "$file")
            printf '%s %s %s %s\n' "$mtime" "$1" "$2" "$rel" >> "$tmp"
        fi
    done
    mv "$tmp" "$baseline_file"
    log "[sim-build] updated native review baseline: $baseline_file"
}

baseline_has_line() {
    line=$1
    grep -F -x "$line" "$baseline_file" >/dev/null 2>&1
}

check_review_inputs() {
    needs_review=0
    if [ ! -e "$baseline_file" ]; then
        log "[sim-build:review-needed] native review baseline missing; run sh sim_mp/build.sh after initial verification"
        review_status=1
        return
    fi
    while IFS= read -r rel; do
        file="$root_dir/$rel"
        if [ ! -e "$file" ]; then
            continue
        fi
        mtime=$(stat -c %Y "$file" 2>/dev/null || printf '0')
        set -- $(cksum "$file")
        line="$mtime $1 $2 $rel"
        if ! baseline_has_line "$line"; then
            log "[sim-build:review-needed] $rel changed; verify simulator audio shim/sidecars"
            needs_review=1
        fi
    done <<EOF
$(review_inputs)
EOF
    if [ "$needs_review" -ne 0 ]; then
        review_status=1
    fi
}

target_needs_audio_review() {
    case "$1" in
        all|audio|audio-player|radio-player) return 0 ;;
        *) return 1 ;;
    esac
}

run_target() {
    case "$1" in
        all)
            build_viewer
            build_audio_player
            build_radio_player
            build_frame_sidecar
            ;;
        viewer)
            build_viewer
            ;;
        audio)
            build_audio_player
            build_radio_player
            ;;
        audio-player)
            build_audio_player
            ;;
        radio-player)
            build_radio_player
            ;;
        frame-sidecar)
            build_frame_sidecar
            ;;
        *)
            usage
            die "unknown sim native build target: $1"
            ;;
    esac
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --force)
            force=1
            ;;
        --clean)
            mode=clean
            ;;
        --check)
            mode=check
            ;;
        --update-baseline)
            update_baseline=1
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --*)
            usage
            die "unknown option: $1"
            ;;
        *)
            targets="${targets}${targets:+ }$1"
            ;;
    esac
    shift
done

if [ -z "$targets" ]; then
    targets=all
fi

if [ "$mode" = "clean" ]; then
    rm -f \
        "$sim_dir/viewer/sdl_fb_viewer" \
        "$sim_dir/audio/sdl_audio_player" \
        "$sim_dir/audio/sdl_radio_player" \
        "$sim_dir/native/sim_frame_sidecar"
    log "[sim-build] removed simulator native binaries"
    exit 0
fi

if [ "$update_baseline" -eq 1 ]; then
    write_review_baseline
fi

for target in $targets; do
    run_target "$target"
done

review_requested=0
for target in $targets; do
    if target_needs_audio_review "$target"; then
        review_requested=1
        break
    fi
done

if [ "$review_requested" -eq 1 ]; then
    if [ ! -e "$baseline_file" ] && [ "$mode" != "check" ]; then
        write_review_baseline
    else
        check_review_inputs
    fi
fi

if [ "$mode" = "check" ] && [ "$review_status" -ne 0 ]; then
    status=1
fi

if [ "$review_status" -ne 0 ] && [ "$mode" != "check" ]; then
    log "[sim-build] native review is pending; after verifying simulator behavior, run: sh sim_mp/build.sh --update-baseline"
fi

exit "$status"
