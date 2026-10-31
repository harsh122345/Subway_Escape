#!/usr/bin/env python3
"""
Subway Escape - SAMPLE BOT (Python)  "Basic Collector"
======================================================

A deliberately simple bot, provided as a baseline so you can compare your own
bot against it in the practice arena.

It is built exactly like the template: the whole strategy lives in the one
function  strategy(...)  and returns a list with one action per runner.
Everything below the "YOUR CODE ENDS HERE" line is the same as in the template.

Its whole strategy, in plain words:
    1. If standing on a safehouse while carrying loot  -> DEPOSIT.
    2. If a drop is lying on my node and I have room   -> COLLECT.
    3. If I'm (nearly) full, or nothing is left to grab -> walk to the cheapest safehouse.
    4. Otherwise walk toward the drop that looks best:  value / travel cost.
    5. Walking uses the cheapest path by the CURRENT track weights,
       so blocked tracks are avoided.

What it does NOT do (room for you to improve!):
    * It never looks at the police positions or velocities.
    * It ignores how fast each drop is losing value and how long it will live.
    * It never plans around other bots or thinks ahead more than one drop.
    * It can walk through a danger zone if the path happens to cross one.

Test it quickly (no engine needed):
    python sample_bot/python/basic_bot.py --test

Run it in the practice arena:
    python practice_arena/run_practice.py --bot "{python} sample_bot/python/basic_bot.py"
"""

import heapq
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
# How full the backpack must be before the bot heads for a safehouse.
FULL_FRACTION = 0.8


def cheapest_paths(neighbors, start):
    """Cheapest route by current weights. Returns (cost_to, first_step_to), keyed by node id."""
    cost_to = {start: 0.0}
    first_step_to = {start: start}
    queue = [(0.0, start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost > cost_to.get(node, INF):
            continue
        for next_node, weight in neighbors[node]:
            if weight == INF:                       # blocked track
                continue
            new_cost = cost + weight
            if new_cost < cost_to.get(next_node, INF):
                cost_to[next_node] = new_cost
                first_step_to[next_node] = next_node if node == start else first_step_to[node]
                heapq.heappush(queue, (new_cost, next_node))
    return cost_to, first_step_to


def decide_for_runner(runner, nodes, neighbors, drop_at_node, safehouses):
    rid = runner["id"]
    here = runner["current_node"]
    carrying = runner["carrying_loot"]
    capacity = runner["max_capacity"]

    # 1) Bank the loot if we are standing on a safehouse.
    if carrying > 0 and nodes[here]["type"] == "safehouse":
        return {"runner_id": rid, "action": "DEPOSIT"}

    # 2) Pick up a drop on this node if there is room in the backpack.
    if here in drop_at_node and carrying < capacity:
        return {"runner_id": rid, "action": "COLLECT"}

    cost_to, first_step_to = cheapest_paths(neighbors, here)

    # 3) Cheapest reachable safehouse (used when full or when nothing is worth fetching).
    reachable_safehouses = [s for s in safehouses if s in cost_to and s != here]
    nearest_safehouse = min(reachable_safehouses, key=lambda s: cost_to[s], default=None)

    # 4) Best drop to fetch: highest value per unit of travel cost.
    best_drop_node, best_score = None, 0.0
    for node_id, drop in drop_at_node.items():
        if node_id == here or node_id not in cost_to:
            continue
        score = drop["current_value"] / (cost_to[node_id] + 1.0)
        if score > best_score:
            best_drop_node, best_score = node_id, score

    is_nearly_full = carrying >= FULL_FRACTION * capacity
    if carrying > 0 and (is_nearly_full or best_drop_node is None):
        target = nearest_safehouse
    else:
        target = best_drop_node

    if target is None:
        return {"runner_id": rid, "action": "HOLD"}
    return {"runner_id": rid, "action": "TRAVERSE", "target_node": first_step_to[target]}


def strategy(tick, nodes, neighbors, runners, drops, police, safehouses, money_spots):
    """Return a list with one action per runner."""
    # node_id -> the most valuable drop lying on that node
    drop_at_node = {}
    for drop in drops:
        best = drop_at_node.get(drop["node_id"])
        if best is None or drop["current_value"] > best["current_value"]:
            drop_at_node[drop["node_id"]] = drop

    return [decide_for_runner(runner, nodes, neighbors, drop_at_node, safehouses)
            for runner in runners]


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
