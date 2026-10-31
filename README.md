# Subway Escape - Participant Kit

**OptimatX Club · IIT Patna (Celesta) · AI × Maths Hackathon**

Build a bot that runs through a subway network, grabs cash, dodges the police and banks as much money as possible in 300 ticks.
This kit has everything you need to build, test and submit your bot.

---

## What is in this folder

```
participant_kit/
├── README.md                    ← you are here
├── docs/                        ← READ THESE
│   ├── 01_problem_guide.md          the game explained in plain language
│   ├── 02_input_output_reference.md exact JSON your bot receives and sends
│   ├── 03_how_to_run.md             install, build, run, compare (Windows / Linux / macOS)
│   ├── 04_testing_and_debugging.md  testing routine, edge cases, common mistakes, checklist
│   └── 05_references.md             links and topics to revise
├── templates/                   ← START HERE: fill-in-the-blanks bots (they do nothing yet)
│   ├── python/my_bot.py
│   └── cpp/my_bot.cpp
├── sample_bot/                  ← a basic working bot to compare against
│   ├── python/basic_bot.py
│   └── cpp/basic_bot.cpp
├── practice_arena/              ← local simulator + comparison table
│   ├── practice_arena.py
│   └── run_practice.py
├── tools/
│   ├── check_bot.py                 checks your bot speaks the protocol
│   ├── build_cpp.sh                 C++ build (Linux / macOS)
│   └── build_cpp.bat                C++ build (Windows)
├── third_party/json.hpp         ← C++ JSON library (included, nothing to install)
└── submission/                  ← your team file + your final bot go here
    ├── team_info.json
    └── README.md
```

---

## Quick start (5 minutes)

You need **Python 3.8+**. For C++ you also need a C++17 compiler (details in `docs/03_how_to_run.md`).

**1. Watch the sample bot play**
```bash
python practice_arena/run_practice.py --bot "{python} sample_bot/python/basic_bot.py"
```

**2. Copy a template into `submission/`**
```bash
cp templates/python/my_bot.py submission/my_bot.py        # Python
cp templates/cpp/my_bot.cpp   submission/my_bot.cpp       # C++
```
(Windows: use `copy` and backslashes.)

**3. Write your strategy** in the function marked `YOUR CODE STARTS HERE`
(`decide_for_runner` in Python, `decideForRunner` in C++).

**4. Test and compare**
```bash
python tools/check_bot.py --bot "{python} submission/my_bot.py"
python practice_arena/run_practice.py --bot "{python} submission/my_bot.py" --bot "{python} sample_bot/python/basic_bot.py" --runs 10
```
(C++: build with `./tools/build_cpp.sh submission/my_bot.cpp` first, then use `"./submission/my_bot"` as the bot command.)

**5. Fill in `submission/team_info.json` and submit the `submission/` folder.**

---

## The rules in 6 lines

1. 300 ticks. Score = money **deposited** at safehouses.
2. Each tick: engine sends one JSON line → your bot answers one JSON line. **1 second** limit.
3. Actions per runner: `TRAVERSE`, `HOLD`, `COLLECT`, `DEPOSIT`.
4. Police danger zones **stun** a runner for 3 ticks and **wipe** its carried loot.
5. Drops lose value over time and expire.
6. Three invalid / late answers in a row → disqualified.

## Important notes

- The practice arena is **not** the official engine. It only speaks the same message format.
  Build a bot that reads the state it is given, not one that is tuned to the practice arena.
- The official engine's internal formulas and generation details are not published.
- Official announcements, updates and extra starter files (including Java) are shared in the official WhatsApp group.

Good luck, and may your runner always find the shortest way home.
