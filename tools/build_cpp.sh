#!/usr/bin/env bash
# Build a C++ bot.
#   Usage (from the participant_kit folder):
#       ./tools/build_cpp.sh templates/cpp/my_bot.cpp            -> creates ./templates/cpp/my_bot
#       ./tools/build_cpp.sh my_bot.cpp my_output_name           -> custom output name
#
# Works with g++ (version 9 or newer) or clang++ (version 10 or newer).

set -e

SOURCE="$1"
if [ -z "$SOURCE" ]; then
    echo "Usage: ./tools/build_cpp.sh <source.cpp> [output_name]"
    exit 1
fi

case "$SOURCE" in
    *.cpp) ;;
    *) echo "The source file must end with .cpp (you gave: $SOURCE)"; exit 1 ;;
esac

OUTPUT="${2:-${SOURCE%.cpp}}"
KIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if command -v g++ >/dev/null 2>&1; then
    COMPILER=g++
elif command -v clang++ >/dev/null 2>&1; then
    COMPILER=clang++
else
    echo "No C++ compiler found. Install g++ (Linux: sudo apt install g++ | macOS: xcode-select --install)."
    exit 1
fi

echo "Compiling $SOURCE with $COMPILER ..."
"$COMPILER" -std=c++17 -O2 -Wall -Wextra -I "$KIT_DIR/third_party" "$SOURCE" -o "$OUTPUT"
echo "Done. Run it with:  $OUTPUT"
