# Your submission folder

This is the only folder you hand in. Everything the organisers need from you lives here.

## What goes in this folder

| File | What it is |
|------|------------|
| `team_info.json` | Your team details and how to start your bot. **Fill this in first.** |
| your bot's source file | `my_bot.py` **or** `my_bot.cpp`, copied from `templates/` and completed by you |
| any extra files your bot needs | only if truly needed (e.g. a helper `.py` file). Keep it small. |

## Step by step

1. **Pick one language** and copy its template into this folder:

   ```
   Python :  copy templates/python/my_bot.py   ->  submission/my_bot.py
   C++    :  copy templates/cpp/my_bot.cpp     ->  submission/my_bot.cpp
   ```

   (C++ files include `json.hpp`; the build script finds it in `third_party/`, so you do not need to copy it.)

2. **Fill in `team_info.json`.**

   Python team:
   ```json
   "language": "python",
   "entry_file": "my_bot.py",
   "build_command": "",
   "run_command": "python my_bot.py"
   ```

   C++ team:
   ```json
   "language": "cpp",
   "entry_file": "my_bot.cpp",
   "build_command": "g++ -std=c++17 -O2 -I ../third_party my_bot.cpp -o my_bot",
   "run_command": "./my_bot"
   ```
   (On Windows the run command is `my_bot.exe`.)

   For solo participant leave member 2 as it is.

3. **Write your strategy** in the `strategy` function (Python) or `strategy`
   function (C++). Everything else in the file is already done for you.

4. **Test it** (always from the `participant_kit` folder):

   ```
   python tools/check_bot.py --team-info submission/team_info.json
   python practice_arena/run_practice.py --bot "{python} submission/my_bot.py" --bot "{python} sample_bot/python/basic_bot.py" --runs 10
   ```

5. **Submit** this folder the way the organisers announce (WhatsApp group / form).
   Do not rename `team_info.json`. Do not include compiled binaries unless asked.

## Before you submit - checklist

- [ ] `team_info.json` is fully filled in
- [ ] `tools/check_bot.py` says "all checks passed"
- [ ] Your bot beats (or at least matches) the sample bot in the practice arena over 10+ maps
- [ ] Your bot answers well under 1 second on every tick (look at the `MaxMs` column)
- [ ] Your bot prints **only** the JSON answer to stdout (debug text goes to stderr)
- [ ] The program uses no internet, no files outside this folder, no manual input

Good luck!
