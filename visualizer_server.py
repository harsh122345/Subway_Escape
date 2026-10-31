import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import threading
import time

# Import the local practice arena modules
from practice_arena.practice_arena import PracticeArena, Node, Edge, Runner, Drop, Cop, BotStats

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_bot_command(bot_name):
    if bot_name == "my_bot":
        return [os.path.abspath(os.path.join(BASE_DIR, "submission", "my_bot.exe"))]
    elif bot_name == "basic_bot":
        return [os.path.abspath(os.path.join(BASE_DIR, "sample_bot", "cpp", "basic_bot.exe"))]
    elif bot_name == "basic_bot_py":
        return [sys.executable, os.path.abspath(os.path.join(BASE_DIR, "sample_bot", "python", "basic_bot.py"))]
    return [os.path.abspath(os.path.join(BASE_DIR, "submission", "my_bot.exe"))]

def record_full_match(bot1_name="my_bot", bot2_name="basic_bot", seed=100, max_ticks=300):
    commands = [get_bot_command(bot1_name)]
    bot_names = {1: bot1_name}
    if bot2_name and bot2_name != "none":
        commands.append(get_bot_command(bot2_name))
        bot_names[2] = bot2_name

    arena = PracticeArena(commands, seed=seed, ticks=max_ticks, verbose=False, log_dir=os.path.join(BASE_DIR, "practice_logs"))
    
    # Pre-record static graph layout
    static_nodes = [{"id": n.id, "x": n.x, "y": n.y, "type": n.type} for n in arena.nodes.values()]
    static_edges = [{"from": e.a, "to": e.b, "base_weight": e.base_weight} for e in arena.edges]

    os.makedirs(arena.log_dir, exist_ok=True)
    for bot_id, cmd in arena.commands.items():
        from practice_arena.practice_arena import BotProcess
        log_path = os.path.join(arena.log_dir, f"bot{bot_id}_seed{arena.seed}_stderr.log")
        bot = BotProcess(bot_id, cmd, log_path)
        if bot.error:
            arena.stats[bot_id].disqualified = True
        arena.bots[bot_id] = bot

    ticks_data = []

    try:
        for t in range(max_ticks):
            # Capture state before step
            current_drops = [
                {
                    "drop_id": d.drop_id,
                    "node_id": d.node_id,
                    "target_safehouse": d.target_safehouse,
                    "value": round(arena._drop_value(d), 1),
                    "ttl": d.ttl
                }
                for d in arena.drops
            ]
            current_cops = [
                {
                    "id": c.id,
                    "x": round(c.x, 1),
                    "y": round(c.y, 1),
                    "vx": round(c.vx, 2),
                    "vy": round(c.vy, 2),
                    "radius": c.radius
                }
                for c in arena.cops
            ]
            current_runners = [
                {
                    "id": r.id,
                    "node": r.node,
                    "x": round(r.x, 1),
                    "y": round(r.y, 1),
                    "loot": round(r.loot, 1),
                    "status": r.status,
                    "stun_left": r.stun_left
                }
                for r in arena.runners.values()
            ]
            edge_weights = [
                {
                    "from": e.a,
                    "to": e.b,
                    "blocked": (e.current_weight == float("inf")),
                    "weight": round(e.current_weight if e.current_weight != float("inf") else -1.0, 1)
                }
                for e in arena.edges
            ]

            scores = {
                b_id: {
                    "name": bot_names.get(b_id, f"Bot {b_id}"),
                    "score": round(st.score, 1),
                    "collections": st.collections,
                    "deposits": st.deposits,
                    "captures": st.captures,
                    "loot_lost": round(st.loot_lost, 1),
                    "invalid_actions": st.invalid_actions
                }
                for b_id, st in arena.stats.items()
            }

            ticks_data.append({
                "tick": t,
                "runners": current_runners,
                "drops": current_drops,
                "police": current_cops,
                "edges": edge_weights,
                "scores": scores
            })

            arena.step()
    finally:
        for bot in arena.bots.values():
            bot.stop()

    final_scores = {
        b_id: {
            "name": bot_names.get(b_id, f"Bot {b_id}"),
            "score": round(st.score, 1),
            "collections": st.collections,
            "deposits": st.deposits,
            "captures": st.captures,
            "loot_lost": round(st.loot_lost, 1),
            "invalid_actions": st.invalid_actions,
            "avg_ms": round(st.total_response_ms / max(1, st.answered_ticks), 2),
            "max_ms": round(st.max_response_ms, 1)
        }
        for b_id, st in arena.stats.items()
    }

    return {
        "nodes": static_nodes,
        "edges": static_edges,
        "ticks": ticks_data,
        "final_summary": final_scores
    }

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Subway Escape · Autonomous Bot Visualizer</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0a0e17;
            --bg-panel: #111827;
            --bg-card: rgba(17, 24, 39, 0.7);
            --border: rgba(255, 255, 255, 0.08);
            --border-highlight: rgba(99, 102, 241, 0.4);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-cyan: #06b6d4;
            --accent-indigo: #6366f1;
            --accent-gold: #fbbf24;
            --accent-emerald: #10b981;
            --accent-rose: #f43f5e;
            --accent-purple: #a855f7;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            font-family: 'Outfit', -apple-system, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* Top Navigation Header */
        header {
            background: linear-gradient(180deg, rgba(17, 24, 39, 0.95) 0%, rgba(10, 14, 23, 0.8) 100%);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .brand-badge {
            background: linear-gradient(135deg, var(--accent-indigo), var(--accent-cyan));
            color: white;
            font-weight: 800;
            font-size: 0.85rem;
            padding: 0.35rem 0.65rem;
            border-radius: 8px;
            letter-spacing: 0.05em;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            box-shadow: 0 0 15px rgba(99, 102, 241, 0.4);
        }

        .brand-title {
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(to right, #ffffff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .status-pill {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.85rem;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.04);
            padding: 0.4rem 0.8rem;
            border-radius: 9999px;
            border: 1px solid var(--border);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--accent-emerald);
            box-shadow: 0 0 8px var(--accent-emerald);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }

        /* Main Workspace Layout */
        .workspace {
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 1.5rem;
            padding: 1.5rem 2rem;
            flex: 1;
            max-width: 1700px;
            width: 100%;
            margin: 0 auto;
        }

        /* Left Column: Canvas Viewport */
        .arena-container {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .canvas-card {
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 20px 40px -15px rgba(0,0,0,0.5);
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        #arenaCanvas {
            width: 100%;
            max-width: 820px;
            aspect-ratio: 1;
            display: block;
            background: radial-gradient(circle at center, #131c2e 0%, #0c121e 100%);
            border-radius: 12px;
            cursor: crosshair;
        }

        /* Canvas Overlay Legend */
        .canvas-legend {
            position: absolute;
            top: 1rem;
            left: 1rem;
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            background: rgba(10, 14, 23, 0.85);
            backdrop-filter: blur(8px);
            padding: 0.5rem 0.85rem;
            border-radius: 8px;
            border: 1px solid var(--border);
            font-size: 0.75rem;
            font-weight: 500;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .legend-indicator {
            width: 10px;
            height: 10px;
            border-radius: 3px;
        }

        /* Playback Controls Toolbar */
        .controls-card {
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1rem 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
        }

        .timeline-bar {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .timeline-slider {
            flex: 1;
            height: 6px;
            border-radius: 3px;
            background: rgba(255, 255, 255, 0.1);
            outline: none;
            -webkit-appearance: none;
            cursor: pointer;
        }

        .timeline-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: var(--accent-cyan);
            box-shadow: 0 0 10px var(--accent-cyan);
            cursor: pointer;
            transition: transform 0.1s;
        }

        .timeline-slider::-webkit-slider-thumb:hover {
            transform: scale(1.3);
        }

        .tick-display {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--accent-cyan);
            min-width: 85px;
            text-align: right;
        }

        .actions-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.75rem;
        }

        .btn-group {
            display: flex;
            gap: 0.5rem;
        }

        button {
            font-family: 'Outfit', sans-serif;
            font-size: 0.85rem;
            font-weight: 600;
            border-radius: 8px;
            padding: 0.55rem 1rem;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid transparent;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--accent-indigo), #4f46e5);
            color: white;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
        }

        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(99, 102, 241, 0.5);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            border-color: var(--border);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
        }

        .btn-accent {
            background: linear-gradient(135deg, var(--accent-cyan), #0891b2);
            color: white;
            box-shadow: 0 4px 12px rgba(6, 182, 212, 0.35);
        }

        .btn-accent:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(6, 182, 212, 0.5);
        }

        .speed-selector {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .speed-btn {
            padding: 0.3rem 0.6rem;
            font-size: 0.75rem;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-muted);
            border: 1px solid var(--border);
        }

        .speed-btn.active {
            background: var(--accent-cyan);
            color: #000;
            font-weight: 700;
            border-color: var(--accent-cyan);
        }

        /* Right Column: Telemetry & Config Sidebar */
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }

        .card {
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .card-title {
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        /* Match Setup Form */
        .config-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
        }

        label {
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        select, input {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 0.5rem 0.75rem;
            border-radius: 8px;
            font-family: inherit;
            font-size: 0.85rem;
            outline: none;
            transition: border-color 0.2s;
        }

        select:focus, input:focus {
            border-color: var(--accent-indigo);
        }

        /* Live Scoreboards */
        .scores-list {
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
        }

        .bot-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 0.85rem;
            transition: all 0.2s;
        }

        .bot-card.leader {
            border-color: var(--accent-gold);
            background: rgba(251, 191, 36, 0.03);
            box-shadow: 0 0 15px rgba(251, 191, 36, 0.08);
        }

        .bot-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }

        .bot-name {
            font-weight: 700;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .bot-tag {
            font-size: 0.65rem;
            font-weight: 700;
            padding: 0.15rem 0.45rem;
            border-radius: 4px;
            text-transform: uppercase;
        }

        .tag-1 { background: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.4); }
        .tag-2 { background: rgba(244, 63, 94, 0.2); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.4); }

        .bot-score {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.35rem;
            font-weight: 800;
            color: var(--accent-gold);
            text-shadow: 0 0 10px rgba(251, 191, 36, 0.3);
        }

        .bot-stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.5rem;
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.75rem;
        }

        .stat-item {
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
        }

        .stat-label {
            color: var(--text-muted);
            font-size: 0.68rem;
        }

        .stat-val {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            color: var(--text-main);
        }

        .backpack-bar-container {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 0.4rem;
        }

        .backpack-bar {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-emerald), var(--accent-cyan));
            border-radius: 3px;
            transition: width 0.15s ease-out;
        }

        /* Loading Spinner Overlay */
        .loading-overlay {
            position: absolute;
            inset: 0;
            background: rgba(10, 14, 23, 0.85);
            backdrop-filter: blur(8px);
            display: none;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 1rem;
            z-index: 20;
            border-radius: 16px;
        }

        .spinner {
            width: 48px;
            height: 48px;
            border: 4px solid rgba(99, 102, 241, 0.2);
            border-top-color: var(--accent-indigo);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loading-text {
            font-weight: 600;
            color: var(--text-main);
            font-size: 0.95rem;
        }
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <div class="brand-badge">C++17 BOT</div>
            <div class="brand-title">Subway Escape Arena Visualizer</div>
        </div>
        <div class="status-pill">
            <div class="pulse-dot"></div>
            <span>Simulation Server Online</span>
        </div>
    </header>

    <div class="workspace">
        <!-- Left: Canvas Visualizer -->
        <div class="arena-container">
            <div class="canvas-card">
                <div class="canvas-legend">
                    <div class="legend-item"><div class="legend-indicator" style="background:#10b981; box-shadow:0 0 6px #10b981;"></div> Safehouse</div>
                    <div class="legend-item"><div class="legend-indicator" style="background:#fbbf24; box-shadow:0 0 6px #fbbf24;"></div> Money Spot (Drop)</div>
                    <div class="legend-item"><div class="legend-indicator" style="background:#38bdf8;"></div> Junction</div>
                    <div class="legend-item"><div class="legend-indicator" style="background:#ef4444; border-radius:50%;"></div> Police Radar</div>
                    <div class="legend-item"><div class="legend-indicator" style="background:#6366f1;"></div> Runner 1 (my_bot)</div>
                    <div class="legend-item"><div class="legend-indicator" style="background:#f43f5e;"></div> Runner 2 (basic_bot)</div>
                </div>

                <div class="loading-overlay" id="loadingOverlay">
                    <div class="spinner"></div>
                    <div class="loading-text" id="loadingText">Running Simulation (300 ticks)...</div>
                </div>

                <canvas id="arenaCanvas" width="800" height="800"></canvas>
            </div>

            <!-- Playback Controls -->
            <div class="controls-card">
                <div class="timeline-bar">
                    <input type="range" id="tickSlider" class="timeline-slider" min="0" max="299" value="0">
                    <div class="tick-display"><span id="curTick">000</span> / 300</div>
                </div>
                <div class="actions-row">
                    <div class="btn-group">
                        <button class="btn-primary" id="playBtn">▶ Play</button>
                        <button class="btn-secondary" id="resetBtn">↺ Restart</button>
                        <button class="btn-secondary" id="prevBtn">⏮</button>
                        <button class="btn-secondary" id="nextBtn">⏭</button>
                    </div>

                    <div class="speed-selector">
                        <span>Speed:</span>
                        <button class="speed-btn" data-speed="200">0.5x</button>
                        <button class="speed-btn active" data-speed="100">1x</button>
                        <button class="speed-btn" data-speed="40">2.5x</button>
                        <button class="speed-btn" data-speed="15">5x</button>
                        <button class="speed-btn" data-speed="5">MAX</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Right: Control & Telemetry Panel -->
        <div class="sidebar">
            <!-- Simulation Match Settings -->
            <div class="card">
                <div class="card-title">
                    <span>Match Configuration</span>
                </div>
                <div class="config-grid">
                    <div class="form-group">
                        <label>Bot 1 (Main)</label>
                        <select id="bot1Select">
                            <option value="my_bot" selected>submission/my_bot (C++)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Bot 2 (Opponent)</label>
                        <select id="bot2Select">
                            <option value="basic_bot" selected>sample/basic_bot (C++)</option>
                            <option value="none">Solo (Single Runner)</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label>Map Seed</label>
                    <input type="number" id="mapSeed" value="100">
                </div>

                <button class="btn-accent" id="startMatchBtn">⚡ Run New Match</button>
            </div>

            <!-- Live Scoreboards -->
            <div class="card">
                <div class="card-title">
                    <span>Match Telemetry</span>
                    <span style="font-size: 0.75rem; color: var(--text-muted);" id="matchStatusLabel">Seed: 100</span>
                </div>
                <div class="scores-list" id="scoresContainer">
                    <!-- Populated dynamically -->
                </div>
            </div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById("arenaCanvas");
        const ctx = canvas.getContext("2d");
        const loadingOverlay = document.getElementById("loadingOverlay");
        const tickSlider = document.getElementById("tickSlider");
        const curTickSpan = document.getElementById("curTick");
        const playBtn = document.getElementById("playBtn");
        const resetBtn = document.getElementById("resetBtn");
        const prevBtn = document.getElementById("prevBtn");
        const nextBtn = document.getElementById("nextBtn");
        const startMatchBtn = document.getElementById("startMatchBtn");
        const scoresContainer = document.getElementById("scoresContainer");
        const speedButtons = document.querySelectorAll(".speed-btn");

        let matchData = null;
        let currentTickIndex = 0;
        let isPlaying = false;
        let playInterval = null;
        let tickDelay = 100;

        // Scaling constants
        const WORLD_MAX = 500.0;
        const CANVAS_SIZE = 800.0;
        const PADDING = 40.0;
        const SCALE = (CANVAS_SIZE - PADDING * 2) / WORLD_MAX;

        function toCanvasX(worldX) { return PADDING + worldX * SCALE; }
        function toCanvasY(worldY) { return PADDING + worldY * SCALE; }

        async function loadAndRunMatch(bot1, bot2, seed) {
            loadingOverlay.style.display = "flex";
            try {
                const response = await fetch(`/api/run_match?bot1=${bot1}&bot2=${bot2}&seed=${seed}`);
                matchData = await response.json();
                tickSlider.max = matchData.ticks.length - 1;
                currentTickIndex = 0;
                document.getElementById("matchStatusLabel").textContent = `Seed: ${seed}`;
                renderTick(0);
                startPlayback();
            } catch (err) {
                alert("Error running match: " + err);
            } finally {
                loadingOverlay.style.display = "none";
            }
        }

        function renderTick(index) {
            if (!matchData || !matchData.ticks[index]) return;
            const state = matchData.ticks[index];
            const nodes = matchData.nodes;
            const edges = state.edges;

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // 1. Draw Edges (Subway Tracks)
            for (const edge of edges) {
                const nodeA = nodes.find(n => n.id === edge.from);
                const nodeB = nodes.find(n => n.id === edge.to);
                if (!nodeA || !nodeB) continue;

                const ax = toCanvasX(nodeA.x);
                const ay = toCanvasY(nodeA.y);
                const bx = toCanvasX(nodeB.x);
                const by = toCanvasY(nodeB.y);

                ctx.beginPath();
                ctx.moveTo(ax, ay);
                ctx.lineTo(bx, by);

                if (edge.blocked) {
                    ctx.strokeStyle = "rgba(239, 68, 68, 0.4)";
                    ctx.lineWidth = 1.5;
                    ctx.setLineDash([4, 4]);
                } else if (edge.weight > edge.base_weight + 5) {
                    ctx.strokeStyle = "rgba(251, 191, 36, 0.5)";
                    ctx.lineWidth = 2.5;
                    ctx.setLineDash([]);
                } else {
                    ctx.strokeStyle = "rgba(56, 189, 248, 0.22)";
                    ctx.lineWidth = 2;
                    ctx.setLineDash([]);
                }
                ctx.stroke();
                ctx.setLineDash([]);
            }

            // 2. Draw Nodes
            for (const node of nodes) {
                const nx = toCanvasX(node.x);
                const ny = toCanvasY(node.y);

                ctx.beginPath();
                if (node.type === "safehouse") {
                    ctx.arc(nx, ny, 11, 0, Math.PI * 2);
                    ctx.fillStyle = "rgba(16, 185, 129, 0.25)";
                    ctx.fill();
                    ctx.strokeStyle = "#10b981";
                    ctx.lineWidth = 3;
                    ctx.stroke();

                    // Icon center
                    ctx.beginPath();
                    ctx.arc(nx, ny, 4, 0, Math.PI * 2);
                    ctx.fillStyle = "#10b981";
                    ctx.fill();
                } else if (node.type === "money_spot") {
                    ctx.arc(nx, ny, 7, 0, Math.PI * 2);
                    ctx.fillStyle = "rgba(251, 191, 36, 0.2)";
                    ctx.fill();
                    ctx.strokeStyle = "rgba(251, 191, 36, 0.6)";
                    ctx.lineWidth = 1.5;
                    ctx.stroke();
                } else {
                    ctx.arc(nx, ny, 4.5, 0, Math.PI * 2);
                    ctx.fillStyle = "rgba(56, 189, 248, 0.6)";
                    ctx.fill();
                }
            }

            // 3. Draw Active Drops
            for (const drop of state.drops) {
                const node = nodes.find(n => n.id === drop.node_id);
                if (!node) continue;
                const dx = toCanvasX(node.x);
                const dy = toCanvasY(node.y);

                ctx.beginPath();
                ctx.arc(dx, dy, 9, 0, Math.PI * 2);
                ctx.fillStyle = "#fbbf24";
                ctx.shadowColor = "#fbbf24";
                ctx.shadowBlur = 12;
                ctx.fill();
                ctx.shadowBlur = 0;

                ctx.fillStyle = "#000";
                ctx.font = "bold 9px 'JetBrains Mono', monospace";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText("$", dx, dy);

                // Value tag
                ctx.fillStyle = "#fef08a";
                ctx.font = "600 10px 'Outfit', sans-serif";
                ctx.fillText(`$${Math.round(drop.value)}`, dx, dy - 14);
            }

            // 4. Draw Police Danger Radii
            for (const cop of state.police) {
                const cx = toCanvasX(cop.x);
                const cy = toCanvasY(cop.y);
                const cr = cop.radius * SCALE;

                ctx.beginPath();
                ctx.arc(cx, cy, cr, 0, Math.PI * 2);
                ctx.fillStyle = "rgba(239, 68, 68, 0.12)";
                ctx.fill();
                ctx.strokeStyle = "rgba(239, 68, 68, 0.7)";
                ctx.lineWidth = 1.5;
                ctx.stroke();

                // Velocity direction vector
                ctx.beginPath();
                ctx.moveTo(cx, cy);
                ctx.lineTo(cx + cop.vx * 6 * SCALE, cy + cop.vy * 6 * SCALE);
                ctx.strokeStyle = "#f87171";
                ctx.lineWidth = 2;
                ctx.stroke();

                // Cop central icon
                ctx.beginPath();
                ctx.arc(cx, cy, 5, 0, Math.PI * 2);
                ctx.fillStyle = "#ef4444";
                ctx.fill();
            }

            // 5. Draw Runners
            const runnerColors = ["#6366f1", "#f43f5e", "#10b981", "#a855f7"];
            for (let i = 0; i < state.runners.length; i++) {
                const runner = state.runners[i];
                const rx = toCanvasX(runner.x);
                const ry = toCanvasY(runner.y);
                const color = runnerColors[i % runnerColors.length];

                // Runner glow
                ctx.beginPath();
                ctx.arc(rx, ry, 11, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.shadowColor = color;
                ctx.shadowBlur = 15;
                ctx.fill();
                ctx.shadowBlur = 0;

                ctx.strokeStyle = "#ffffff";
                ctx.lineWidth = 2.5;
                ctx.stroke();

                // Runner number
                ctx.fillStyle = "#ffffff";
                ctx.font = "bold 10px 'JetBrains Mono', monospace";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(runner.id.toString(), rx, ry);

                // Loot indicator badge
                if (runner.loot > 0) {
                    ctx.fillStyle = "#fbbf24";
                    ctx.font = "700 11px 'JetBrains Mono', monospace";
                    ctx.fillText(`$${Math.round(runner.loot)}`, rx, ry - 16);
                }

                if (runner.status === "STUNNED") {
                    ctx.fillStyle = "#ef4444";
                    ctx.font = "800 10px 'Outfit', sans-serif";
                    ctx.fillText(`⚡ STUN (${runner.stun_left})`, rx, ry + 18);
                }
            }

            // Update UI Counters
            tickSlider.value = index;
            curTickSpan.textContent = index.toString().padStart(3, "0");
            updateTelemetry(state.scores, state.runners);
        }

        function updateTelemetry(scores, runners) {
            scoresContainer.innerHTML = "";
            const botIds = Object.keys(scores);
            botIds.sort((a, b) => scores[b].score - scores[a].score);

            botIds.forEach((bId, idx) => {
                const info = scores[bId];
                const runner = runners.find(r => r.id == bId) || { loot: 0, status: "ACTIVE" };
                const isLeader = (idx === 0);

                const card = document.createElement("div");
                card.className = `bot-card ${isLeader ? 'leader' : ''}`;
                card.innerHTML = `
                    <div class="bot-header">
                        <div class="bot-name">
                            <span>${info.name}</span>
                            <span class="bot-tag tag-${bId}">${bId == 1 ? 'MY BOT' : 'SAMPLE'}</span>
                        </div>
                        <div class="bot-score">$${Math.round(info.score).toLocaleString()}</div>
                    </div>
                    <div class="stat-label">Backpack: $${Math.round(runner.loot)} / 500</div>
                    <div class="backpack-bar-container">
                        <div class="backpack-bar" style="width: ${(runner.loot / 500) * 100}%"></div>
                    </div>
                    <div class="bot-stats-grid">
                        <div class="stat-item"><span class="stat-label">Collected</span><span class="stat-val">${info.collections}</span></div>
                        <div class="stat-item"><span class="stat-label">Deposits</span><span class="stat-val">${info.deposits}</span></div>
                        <div class="stat-item"><span class="stat-label">Caught</span><span class="stat-val" style="color:${info.captures > 0 ? '#ef4444' : '#10b981'}">${info.captures}</span></div>
                    </div>
                `;
                scoresContainer.appendChild(card);
            });
        }

        function startPlayback() {
            if (isPlaying) return;
            isPlaying = true;
            playBtn.textContent = "⏸ Pause";
            playInterval = setInterval(() => {
                if (currentTickIndex >= matchData.ticks.length - 1) {
                    stopPlayback();
                    return;
                }
                currentTickIndex++;
                renderTick(currentTickIndex);
            }, tickDelay);
        }

        function stopPlayback() {
            isPlaying = false;
            playBtn.textContent = "▶ Play";
            if (playInterval) clearInterval(playInterval);
            playInterval = null;
        }

        playBtn.addEventListener("click", () => {
            if (isPlaying) stopPlayback();
            else startPlayback();
        });

        resetBtn.addEventListener("click", () => {
            stopPlayback();
            currentTickIndex = 0;
            renderTick(0);
        });

        prevBtn.addEventListener("click", () => {
            stopPlayback();
            if (currentTickIndex > 0) {
                currentTickIndex--;
                renderTick(currentTickIndex);
            }
        });

        nextBtn.addEventListener("click", () => {
            stopPlayback();
            if (matchData && currentTickIndex < matchData.ticks.length - 1) {
                currentTickIndex++;
                renderTick(currentTickIndex);
            }
        });

        tickSlider.addEventListener("input", (e) => {
            stopPlayback();
            currentTickIndex = parseInt(e.target.value);
            renderTick(currentTickIndex);
        });

        speedButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                speedButtons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                tickDelay = parseInt(btn.dataset.speed);
                if (isPlaying) {
                    stopPlayback();
                    startPlayback();
                }
            });
        });

        startMatchBtn.addEventListener("click", () => {
            const b1 = document.getElementById("bot1Select").value;
            const b2 = document.getElementById("bot2Select").value;
            const seed = parseInt(document.getElementById("mapSeed").value) || 100;
            loadAndRunMatch(b1, b2, seed);
        });

        // Initial Load
        loadAndRunMatch("my_bot", "basic_bot", 100);
    </script>
</body>
</html>
"""

class VisualizerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
        elif parsed.path == "/api/run_match":
            params = urllib.parse.parse_qs(parsed.query)
            bot1 = params.get("bot1", ["my_bot"])[0]
            bot2 = params.get("bot2", ["basic_bot"])[0]
            seed = int(params.get("seed", ["100"])[0])
            
            data = record_full_match(bot1, bot2, seed=seed)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        # Silence verbose request logs
        return

def run_server():
    server = socketserver.TCPServer(("127.0.0.1", PORT), VisualizerHandler)
    print(f"Visualizer server live at http://localhost:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
