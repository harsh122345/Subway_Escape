# 04 · Testing and Debugging Your Bot

A bot that scores well *once* may just have been lucky. This page shows how to test properly.

---

## 1. A good testing routine

1. **Make it valid first.** Run `tools/check_bot.py`. It must say "all checks passed".
2. **Make it safe.** Run in the practice arena with `--verbose` on a single map. Watch for
   illegal actions (`BadActs`) and for strange behaviour like walking back and forth.
3. **Make it good.** Compare against the sample bot over **at least 10 maps** (`--runs 10`).
4. **Change one thing at a time.** Keep a small notebook: *what I changed → what the average score did*.
5. **Use the same seeds** when comparing two versions (`--seed 1 --runs 10` both times), so both versions face the same maps.
6. **Test the edge cases** (below) before you submit.

```bash
python practice_arena/run_practice.py --bot "{python} submission/my_bot.py" --bot "{python} sample_bot/python/basic_bot.py" --runs 10 --seed 100
```

---

## 2. Edge cases your bot must survive

| Situation | What a robust bot does |
|-----------|------------------------|
| The runner is **stunned** | Sends a valid action anyway (`HOLD`) |
| There are **no drops** on the map | Does something sensible, no crash |
| The target drop **vanishes** while you walk to it | Picks a new target |
| A track on your route becomes **blocked** (`-1`) | Re-plans |
| The backpack is **full** | Stops collecting, deposits |
| You stand on a drop but the backpack has **no room** | Does not waste ticks on `COLLECT` |
| The **only** route passes close to the police | Decides deliberately: wait or go |
| Two bots chase the **same drop** | Handles losing it |
| Very **long** computation | Has a time guard so a tick never exceeds ~0.5 s |

---

## 3. Debugging tips

- **Watch the verbose output.** `--verbose` prints each collect, deposit, capture and illegal action with its tick number.
- **Log your reasons.** Write *why* the bot chose an action to stderr:
  ```python
  log(f"tick {world.tick}: runner {runner['id']} -> node {target} (score {score:.2f})")
  ```
  Read it in `practice_logs/bot1_seed1_stderr.log`. Don't log huge dumps every tick - keep it modest.
- **Reproduce a bad moment.** Use `--seed` to replay the same map and `--ticks` to stop early.
- **Test a function alone.** Save one tick's input line to a file and call your function on it from a tiny script.
- **Time yourself.** `AvgMs` and especially `MaxMs` in the results table show your thinking time. Python bots that
  recompute shortest paths for every node every tick can get slow - measure it.

---

## 4. The most common mistakes

1. **Printing to stdout** other than the answer (a stray `print("here")` breaks the JSON).
2. **Forgetting to flush** the output (the templates already flush - keep that line).
3. **Moving to a node that is not adjacent.** `TRAVERSE` goes to a *neighbour*, one step at a time.
4. **Collecting and depositing in the wrong place.** `COLLECT` needs a drop on your node; `DEPOSIT` needs a safehouse.
5. **Treating `-1` as a tiny weight.** `-1` means **blocked**. The templates convert it to `INF` for you.
6. **Assuming the map never changes.** Positions are fixed, but weights, drops and police change every tick.
7. **Hard-coding for the practice arena.** The official map and numbers differ. Always read them from the input.
8. **Over-fitting to one seed.** Always test on many maps.
9. **Crashing on an unexpected state** (e.g. empty list). Guard against empty drops, empty paths, unreachable nodes.
10. **Slow start-up or slow ticks.** Remember the 1-second limit includes everything.

---

## 5. Pre-submission checklist

- [ ] `python tools/check_bot.py --team-info submission/team_info.json` passes
- [ ] `Misses` = 0 and `BadActs` = 0 (or very close) over 10+ maps
- [ ] `MaxMs` is comfortably below 1000 ms
- [ ] Your bot beats the sample bot on average
- [ ] Nothing but the JSON answer is printed to stdout
- [ ] No internet access, no reading/writing files outside your folder, no manual input
- [ ] `team_info.json` filled in and the run command works from inside the `submission` folder

---

## 6. FAQ

**Is the practice arena the same as the official match?**  
No. It uses the same message format, but the map, police behaviour and numbers are only similar in spirit. Use it to test that your
bot is correct, fast and sensible, not to squeeze out the last points.

**Can my bot remember things between ticks?**  
Yes. Your program stays alive for the whole match, so global variables / class members persist.

**Can I use libraries?**  
Python: the standard library is always available; do not assume extra packages (e.g. numpy) exist on the judging machine unless the organisers say so.
C++: standard library plus the bundled `json.hpp`.

**Can I use multithreading or precomputed tables?**  
You may, as long as you stay within the time and memory limits.

**What if I have more than one runner?**  
The templates already loop over `my_runners`. Send one action per runner.

**Where can I ask questions?**  
In the official WhatsApp group announced by the organisers. All updates and starter files are shared there.
