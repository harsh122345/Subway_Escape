# 01 · Understanding the Problem

> **Subway Escape - The Ultimate Chase** · OptimatX Club, IIT Patna (Celesta) · AI × Maths Hackathon

Read this document first. It explains the game in plain language. The exact message format
is in [02_input_output_reference.md](02_input_output_reference.md).

---

## 1. The idea in one minute

Remember Subway Surfers? Cash everywhere, police chasing you, and you try to grab as much as
you can. In this event **you do not control the runner - your program does.**

- Money drops appear at certain places on a subway map.
- Your runner must **collect** it and carry it to a **safehouse** to **deposit** it.
- Police officers patrol the map. If they catch your runner, the carried money is **lost**.
- Money slowly **loses value** as time passes, and drops **disappear** after a while.
- The match lasts exactly **300 ticks**. Your **score = total money you deposited**.

```
   collect  ───────►  carry (risky!)  ───────►  deposit
   (race the clock)   (avoid the police)        (money is now safe)
```

Money you are still carrying when the match ends is worth **nothing**.

---

## 2. What is on the map

| Thing | What it is | How you see it |
|-------|-----------|----------------|
| **Node** | A place on the map. Three kinds: `junction`, `money_spot`, `safehouse`. | `graph_nodes` |
| **Edge (track)** | A track connecting two nodes. You can travel it in **both directions**. | `graph_edges` |
| **Runner** | Your character. Stands on a node. Has a backpack with a maximum capacity. | `my_runners` |
| **Money drop** | Cash lying on a money spot. Has a value, a decay rate and a lifetime. | `active_money_drops` |
| **Police officer** | Moves around. Projects a circular danger zone around itself. | `police_officers` |

- **Money spots** are where drops appear.
- **Safehouses** are where you deposit.
- **Junctions** just connect things.

### Track weights (travel cost)

Every track has two numbers:

- `base_weight` - its normal, fixed cost.
- `current_weight` - its cost **right now**. It changes during the match depending on what
  the police are doing near that track.
  - Usually it is close to `base_weight`.
  - Police nearby make it **larger**.
  - If a track is completely blocked, the engine sends `-1` (think of it as "infinite cost").

The engine does not publish how `current_weight` is computed. Your bot's job is to read the
value it is given each tick and make good decisions from it.

---

## 3. What happens every tick

```
 ┌────────────────────────────────────────────────────────────────────┐
 │ ENGINE                                   YOUR BOT                  │
 │                                                                    │
 │  updates the world            ──►   receives ONE line of JSON      │
 │  (police move, weights change,        (the whole current state)    │
 │   drops age, ...)                                                  │
 │                                       thinks  (< 1 second!)        │
 │  carries out your actions     ◄──   sends ONE line of JSON         │
 │  checks police captures               (one action per runner)      │
 └────────────────────────────────────────────────────────────────────┘
                         repeated 300 times
```

Your bot sees the **complete** state each tick. It does not need to remember anything between
ticks (but it may, if your strategy wants to).

---

## 4. Your actions

You choose **one action per runner per tick**.

| Action | What it does | Needs |
|--------|--------------|-------|
| `TRAVERSE` | Move the runner to a **directly connected** node. | `target_node` - the neighbour's id |
| `HOLD` | Stay exactly where you are. | nothing |
| `COLLECT` | Pick up the money drop lying on the runner's **current node**. The drop is removed from the map and its current value goes into the backpack, up to the backpack's capacity. | a drop on your node |
| `DEPOSIT` | Bank everything in the backpack. Score goes up, backpack becomes empty. | runner standing on a `safehouse` |

Things worth knowing:

- A single `TRAVERSE` takes the runner to the neighbouring node you named. Moving across the
  map takes several ticks and several `TRAVERSE` actions.
- Moving, collecting and depositing are **separate** actions. Arriving at a drop does not
  collect it; you must send `COLLECT` on a later tick while standing there.
- An **illegal** action (for example `TRAVERSE` to a node that is not connected, `COLLECT` with
  no drop, `DEPOSIT` away from a safehouse) is simply ignored. The runner does nothing that tick.
- Other bots share the same map and the same drops. If two runners want the same drop in the
  same tick, only one of them gets it. Do not rely on winning that tie.

---

## 5. Police and capture

- Each police officer has a position `(x, y)`, a velocity `(vx, vy)` and a **radius**.
- The circle of that radius around the officer is the **danger zone**.
- If a runner is inside a danger zone when the tick is checked:
  1. the runner is **stunned for 3 ticks** - it ignores all commands (`status: "STUNNED"`), and
  2. the loot it carries is **wiped to zero**.
- Money you have already **deposited is always safe**.

The engine does not publish how the officers choose where to go. You do get their position,
velocity and radius every tick.

---

## 6. Money decay and expiry

Every drop loses value over time, following exponential decay:

```
M(t) = M0 · e^(−λ·t)
```

- `M0` - the starting value of the drop
- `λ` (`leak_lambda`) - how fast **this** drop decays (different for every drop)
- `t` - the number of ticks since the drop appeared

You do not have to compute this yourself: each drop already carries its `current_value`.
A drop also has `ttl_remaining` - the number of ticks before it **disappears** completely.

---

## 7. Rules, limits and disqualification

| Rule | Detail |
|------|--------|
| Match length | exactly 300 ticks |
| Time per tick | **1 second** to answer |
| Memory | 256 MB |
| Input / output | standard input / standard output, **one JSON line each way per tick** |
| Autonomy | the bot must run by itself; no manual control during a match |
| Disqualification | **three consecutive ticks** without a valid, in-time answer ends your match: the process is stopped and you are disqualified |

A "valid answer" means: valid JSON, in the right format, in time.

---

## 8. What is *not* published

To keep the competition about **your** ideas, the following are intentionally **not**
documented, and the practice arena is only an approximation of them:

- the exact formula that turns police positions into `current_weight`,
- how the police choose their movement,
- how the map is generated, and how money drops are created and replaced,
- the exact numbers (counts, sizes, ranges) used in the official match.

Do not try to reverse-engineer them. Build a bot that **reads the state it is given** and
reacts sensibly - that is what the official match rewards.

---

## 9. Questions worth thinking about

These have no single right answer. They are here to point your thinking in useful directions.

- Which drop is worth chasing right now? Does "closest" always mean "best"?
- When is it better to deposit a small amount early instead of waiting for a full backpack?
- How should the travel cost, the decay of a drop, and its remaining lifetime be combined into one decision?
- Is a cheap route that passes near a police officer really cheap?
- Police move. What can you say about where an officer will be in a few ticks?
- If a track gets blocked while you are on your way, what do you do?
- What should a runner do while stunned, or when there is nothing worth doing?
- How can you tell whether a change to your bot actually made it better, and not just lucky?

---

## 10. Glossary

| Term | Meaning |
|------|---------|
| **Tick** | One step of the game. The match has 300. |
| **Runner** | The character your bot controls. |
| **Backpack / loot** | Money the runner is carrying but has not deposited yet (`carrying_loot`). |
| **Banked / deposited** | Money safely added to your score. |
| **Stun** | 3 ticks of being frozen after a capture. |
| **TTL** | "Time to live": ticks left before a drop vanishes. |
| **Blocked edge** | A track with `current_weight = -1`. |

Next: [02_input_output_reference.md](02_input_output_reference.md)
