// ============================================================================
// Subway Escape - C++ bot template  (C++17)
// ============================================================================
//
// YOUR JOB
// --------
// Write the function  strategy(const World& world)  below. That is the ONLY
// place you edit. Everything else (reading the game, checking your answer,
// sending it back) is already done for you.
//
// Every tick the engine calls your function with the current game state.
// You return a vector with ONE action per runner.
//
//   INPUT: the `world` object
//   -------------------------
//   world.tick                     int
//   world.nodes                    map: node id -> Node {id, x, y, type}
//                                  type: "junction", "money_spot", "safehouse"
//   world.neighbors.at(id)         vector of Neighbor {nodeId, weight}
//                                  tracks work both ways; weight is INF if blocked
//   world.runners                  YOUR runners, each a Runner:
//                                  {id, currentNode, x, y, carryingLoot,
//                                   maxCapacity, status, stunTicksRemaining}
//                                  status: "ACTIVE" or "STUNNED"
//   world.drops                    money drops, each a MoneyDrop:
//                                  {dropId, nodeId, targetSafehouseNode,
//                                   currentValue, leakLambda, ttlRemaining}
//   world.police                   police officers, each a Police:
//                                  {id, x, y, vx, vy, radius}
//   world.safehouseIds             node ids where you can deposit
//   world.moneySpotIds             node ids where drops can appear
//
//   OUTPUT: what strategy must return
//   ---------------------------------
//   A std::vector<Action> with one Action per runner. An Action is
//   { runnerId, "TYPE", targetNode }. The 4 possible actions:
//
//       { 0, "TRAVERSE", 5 }    move runner 0 to neighbour node 5
//       { 0, "COLLECT",  -1 }   pick up the drop on this node
//       { 0, "DEPOSIT",  -1 }   bank loot (be on a safehouse)
//       { 0, "HOLD",     -1 }   do nothing
//
//   (targetNode is only used by TRAVERSE; write -1 for the others.)
//
//   Example:  return { {0, "TRAVERSE", 5}, {1, "HOLD", -1} };
//
// RULES
// -----
//   * One action per runner per tick. Answer within 1 second.
//   * If you forget a runner, or return an invalid action, that runner holds.
//     A warning is written to the log so you can fix it.
//   * Stunned runners ignore commands, you do not need to handle them.
//   * Use log("...") to debug. NEVER print to std::cout; it breaks the game.
//
// TEST IT
// -------
//   Quick check on a tiny sample (no engine needed):   my_bot --test
//
//   Build (from the participant_kit folder):
//     Linux / macOS :  ./tools/build_cpp.sh templates/cpp/my_bot.cpp
//     Windows       :  tools\build_cpp.bat templates\cpp\my_bot.cpp
// ============================================================================

#include <cmath>
#include <iostream>
#include <limits>
#include <string>
#include <unordered_map>
#include <vector>

#include "json.hpp"   // nlohmann/json - lives in participant_kit/third_party

using json = nlohmann::json;

constexpr double INF = std::numeric_limits<double>::infinity();

// ============================================================================
//  DATA TYPES  (what the engine sends)
// ============================================================================
struct Node {
    int id = 0;
    double x = 0, y = 0;
    std::string type;               // "junction", "money_spot" or "safehouse"
};

struct Neighbor {
    int nodeId = 0;
    double weight = 0;              // current weight of the track (INF when blocked)
};

struct Runner {
    int id = 0;
    int currentNode = 0;
    double x = 0, y = 0;
    double carryingLoot = 0;
    double maxCapacity = 0;
    std::string status;             // "ACTIVE" or "STUNNED"
    int stunTicksRemaining = 0;
};

struct MoneyDrop {
    int dropId = 0;
    int nodeId = 0;
    int targetSafehouseNode = 0;
    double currentValue = 0;
    double leakLambda = 0;
    int ttlRemaining = 0;
};

struct Police {
    int id = 0;
    double x = 0, y = 0;
    double vx = 0, vy = 0;
    double radius = 0;
};

// What you answer with, for one runner.
struct Action {
    int runnerId = 0;
    std::string type = "HOLD";      // "TRAVERSE", "HOLD", "COLLECT" or "DEPOSIT"
    int targetNode = -1;            // only used by TRAVERSE
};

// ============================================================================
//  WORLD  (everything the engine told us this tick)
// ============================================================================
struct World {
    int tick = 0;
    std::unordered_map<int, Node> nodes;                         // node id -> node
    std::unordered_map<int, std::vector<Neighbor>> neighbors;    // node id -> adjacent nodes
    std::vector<Runner> runners;                                 // your runners
    std::vector<MoneyDrop> drops;
    std::vector<Police> police;
    std::vector<int> safehouseIds;
    std::vector<int> moneySpotIds;
};

void log(const std::string& message) {
    std::cerr << message << std::endl;          // stderr: never mixes with the answer
}

// ============================================================================
//  >>>  YOUR CODE STARTS HERE  <<<
// ============================================================================

// Return a vector with one action per runner.
// See the top of this file for what `world` contains.
std::vector<Action> strategy(const World& world) {
    std::vector<Action> actions;
    for (const Runner& runner : world.runners) {
        // TODO: replace this with your own logic.
        actions.push_back({runner.id, "HOLD", -1});   // default: do nothing
    }
    return actions;
}

// ============================================================================
//  >>>  YOUR CODE ENDS HERE  <<<
//  Everything below is handled for you. You normally do not edit it.
// ============================================================================

// Parsing: JSON text -> World
World parseWorld(const json& state) {
    World world;
    world.tick = state.at("tick").get<int>();

    for (const auto& n : state.at("graph_nodes")) {
        Node node;
        node.id = n.at("id").get<int>();
        node.x = n.at("x").get<double>();
        node.y = n.at("y").get<double>();
        node.type = n.at("type").get<std::string>();
        world.nodes[node.id] = node;
        world.neighbors[node.id];                                // make sure an entry exists
        if (node.type == "safehouse") world.safehouseIds.push_back(node.id);
        if (node.type == "money_spot") world.moneySpotIds.push_back(node.id);
    }

    for (const auto& e : state.at("graph_edges")) {
        int from = e.at("from").get<int>();
        int to = e.at("to").get<int>();
        double weight = e.at("current_weight").get<double>();
        if (weight < 0) weight = INF;                            // engine sends -1 for "blocked"
        world.neighbors[from].push_back({to, weight});
        world.neighbors[to].push_back({from, weight});
    }

    for (const auto& r : state.at("my_runners")) {
        Runner runner;
        runner.id = r.at("id").get<int>();
        runner.currentNode = r.at("current_node").get<int>();
        runner.x = r.at("x").get<double>();
        runner.y = r.at("y").get<double>();
        runner.carryingLoot = r.at("carrying_loot").get<double>();
        runner.maxCapacity = r.at("max_capacity").get<double>();
        runner.status = r.at("status").get<std::string>();
        runner.stunTicksRemaining = r.at("stun_ticks_remaining").get<int>();
        world.runners.push_back(runner);
    }

    for (const auto& d : state.at("active_money_drops")) {
        MoneyDrop drop;
        drop.dropId = d.at("drop_id").get<int>();
        drop.nodeId = d.at("node_id").get<int>();
        drop.targetSafehouseNode = d.at("target_safehouse_node").get<int>();
        drop.currentValue = d.at("current_value").get<double>();
        drop.leakLambda = d.at("leak_lambda").get<double>();
        drop.ttlRemaining = d.at("ttl_remaining").get<int>();
        world.drops.push_back(drop);
    }

    for (const auto& p : state.at("police_officers")) {
        Police cop;
        cop.id = p.at("id").get<int>();
        cop.x = p.at("x").get<double>();
        cop.y = p.at("y").get<double>();
        cop.vx = p.at("vx").get<double>();
        cop.vy = p.at("vy").get<double>();
        cop.radius = p.at("radius").get<double>();
        world.police.push_back(cop);
    }
    return world;
}

static Action holdAction(int runnerId) { return {runnerId, "HOLD", -1}; }

// Validate what strategy() returned. Bad or missing actions become HOLD.
std::vector<Action> checkActions(const std::vector<Action>& raw, const World& world) {
    std::unordered_map<int, const Runner*> runnerById;
    for (const Runner& r : world.runners) runnerById[r.id] = &r;

    std::unordered_map<int, Action> chosen;
    for (const Action& a : raw) {
        auto found = runnerById.find(a.runnerId);
        if (found == runnerById.end()) {
            log("WARNING: ignored action for unknown runner " + std::to_string(a.runnerId));
            continue;
        }
        if (chosen.count(a.runnerId)) {
            log("WARNING: runner " + std::to_string(a.runnerId) +
                " got more than one action, using the first.");
            continue;
        }
        if (a.type != "TRAVERSE" && a.type != "HOLD" && a.type != "COLLECT" && a.type != "DEPOSIT") {
            log("WARNING: runner " + std::to_string(a.runnerId) + " has invalid action '" + a.type + "'.");
            continue;
        }
        if (a.type == "TRAVERSE") {
            bool freeNeighbor = false;
            auto nb = world.neighbors.find(found->second->currentNode);
            if (nb != world.neighbors.end())
                for (const Neighbor& n : nb->second)
                    if (n.nodeId == a.targetNode && !std::isinf(n.weight)) freeNeighbor = true;
            if (!freeNeighbor) {
                log("WARNING: runner " + std::to_string(a.runnerId) + " cannot traverse " +
                    std::to_string(found->second->currentNode) + " -> " +
                    std::to_string(a.targetNode) + " (not a free neighbour).");
                continue;
            }
        }
        chosen[a.runnerId] = a;
    }

    std::vector<Action> finalActions;
    for (const Runner& r : world.runners) {
        auto it = chosen.find(r.id);
        if (r.status == "STUNNED") {
            finalActions.push_back(holdAction(r.id));   // stunned runners ignore commands anyway
        } else if (it != chosen.end()) {
            finalActions.push_back(it->second);
        } else {
            log("WARNING: runner " + std::to_string(r.id) + " had no action, holding.");
            finalActions.push_back(holdAction(r.id));
        }
    }
    return finalActions;
}

json actionsToJson(const std::vector<Action>& actions) {
    json list = json::array();
    for (const Action& a : actions) {
        json item = {{"runner_id", a.runnerId}, {"action", a.type}};
        if (a.type == "TRAVERSE") item["target_node"] = a.targetNode;
        list.push_back(item);
    }
    return json{{"runner_actions", list}};
}

// One tick: raw JSON text in, answer JSON out. Never throws.
json runTick(const std::string& line) {
    try {
        World world = parseWorld(json::parse(line));
        return actionsToJson(checkActions(strategy(world), world));
    } catch (const std::exception& error) {
        // Never crash: a bug in your strategy costs one tick, not the match.
        log(std::string("error: ") + error.what());
        return json{{"runner_actions", json::array()}};
    }
}

const char* SAMPLE_STATE = R"({
  "tick": 0,
  "graph_nodes": [
    {"id": 0, "x": 0, "y": 0, "type": "safehouse"},
    {"id": 1, "x": 1, "y": 0, "type": "junction"},
    {"id": 2, "x": 2, "y": 0, "type": "money_spot"}
  ],
  "graph_edges": [
    {"from": 0, "to": 1, "current_weight": 1.0},
    {"from": 1, "to": 2, "current_weight": 1.0}
  ],
  "my_runners": [
    {"id": 0, "current_node": 0, "x": 0, "y": 0, "carrying_loot": 0,
     "max_capacity": 100, "status": "ACTIVE", "stun_ticks_remaining": 0}
  ],
  "active_money_drops": [
    {"drop_id": 1, "node_id": 2, "target_safehouse_node": 0,
     "current_value": 50, "leak_lambda": 0.01, "ttl_remaining": 30}
  ],
  "police_officers": [
    {"id": 0, "x": 5, "y": 5, "vx": 0, "vy": 0, "radius": 1}
  ]
})";

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "--test") {
        std::cout << "Sample input : 1 runner on safehouse 0, a 50-value drop on node 2\n";
        std::cout << "Your output  : " << runTick(SAMPLE_STATE).dump() << '\n';
        std::cout << "Format is valid. (Warnings, if any, are shown above.)\n";
        return 0;
    }

    std::ios::sync_with_stdio(false);
    std::string line;
    while (std::getline(std::cin, line)) {          // one line = one tick
        if (line.empty()) continue;
        std::cout << runTick(line).dump() << '\n' << std::flush;
    }
    return 0;
}