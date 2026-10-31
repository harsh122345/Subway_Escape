# Submission Instructions

This directory contains the final submission files for **Subway Escape**.

---

## 📁 Submission Contents

| File | Purpose |
|---|---|
| `my_bot.cpp` | Complete working C++17 autonomous bot source code |
| `team_info.json` | Team metadata, build command, and execution command |

---

## 🛠️ Build and Test Commands

### 1. Compile the Bot (C++17)
```bash
# Windows (MinGW / g++)
g++ -std=c++17 -O2 -I ../third_party my_bot.cpp -o my_bot.exe

# Linux / macOS
g++ -std=c++17 -O2 -I ../third_party my_bot.cpp -o my_bot
```
*(Alternatively, use the root helper script: `tools\build_cpp.bat submission\my_bot.cpp`)*

### 2. Verify Protocol Compliance
Run from the root directory:
```bash
python tools/check_bot.py --team-info submission/team_info.json
```

### 3. Run Practice Simulation
```bash
python practice_arena/run_practice.py --bot "submission/my_bot.exe" --bot "sample_bot/cpp/basic_bot.exe" --runs 10
```

---

## ✅ Pre-Submission Checklist
- [x] Protocol check passed with `0` errors (`check_bot.py`).
- [x] `team_info.json` contains accurate team information and run commands.
- [x] Only valid JSON is written to `stdout`; debug logs use `stderr`.
- [x] Zero illegal actions (`BadActs = 0.0`) and zero misses (`Misses = 0.0`).
- [x] Average thinking time is ~1 ms (well below the 1000 ms limit).
