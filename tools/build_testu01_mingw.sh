#!/usr/bin/env bash
# Build TestU01 1.2.3 with plain gcc, without autotools.
#
# Linux/macOS users can use the upstream `./configure && make` instead; this
# script exists for Windows (MSYS2 / Git-Bash + MinGW gcc), where autotools
# are usually missing. It also works on Linux.
#
# Usage: tools/build_testu01_mingw.sh <TestU01-1.2.3 source dir>
# Produces: <src>/build/include/*.h and <src>/build/libtestu01.a
set -euo pipefail

SRC="$(cd "$1" && pwd)"
OUT="$SRC/build"
INC="$OUT/include"
mkdir -p "$INC" "$OUT/obj"

# TestU01 headers are generated from its literate .tex sources by `tcode`.
gcc -std=gnu99 -O2 -w -o "$OUT/tcode" "$SRC/mylib/tcode.c"
. <(sed -n '/^MYLIBHEADERS/p;/^PROBDISTHEADERS/p;/^TESTU01HEADERS/p' "$SRC/include/Makefile.def" | sed 's/ = /="/; s/$/"/')
for h in $MYLIBHEADERS;    do "$OUT/tcode" "$SRC/mylib/${h%.h}.tex"    "$INC/$h"; done
for h in $PROBDISTHEADERS; do "$OUT/tcode" "$SRC/probdist/${h%.h}.tex" "$INC/$h"; done
for h in $TESTU01HEADERS;  do "$OUT/tcode" "$SRC/testu01/${h%.h}.tex"  "$INC/$h"; done
cp "$SRC/mylib/num.h" "$INC/" 2>/dev/null || true

# What `configure` would have detected for a C99 compiler (MinGW-w64 or glibc).
cat > "$INC/gdefconf.h" <<'EOF'
#ifndef GDEFCONF_H
#define GDEFCONF_H
#define HAVE_LONG_LONG 1
#define HAVE_ERF 1
#define HAVE_LGAMMA 1
#define HAVE_UNISTD_H 1
#define HAVE_STDINT_H 1
#define HAVE_UINT32_T 1
#define HAVE_UINT8_T 1
#endif
EOF
cat > "$INC/config.h" <<'EOF'
#define HAVE_LONG_LONG 1
#define HAVE_ERF 1
#define HAVE_LGAMMA 1
#define HAVE_LOG1P 1
#define PACKAGE_STRING "TestU01 1.2.3"
#define HAVE_UNISTD_H 1
#define HAVE_STDINT_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRING_H 1
#define HAVE_UINT32_T 1
#define HAVE_UINT8_T 1
EOF
if [ "${OS:-}" = "Windows_NT" ]; then echo '#define HAVE_WINDOWS_H 1' >> "$INC/config.h"; fi

. <(sed -n '/^MYLIBSOURCES/p;/^PROBDISTSOURCES/p;/^TESTU01SOURCES/p' "$SRC/include/Makefile.def" | sed 's/ = /="/; s/$/"/')
objs=()
build() { # dir sources...
  local dir=$1; shift
  for c in "$@"; do
    o="$OUT/obj/${c%.c}.o"
    gcc -std=gnu99 -O2 -w -DHAVE_CONFIG_H -I"$INC" -c "$SRC/$dir/$c" -o "$o"
    objs+=("$o")
  done
}
build mylib $MYLIBSOURCES
build probdist $PROBDISTSOURCES
build testu01 $TESTU01SOURCES
rm -f "$OUT/libtestu01.a"
ar rcs "$OUT/libtestu01.a" "${objs[@]}"
echo "Built $OUT/libtestu01.a (${#objs[@]} objects); headers in $INC"
