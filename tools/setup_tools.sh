#!/usr/bin/env bash
# Download and build the external test suites into $HQRNG_TOOLS (default ./third_party).
#
#   NIST STS 2.1.2  -> $HQRNG_TOOLS/sts/assess
#   TestU01 1.2.3   -> $HQRNG_TOOLS/bin/testu01_file   (our file harness)
#   Dieharder       -> from the OS package manager (Linux/WSL only)
#
# Works on Linux, macOS, and Windows Git-Bash/MSYS2 with MinGW gcc.
# Windows note: keep $HQRNG_TOOLS on a short path (e.g. C:/qrng-tools); gcc and
# Aer both break on paths longer than 260 characters.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TOOLS="${HQRNG_TOOLS:-$HERE/../third_party}"
mkdir -p "$TOOLS/bin" "$TOOLS/downloads"
TOOLS="$(cd "$TOOLS" && pwd)"
EXE=""; LIBS="-lm"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) EXE=".exe"; LIBS="-lm -lws2_32";; esac

fetch() { [ -s "$2" ] || curl -fsSL --retry 3 -o "$2" "$1"; }

# ---- NIST SP 800-22 STS 2.1.2 --------------------------------------------
if [ ! -x "$TOOLS/sts/assess$EXE" ]; then
  fetch https://csrc.nist.gov/CSRC/media/Projects/Random-Bit-Generation/documents/sts-2_1_2.zip \
        "$TOOLS/downloads/sts-2_1_2.zip"
  rm -rf "$TOOLS/downloads/sts" && mkdir -p "$TOOLS/downloads/sts"
  unzip -q "$TOOLS/downloads/sts-2_1_2.zip" -d "$TOOLS/downloads/sts"
  rm -rf "$TOOLS/sts" && mv "$TOOLS/downloads/sts/sts-2.1.2/sts-2.1.2" "$TOOLS/sts"
  rm -rf "$TOOLS/sts/data"            # 40 MB of sample data we don't need
  gcc -O2 -w -I"$TOOLS/sts/include" -o "$TOOLS/sts/assess$EXE" "$TOOLS"/sts/src/*.c -lm
  echo "built $TOOLS/sts/assess$EXE"
fi

# ---- TestU01 1.2.3 + file harness ------------------------------------------
if [ ! -x "$TOOLS/bin/testu01_file$EXE" ]; then
  fetch http://simul.iro.umontreal.ca/testu01/TestU01.zip "$TOOLS/downloads/TestU01.zip"
  rm -rf "$TOOLS/testu01" "$TOOLS/downloads/tu" && mkdir -p "$TOOLS/downloads/tu"
  unzip -q "$TOOLS/downloads/TestU01.zip" -d "$TOOLS/downloads/tu"
  mv "$TOOLS/downloads/tu/TestU01-1.2.3" "$TOOLS/testu01"
  bash "$HERE/build_testu01_mingw.sh" "$TOOLS/testu01"
  gcc -std=gnu99 -O2 -w -I"$TOOLS/testu01/build/include" "$HERE/testu01_file.c" \
      "$TOOLS/testu01/build/libtestu01.a" $LIBS -o "$TOOLS/bin/testu01_file$EXE"
  echo "built $TOOLS/bin/testu01_file$EXE"
fi

# ---- Dieharder ---------------------------------------------------------------
if command -v dieharder >/dev/null 2>&1; then
  echo "dieharder: $(command -v dieharder)"
else
  echo "dieharder not found. Linux/WSL: sudo apt-get install -y dieharder (no native Windows build)."
fi
echo "Tools ready in $TOOLS. Export HQRNG_TOOLS=$TOOLS if that is not ./third_party."
