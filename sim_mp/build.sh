#!/bin/sh
set -u

sim_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root_dir=$(CDPATH= cd -- "$sim_dir/.." && pwd)

mode=build
force=0
targets=""
status=0

usage() {
    cat <<EOF
usage: sh sim_mp/build.sh [--force] [--clean] [--check] [target...]

targets:
  all              build/check every simulator native helper
  viewer           sim_mp/viewer/sdl_fb_viewer
  audio            both local audio and radio audio sidecars
  audio-player     sim_mp/audio/sdl_audio_player
  radio-player     sim_mp/audio/sdl_radio_player
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

# SDL2 discovery (cached)
SDL2_CFLAGS=""
SDL2_LIBS=""
SDL2_ARCH_FLAGS=""
SDL2_DISCOVERY_NOTES=""

# Check whether a dylib/framework contains the given architecture.
# Usage: _dylib_has_arch <path-to-dylib> <arch>
_dylib_has_arch() {
    [ -f "$1" ] || return 1
    lipo -info "$1" 2>/dev/null | grep -q "$2"
}

_note_sdl2() {
    SDL2_DISCOVERY_NOTES="${SDL2_DISCOVERY_NOTES}${SDL2_DISCOVERY_NOTES:+
}$*"
}

_set_sdl2_flags() {
    # $1 = source label, $2 = cflags, $3 = libs
    _source=$1
    SDL2_CFLAGS=$2
    SDL2_LIBS=$3
    _note_sdl2 "$_source cflags: $SDL2_CFLAGS"
    _note_sdl2 "$_source libs: $SDL2_LIBS"
    return 0
}

_discover_sdl2() {
    if [ -n "$SDL2_LIBS" ]; then
        return 0
    fi

    _os=$(uname -s)
    _arch=$(uname -m)

    # Try candidate SDL2 installation
    _try_sdl2() {
        # $1 = include dir, $2 = lib dir
        _inc=$1
        _libdir=$2

        [ -d "$_inc" ] || return 1
        # accept SDL2/SDL.h style
        if [ -f "$_inc/SDL.h" ]; then
            SDL2_CFLAGS="-D_THREAD_SAFE -I${_inc}"
        elif [ -f "$_inc/SDL2/SDL.h" ]; then
            SDL2_CFLAGS="-D_THREAD_SAFE -I${_inc}/SDL2"
        else
            return 1
        fi

        # locate the shared library
        _dylib=""
        for _cand in \
            "$_libdir/libSDL2.dylib" \
            "$_libdir/libSDL2.so" \
            "$_libdir/libSDL2-2.0.so" \
            "$_libdir/libSDL2.dll.a" \
        ; do
            if [ -f "$_cand" ]; then
                _dylib=$_cand
                break
            fi
        done

        # Also accept .framework on macOS
        if [ -z "$_dylib" ] && [ "$_os" = "Darwin" ]; then
            for _fw in "$_libdir/SDL2.framework/SDL2" "$_inc/../SDL2.framework/SDL2"; do
                if [ -f "$_fw" ]; then
                    _dylib=$_fw
                    SDL2_CFLAGS="-D_THREAD_SAFE -F${_libdir} -I${_libdir}/SDL2.framework/Headers"
                    SDL2_LIBS="-F${_libdir} -framework SDL2"
                    return 0   # frameworks are typically fat — trust them
                fi
            done
        fi

        if [ -z "$_dylib" ]; then
            return 1
        fi

        SDL2_LIBS="-L${_libdir} -lSDL2"

        # Linux and other non-macOS platforms do not use lipo. If the
        # headers and library were found, let the compiler/linker validate it.
        if [ "$_os" != "Darwin" ]; then
            return 0
        fi

        # Architecture check
        if _dylib_has_arch "$_dylib" "$_arch"; then
            return 0
        fi

        # Cross-compile x86_64 on arm64
        if [ "$_os" = "Darwin" ] && [ "$_arch" = "arm64" ] && _dylib_has_arch "$_dylib" "x86_64"; then
            SDL2_ARCH_FLAGS="-arch x86_64"
            log "[sim-build] SDL2 is x86_64 — building for x86_64 (runs under Rosetta 2)"
            return 0
        fi

        # Mismatch we cannot resolve → clear and fall through
        SDL2_CFLAGS=""
        SDL2_LIBS=""
        return 1
    }

    # Prefer /opt/homebrew on Apple Silicon when pkg-config is used.
    if [ "$_os" = "Darwin" ] && [ "$_arch" = "arm64" ]; then
        export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
    fi

    # 1. pkg-config. This is the most reliable path on Linux multiarch
    # installs and also works for most Homebrew installs.
    if command -v pkg-config >/dev/null 2>&1; then
        if pkg-config --exists sdl2 2>/dev/null; then
            _pc_cflags=$(pkg-config --cflags sdl2 2>/dev/null)
            _pc_libs=$(pkg-config --libs sdl2 2>/dev/null)
            if [ -n "$_pc_libs" ]; then
                if [ "$_os" = "Darwin" ]; then
                    _pc_inc=$(pkg-config --variable=includedir sdl2 2>/dev/null)
                    _pc_lib=$(pkg-config --variable=libdir sdl2 2>/dev/null)
                    _note_sdl2 "pkg-config cflags: $_pc_cflags"
                    _note_sdl2 "pkg-config libs: $_pc_libs"
                    if [ -n "$_pc_inc" ] && [ -n "$_pc_lib" ]; then
                        _try_sdl2 "$_pc_inc" "$_pc_lib" && return 0
                    fi
                    _note_sdl2 "pkg-config sdl2 was not usable for macOS architecture validation"
                else
                    _set_sdl2_flags "pkg-config" "$_pc_cflags" "$_pc_libs" && return 0
                fi
            fi
            _note_sdl2 "pkg-config found sdl2 but returned empty linker flags"
        else
            _note_sdl2 "pkg-config could not find sdl2"
        fi
    else
        _note_sdl2 "pkg-config not found"
    fi

    # 2. sdl2-config fallback.
    if command -v sdl2-config >/dev/null 2>&1; then
        _sc_cflags=$(sdl2-config --cflags 2>/dev/null)
        _sc_libs=$(sdl2-config --libs 2>/dev/null)
        if [ -n "$_sc_libs" ]; then
            if [ "$_os" = "Darwin" ]; then
                _sc_prefix=$(sdl2-config --prefix 2>/dev/null)
                _note_sdl2 "sdl2-config cflags: $_sc_cflags"
                _note_sdl2 "sdl2-config libs: $_sc_libs"
                if [ -n "$_sc_prefix" ]; then
                    _try_sdl2 "$_sc_prefix/include" "$_sc_prefix/lib" && return 0
                fi
                _note_sdl2 "sdl2-config sdl2 was not usable for macOS architecture validation"
            else
                _set_sdl2_flags "sdl2-config" "$_sc_cflags" "$_sc_libs" && return 0
            fi
        fi
        _note_sdl2 "sdl2-config found but returned empty linker flags"
    else
        _note_sdl2 "sdl2-config not found"
    fi

    # 3. macOS Homebrew explicit probes, including Rosetta installs.
    if [ "$_os" = "Darwin" ]; then
        for _brew_prefix in "/opt/homebrew" "/usr/local"; do
            if [ -d "$_brew_prefix/opt/sdl2" ]; then
                _try_sdl2 "$_brew_prefix/opt/sdl2/include" "$_brew_prefix/opt/sdl2/lib" && return 0
            fi
            if [ -d "$_brew_prefix/include/SDL2" ]; then
                _try_sdl2 "$_brew_prefix/include" "$_brew_prefix/lib" && return 0
            fi
        done
    fi

    # 4. Common Linux paths
    for _sys_prefix in "/usr" "/usr/local"; do
        _try_sdl2 "$_sys_prefix/include" "$_sys_prefix/lib" && return 0
        _try_sdl2 "$_sys_prefix/include/SDL2" "$_sys_prefix/lib" && return 0
        # some 64-bit distros
        _try_sdl2 "$_sys_prefix/include" "$_sys_prefix/lib/x86_64-linux-gnu" && return 0
        _try_sdl2 "$_sys_prefix/include/SDL2" "$_sys_prefix/lib/x86_64-linux-gnu" && return 0
    done

    return 1
}

require_sdl2() {
    if _discover_sdl2; then
        return 0
    fi
    cat >&2 <<'EOF'
SDL2 development files not usable.
  macOS:            brew install sdl2
  Debian/Ubuntu:    sudo apt install libsdl2-dev
  Fedora:           sudo dnf install SDL2-devel
  Arch:             sudo pacman -S sdl2
  MSYS2:            pacman -S mingw-w64-x86_64-SDL2

If you're on Apple Silicon and only have x86_64 SDL2 (Rosetta Homebrew),
the script will automatically build x86_64 binaries that run under Rosetta 2.
For native arm64 builds, install SDL2 via native Homebrew at /opt/homebrew.
EOF
    if [ -n "$SDL2_DISCOVERY_NOTES" ]; then
        printf '\nSDL2 discovery notes:\n%s\n' "$SDL2_DISCOVERY_NOTES" >&2
    fi
    exit 2
}

compile_sdl() {
    binary=$1
    source=$2
    require_sdl2
    log "[sim-build] cc $binary"
    cc -O2 $SDL2_ARCH_FLAGS -o "$binary" "$source" $SDL2_CFLAGS $SDL2_LIBS
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

run_target() {
    case "$1" in
        all)
            build_viewer
            build_audio_player
            build_radio_player
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
        "$sim_dir/audio/sdl_radio_player"
    log "[sim-build] removed simulator native binaries"
    exit 0
fi

for target in $targets; do
    run_target "$target"
done

exit "$status"
