#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
picoware_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)

micropython_dir=${MICROPYTHON_DIR:-}
if [ -z "$micropython_dir" ]; then
    for candidate in \
        "$HOME/pico/micropython" \
        "$HOME/Picocalc_programming/micropython" \
        "$picoware_dir/../micropython"
    do
        if [ -f "$candidate/ports/unix/Makefile" ]; then
            micropython_dir=$candidate
            break
        fi
    done
fi

if [ -z "$micropython_dir" ] || [ ! -f "$micropython_dir/ports/unix/Makefile" ]; then
    echo "MicroPython Unix source tree not found." >&2
    echo "Set MICROPYTHON_DIR to a MicroPython checkout." >&2
    exit 1
fi

source_alias=${PICOWARE_DESKTOP_SOURCE_ALIAS:-"/tmp/picoware-desktop-src-$(id -u)"}
if [ -L "$source_alias" ]; then
    alias_target=$(CDPATH= cd -- "$source_alias" && pwd -P)
    if [ "$alias_target" != "$picoware_dir" ]; then
        echo "Desktop source alias points to another checkout: $source_alias" >&2
        echo "Remove it or set PICOWARE_DESKTOP_SOURCE_ALIAS." >&2
        exit 1
    fi
elif [ -e "$source_alias" ]; then
    echo "Desktop source alias exists and is not a symlink: $source_alias" >&2
    echo "Set PICOWARE_DESKTOP_SOURCE_ALIAS to an unused path." >&2
    exit 1
else
    ln -s "$picoware_dir" "$source_alias"
fi

if [ -n "${PICOWARE_DESKTOP_BUILD_DIR:-}" ]; then
    build_dir=$PICOWARE_DESKTOP_BUILD_DIR
    display_build_dir=$build_dir
else
    build_dir="$source_alias/builds/MicroPython/desktop"
    display_build_dir="$picoware_dir/builds/MicroPython/desktop"
fi
module_dir="$source_alias/src/MicroPython/Desktop/modules"
variant_dir="$source_alias/src/MicroPython/Desktop/variant"
native_check='import auto_complete, c, font, mjs, mmbasic, picoware_desktop, response, vector, video; expected = ("auto_complete", "c", "font", "mjs", "mmbasic", "response", "video", "vector"); assert picoware_desktop.BOARD_ID == 15; assert picoware_desktop.native_modules() == expected; print("[desktop-build:ok] native modules", expected)'
jobs=${PICOWARE_BUILD_JOBS:-}
if [ -z "$jobs" ]; then
    if command -v getconf >/dev/null 2>&1; then
        jobs=$(getconf _NPROCESSORS_ONLN 2>/dev/null || true)
    fi
    jobs=${jobs:-2}
fi

case ${1:-build} in
    --clean|clean)
        make -C "$micropython_dir/ports/unix" \
            BUILD="$build_dir" \
            VARIANT_DIR="$variant_dir" \
            USER_C_MODULES="$module_dir" \
            FROZEN_MANIFEST= \
            CFLAGS_EXTRA="-DDESKTOP -Wno-error" \
            clean
        exit 0
        ;;
    --check|check)
        if [ ! -x "$build_dir/micropython" ]; then
            echo "Desktop MicroPython is not built: $build_dir/micropython" >&2
            exit 1
        fi
        "$build_dir/micropython" -c "$native_check"
        exit 0
        ;;
    build|"")
        ;;
    *)
        echo "usage: sh tools/micropython-desktop.sh [build|check|clean]" >&2
        exit 2
        ;;
esac

mkdir -p "$build_dir"

# remove stale user-module build outputs
for mkfile in "$module_dir"/*/micropython.mk; do
    [ -f "$mkfile" ] || continue
    rm -rf "$build_dir/$(basename "$(dirname "$mkfile")")"
done
# remove normalized paths from relative module sources
rm -rf "$source_alias/builds/c"
# sweep leftover module build dirs
for dir in "$build_dir"/*/; do
    [ -d "$dir" ] || continue
    case "$(basename "$dir")" in
        py|extmod|lib|shared|genhdr) ;;
        *) rm -rf "$dir" ;;
    esac
done

if [ ! -x "$micropython_dir/mpy-cross/build/mpy-cross" ]; then
    make -C "$micropython_dir/mpy-cross" -j"$jobs"
fi

make -C "$micropython_dir/ports/unix" \
    -j"$jobs" \
    BUILD="$build_dir" \
    VARIANT_DIR="$variant_dir" \
    USER_C_MODULES="$module_dir" \
    FROZEN_MANIFEST= \
    CFLAGS_EXTRA="-DDESKTOP -Wno-error"

"$build_dir/micropython" -c "$native_check"

echo "Desktop MicroPython build complete: $display_build_dir/micropython"
