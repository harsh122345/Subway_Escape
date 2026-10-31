# 03 · How to Run and Test

This guide takes you from "nothing installed" to "my bot is playing a match". It covers
**Windows, Linux and macOS**, **Python** and **C++**.

> Run every command from inside the **`participant_kit`** folder unless stated otherwise.

---

## 1. What you need

| Tool | Supported versions | Needed for |
|------|-------------------|------------|
| **Python** | 3.8 or newer (tested on 3.12). Python 3 only, not Python 2. | the practice arena (always), and Python bots |
| **C++ compiler** | must support **C++17**: g++ 9+, clang++ 10+, or MSVC 2019+ | C++ bots only |

No extra Python packages are needed. The practice arena, the checker and the Python templates use only the standard library.
The C++ JSON library (`json.hpp`) is already included in `third_party/`.

### Check what you have

```bash
python --version        # or: python3 --version   (Windows: py --version)
g++ --version           # or: clang++ --version
```

### Installing the tools

**Windows**
- Python: download from <https://www.python.org/downloads/> and tick **"Add python.exe to PATH"** during installation.
- C++ (choose one):
  - **MSYS2 / MinGW-w64 g++** - install MSYS2 from <https://www.msys2.org/>, then in the MSYS2 UCRT64 terminal run
    `pacman -S mingw-w64-ucrt-x86_64-gcc`, and add `C:\msys64\ucrt64\bin` to your PATH.
  - **Visual Studio Build Tools** (MSVC) - install the "Desktop development with C++" workload, then use
    the **"x64 Native Tools Command Prompt for VS"** to run the build script.

**Linux (Ubuntu / Debian)**
```bash
sudo apt update
sudo apt install python3 g++
```

**macOS**
```bash
xcode-select --install        # gives you clang++ (works as the C++ compiler)
# Python: https://www.python.org/downloads/  or  brew install python
```

---

## 2. The five-minute quick start

Use the sample bot to see everything working before you write any code.

```bash
python practice_arena/run_practice.py --bot "{python} sample_bot/python/basic_bot.py"
```

> **About `python`:** the name differs between systems (`python`, `python3`, or `py` on Windows).
> Inside `--bot "..."` you can always write **`{python}`**: it is replaced by the Python you are running
> the command with. So the same line works everywhere. Use your own name (`python3 practice_arena/...`) for the first word.

You will see a results table with the score, how many drops were collected, how often the bot was
caught, and how long it thinks per tick.

---

## 3. Running a Python bot

1. Copy the template and edit it:
   ```bash
   # Linux / macOS
   cp templates/python/my_bot.py submission/my_bot.py
   # Windows (cmd / PowerShell)
   copy templates\python\my_bot.py submission\my_bot.py
   ```
2. Write your strategy inside `decide_for_runner`.
3. Check that it speaks the protocol:
   ```bash
   python tools/check_bot.py --bot "{python} submission/my_bot.py"
   ```
4. Play it:
   ```bash
   python practice_arena/run_practice.py --bot "{python} submission/my_bot.py"
   ```

---

## 4. Running a C++ bot

1. Copy the template and edit it:
   ```bash
   # Linux / macOS
   cp templates/cpp/my_bot.cpp submission/my_bot.cpp
   # Windows
   copy templates\cpp\my_bot.cpp submission\my_bot.cpp
   ```
2. Write your strategy inside `decideForRunner`.
3. **Build** it:

   | System | Command |
   |--------|---------|
   | Linux / macOS | `./tools/build_cpp.sh submission/my_bot.cpp` |
   | Windows (g++ or MSVC) | `tools\build_cpp.bat submission\my_bot.cpp` |

   On Linux / macOS, if you get "permission denied", run `chmod +x tools/build_cpp.sh` once.

   <details>
   <summary>Building by hand (without the scripts)</summary>

   ```bash
   # g++ or clang++ (Linux / macOS / MinGW)
   g++ -std=c++17 -O2 -I third_party submission/my_bot.cpp -o submission/my_bot

   # MSVC (x64 Native Tools Command Prompt)
   cl /std:c++17 /O2 /EHsc /I third_party submission\my_bot.cpp /Fe:submission\my_bot.exe
   ```
   Always compile with `-O2` (or `/O2`). An unoptimised build can be several times slower.
   </details>

4. Check and play it:
   ```bash
   # Linux / macOS
   python tools/check_bot.py --bot "./submission/my_bot"
   python practice_arena/run_practice.py --bot "./submission/my_bot"

   # Windows
   python tools\check_bot.py --bot "submission\my_bot.exe"
   python practice_arena\run_practice.py --bot "submission\my_bot.exe"
   ```

---

## 5. Comparing with the sample bot

The sample bot (`sample_bot/`) is a simple baseline. If your bot cannot beat it, your strategy needs work.
Put both bots in **the same match** and run **many maps** so luck averages out:

```bash
# Python vs Python sample, 10 different maps
python practice_arena/run_practice.py \
    --bot "{python} submission/my_bot.py" \
    --bot "{python} sample_bot/python/basic_bot.py" \
    --runs 10
```

Line-continuation characters differ by shell: `\` for bash/zsh, `` ` `` for PowerShell, `^` for cmd.
Or just put everything on one line.

A C++ bot against a compiled C++ sample (build the sample first with the build script):

```bash
./tools/build_cpp.sh sample_bot/cpp/basic_bot.cpp
python practice_arena/run_practice.py --bot "./submission/my_bot" --bot "./sample_bot/cpp/basic_bot" --runs 10
```

You can mix languages, and you can add as many `--bot` options as you like. Bots are numbered in the order given.

> Bots in one match compete for the same drops, so a bot can lose a drop to its opponent. The numbers you see are
> therefore relative. For a "clean" score of one bot alone, run it **alone**.

### All options of `run_practice.py`

| Option | Meaning | Default |
|--------|---------|---------|
| `--bot "COMMAND"` | start a bot with this command (repeat for more bots) | required |
| `--runs N` | number of matches, each on a different map | 1 |
| `--seed S` | first map seed (use the same seed to repeat the same maps) | 1 |
| `--ticks T` | ticks per match | 300 |
| `--verbose` | print what happens each tick (collects, deposits, captures, illegal moves) | off |
| `--log-dir DIR` | where your bot's stderr logs are saved | `practice_logs` |

---

## 6. Reading the results table

```
Bot             Score   Collected  Deposits  Caught  LootLost  BadActs  Misses  AvgMs  MaxMs
1:my_bot.py     18,682  55.0       39.0      0.2     100       0.0      0.0     0.6    55
```

| Column | Meaning | What to look for |
|--------|---------|------------------|
| **Score** | Money deposited (average per match) | Higher is better. This is what counts. |
| **Collected** | Drops picked up | Many collects but low score → you collect but do not deposit |
| **Deposits** | Successful deposits | Few deposits with big loads is risky; many tiny ones waste time |
| **Caught** | Times caught by police | Should be low |
| **LootLost** | Money wiped by captures | The price of being caught |
| **BadActs** | Illegal actions (ignored by the engine) | **Should be 0.** Each one is a wasted tick. |
| **Misses** | Ticks with no valid / in-time answer | **Must be 0.** Three in a row = disqualified. |
| **AvgMs / MaxMs** | Your thinking time per tick | **MaxMs must stay far below 1000** |

Use `--verbose` to see *why* a number looks the way it does.

---

## 7. Where do my debug prints go?

- Anything written to **stderr** is saved in `practice_logs/bot<N>_seed<S>_stderr.log`.
- Anything written to **stdout** is treated as your answer. Printing extra text there breaks your bot.

Python: `log("my message")`   ·   C++: `log("my message");`

---

## 8. Other languages (Java and friends)

The protocol is just "one JSON line in, one JSON line out". Any language that can read standard input and write standard output works,
and the practice arena accepts any start command, for example:

```bash
python practice_arena/run_practice.py --bot "java -cp mybot MyBot"
```

Official starter wrappers for C++, Python and Java are shared by the organisers in the WhatsApp group.

---

## 9. Troubleshooting

| Problem | Likely cause and fix |
|---------|----------------------|
| `Could not start bot ... No such file or directory` | Wrong path in `--bot`, or the C++ program is not built yet. Run from the `participant_kit` folder. |
| `python: command not found` | Use `python3`, or `py` on Windows. Inside `--bot` use `{python}`. |
| `Permission denied` running `./my_bot` | `chmod +x my_bot` (Linux / macOS). |
| `fatal error: json.hpp: No such file` | Compile with `-I third_party` (the build script does this). |
| `Misses` is not 0 | Your bot is too slow, crashed, or printed something that is not valid JSON. Check `practice_logs/`. |
| Bot gets disqualified at once | It exits on start-up. Run the bot alone in a terminal and look for errors. |
| `BadActs` is high | You send `TRAVERSE` along blocked / non-existent tracks, `COLLECT` with no drop, or `DEPOSIT` away from a safehouse. Use `--verbose`. |
| Windows: quotes problems | Use double quotes `"..."` around the whole `--bot` value, forward slashes inside are fine. |

Next: [04_testing_and_debugging.md](04_testing_and_debugging.md)
