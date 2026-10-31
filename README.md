# 🚇 Subway Escape — Risk-Aware Autonomous Bot

> **An intelligent C++17 agent for dynamic pathfinding, police avoidance, and economic optimization**

---

## 📌 Project Overview

**Subway Escape** is an autonomous decision-making challenge in which a bot controls runners moving through a dynamically changing subway network.

The objective is to **maximize the total amount of money successfully deposited into safehouses within exactly 300 game ticks**.

The challenge is not simply about finding the shortest path. The bot must make intelligent decisions by balancing four important factors:

1. **Pathfinding:** Finding efficient routes through a weighted subway graph.
2. **Economic optimization:** Selecting valuable money drops before their value decreases or they expire.
3. **Risk management:** Avoiding police officers and minimizing the possibility of losing collected money.
4. **Resource management:** Managing backpack capacity and depositing collected money at the right time.

This project implements a **Risk-Aware Economic Planning Agent** using **C++17** and graph-based optimization algorithms.

---

## 🎯 Problem Understanding

### The subway environment consists of:

| Component | Description |
|---|---|
| **Nodes** | Subway locations such as junctions, money spots, and safehouses |
| **Edges** | Connections between nodes with dynamically changing travel costs |
| **Runners** | Autonomous agents controlled by the bot |
| **Money Drops** | Collectible cash that loses value over time |
| **Police Officers** | Moving threats with positions, velocities, and danger radii |
| **Safehouses** | Locations where collected money can be deposited |

### How the game works

The runner follows a simple but strategically important cycle:

$$\text{Explore} \longrightarrow \text{Collect} \longrightarrow \text{Escape} \longrightarrow \text{Deposit}$$

1. Money appears at different locations.
2. The runner travels to a money spot and collects the available cash.
3. The collected money is stored in its backpack.
4. The runner must reach a safehouse and deposit the money.
5. If the police capture the runner, its carried money is **lost**.
6. Any money remaining in the backpack when the match ends contributes **nothing** to the score.

> **Key Rule:** The actual objective is not to maximize the amount collected, but to maximize the amount **safely deposited**.

---

## 🧠 Implementation Architecture

The bot follows a hybrid planning architecture combining graph algorithms, predictive risk estimation, and economic decision-making.

```text
               CURRENT GAME STATE
                       │
                       ▼
               JSON STATE PARSER
                       │
                       ▼
              DYNAMIC GRAPH MODEL
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
      BFS HOPS                    DIJKSTRA
         │                           │
         └─────────────┬─────────────┘
                       ▼
            POLICE RISK ESTIMATION
                       │
                       ▼
             MONEY DROP EVALUATION
                       │
                       ▼
          SINGLE / TWO-DROP PLANNING
                       │
                       ▼
            DEPOSIT PRIORITY CHECK
                       │
                       ▼
          MULTI-RUNNER COORDINATION
                       │
                       ▼
               ACTION VALIDATION
                       │
                       ▼
                  JSON OUTPUT
```

The bot repeats this process every tick using the latest information provided by the game engine.

---

## ⚙️ 1. Dynamic Graph Modeling

The subway network is represented as an undirected weighted graph:
- Each subway location represents a vertex.
- Each railway connection represents an edge.
- Each edge has a dynamically updated `current_weight`.
- An adjacency-list representation is used to store the graph efficiently.

### Why dynamic graph planning?

The cost of travelling between two stations can change during the match because of police activity.

For example:

| Connection | Previous Cost | Current Cost |
|---|---|---|
| A → B | 3 | 7 |
| A → C | 5 | 4 |
| B → D | 2 | **Blocked** (`-1`) |

A route that was previously optimal might no longer be the best choice.

The bot therefore reconstructs the current graph from the incoming JSON state and recalculates its routes using the latest edge weights.

> **Blocked edges:** An edge with a negative `current_weight` is treated as unavailable (infinite cost).

---

## 🗺️ 2. Pathfinding: BFS + Risk-Weighted Dijkstra

Two complementary graph algorithms are used for route evaluation.

### A. Breadth-First Search (BFS)
BFS calculates the minimum number of edge traversals required to reach every reachable node.

**Why is this important?**
- Each `TRAVERSE` action moves a runner across one directly connected edge and consumes one tick.
- Therefore, BFS helps estimate:
  - Number of traversals to a money drop.
  - Number of traversals to a safehouse.
  - Whether a drop can be reached before its expiry.
  - Whether the runner can return before tick 300.
- BFS is particularly useful for estimating the time required to complete a journey.

### B. Dijkstra's Shortest Path Algorithm
Standard Dijkstra finds the minimum-cost route in a weighted graph.

However, this implementation extends the edge cost by incorporating an estimated police-risk penalty:

$$\text{Effective Edge Cost} = \text{Current Track Weight} + (\text{Police Threat} \times \text{Police Penalty Weight})$$

The route with the lowest accumulated effective cost is preferred.

The implementation also stores:
- `weightedCost`: Accumulated risk-adjusted route cost.
- `hopCount`: Minimum number of traversals from BFS.
- `firstStep`: The immediate next node to visit.
- `pathRisk`: Accumulated estimated police threat.

This allows the bot to consider both travel efficiency and potential danger.

- **Why not use only BFS?** BFS treats every edge as equal, whereas Dijkstra considers the changing travel costs and additional risk penalties.
- **Why not use A\*?** Dijkstra is a straightforward choice for this environment because the graph weights change frequently and the bot needs paths to multiple candidate destinations. A* could be explored later for targeted pathfinding.

---

## 🚨 3. Police Prediction and Risk-Aware Routing

Avoiding police is essential because capture causes the runner to become stunned for three ticks and lose all carried loot.

Each police officer provides:
- **Position:** `(x, y)`
- **Velocity:** `(vx, vy)`
- **Danger radius:** `radius`

The bot uses a constant-velocity approximation to estimate the officer's future position.

### Police position prediction
For a future time offset $t$:
$$\text{predicted\_x} = \text{current\_x} + \text{velocity\_x} \times t$$
$$\text{predicted\_y} = \text{current\_y} + \text{velocity\_y} \times t$$

The distance between the predicted police position and a subway node is then calculated using Euclidean distance:
$$\text{distance} = \sqrt{(\text{runner\_x} - \text{police\_x})^2 + (\text{runner\_y} - \text{police\_y})^2}$$

### Threat evaluation
The implementation considers a safety margin beyond the officer's danger radius:
- Nodes outside the safety margin receive no additional threat.
- Nodes close to the danger zone receive a proportional threat score.
- Nodes inside the immediate danger threshold receive a high threat score.
- The estimated threat is incorporated into Dijkstra's route cost through a configurable penalty.

### Immediate collision prevention
Before executing a traversal, the bot performs an additional safety check on the next node:
- If the predicted police position makes that step unsafe, the bot attempts to find an alternative neighboring node.
- If no sufficiently safe alternative is available, it chooses `HOLD`.

> **Important:** Police movement prediction is an approximation based on the available velocity information. It is not a guarantee of future police behavior.

---

## 💰 4. Economic Optimization: Selecting Valuable Drops

One of the most important decisions is determining which money drop is worth pursuing. A drop should not be selected merely because it has the highest current value or is closest to the runner.

The bot considers:
- Current drop value
- Estimated arrival time
- Exponential value decay
- Remaining lifetime (TTL)
- Backpack capacity
- Return journey to a safehouse
- Estimated police exposure
- Remaining match duration

### Exponential decay
Money drops lose value over time according to exponential decay:
$$M(t) = M_0 \cdot e^{-\lambda t}$$

Where:
- $M_0$ is the starting value.
- $\lambda$ is the drop's decay rate (`leak_lambda`).
- $t$ is elapsed time.

The implementation estimates the value at arrival using:
$$V_{\text{arrival}} = V_{\text{current}} \cdot e^{-\lambda T}$$

Here, `current_value` is already the value supplied by the engine at the current tick.

### Drop feasibility
Before selecting a drop, the bot checks:
1. Is the drop reachable?
2. Will it still exist when the runner arrives?
3. Is there enough backpack capacity?
4. Can the runner reach a safehouse afterward?
5. Can the entire journey be completed before tick 300?

Drops that fail these feasibility checks are rejected.

### Utility-based target selection
For each feasible drop, the bot estimates its expected benefit relative to the time and route cost using a heuristic utility score:

$$U = \frac{L \times P_{\text{survival}}}{T_{\text{effective}} + 0.01 \cdot C_{\text{route}}}$$

Where:
- $L$ is the additional loot expected from the drop.
- $P_{\text{survival}}$ is the estimated survival factor.
- $T_{\text{effective}}$ is the estimated journey duration.
- $C_{\text{route}}$ is the risk-weighted route cost.

The candidate with the highest utility is selected. This is a heuristic optimization strategy rather than a guaranteed globally optimal solution.

---

## 🔄 5. Two-Drop Lookahead Planning

A purely greedy strategy evaluates only one drop at a time. However, sometimes collecting two nearby drops before returning to a safehouse can be more profitable.

The implementation therefore evaluates both:
- **Single-drop collection routes**
- **Two-drop collection routes**

### Example
Suppose the runner has 600 units of remaining backpack capacity:

| Drop | Value | Travel from previous location |
|---|---|---|
| **A** | 300 | 3 ticks |
| **B** | 250 | 2 ticks |

Instead of immediately returning after collecting A, the bot checks whether visiting B is worthwhile:
- Whether enough backpack capacity remains.
- Whether B will expire before arrival.
- Whether the combined route can reach a safehouse.
- Whether the combined loot justifies the extra journey.
- Whether the police risk remains acceptable.

The code performs a bounded two-drop candidate evaluation using nested candidate loops. This is a limited lookahead approach, not a general multi-level beam-search implementation. The best feasible route is selected according to its calculated utility.

---

## 🏦 6. Intelligent Deposit Management

Collecting money is only half the problem. The runner must successfully deposit it.

The bot uses a configurable backpack-capacity threshold:
```cpp
FULL_CAPACITY_RATIO = 0.78;
```
This means the runner is directed toward a safehouse when its backpack reaches approximately 78% of maximum capacity. Deposit priority is also triggered when the remaining match time is insufficient for safely continuing the collection strategy.

### Deposit decision rules

| Situation | Bot decision |
|---|---|
| Runner is on a safehouse with carried money | **Deposit immediately** |
| Backpack reaches 78% capacity | **Prioritize returning to a safehouse** |
| Time is running out | **Prioritize depositing** |
| Very little backpack capacity remains | **Stop pursuing additional drops** |
| No worthwhile collection target exists while carrying loot | **Return to a safehouse** |

This strategy attempts to balance collection opportunities against the risk of losing accumulated money.

---

## 👥 7. Multi-Runner Coordination

When multiple runners are available, allowing all of them to pursue the same drop can waste valuable actions.

The implementation introduces lightweight coordination using a shared set of reserved drop IDs.

### How it works:
1. Runners are sorted according to the amount of loot they currently carry.
2. Runners carrying more loot receive planning priority.
3. When a runner selects a drop, its ID is added to the reserved set.
4. Other runners skip already reserved drops.
5. Each runner independently evaluates its next action using the current world state.

This reduces duplicate target selection and gives runners carrying valuable inventory higher priority. It is a greedy coordination mechanism, rather than a globally optimal multi-agent assignment algorithm.

---

## 🛡️ 8. Action Validation and Safe Execution

The bot does not directly send every planned action to the game engine. A validation layer checks the selected actions before converting them into JSON.

The supported actions are:

| Action | Purpose |
|---|---|
| `TRAVERSE` | Move to an adjacent connected node |
| `COLLECT` | Collect a drop at the runner's current node |
| `DEPOSIT` | Deposit carried money at a safehouse |
| `HOLD` | Remain at the current node |

### Additional checks include:
- Ensuring the runner ID exists.
- Ensuring traversal targets are directly connected.
- Rejecting blocked edges.
- Preventing multiple commands for the same runner.
- Forcing stunned runners to `HOLD`.
- Providing fallback `HOLD` actions when necessary.

This helps prevent invalid actions and improves protocol reliability.

---

## 🔁 9. Replanning Every Tick

The bot follows a **receding-horizon decision-making approach**.

Instead of calculating a complete route once and blindly following it, the bot reassesses its decision every tick:

$$\text{Tick 1: Read state} \to \text{Evaluate routes} \to \text{Select action}$$
$$\text{Tick 2: Read updated state} \to \text{Recalculate paths} \to \text{Select action}$$
$$\text{Tick 3: Read updated state} \to \text{Re-evaluate drops and police} \to \text{Select action}$$
$$\dots$$
$$\text{Tick 300: Prioritize depositing any feasible carried inventory}$$

This is important because:
- Track weights change.
- Police positions change.
- Money drops decay and expire.
- Other teams may collect available drops.
- Runners move and their backpack capacity changes.

The bot therefore adapts its decisions to the latest available game state.

---

## 🧩 Technology Stack

| Technology | Usage |
|---|---|
| **C++17** | Main implementation language |
| **STL** | Data structures and algorithms |
| `std::vector` | Graph adjacency and entity storage |
| `std::unordered_map` | Node and runner lookup |
| `std::priority_queue` | Dijkstra's priority queue |
| `std::queue` | BFS traversal |
| `std::unordered_set` | Visited nodes and reserved drops |
| **nlohmann/json** | JSON parsing and serialization (`third_party/json.hpp`) |
| `<cmath>` | Distance, decay, and risk calculations |

---

## 📂 Project Structure

```text
Subway_Escape/
│
├── docs/
│   ├── 01_problem_guide.md
│   ├── 02_input_output_reference.md
│   ├── 03_how_to_run.md
│   ├── 04_testing_and_debugging.md
│   └── 05_references.md
│
├── practice_arena/
│   ├── practice_arena.py
│   └── run_practice.py
│
├── sample_bot/
│   └── cpp/
│       └── basic_bot.cpp
│
├── templates/
│   └── cpp/
│       └── my_bot.cpp
│
├── submission/
│   ├── my_bot.cpp
│   ├── team_info.json
│   └── README.md
│
├── third_party/
│   └── json.hpp
│
├── tools/
│   ├── check_bot.py
│   └── build_cpp.bat
│
├── README.md
└── .gitignore
```

---

## 🚀 Getting Started

### Requirements
- C++17-compatible compiler (GCC or MinGW).
- Python 3.8 or newer for the testing tools.
- Git.

### 1. Clone the repository
```bash
git clone https://github.com/harsh122345/Subway_Escape.git
cd Subway_Escape
```

### 2. Compile the C++ bot
On Windows using MinGW / g++:
```bash
g++ -std=c++17 -O2 -I third_party submission/my_bot.cpp -o submission/my_bot.exe
```
Alternatively, use the provided build script:
```cmd
tools\build_cpp.bat submission\my_bot.cpp
```

### 3. Run the bot's built-in test
```cmd
submission\my_bot.exe --test
```

### 4. Validate the submission
```bash
python tools/check_bot.py --team-info submission/team_info.json
```

### 5. Run practice simulations
Compile the sample C++ bot first if its executable is not already available:
```cmd
tools\build_cpp.bat sample_bot\cpp\basic_bot.cpp
```
Then run:
```bash
python practice_arena/run_practice.py --bot "submission/my_bot.exe" --bot "sample_bot/cpp/basic_bot.exe" --runs 10
```

Refer to `docs/03_how_to_run.md` and `docs/04_testing_and_debugging.md` for exact environment-specific commands.

---

## 📊 Configurable Strategy Parameters

The implementation exposes several tunable constants in the `Config` namespace:

| Parameter | Current value | Purpose |
|---|---|---|
| `FULL_CAPACITY_RATIO` | `0.78` | Backpack threshold for deposit priority |
| `POLICE_SAFETY_MARGIN` | `5.0` | Extra distance beyond police danger radius |
| `POLICE_PENALTY_WEIGHT` | `50.0` | Weight of police threat in route cost |
| `MATCH_END_BUFFER` | `2.0` | Additional time buffer before match end |
| `TWO_DROP_MIN_EXTRA` | `30.0` | Minimum extra loot considered for a second drop |
| `SAFEHOUSE_COST_FACTOR` | `0.35` | Relative weight of return journey in utility |

> These values are heuristic parameters and should be tuned through repeated practice simulations rather than treated as mathematically optimal constants.

---

## ⚠️ Current Limitations and Future Improvements

The current implementation provides a practical hybrid planning strategy, but several improvements are possible.

### Current limitations
- Police movement is approximated using constant-velocity prediction.
- The police-risk model is heuristic and cannot guarantee collision avoidance.
- Two-drop planning evaluates pairs rather than arbitrary-length collection sequences.
- Multi-runner coordination uses greedy reservation instead of global assignment.
- Path-risk estimates are approximations based on the current graph and predicted police positions.
- The planner recalculates decisions every tick rather than maintaining a persistent long-term plan.

### Future improvements
- Implement a more accurate time-dependent police prediction model.
- Improve path-risk estimation using time-expanded graph states.
- Introduce deeper beam search for multi-drop route planning.
- Use Hungarian assignment or another global matching algorithm for runner coordination.
- Tune utility parameters through automated simulation experiments.
- Explore reinforcement learning as an experimental alternative to the heuristic planner.

---

## 🏁 Final Objective

The central idea behind this implementation is simple:

> **A successful autonomous bot should not merely find money. It should understand when to collect it, how to reach it efficiently, how to survive the journey, and when to secure its earnings.**

By combining graph-based pathfinding, risk estimation, economic utility evaluation, and resource management, this project aims to build an adaptive autonomous agent that maximizes safely deposited capital within the 300-tick limit.

---

## 👤 Author
- **Author:** Harsh Kumar
- **Project:** Subway Escape — Autonomous Bot
- **Language:** C++17
- **Repository:** [Subway_Escape](https://github.com/harsh122345/Subway_Escape)
