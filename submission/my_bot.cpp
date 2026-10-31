// ============================================================================
// Subway Escape - Autonomous C++17 High-Performance Bot
// Optimized Risk-Aware Economic Planner & Multi-Runner Coordinator
// ============================================================================

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <queue>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "json.hpp"   // nlohmann/json - lives in participant_kit/third_party

using json = nlohmann::json;

constexpr double INF = std::numeric_limits<double>::infinity();
constexpr int TOTAL_MATCH_TICKS = 300;

// ============================================================================
//  DATA TYPES (Matching Engine Protocol)
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
//  WORLD STATE
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
//  ALGORITHMIC STRATEGY: RISK-AWARE ECONOMIC PLANNER
// ============================================================================

namespace Config {
    constexpr double FULL_CAPACITY_RATIO = 0.78;   // Head to safehouse if bag >= 78% full
    constexpr double POLICE_SAFETY_MARGIN = 5.0;   // Buffer beyond officer radius
    constexpr double POLICE_PENALTY_WEIGHT = 50.0; // Dynamic route penalty
    constexpr double MATCH_END_BUFFER = 2.0;       // Ticks buffer before tick 300
    constexpr double TWO_DROP_MIN_EXTRA = 30.0;    // Min extra loot to pursue second drop
    constexpr double SAFEHOUSE_COST_FACTOR = 0.35; // Weight of future safehouse transit
}

inline double euclideanDist(double x1, double y1, double x2, double y2) {
    return std::hypot(x1 - x2, y1 - y2);
}

struct PathResult {
    std::unordered_map<int, double> weightedCost;  // Weighted distance including police proximity
    std::unordered_map<int, int> hopCount;         // Exact number of hops/ticks
    std::unordered_map<int, int> firstStep;        // Immediate next node along path
    std::unordered_map<int, double> pathRisk;      // Cumulative police risk
};

// Predict officer position at future tick offset dt
inline std::pair<double, double> predictPolicePos(const Police& cop, int dt) {
    return {cop.x + cop.vx * dt, cop.y + cop.vy * dt};
}

// Evaluate police threat for a node at future tick dt
double evaluateNodePoliceRisk(const World& world, int nodeId, int dt) {
    auto it = world.nodes.find(nodeId);
    if (it == world.nodes.end()) return 0.0;
    const Node& node = it->second;

    double maxThreat = 0.0;
    for (const auto& cop : world.police) {
        auto [px, py] = predictPolicePos(cop, dt);
        double dist = euclideanDist(node.x, node.y, px, py);
        double dangerZone = cop.radius + Config::POLICE_SAFETY_MARGIN;

        if (dist <= cop.radius + 1.5) {
            return 10.0; // Imminent danger
        } else if (dist < dangerZone) {
            double threat = (dangerZone - dist) / dangerZone;
            if (threat > maxThreat) maxThreat = threat;
        }
    }
    return maxThreat;
}

// Compute BFS (exact ticks) and Dijkstra (safest cheapest route)
PathResult computeShortestPaths(const World& world, int startNode) {
    PathResult res;

    // --- 1. BFS for hop count ---
    std::queue<int> q;
    std::unordered_set<int> visited;
    q.push(startNode);
    visited.insert(startNode);
    res.hopCount[startNode] = 0;

    while (!q.empty()) {
        int u = q.front();
        q.pop();
        int curHops = res.hopCount[u];

        auto nbIt = world.neighbors.find(u);
        if (nbIt != world.neighbors.end()) {
            for (const auto& nb : nbIt->second) {
                if (nb.weight == INF) continue;
                if (visited.find(nb.nodeId) == visited.end()) {
                    visited.insert(nb.nodeId);
                    res.hopCount[nb.nodeId] = curHops + 1;
                    q.push(nb.nodeId);
                }
            }
        }
    }

    // --- 2. Dijkstra for risk-weighted path ---
    using PQItem = std::pair<double, int>;
    std::priority_queue<PQItem, std::vector<PQItem>, std::greater<PQItem>> pq;

    res.weightedCost[startNode] = 0.0;
    res.firstStep[startNode] = startNode;
    res.pathRisk[startNode] = 0.0;
    pq.push({0.0, startNode});

    while (!pq.empty()) {
        auto [curCost, u] = pq.top();
        pq.pop();

        if (curCost > res.weightedCost[u]) continue;

        auto nbIt = world.neighbors.find(u);
        if (nbIt == world.neighbors.end()) continue;

        int stepTime = res.hopCount.count(u) ? res.hopCount[u] : 0;

        for (const auto& nb : nbIt->second) {
            if (nb.weight == INF) continue;

            double threat = evaluateNodePoliceRisk(world, nb.nodeId, stepTime + 1);
            double edgeCost = nb.weight + threat * Config::POLICE_PENALTY_WEIGHT;
            double nextCost = curCost + edgeCost;

            auto costIt = res.weightedCost.find(nb.nodeId);
            if (costIt == res.weightedCost.end() || nextCost < costIt->second) {
                res.weightedCost[nb.nodeId] = nextCost;
                res.firstStep[nb.nodeId] = (u == startNode) ? nb.nodeId : res.firstStep[u];
                res.pathRisk[nb.nodeId] = res.pathRisk[u] + threat;
                pq.push({nextCost, nb.nodeId});
            }
        }
    }

    return res;
}

const MoneyDrop* getDropOnNode(const World& world, int nodeId) {
    const MoneyDrop* best = nullptr;
    for (const auto& d : world.drops) {
        if (d.nodeId == nodeId && (best == nullptr || d.currentValue > best->currentValue)) {
            best = &d;
        }
    }
    return best;
}

inline double predictDropValue(double currentValue, double leakLambda, int dt) {
    if (dt <= 0) return currentValue;
    return currentValue * std::exp(-leakLambda * dt);
}

struct RouteCandidate {
    int targetNode = -1;
    int primaryDropId = -1;
    int secondaryDropId = -1;
    double utility = -1.0;
    int firstStepNode = -1;
    bool isDepositRoute = false;
};

// Check if stepping onto nextNodeId at tick 1 is safe
bool isStepSafeFromPolice(const World& world, int nextNodeId) {
    auto it = world.nodes.find(nextNodeId);
    if (it == world.nodes.end()) return false;
    const Node& node = it->second;

    for (const auto& cop : world.police) {
        auto [px, py] = predictPolicePos(cop, 1);
        double dist = euclideanDist(node.x, node.y, px, py);
        if (dist <= cop.radius + 1.0) {
            return false;
        }
    }
    return true;
}

RouteCandidate planForRunner(const Runner& runner,
                             const World& world,
                             const std::unordered_set<int>& reservedDropIds) {
    RouteCandidate bestRoute;
    const int here = runner.currentNode;
    const int ticksLeft = TOTAL_MATCH_TICKS - world.tick;
    const double capacityLeft = std::max(0.0, runner.maxCapacity - runner.carryingLoot);

    PathResult runnerPaths = computeShortestPaths(world, here);

    int closestSafehouse = -1;
    int closestSafehouseHops = 999999;
    double closestSafehouseCost = INF;

    for (int sId : world.safehouseIds) {
        if (!runnerPaths.hopCount.count(sId)) continue;
        int hops = runnerPaths.hopCount[sId];
        double cost = runnerPaths.weightedCost[sId];
        if (hops < closestSafehouseHops || (hops == closestSafehouseHops && cost < closestSafehouseCost)) {
            closestSafehouse = sId;
            closestSafehouseHops = hops;
            closestSafehouseCost = cost;
        }
    }

    // Check mandatory deposit conditions
    bool nearlyFull = (runner.carryingLoot >= Config::FULL_CAPACITY_RATIO * runner.maxCapacity);
    bool timeRunningOut = (closestSafehouse != -1 && closestSafehouseHops + Config::MATCH_END_BUFFER >= ticksLeft);

    if (runner.carryingLoot > 0 && closestSafehouse != -1) {
        if (nearlyFull || timeRunningOut) {
            bestRoute.targetNode = closestSafehouse;
            bestRoute.firstStepNode = runnerPaths.firstStep[closestSafehouse];
            bestRoute.utility = 1e6; // Immediate priority
            bestRoute.isDepositRoute = true;
            return bestRoute;
        }
    }

    if (capacityLeft <= 10.0 || timeRunningOut) {
        if (runner.carryingLoot > 0 && closestSafehouse != -1) {
            bestRoute.targetNode = closestSafehouse;
            bestRoute.firstStepNode = runnerPaths.firstStep[closestSafehouse];
            bestRoute.utility = 1e6;
            bestRoute.isDepositRoute = true;
        }
        return bestRoute;
    }

    // 1. Single-Drop Candidates: Marginal loot divided by effective transit ticks
    for (const auto& dropA : world.drops) {
        if (reservedDropIds.count(dropA.dropId)) continue;
        if (!runnerPaths.hopCount.count(dropA.nodeId)) continue;

        int hopsToA = runnerPaths.hopCount[dropA.nodeId];
        if (hopsToA >= dropA.ttlRemaining) continue;

        double valA = predictDropValue(dropA.currentValue, dropA.leakLambda, hopsToA);
        double lootA = std::min(capacityLeft, valA);
        if (lootA <= 5.0) continue;

        PathResult pathsFromA = computeShortestPaths(world, dropA.nodeId);

        int safehouseFromA = -1;
        int hopsAToSafe = 999999;
        if (dropA.targetSafehouseNode > 0 && pathsFromA.hopCount.count(dropA.targetSafehouseNode)) {
            safehouseFromA = dropA.targetSafehouseNode;
            hopsAToSafe = pathsFromA.hopCount[safehouseFromA];
        } else {
            for (int sId : world.safehouseIds) {
                if (pathsFromA.hopCount.count(sId) && pathsFromA.hopCount[sId] < hopsAToSafe) {
                    hopsAToSafe = pathsFromA.hopCount[sId];
                    safehouseFromA = sId;
                }
            }
        }
        if (safehouseFromA == -1) continue;

        int roundTripTicks = hopsToA + 1 + hopsAToSafe + 1;
        if (roundTripTicks > ticksLeft) continue; // Infeasible before match end

        double pathRisk = runnerPaths.pathRisk[dropA.nodeId] + pathsFromA.pathRisk[safehouseFromA];
        double survivalProb = std::max(0.15, 1.0 - pathRisk * 0.12);

        // Marginal utility based on loot gained from this drop
        double effectiveTicks = (hopsToA + 1.0) + Config::SAFEHOUSE_COST_FACTOR * (hopsAToSafe + 1.0);
        double singleUtility = (lootA * survivalProb) / (effectiveTicks + 0.01 * runnerPaths.weightedCost[dropA.nodeId]);

        if (singleUtility > bestRoute.utility) {
            bestRoute.targetNode = dropA.nodeId;
            bestRoute.firstStepNode = runnerPaths.firstStep[dropA.nodeId];
            bestRoute.primaryDropId = dropA.dropId;
            bestRoute.secondaryDropId = -1;
            bestRoute.utility = singleUtility;
            bestRoute.isDepositRoute = false;
        }

        // 2. Two-Drop Candidates: Beam search
        double capacityAfterA = capacityLeft - lootA;
        if (capacityAfterA >= Config::TWO_DROP_MIN_EXTRA) {
            for (const auto& dropB : world.drops) {
                if (dropB.dropId == dropA.dropId || reservedDropIds.count(dropB.dropId)) continue;
                if (!pathsFromA.hopCount.count(dropB.nodeId)) continue;

                int hopsAToB = pathsFromA.hopCount[dropB.nodeId];
                int arrivalTimeB = hopsToA + 1 + hopsAToB;
                if (arrivalTimeB >= dropB.ttlRemaining) continue;

                double valB = predictDropValue(dropB.currentValue, dropB.leakLambda, arrivalTimeB);
                double lootB = std::min(capacityAfterA, valB);
                if (lootB < Config::TWO_DROP_MIN_EXTRA) continue;

                PathResult pathsFromB = computeShortestPaths(world, dropB.nodeId);
                int safehouseFromB = -1;
                int hopsBToSafe = 999999;
                for (int sId : world.safehouseIds) {
                    if (pathsFromB.hopCount.count(sId) && pathsFromB.hopCount[sId] < hopsBToSafe) {
                        hopsBToSafe = pathsFromB.hopCount[sId];
                        safehouseFromB = sId;
                    }
                }
                if (safehouseFromB == -1) continue;

                int twoTripTicks = arrivalTimeB + 1 + hopsBToSafe + 1;
                if (twoTripTicks > ticksLeft) continue;

                double totalRisk = runnerPaths.pathRisk[dropA.nodeId] +
                                   pathsFromA.pathRisk[dropB.nodeId] +
                                   pathsFromB.pathRisk[safehouseFromB];
                double twoSurvival = std::max(0.12, 1.0 - totalRisk * 0.12);

                double twoEffTicks = (arrivalTimeB + 1.0) + Config::SAFEHOUSE_COST_FACTOR * (hopsBToSafe + 1.0);
                double twoUtility = ((lootA + lootB) * twoSurvival) / twoEffTicks;

                if (twoUtility > bestRoute.utility) {
                    bestRoute.targetNode = dropA.nodeId;
                    bestRoute.firstStepNode = runnerPaths.firstStep[dropA.nodeId];
                    bestRoute.primaryDropId = dropA.dropId;
                    bestRoute.secondaryDropId = dropB.dropId;
                    bestRoute.utility = twoUtility;
                    bestRoute.isDepositRoute = false;
                }
            }
        }
    }

    // If no good drop was found and carrying loot, head to safehouse
    if (bestRoute.utility < 0.0 && runner.carryingLoot > 0 && closestSafehouse != -1) {
        bestRoute.targetNode = closestSafehouse;
        bestRoute.firstStepNode = runnerPaths.firstStep[closestSafehouse];
        bestRoute.utility = 1.0;
        bestRoute.isDepositRoute = true;
    }

    return bestRoute;
}

// Find safe evasion step if needed
int findSafeEvasionStep(const World& world, int currentNode) {
    auto it = world.neighbors.find(currentNode);
    if (it == world.neighbors.end()) return -1;

    int safestNode = -1;
    double maxDistToCop = -1.0;

    for (const auto& nb : it->second) {
        if (nb.weight == INF) continue;

        auto nodeIt = world.nodes.find(nb.nodeId);
        if (nodeIt == world.nodes.end()) continue;

        double minCopDist = INF;
        for (const auto& cop : world.police) {
            auto [px, py] = predictPolicePos(cop, 1);
            double dist = euclideanDist(nodeIt->second.x, nodeIt->second.y, px, py);
            if (dist < minCopDist) minCopDist = dist;
        }

        if (minCopDist > maxDistToCop) {
            maxDistToCop = minCopDist;
            safestNode = nb.nodeId;
        }
    }

    if (maxDistToCop > 16.0) return safestNode;
    return -1;
}

Action decideForRunner(const Runner& runner,
                       const World& world,
                       std::unordered_set<int>& reservedDropIds) {
    const int here = runner.currentNode;
    const bool onSafehouse = (world.nodes.count(here) && world.nodes.at(here).type == "safehouse");

    // 1. Bank loot if standing on a safehouse
    if (runner.carryingLoot > 0.0 && onSafehouse) {
        return {runner.id, "DEPOSIT", -1};
    }

    // 2. Collect drop on current node if room exists
    const MoneyDrop* dropHere = getDropOnNode(world, here);
    if (dropHere != nullptr && runner.carryingLoot < runner.maxCapacity) {
        reservedDropIds.insert(dropHere->dropId);
        return {runner.id, "COLLECT", -1};
    }

    // 3. Plan optimal route
    RouteCandidate bestPlan = planForRunner(runner, world, reservedDropIds);

    if (bestPlan.primaryDropId != -1) reservedDropIds.insert(bestPlan.primaryDropId);
    if (bestPlan.secondaryDropId != -1) reservedDropIds.insert(bestPlan.secondaryDropId);

    // 4. Validate and execute step
    int stepNode = bestPlan.firstStepNode;
    bool stepValid = false;

    auto nbIt = world.neighbors.find(here);
    if (nbIt != world.neighbors.end()) {
        for (const auto& nb : nbIt->second) {
            if (nb.nodeId == stepNode && nb.weight != INF) {
                stepValid = true;
                break;
            }
        }
    }

    if (!stepValid || stepNode == here || stepNode == -1) {
        if (runner.carryingLoot > 0.0) {
            PathResult paths = computeShortestPaths(world, here);
            for (int sId : world.safehouseIds) {
                if (paths.hopCount.count(sId) && paths.firstStep.count(sId) && paths.firstStep[sId] != here) {
                    stepNode = paths.firstStep[sId];
                    stepValid = true;
                    break;
                }
            }
        }
    }

    // Check collision danger with police
    if (stepValid && !isStepSafeFromPolice(world, stepNode)) {
        int evasionNode = findSafeEvasionStep(world, here);
        if (evasionNode != -1 && evasionNode != here) {
            stepNode = evasionNode;
        } else {
            return {runner.id, "HOLD", -1};
        }
    }

    if (stepValid && stepNode != -1 && stepNode != here) {
        return {runner.id, "TRAVERSE", stepNode};
    }

    return {runner.id, "HOLD", -1};
}

std::vector<Action> strategy(const World& world) {
    std::vector<Action> actions;
    std::unordered_set<int> reservedDropIds;

    std::vector<Runner> activeRunners = world.runners;
    std::sort(activeRunners.begin(), activeRunners.end(), [](const Runner& a, const Runner& b) {
        return a.carryingLoot > b.carryingLoot;
    });

    for (const Runner& runner : activeRunners) {
        if (runner.status == "STUNNED") {
            actions.push_back({runner.id, "HOLD", -1});
        } else {
            actions.push_back(decideForRunner(runner, world, reservedDropIds));
        }
    }
    return actions;
}

// ============================================================================
//  >>>  PARSER & ENGINE PROTOCOL (DO NOT EDIT)  <<<
// ============================================================================

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
        world.neighbors[node.id];
        if (node.type == "safehouse") world.safehouseIds.push_back(node.id);
        if (node.type == "money_spot") world.moneySpotIds.push_back(node.id);
    }

    for (const auto& e : state.at("graph_edges")) {
        int from = e.at("from").get<int>();
        int to = e.at("to").get<int>();
        double weight = e.at("current_weight").get<double>();
        if (weight < 0) weight = INF;
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

std::vector<Action> checkActions(const std::vector<Action>& raw, const World& world) {
    std::unordered_map<int, const Runner*> runnerById;
    for (const Runner& r : world.runners) runnerById[r.id] = &r;

    std::unordered_map<int, Action> chosen;
    for (const Action& a : raw) {
        auto found = runnerById.find(a.runnerId);
        if (found == runnerById.end()) continue;
        if (chosen.count(a.runnerId)) continue;
        if (a.type != "TRAVERSE" && a.type != "HOLD" && a.type != "COLLECT" && a.type != "DEPOSIT") continue;
        if (a.type == "TRAVERSE") {
            bool freeNeighbor = false;
            auto nb = world.neighbors.find(found->second->currentNode);
            if (nb != world.neighbors.end())
                for (const Neighbor& n : nb->second)
                    if (n.nodeId == a.targetNode && !std::isinf(n.weight)) freeNeighbor = true;
            if (!freeNeighbor) continue;
        }
        chosen[a.runnerId] = a;
    }

    std::vector<Action> finalActions;
    for (const Runner& r : world.runners) {
        auto it = chosen.find(r.id);
        if (r.status == "STUNNED") {
            finalActions.push_back(holdAction(r.id));
        } else if (it != chosen.end()) {
            finalActions.push_back(it->second);
        } else {
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

json runTick(const std::string& line) {
    try {
        World world = parseWorld(json::parse(line));
        return actionsToJson(checkActions(strategy(world), world));
    } catch (const std::exception& error) {
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
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        std::cout << runTick(line).dump() << '\n' << std::flush;
    }
    return 0;
}