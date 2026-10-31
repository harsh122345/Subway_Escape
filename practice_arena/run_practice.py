#!/usr/bin/env python3
"""
Run your bot(s) in the practice arena and print a comparison table.

Run this from the participant_kit folder.

Examples
--------
Your bot alone, one match:
    python practice_arena/run_practice.py --bot "{python} templates/python/my_bot.py"

Your bot against the sample bot, averaged over 10 different maps:
    python practice_arena/run_practice.py \
        --bot "{python} templates/python/my_bot.py" \
        --bot "{python} sample_bot/python/basic_bot.py" \
        --runs 10

A compiled C++ bot (Linux/macOS: ./path/to/bot   Windows: path\\to\\bot.exe):
    python practice_arena/run_practice.py --bot "./sample_bot/cpp/basic_bot" --bot "{python} sample_bot/python/basic_bot.py"

Notes
-----
* "{python}" is replaced with the Python you are currently using, so the same
  command works on Windows, Linux and macOS ("python", "python3" and "py" differ).
* Every --bot is placed in the SAME match (they share the map and compete for
  the same drops). Bot numbers follow the order of the --bot options.
* Your bot's debug output (stderr) is saved in practice_logs/.
"""

import argparse
import os
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from practice_arena import PracticeArena, TOTAL_TICKS   # noqa: E402


def split_command(text):
    """Turn a command string into a list, replacing the {python} placeholder."""
    parts = shlex.split(text, posix=(os.name != "nt"))
    parts = [p.strip('"') for p in parts]
    return [sys.executable if p == "{python}" else p for p in parts]


def print_table(labels, rows):
    header = ["Bot", "Score", "Collected", "Deposits", "Caught", "LootLost", "BadActs", "Misses", "AvgMs", "MaxMs"]
    widths = [max(len(header[i]), max(len(r[i]) for r in rows)) for i in range(len(header))]
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(header))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(r[i].ljust(widths[i]) for i in range(len(header))))


def main():
    parser = argparse.ArgumentParser(description="Subway Escape practice arena")
    parser.add_argument("--bot", action="append", required=True, metavar="COMMAND",
                        help='command that starts a bot, e.g. "{python} my_bot.py" (repeat for more bots)')
    parser.add_argument("--runs", type=int, default=1, help="number of matches (each on a different map)")
    parser.add_argument("--seed", type=int, default=1, help="first map seed (default 1)")
    parser.add_argument("--ticks", type=int, default=TOTAL_TICKS, help="ticks per match (default 300)")
    parser.add_argument("--verbose", action="store_true", help="print what happens each tick")
    parser.add_argument("--log-dir", default="practice_logs", help="where bot stderr logs are saved")
    args = parser.parse_args()

    commands = [split_command(c) for c in args.bot]
    labels = [os.path.basename(c[-1]) if len(c) > 1 else os.path.basename(c[0]) for c in commands]
    totals = [dict(score=0.0, collections=0, deposits=0, captures=0, lost=0.0, bad=0, miss=0,
                   avg_ms=0.0, max_ms=0.0, dq=0) for _ in commands]

    for run_index in range(args.runs):
        seed = args.seed + run_index
        print(f"\n=== Match {run_index + 1}/{args.runs}  (map seed {seed}) ===")
        arena = PracticeArena(commands, seed=seed, ticks=args.ticks, verbose=args.verbose, log_dir=args.log_dir)
        stats = arena.run()
        for i, bot_id in enumerate(sorted(stats)):
            st, t = stats[bot_id], totals[i]
            t["score"] += st.score
            t["collections"] += st.collections
            t["deposits"] += st.deposits
            t["captures"] += st.captures
            t["lost"] += st.loot_lost
            t["bad"] += st.invalid_actions
            t["miss"] += st.misses
            t["avg_ms"] += st.total_response_ms / max(1, st.answered_ticks)
            t["max_ms"] = max(t["max_ms"], st.max_response_ms)
            t["dq"] += 1 if st.disqualified else 0
        if args.runs == 1:
            print(f"Final scores for match on seed {seed}:")
            for bot_id in sorted(stats, key=lambda b: -stats[b].score):
                print(f"  Bot {bot_id} ({labels[bot_id - 1]}): ${stats[bot_id].score:,.0f}"
                      + ("   DISQUALIFIED" if stats[bot_id].disqualified else ""))

    n = args.runs
    print(f"\n=== Summary: average per match over {n} match(es) ===")
    order = sorted(range(len(commands)), key=lambda i: -totals[i]["score"])
    rows = []
    for i in order:
        t = totals[i]
        name = f"{i + 1}:{labels[i]}" + (f" (DQ x{t['dq']})" if t["dq"] else "")
        rows.append([name, f"{t['score'] / n:,.0f}", f"{t['collections'] / n:.1f}", f"{t['deposits'] / n:.1f}",
                     f"{t['captures'] / n:.1f}", f"{t['lost'] / n:,.0f}", f"{t['bad'] / n:.1f}",
                     f"{t['miss'] / n:.1f}", f"{t['avg_ms'] / n:.1f}", f"{t['max_ms']:.0f}"])
    print_table(labels, rows)
    print("\nColumns: Score = banked money | Collected = drops picked up | Deposits = successful deposits |")
    print("         Caught = times caught by police | LootLost = loot wiped by capture | BadActs = illegal actions |")
    print("         Misses = ticks with no valid answer | AvgMs/MaxMs = your thinking time per tick")


if __name__ == "__main__":
    main()
