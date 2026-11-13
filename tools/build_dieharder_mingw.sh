#!/usr/bin/env bash
# Build a native Windows dieharder.exe (Dieharder 3.31.1 + GSL 2.8, statically linked)
# with MinGW-w64 gcc, without autotools and without installing anything system-wide.
#
#   bash tools/build_dieharder_mingw.sh [TOOLS_DIR]      # default: $HQRNG_TOOLS or ./third_party
#   -> TOOLS_DIR/bin/dieharder.exe
#
# Needs: gcc (MinGW-w64), curl, tar, zstd (all in MSYS2 / Git-Bash + MSYS2 mingw64).
# Source changes are minimal: fopen(..., "r") -> "rb" so Windows does not translate
# CR/LF bytes or stop at 0x1A in binary input, a `uint` typedef, and -fcommon for GCC >= 10.
# On Linux just use `apt install dieharder`.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TOOLS="${1:-${HQRNG_TOOLS:-$HERE/../third_party}}"
mkdir -p "$TOOLS/bin" "$TOOLS/downloads"
TOOLS="$(cd "$TOOLS" && pwd)"
B="$TOOLS/dieharder-build"
rm -rf "$B" && mkdir -p "$B/cfg" "$B/obj" "$B/gsl"

fetch() { [ -s "$2" ] || curl -fsSL --retry 3 -o "$2" "$1"; }
fetch https://webhome.phy.duke.edu/~rgb/General/dieharder/dieharder-3.31.1.tgz "$TOOLS/downloads/dieharder-3.31.1.tgz"
fetch https://repo.msys2.org/mingw/mingw64/mingw-w64-x86_64-gsl-2.8-1-any.pkg.tar.zst "$TOOLS/downloads/gsl-2.8.pkg.tar.zst"

# the tarball contains m4 symlinks to /usr/share/aclocal that cannot be created on Windows; they are not needed
tar -xzf "$TOOLS/downloads/dieharder-3.31.1.tgz" -C "$B" --exclude='*/m4/*'
zstd -dc "$TOOLS/downloads/gsl-2.8.pkg.tar.zst" | tar -x -C "$B/gsl"
SRC="$B/dieharder-3.31.1"

for f in random_seed.c rng_dev_arandom.c rng_dev_random.c rng_dev_urandom.c rng_file_input_raw.c; do
  sed -i 's/,"r")/,"rb")/' "$SRC/libdieharder/$f"
done

cat > "$B/cfg/compat.h" <<'EOF'
#ifndef DH_COMPAT_H
#define DH_COMPAT_H
typedef unsigned int uint;
#endif
EOF
cat > "$B/cfg/config.h" <<'EOF'
#define HAVE_INTTYPES_H 1
#define HAVE_LIBGSL 1
#define HAVE_LIBGSLCBLAS 1
#define HAVE_STDINT_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRING_H 1
#define HAVE_STRINGS_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_UNISTD_H 1
#define PACKAGE "dieharder"
#define PACKAGE_NAME "dieharder"
#define PACKAGE_VERSION "3.31.1"
#define STDC_HEADERS 1
EOF

CF="-std=gnu99 -O2 -w -fcommon -DVERSION=3.31.1 -DLITTLE_ENDIAN=1 -D_USE_MATH_DEFINES -D_FILE_OFFSET_BITS=64
    -I$B/cfg -I$SRC/include -I$B/gsl/mingw64/include -include $B/cfg/compat.h"
LIBSRC="$(sed -n '/^libdieharder_la_SOURCES/,/^$/p' "$SRC/libdieharder/Makefile.am" | grep -o '[A-Za-z0-9_-]*\.c' | grep -v '^rng_jenkins.c$')"
APPSRC="$(sed -n '/^dieharder_SOURCES/,/^$/p' "$SRC/dieharder/Makefile.am" | grep -o '[A-Za-z0-9_-]*\.c')"
for f in $LIBSRC; do gcc $CF -c "$SRC/libdieharder/$f" -o "$B/obj/lib_${f%.c}.o"; done
for f in $APPSRC; do gcc $CF -I"$SRC/dieharder" -c "$SRC/dieharder/$f" -o "$B/obj/app_${f%.c}.o"; done
gcc -static -o "$TOOLS/bin/dieharder.exe" "$B"/obj/*.o -L"$B/gsl/mingw64/lib" -lgsl -lgslcblas -lws2_32 -lm
"$TOOLS/bin/dieharder.exe" -l | head -8
echo "built $TOOLS/bin/dieharder.exe"
