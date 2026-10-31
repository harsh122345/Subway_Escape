# 02 · Input / Output Reference

This is the exact message format between the engine and your bot.

- **Transport:** standard input (`stdin`) and standard output (`stdout`).
- **Format:** JSON, **exactly one line per message**.
- **Rhythm:** for each of the 300 ticks the engine sends one line; your bot must reply with one line.
- **Start / end:** your program is started once. Keep reading lines until `stdin` is closed (end of file), then exit.

> **stdout is reserved for your answer.** Anything else you print there breaks the protocol.
> For debugging use `stderr` (`log(...)` in the templates).

---

## 1. What the engine sends you (input)

One line of JSON per tick. Shown here pretty-printed and shortened:

```json
{
  "tick": 12,
  "graph_nodes": [
    { "id": 1, "x": 52.4, "y": 310.9, "type": "safehouse" },
    { "id": 6, "x": 188.0, "y": 97.2, "type": "money_spot" },
    { "id": 20, "x": 240.5, "y": 401.7, "type": "junction" }
  ],
  "graph_edges": [
    { "from": 1, "to": 20, "base_weight": 93.4, "current_weight": 96.1 },
    { "from": 20, "to": 6, "base_weight": 55.0, "current_weight": -1.0 }
  ],
  "my_runners": [
    {
      "id": 3, "current_node": 20, "x": 240.5, "y": 401.7,
      "carrying_loot": 270.5, "max_capacity": 500.0,
      "status": "ACTIVE", "stun_ticks_remaining": 0
    }
  ],
  "active_money_drops": [
    {
      "drop_id": 1012, "node_id": 6, "target_safehouse_node": 1,
      "current_value": 412.8, "leak_lambda": 0.011, "ttl_remaining": 47
    }
  ],
  "police_officers": [
    { "id": 1, "x": 200.2, "y": 130.0, "vx": 2.1, "vy": -0.8, "radius": 15.0 }
  ]
}
```

### Top level

| Field | Type | Meaning |
|-------|------|---------|
| `tick` | int | Current tick number, starting at 0 |
| `graph_nodes` | list | Every node on the map (same every tick) |
| `graph_edges` | list | Every track (positions are fixed; **weights change**) |
| `my_runners` | list | **Only your** runner(s) |
| `active_money_drops` | list | Every drop currently on the map |
| `police_officers` | list | Every police officer |

### `graph_nodes[]`

| Field | Type | Meaning |
|-------|------|---------|
| `id` | int | Unique node id |
| `x`, `y` | float | Position on the map |
| `type` | string | `"junction"`, `"money_spot"` or `"safehouse"` |

### `graph_edges[]`

| Field | Type | Meaning |
|-------|------|---------|
| `from`, `to` | int | The two node ids the track connects. **Tracks work in both directions**, but each track is listed only once. |
| `base_weight` | float | Normal travel cost (fixed) |
| `current_weight` | float | Travel cost right now. **`-1.0` means blocked** (treat as infinity) |

### `my_runners[]`

| Field | Type | Meaning |
|-------|------|---------|
| `id` | int | Use this as `runner_id` in your answer |
| `current_node` | int | The node the runner is standing on |
| `x`, `y` | float | Runner position (same as that node) |
| `carrying_loot` | float | Money in the backpack, not yet deposited |
| `max_capacity` | float | Backpack limit |
| `status` | string | `"ACTIVE"` or `"STUNNED"` |
| `stun_ticks_remaining` | int | Ticks until the stun ends (0 when active) |

### `active_money_drops[]`

| Field | Type | Meaning |
|-------|------|---------|
| `drop_id` | int | Unique id of the drop |
| `node_id` | int | The money spot it is lying on |
| `target_safehouse_node` | int | The safehouse that belongs to this drop (see the rulebook and WhatsApp announcements for how it is used) |
| `current_value` | float | Worth right now (already decayed) |
| `leak_lambda` | float | Decay rate λ of this drop |
| `ttl_remaining` | int | Ticks left before the drop disappears |

### `police_officers[]`

| Field | Type | Meaning |
|-------|------|---------|
| `id` | int | Officer id |
| `x`, `y` | float | Position |
| `vx`, `vy` | float | Velocity (change in position per tick) |
| `radius` | float | Radius of the danger zone around the officer |

---

## 2. What you send back (output)

One line of JSON:

```json
{ "runner_actions": [ { "runner_id": 3, "action": "TRAVERSE", "target_node": 20 } ] }
```

### Fields

| Field | Required | Meaning |
|-------|----------|---------|
| `runner_actions` | always | A list with one entry per runner you want to command |
| `runner_id` | always | The `id` of one of **your** runners |
| `action` | always | `"TRAVERSE"`, `"HOLD"`, `"COLLECT"` or `"DEPOSIT"` |
| `target_node` | only for `TRAVERSE` | The id of a node directly connected to the runner's current node |

### One example for each action

```json
{ "runner_actions": [ { "runner_id": 3, "action": "TRAVERSE", "target_node": 20 } ] }
{ "runner_actions": [ { "runner_id": 3, "action": "HOLD" } ] }
{ "runner_actions": [ { "runner_id": 3, "action": "COLLECT" } ] }
{ "runner_actions": [ { "runner_id": 3, "action": "DEPOSIT" } ] }
```


```json
{ "runner_actions": [
    { "runner_id": 3, "action": "COLLECT" },
    { "runner_id": 4, "action": "TRAVERSE", "target_node": 9 }
] }
```

---

## 3. Rules of the conversation

1. **One line in, one line out.** Always answer, every tick, even if you have nothing to do (`HOLD`).
2. **Flush your output.** Without flushing, the engine never sees your answer and you time out.
   (The templates already do this.)
3. **Answer within 1 second.** Slow code costs you ticks; three in a row disqualifies you.
4. **Valid JSON only.** No trailing text, no comments, no `NaN` / `Infinity` values.
5. **Never exit early.** If your program stops, the engine cannot get answers from it.
6. **Do not wait for extra input.** After the engine sends a tick, answer it. Do not ask for anything else.
7. **Start-up counts.** Your program is started once before tick 0. Keep start-up quick (heavy imports, huge tables).

### Blocked tracks and infinity

JSON has no infinity, so the engine sends `-1.0` for a blocked track. Both templates convert this
for you (`INF` in Python, `INF` constant in C++), so you can write `if weight == INF` safely.

---

Next: [03_how_to_run.md](03_how_to_run.md)
