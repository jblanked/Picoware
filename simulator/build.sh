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
usage: sh simulator/build.sh [--force] [--clean] [--check] [target...]

targets:
  all              build/check every simulator native helper
  viewer           simulator/viewer/sdl_fb_viewer
  audio            both local audio and radio audio sidecars
  audio-player     simulator/audio/sdl_audio_player
  radio-player     simulator/audio/sdl_radio_player
  jpeg             simulator/jpeg/sim_jpeg_decode
  gameboy          simulator/gameboy/sim_gameboy_runner
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

# Check whether a dylib/framework contains the given architecture.
# Usage: _dylib_has_arch <path-to-dylib> <arch>
_dylib_has_arch() {
    [ -f "$1" ] || return 1
    # lipo is macOS only; skip architecture check on other platforms
    if [ "$(uname -s)" != "Darwin" ]; then
        return 0
    fi
    lipo -info "$1" 2>/dev/null | grep -q "$2"
}

_discover_sdl2() {
    if [ -n "$SDL2_CFLAGS" ]; then
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

    # 1. macOS Homebrew
    if [ "$_os" = "Darwin" ]; then
        # Check both Homebrew prefixes
        for _brew_prefix in "/opt/homebrew" "/usr/local"; do
            if [ -d "$_brew_prefix/opt/sdl2" ]; then
                _try_sdl2 "$_brew_prefix/opt/sdl2/include" "$_brew_prefix/opt/sdl2/lib" && return 0
            fi
            if [ -d "$_brew_prefix/include/SDL2" ]; then
                _try_sdl2 "$_brew_prefix/include" "$_brew_prefix/lib" && return 0
            fi
        done
    fi

    # 2. pkg-config
    # Prefer /opt/homebrew on Apple Silicon
    if [ "$_os" = "Darwin" ] && [ "$_arch" = "arm64" ]; then
        export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
    fi

    if command -v pkg-config >/dev/null 2>&1 && pkg-config --exists sdl2 2>/dev/null; then
        _pc_inc=$(pkg-config --variable=includedir sdl2 2>/dev/null)
        _pc_lib=$(pkg-config --variable=libdir sdl2 2>/dev/null)
        [ -z "$_pc_inc" ] && _pc_inc="$(pkg-config --variable=prefix sdl2 2>/dev/null)/include"
        [ -z "$_pc_lib" ] && _pc_lib="$(pkg-config --variable=prefix sdl2 2>/dev/null)/lib"
        _try_sdl2 "$_pc_inc" "$_pc_lib" && return 0
    fi

    # 3. sdl2-config fallback
    if command -v sdl2-config >/dev/null 2>&1; then
        _sc_prefix=$(sdl2-config --prefix 2>/dev/null)
        _sc_inc="${_sc_prefix}/include"
        _sc_lib=$(sdl2-config --libdir 2>/dev/null)
        [ -z "$_sc_lib" ] && _sc_lib="${_sc_prefix}/lib"
        _try_sdl2 "$_sc_inc" "$_sc_lib" && return 0
    fi

    # 4. Common Linux paths (including multiarch)
    # Auto-detect the system's multiarch tuple (e.g. aarch64-linux-gnu, x86_64-linux-gnu)
    _multiarch=""
    if command -v gcc >/dev/null 2>&1; then
        _multiarch=$(gcc -print-multiarch 2>/dev/null)
    fi
    if [ -z "$_multiarch" ] && command -v dpkg-architecture >/dev/null 2>&1; then
        _multiarch=$(dpkg-architecture -qDEB_HOST_MULTIARCH 2>/dev/null)
    fi

    for _sys_prefix in "/usr" "/usr/local"; do
        _try_sdl2 "$_sys_prefix/include" "$_sys_prefix/lib" && return 0
        _try_sdl2 "$_sys_prefix/include/SDL2" "$_sys_prefix/lib" && return 0
        # try detected multiarch path first
        if [ -n "$_multiarch" ]; then
            _try_sdl2 "$_sys_prefix/include" "$_sys_prefix/lib/$_multiarch" && return 0
            _try_sdl2 "$_sys_prefix/include/SDL2" "$_sys_prefix/lib/$_multiarch" && return 0
        fi
        # fallback: common multiarch paths
        for _ma in x86_64-linux-gnu aarch64-linux-gnu arm-linux-gnueabihf; do
            _try_sdl2 "$_sys_prefix/include" "$_sys_prefix/lib/$_ma" && return 0
            _try_sdl2 "$_sys_prefix/include/SDL2" "$_sys_prefix/lib/$_ma" && return 0
        done
    done

    return 1
}

require_sdl2() {
    if _discover_sdl2; then
        return 0
    fi
    cat >&2 <<'EOF'
SDL2 development files not found.
  macOS:            brew install sdl2
  Debian/Ubuntu:    sudo apt install libsdl2-dev
  Fedora:           sudo dnf install SDL2-devel
  Arch:             sudo pacman -S sdl2
  MSYS2:            pacman -S mingw-w64-x86_64-SDL2

If you're on Apple Silicon and only have x86_64 SDL2 (Rosetta Homebrew),
the script will automatically build x86_64 binaries that run under Rosetta 2.
For native arm64 builds, install SDL2 via native Homebrew at /opt/homebrew.
EOF
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

compile_cxx() {
    binary=$1
    source=$2
    shift 2
    log "[sim-build] c++ $binary"
    c++ -O2 -D__LINUX__ -o "$binary" "$source" "$@"
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
        elif [ "$build_kind" = "cxx" ]; then
            compile_cxx "$binary" "$source" "$@" || status=1
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
        "$sim_dir/audio/sdl_radio_player.c"
}

build_jpeg() {
    check_or_build \
        "jpeg" \
        "$sim_dir/jpeg/sim_jpeg_decode" \
        "cxx" \
        "$sim_dir/jpeg/sim_jpeg_decode.cpp" \
        "$root_dir/src/MicroPython/JPEGDEC/src/JPEGDEC.cpp"
}

build_gameboy() {
    check_or_build \
        "gameboy" \
        "$sim_dir/gameboy/sim_gameboy_runner" \
        "sdl" \
        "$sim_dir/gameboy/sim_gameboy_runner.c" \
        "$root_dir/src/MicroPython/gameboy/PicoCalc-GameBoy/ext/Walnut-CGB/walnut_cgb.h" \
        "$root_dir/src/MicroPython/gameboy/PicoCalc-GameBoy/ext/minigb_apu/minigb_apu.c" \
        "$root_dir/src/MicroPython/gameboy/PicoCalc-GameBoy/ext/minigb_apu/minigb_apu.h"
}

run_target() {
    case "$1" in
        all)
            build_viewer
            build_audio_player
            build_radio_player
            build_jpeg
            build_gameboy
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
        jpeg)
            build_jpeg
            ;;
        gameboy)
            build_gameboy
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
        "$sim_dir/audio/sdl_radio_player" \
        "$sim_dir/jpeg/sim_jpeg_decode" \
        "$sim_dir/gameboy/sim_gameboy_runner"
    log "[sim-build] removed simulator native binaries"
    exit 0
fi

for target in $targets; do
    run_target "$target"
done

exit "$status"
