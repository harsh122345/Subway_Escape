#!/usr/bin/env python3
"""
Quick health check for your bot - run this BEFORE you submit.

It starts your program, feeds it a few small made-up game states, and checks
that every answer is valid JSON in the right format, that the actions are
legal, and that you answer fast enough.

Usage (from the participant_kit folder):
    python tools/check_bot.py --bot "{python} templates/python/my_bot.py"
    python tools/check_bot.py --bot "./templates/cpp/my_bot"
    python tools/check_bot.py --team-info submission/team_info.json

Passing this check does not mean your bot is GOOD - only that it speaks the
protocol correctly. Use the practice arena to measure how well it plays.
"""

import argparse
import json
import os
import queue
import shlex
import subprocess
import sys
import threading
import time

VALID_ACTIONS = {"TRAVERSE", "HOLD", "COLLECT", "DEPOSIT"}
TIME_LIMIT = 1.0

# A tiny map:   1(safehouse) --- 2(junction) --- 3(money_spot) --- 4(junction)
NODES = [
    {"id": 1, "x": 50.0, "y": 50.0, "type": "safehouse"},
    {"id": 2, "x": 120.0, "y": 60.0, "type": "junction"},
    {"id": 3, "x": 190.0, "y": 70.0, "type": "money_spot"},
    {"id": 4, "x": 260.0, "y": 80.0, "type": "junction"},
]
EDGES = [
    {"from": 1, "to": 2, "base_weight": 70.7, "current_weight": 70.7},
    {"from": 2, "to": 3, "base_weight": 70.7, "current_weight": 70.7},
    {"from": 3, "to": 4, "base_weight": 70.7, "current_weight": -1.0},     # blocked on purpose
]
DROP = {"drop_id": 1001, "node_id": 3, "target_safehouse_node": 1,
        "current_value": 400.0, "leak_lambda": 0.01, "ttl_remaining": 50}
COP = {"id": 1, "x": 260.0, "y": 85.0, "vx": 1.0, "vy": 0.0, "radius": 15.0}


def runner(node_id, loot=0.0, status="ACTIVE", stun=0):
    node = next(n for n in NODES if n["id"] == node_id)
    return {"id": 1, "current_node": node_id, "x": node["x"], "y": node["y"], "carrying_loot": loot,
            "max_capacity": 500.0, "status": status, "stun_ticks_remaining": stun}


def make_state(tick, my_runner, drops=(DROP,)):
    return {"tick": tick, "graph_nodes": NODES, "graph_edges": EDGES, "my_runners": [my_runner],
            "active_money_drops": list(drops), "police_officers": [COP]}


SCENARIOS = [
    ("start of match, runner on the safehouse", make_state(0, runner(1))),
    ("runner standing on a junction", make_state(1, runner(2))),
    ("runner on the money spot with a drop", make_state(2, runner(3))),
    ("runner carrying loot, standing on the safehouse", make_state(3, runner(1, loot=300.0))),
    ("runner is stunned", make_state(4, runner(2, status="STUNNED", stun=2))),
    ("no money drops on the map", make_state(5, runner(2), drops=())),
]


def split_command(text):
    parts = shlex.split(text, posix=(os.name != "nt"))
    parts = [p.strip('"') for p in parts]
    return [sys.executable if p == "{python}" else p for p in parts]


def check_answer(raw, state):
    """Returns a list of problems found in the bot's raw answer line."""
    problems = []
    try:
        data = json.loads(raw)
    except Exception as error:
        return [f"answer is not valid JSON ({error}): {raw.strip()[:100]!r}"]
    if not isinstance(data, dict) or "runner_actions" not in data:
        return ['answer must be a JSON object with a "runner_actions" list']
    if not isinstance(data["runner_actions"], list):
        return ['"runner_actions" must be a list']

    my_runner = state["my_runners"][0]
    ids = [a.get("runner_id") for a in data["runner_actions"] if isinstance(a, dict)]
    if my_runner["id"] not in ids:
        problems.append(f"no action given for runner {my_runner['id']} (it will do nothing this tick)")
    if len(ids) != len(set(ids)):
        problems.append("more than one action for the same runner (only one is allowed)")

    for action in data["runner_actions"]:
        if not isinstance(action, dict):
            problems.append(f"action is not an object: {action!r}")
            continue
        kind = action.get("action")
        if kind not in VALID_ACTIONS:
            problems.append(f"unknown action {kind!r} (use TRAVERSE, HOLD, COLLECT or DEPOSIT)")
        if kind == "TRAVERSE":
            target = action.get("target_node")
            here = my_runner["current_node"]
            usable = [e for e in EDGES if {e["from"], e["to"]} == {here, target} and e["current_weight"] >= 0]
            if not isinstance(target, int):
                problems.append("TRAVERSE needs an integer target_node")
            elif not usable:
                problems.append(f"TRAVERSE {here} -> {target} is not a usable track in this test state")
    return problems


def main():
    parser = argparse.ArgumentParser(description="Subway Escape bot checker")
    parser.add_argument("--bot", help='command that starts your bot, e.g. "{python} my_bot.py"')
    parser.add_argument("--team-info", help="path to submission/team_info.json (uses its run_command)")
    args = parser.parse_args()

    command_text = args.bot
    working_dir = None
    if not command_text and args.team_info:
        with open(args.team_info, encoding="utf-8") as f:
            command_text = json.load(f).get("run_command", "")
        working_dir = os.path.dirname(os.path.abspath(args.team_info))   # run from the submission folder
    if not command_text:
        parser.error("give --bot or --team-info")

    command = split_command(command_text)
    if working_dir and command[0] in ("python", "python3", "py"):
        command[0] = sys.executable                  # use whichever Python is running this check
    elif working_dir:
        clean_name = os.path.basename(command[0])
        cand1 = os.path.join(working_dir, command[0])
        cand2 = os.path.join(working_dir, clean_name)
        cand3 = os.path.join(working_dir, clean_name + (".exe" if os.name == "nt" and not clean_name.endswith(".exe") else ""))
        for cand in [cand1, cand2, cand3]:
            if os.path.exists(cand):
                command[0] = os.path.abspath(cand)
                break
    print(f"Starting: {' '.join(command)}" + (f"   (in {working_dir})" if working_dir else "") + "\n")
    try:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=working_dir,
                                stderr=subprocess.PIPE, text=True, bufsize=1, encoding="utf-8")
    except Exception as error:
        print(f"FAIL: could not start your program: {error}")
        sys.exit(1)

    lines = queue.Queue()
    threading.Thread(target=lambda: [lines.put(l) for l in proc.stdout] + [lines.put(None)], daemon=True).start()

    total_problems = 0
    for index, (label, state) in enumerate(SCENARIOS):
        started = time.time()
        try:
            proc.stdin.write(json.dumps(state) + "\n")
            proc.stdin.flush()
            raw = lines.get(timeout=TIME_LIMIT + (2.0 if index == 0 else 0))
        except queue.Empty:
            print(f"[FAIL] {label}\n       no answer within the time limit")
            total_problems += 1
            continue
        except (BrokenPipeError, OSError):
            raw = None
        if raw is None:
            print(f"[FAIL] {label}\n       your program ended / crashed. stderr:\n{proc.stderr.read()[-800:]}")
            sys.exit(1)

        ms = (time.time() - started) * 1000
        problems = check_answer(raw, state)
        status = "ok  " if not problems else "FAIL"
        print(f"[{status}] {label}  ({ms:.0f} ms)")
        print(f"       answered: {raw.strip()[:110]}")
        for problem in problems:
            print(f"       - {problem}")
        total_problems += len(problems)

    proc.terminate()
    print()
    if total_problems:
        print(f"RESULT: {total_problems} problem(s) found. Fix them and run the check again.")
        sys.exit(1)
    print("RESULT: all checks passed. Your bot speaks the protocol correctly.")


if __name__ == "__main__":
    main()
