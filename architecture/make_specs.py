#!/usr/bin/env python3
"""Generate the Archify JSON specs for the portfolio project diagrams.

Each project is described compactly: nodes on a (col, row) grid, connections
between them. Run `python3 make_specs.py` to (re)write specs/<slug>.json, then
`python3 build.py` to validate, render and inject the styled SVGs.
Content rule: every label comes from the project's own page text.
"""
import json, math, os

PITCH_X, PITCH_Y, X0, Y0 = 250, 160, 110, 50
LEGEND = {"frontend": "Interface", "backend": "Core component", "database": "Data / map",
          "security": "Safety-critical", "messagebus": "Supervisor", "external": "Hardware / external"}

def width(label, sub):
    w = int(math.ceil(max(150, 8.2 * len(label) + 28, 5.7 * len(sub) + 28) / 10.0) * 10)
    assert w <= 190, f'node too wide ({w}): {label!r} / {sub!r}'
    return w

def spec(title, nodes, edges, out, pitch=PITCH_X, x0=X0, legend=None, boundaries=None):
    comps = []
    rmin = min(n[5] for n in nodes)
    for n in nodes:
        nid, typ, label, sub, col, row = n[:6]
        w = n[6] if len(n) > 6 else width(label, sub)
        cx = x0 + col * pitch
        comps.append({"id": nid, "type": typ, "label": label, "sublabel": sub,
                      "pos": [int(cx - w / 2), Y0 + int((row - rmin) * PITCH_Y)], "size": [w, 64]})
    conns = []
    for e in edges:
        a, b = e[0], e[1]
        c = {"id": f"{a}-{b}", "from": a, "to": b}
        o = e[2] if len(e) > 2 else {}
        if "label" in o: c["label"] = o["label"]
        if "v" in o: c["variant"] = o["v"]
        if "s" in o: c["fromSide"], c["toSide"] = o["s"]
        for k in ("labelDx", "labelDy"):
            if k in o: c[k] = o[k]
        conns.append(c)
    return {"schema_version": 1, "diagram_type": "architecture",
            "meta": {"title": title, "locale": "en", "output": out + ".html", "quality_profile": "showcase",
                     "legend": {"mode": "auto", "entries": {k: {"label": v} for k, v in (legend or LEGEND).items()}}},
            "components": comps, "connections": conns,
            **({"boundaries": boundaries} if boundaries else {})}

S = {}

# 1. Low-light SLAM  (content rules: no distillation, no phone, no PMU, no Noctifi3r; runs on Spot)
S["low-light-slam"] = spec("Low-Light Dense SLAM on Jetson: system architecture", [
    ("camera", "external", "Spot Camera", "fixed basic exposure", 0, 1),
    ("expo", "backend", "Exposure Gain", "p90 luma, capped at 8x", 1, 1),
    ("frontend", "backend", "SLAM Frontend", "MASt3R + Dark3R matcher", 2, 1),
    ("backend", "backend", "SLAM Backend", "thread, shared model", 3, 1),
    ("map", "database", "Trajectory + Map", "Open3D rendering", 4, 1),
    ("ckpt", "database", "Dark3R Weights", "LoRA merged into ViT-L", 2, 2),
    ("chol", "backend", "CPU Cholesky", "fallback pose solve", 3, 2),
    ("sweep", "external", "Noise Sweep", "raw-domain, +3 to -10 dB", 1, 0),
    ("ref", "external", "Reference Poses", "clean run / COLMAP", 3, 0),
    ("eval", "backend", "Metric Harness", "ATE, RPE, drift, reloc", 4, 0),
], [
    ("camera", "expo", {"label": "raw"}),
    ("expo", "frontend", {"label": "corrected"}),
    ("frontend", "backend", {"label": "keyframes"}),
    ("backend", "map", {"label": "poses"}),
    ("ckpt", "frontend", {"label": "load", "s": ("top", "bottom")}),
    ("backend", "chol", {"label": "if it fails", "v": "dashed", "labelDy": 26}),
    ("sweep", "expo", {"label": "degraded frames", "v": "dashed", "labelDy": 26}),
    ("ref", "eval", {"label": "reference"}),
    ("map", "eval", {"label": "trajectory"}),
], "low-light-slam")

# 2. Autonomous drone navigation
S["drone-navigation"] = spec("Autonomous Drone Navigation: system architecture", [
    ("lidar", "external", "LiDAR + IMU", "onboard sensing", 0, 1),
    ("fastlio", "backend", "FAST-LIO2", "LiDAR-inertial odometry", 1, 1),
    ("rog", "database", "ROG-Map", "inflated occupancy grid", 2, 1),
    ("super", "security", "SUPER Planner", "corridors, MINCO, 15 Hz", 3, 1),
    ("fc", "external", "Flight Controller", "custom quadrotor", 4, 1),
    ("cam", "external", "Camera", "onboard", 0, 2),
    ("track", "backend", "YOLO + BoT-SORT", "TensorRT, ReID tracking", 1, 2),
    ("predict", "backend", "EigenTrajectory", "next 1.5 s, 20 points", 2, 2),
    ("bridge", "backend", "dtdp_super_bridge", "FOLLOW / HOLD / BACK OFF", 3, 2),
], [
    ("lidar", "fastlio", {"label": "scans"}),
    ("fastlio", "rog", {"label": "cloud"}),
    ("rog", "super", {"label": "grid"}),
    ("super", "fc", {"label": "trajectory", "v": "emphasis"}),
    ("cam", "track", {"label": "frames"}),
    ("track", "predict", {"label": "tracks"}),
    ("predict", "bridge", {"label": "path"}),
    ("bridge", "super", {"label": "goal pose", "v": "emphasis", "s": ("top", "bottom")}),
], "drone-navigation")

# 3. IE 574 warehouse kitting (coordinator + request-busy-done)
S["ie574-warehouse-kitting"] = spec("Multi-Robot Warehouse Kitting: system architecture", [
    ("tracker", "database", "Order Tracker", "counts at tray unload only", 2, 0),
    ("coord", "messagebus", "Central Coordinator", "req / busy / done handshakes", 2, 1, 1100),
    ("producer", "external", "Parts Producer", "demand-driven spawn", 0, 2),
    ("pnp", "backend", "Pick-and-Place UR10", "color vision, bin sorting", 1, 2),
    ("mr1", "backend", "Mobile Robot 1", "PioneerP3DX + UR5", 2, 2),
    ("mr2", "backend", "Mobile Robot 2", "KUKA youBot", 3, 2),
    ("cobot", "backend", "Cobot UR10", "tray unloading", 4, 2),
], [
    ("coord", "tracker", {"label": "order status", "s": ("top", "bottom")}),
    ("coord", "producer", {"s": ("bottom", "top")}),
    ("coord", "pnp", {"s": ("bottom", "top")}),
    ("coord", "mr1", {"s": ("bottom", "top")}),
    ("coord", "mr2", {"s": ("bottom", "top")}),
    ("coord", "cobot", {"s": ("bottom", "top")}),
    ("producer", "pnp", {"v": "dashed"}),
    ("pnp", "mr1", {"v": "dashed"}),
    ("mr1", "mr2", {"v": "dashed"}),
    ("mr2", "cobot", {"v": "dashed"}),
], "ie574-warehouse-kitting", pitch=220, x0=150)

# 4. Medicine dispenser
S["medicine-dispenser"] = spec("Automatic Medicine Dispenser: system architecture", [
    ("hopper", "external", "Hopper Sensor", "hopper level", 0, 1),
    ("jam", "external", "Jam Detection", "motor current monitoring", 0, 2),
    ("pi", "backend", "Raspberry Pi", "schedule, motor control", 1, 1.5),
    ("motor", "backend", "Motor + Driver", "drives the drum", 2, 1),
    ("drum", "backend", "Singulation Drum", "pocketed drum, cam gate", 3, 1),
    ("patient", "external", "Patient", "one pill at dose time", 3, 2),
    ("audio", "frontend", "Audio Alert", "missed medication", 2, 2),
    ("lcd", "frontend", "LCD Display", "next scheduled dose", 1, 2.5),
], [
    ("hopper", "pi", {"label": "level"}),
    ("jam", "pi", {"label": "current"}),
    ("pi", "motor", {"label": "drive", "v": "emphasis"}),
    ("motor", "drum", {"label": "rotate"}),
    ("drum", "patient", {"label": "dispense", "v": "emphasis", "s": ("bottom", "top"), "labelDy": 26}),
    ("pi", "audio", {"label": "alert"}),
    ("pi", "lcd", {"label": "next dose", "s": ("bottom", "top"), "labelDy": 26}),
], "medicine-dispenser")

# 5. Cooperative multi-robot transport
S["multi-robot-transport"] = spec("Cooperative Multi-Robot Transport: system architecture", [
    ("dxf", "external", "DXF Floor Plan", "architectural drawing", 0, 1),
    ("grid", "database", "Occupancy Grid", "walls, furniture, doors", 1, 1),
    ("env", "backend", "Joint Environment", "fixed separation, masks", 2, 1),
    ("pi", "backend", "Policy Iteration", "model-based DP", 3, 0),
    ("vi", "backend", "Value Iteration", "model-based DP", 3, 1),
    ("ql", "backend", "Q-Learning", "model-free RL", 3, 2),
    ("bench", "backend", "Benchmark", "speed, optimality, cost", 4, 1),
], [
    ("dxf", "grid", {"label": "parse"}),
    ("grid", "env", {"label": "states"}),
    ("env", "pi", {"s": ("right", "left")}),
    ("env", "vi"),
    ("env", "ql", {"s": ("right", "left")}),
    ("pi", "bench", {"s": ("right", "left")}),
    ("vi", "bench"),
    ("ql", "bench", {"s": ("right", "left")}),
], "multi-robot-transport")

# 6. TDS plasma cutting monitoring
S["tds-plasma-monitoring"] = spec("TDS Plasma Cutting Monitoring: system architecture", [
    ("acoustic", "external", "Acoustic Sensor", "plasma-arc sound", 0, 0.5),
    ("current", "external", "Current Sensor", "cutting-head power draw", 0, 1.5),
    ("pi", "backend", "Raspberry Pi 4", "sample, buffer, preprocess", 1, 1),
    ("ml", "backend", "ML Model", "backup if thresholds fail", 2, 0),
    ("classifier", "backend", "Classifier", "thickness thresholds", 2, 1),
    ("mysql", "database", "MySQL", "time-series storage", 3, 1),
    ("grafana", "frontend", "Grafana", "dashboards + alerts", 3, 2),
    ("operator", "external", "Operator", "live material check", 2, 2),
], [
    ("acoustic", "pi", {"label": "audio", "labelDy": -24}),
    ("current", "pi", {"label": "current"}),
    ("pi", "classifier", {"label": "features"}),
    ("ml", "classifier", {"v": "dashed"}),
    ("classifier", "mysql", {"label": "results"}),
    ("mysql", "grafana", {"label": "query", "s": ("bottom", "top"), "labelDy": 26}),
    ("grafana", "operator", {"label": "alerts"}),
], "tds-plasma-monitoring", boundaries=[{"kind": "region", "label": "Client site: Raspberry Pi 4", "wraps": ["pi", "classifier"]}])

# 7. Terrain-aware path planning
S["terrain-path-planning"] = spec("Terrain-Aware Path Planning: system architecture", [
    ("lidar", "external", "LiDAR", "geometric obstacles", 0, 0.5),
    ("rgbd", "external", "RGB-D Camera", "color + depth", 0, 1.5),
    ("fusion", "backend", "Sensor Fusion", "synchronized streams", 1, 1),
    ("seg", "backend", "DeepLabV3+", "3 terrain classes", 2, 1),
    ("costmap", "database", "Semantic Costmap", "ROS2, smoothed", 3, 1),
    ("planner", "backend", "A* and RRT*", "terrain-aware planners", 4, 1),
    ("baseline", "backend", "Binary Baseline", "obstacle or free only", 4, 0),
    ("robot", "external", "Gazebo Robot", "closes the loop", 4, 2),
], [
    ("lidar", "fusion", {"label": "range"}),
    ("rgbd", "fusion", {"label": "RGB-D"}),
    ("fusion", "seg", {"label": "frames"}),
    ("seg", "costmap", {"label": "classes"}),
    ("costmap", "planner", {"label": "costs"}),
    ("baseline", "planner", {"label": "compared", "v": "dashed", "s": ("bottom", "top"), "labelDy": 26}),
    ("planner", "robot", {"label": "path", "v": "emphasis", "s": ("bottom", "top"), "labelDy": 26}),
], "terrain-path-planning")

if __name__ == "__main__":
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "specs")
    os.makedirs(d, exist_ok=True)
    for k, v in S.items():
        json.dump(v, open(os.path.join(d, k + ".json"), "w"), indent=2)
        print("wrote", k, len(v["components"]), "nodes", len(v["connections"]), "edges")
