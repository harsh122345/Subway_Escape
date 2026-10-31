#!/usr/bin/env python3
"""
Subway Escape - Python bot template
===================================

YOUR JOB
--------
Write the function  strategy(...)  below. That is the ONLY place you edit.
Everything else (reading the game, checking your answer, sending it back)
is already done for you.

Every tick the engine calls your function with the current game state.
You return a LIST with one action per runner.

    INPUT  (the parameters of strategy)
    -----------------------------------
    tick        int     current tick number
    nodes       dict    node_id -> {"x": float, "y": float, "type": str}
                        type is "junction", "money_spot" or "safehouse"
    neighbors   dict    node_id -> [(neighbor_id, weight), ...]
                        tracks work both ways; weight is INF if blocked
    runners     list    YOUR runners, each a dict:
                        {"id", "current_node", "x", "y", "carrying_loot",
                         "max_capacity", "status", "stun_ticks_remaining"}
                        status is "ACTIVE" or "STUNNED"
    drops       list    money drops, each a dict:
                        {"drop_id", "node_id", "target_safehouse_node",
                         "current_value", "leak_lambda", "ttl_remaining"}
    police      list    police officers, each a dict:
                        {"id", "x", "y", "vx", "vy", "radius"}
    safehouses  list    node ids where you can deposit
    money_spots list    node ids where drops can appear

    OUTPUT (what strategy must return)
    ----------------------------------
    A LIST with one action (a dict) per runner. The 4 possible actions:

        {"runner_id": 0, "action": "TRAVERSE", "target_node": 5}   move to neighbour node 5
        {"runner_id": 0, "action": "COLLECT"}                      pick up the drop on this node
        {"runner_id": 0, "action": "DEPOSIT"}                      bank loot (be on a safehouse)
        {"runner_id": 0, "action": "HOLD"}                         do nothing

    Example:  return [
                  {"runner_id": 0, "action": "TRAVERSE", "target_node": 5},
                  {"runner_id": 1, "action": "HOLD"},
              ]

RULES
-----
* One action per runner per tick. Answer within 1 second.
* If you forget a runner, or return an invalid action, that runner holds.
  A warning is written to the log so you can fix it.
* Stunned runners ignore commands, you do not need to handle them.
* Use log("...") to debug. NEVER use print(); it would break the game.

TEST IT
-------
Quick check on a tiny sample (no engine needed):
    python templates/python/my_bot.py --test

Full practice match (from the participant_kit folder):
    python practice_arena/run_practice.py --bot "{python} templates/python/my_bot.py"
"""

import json
import math
import sys
import traceback

INF = math.inf


def log(message):
    """Debug message. Goes to stderr, so it never breaks the game."""
    print(message, file=sys.stderr, flush=True)


# ===========================================================================
#  >>>  YOUR CODE STARTS HERE  <<<
# ===========================================================================
def strategy(tick, nodes, neighbors, runners, drops, police, safehouses, money_spots):
    """
    Return a list with one action per runner.
    See the top of this file for what each parameter contains.
    """
    actions = []
    for runner in runners:
        # TODO: replace this with your own logic.
        actions.append({"runner_id": runner["id"], "action": "HOLD"})   # default: do nothing
    return actions


# ===========================================================================
#  >>>  YOUR CODE ENDS HERE  <<<
#  Everything below is handled for you. You normally do not edit it.
# ===========================================================================
VALID_ACTIONS = {"TRAVERSE", "HOLD", "COLLECT", "DEPOSIT"}


def _hold(runner_id):
    return {"runner_id": runner_id, "action": "HOLD"}


def check_actions(raw, runners, neighbors):
    """Validate what strategy() returned. Bad or missing actions become HOLD."""
    if not isinstance(raw, list):
        log("WARNING: strategy must return a list, got %s. All runners hold." % type(raw).__name__)
        raw = []

    runner_by_id = {r["id"]: r for r in runners}
    chosen = {}
    for item in raw:
        if not isinstance(item, dict) or item.get("runner_id") not in runner_by_id:
            log("WARNING: ignored action with unknown runner: %r" % (item,))
            continue
        rid = item["runner_id"]
        if rid in chosen:
            log("WARNING: runner %s got more than one action, using the first." % rid)
            continue
        kind = item.get("action")
        if kind not in VALID_ACTIONS:
            log("WARNING: runner %s has invalid action %r." % (rid, kind))
            continue
        if kind == "TRAVERSE":
            here = runner_by_id[rid]["current_node"]
            target = item.get("target_node")
            if not any(n == target and w != INF for n, w in neighbors[here]):
                log("WARNING: runner %s cannot traverse %s -> %r (not a free neighbour)."
                    % (rid, here, target))
                continue
            chosen[rid] = {"runner_id": rid, "action": "TRAVERSE", "target_node": target}
        else:
            chosen[rid] = {"runner_id": rid, "action": kind}

    final = []
    for r in runners:
        if r["status"] == "STUNNED":
            final.append(_hold(r["id"]))        # stunned runners ignore commands anyway
        elif r["id"] in chosen:
            final.append(chosen[r["id"]])
        else:
            log("WARNING: runner %s had no action, holding." % r["id"])
            final.append(_hold(r["id"]))
    return final


def run_tick(state):
    """Turn one tick of raw JSON into the list of actions to send back."""
    runners = state.get("my_runners", [])
    try:
        nodes = {n["id"]: {"x": n["x"], "y": n["y"], "type": n["type"]}
                 for n in state["graph_nodes"]}
        neighbors = {node_id: [] for node_id in nodes}
        for e in state["graph_edges"]:
            weight = e["current_weight"]
            if weight < 0:                      # the engine sends -1 for "blocked"
                weight = INF
            neighbors[e["from"]].append((e["to"], weight))
            neighbors[e["to"]].append((e["from"], weight))

        safehouses = [i for i, n in nodes.items() if n["type"] == "safehouse"]
        money_spots = [i for i, n in nodes.items() if n["type"] == "money_spot"]

        raw = strategy(state["tick"], nodes, neighbors, runners,
                       state["active_money_drops"], state["police_officers"],
                       safehouses, money_spots)
        return check_actions(raw, runners, neighbors)
    except Exception:
        # Never crash: a bug in your strategy costs one tick, not the match.
        log(traceback.format_exc())
        return [_hold(r["id"]) for r in runners]


SAMPLE_STATE = {
    "tick": 0,
    "graph_nodes": [
        {"id": 0, "x": 0, "y": 0, "type": "safehouse"},
        {"id": 1, "x": 1, "y": 0, "type": "junction"},
        {"id": 2, "x": 2, "y": 0, "type": "money_spot"},
    ],
    "graph_edges": [
        {"from": 0, "to": 1, "current_weight": 1.0},
        {"from": 1, "to": 2, "current_weight": 1.0},
    ],
    "my_runners": [
        {"id": 0, "current_node": 0, "x": 0, "y": 0, "carrying_loot": 0,
         "max_capacity": 100, "status": "ACTIVE", "stun_ticks_remaining": 0},
    ],
    "active_money_drops": [
        {"drop_id": 1, "node_id": 2, "target_safehouse_node": 0,
         "current_value": 50, "leak_lambda": 0.01, "ttl_remaining": 30},
    ],
    "police_officers": [
        {"id": 0, "x": 5, "y": 5, "vx": 0, "vy": 0, "radius": 1},
    ],
}


def self_test():
    """Run strategy() on a tiny sample and show the result."""
    print("Sample input : 1 runner on safehouse 0, a 50-value drop on node 2")
    actions = run_tick(SAMPLE_STATE)
    print("Your output  :", json.dumps(actions))
    print("Format is valid. (Warnings, if any, are shown above.)")


def main():
    while True:
        line = sys.stdin.readline()
        if not line:                            # engine closed the pipe -> match is over
            break
        line = line.strip()
        if not line:
            continue
        actions = run_tick(json.loads(line))
        print(json.dumps({"runner_actions": actions}), flush=True)


if __name__ == "__main__":
    if "--test" in sys.argv:
        self_test()
    else:
        main()