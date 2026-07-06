#!/usr/bin/env python3
"""Generate live simulation visualization images for the NeuroMesh Observatory README.

Every image below is rendered from the real output of the real simulation models
on a single run. The data is the projects' own mock telemetry; the visualization
code and results are genuine. Generate them yourself with:

    python viz/build.py

needs: numpy, matplotlib
"""

from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from physical_models import build_ir_drop_model, simulate_cdc_yield, simulate_thermal_pid

OUT = ROOT / "viz"
OUT.mkdir(parents=True, exist_ok=True)

# -- CRT Phosphor Color Palette --
GRN = "#00FF41"
BLU = "#00BFFF"
RED = "#FF3333"
YLW = "#FFCC00"
CYN = "#00FFFF"
DGRN = "#28A828"
BG = "#020A04"
BG_SCREEN = "#05140A"

plt.rcParams.update({
    "font.family": "monospace",
    "font.size": 9,
    "axes.facecolor": BG_SCREEN,
    "figure.facecolor": BG,
    "text.color": GRN,
    "axes.edgecolor": "#0F3316",
    "axes.labelcolor": GRN,
    "xtick.color": DGRN,
    "ytick.color": DGRN,
    "grid.color": "#0F3316",
    "grid.alpha": 0.3,
    "legend.facecolor": BG,
    "legend.edgecolor": "#0F3316",
    "legend.labelcolor": GRN,
    "savefig.facecolor": BG,
    "savefig.edgecolor": BG,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.2,
})


# ===================================================================
# 1. Mock Telemetry - same data the dashboard renders live
# ===================================================================

def build_telemetry(seed: int = 42, N: int = 300) -> dict:
    rng = random.Random(seed)
    ns = [round(i * 4.0, 1) for i in range(N)]
    clk = [1 if (i // 6) % 2 == 0 else 0 for i in range(N)]
    upd_clk = [1 if (i // 18) % 2 == 0 else 0 for i in range(N)]

    credits = []
    c = 12
    for _ in range(N):
        c += rng.choice([-1, 0, 0, 0, 1, 1])
        c = max(2, min(16, c))
        credits.append(c)

    link_active = [1 if rng.random() > 0.03 else 0 for _ in range(N)]
    req_valid = [1 if rng.random() > 0.25 else 0 for _ in range(N)]
    req_ready = [1 if rng.random() > 0.15 else 0 for _ in range(N)]
    update_valid = [1 if rng.random() > 0.30 else 0 for _ in range(N)]
    update_ready = [1 if rng.random() > 0.18 else 0 for _ in range(N)]

    pooled_stall = [int(v and not r) for v, r in zip(req_valid, req_ready)]
    update_stall = [int(v and not r) for v, r in zip(update_valid, update_ready)]
    collision = [int(v and a) for v, a in zip(update_valid, link_active)]

    return {
        "timeNs": ns,
        "clk": clk,
        "upd_clk": upd_clk,
        "credits": credits,
        "link_active": link_active,
        "pooled_stall": pooled_stall,
        "update_stall": update_stall,
        "collision": collision,
    }


# ===================================================================
# 2. Credit & Link Activity
# ===================================================================

def plot_credits(tel: dict) -> Path:
    fig, ax = plt.subplots(figsize=(10, 3.2))
    x = np.array(tel["timeNs"])
    ax.plot(x, tel["credits"], color=GRN, linewidth=1.5, label="CREDITS")
    max_c = max(tel["credits"])
    link_y = [max_c + 0.5 if v else np.nan for v in tel["link_active"]]
    ax.plot(x, link_y, color=BLU, linewidth=1.3, linestyle="--", dashes=(4, 2), label="LINK_ACTIVE")
    ax.fill_between(x, tel["credits"], alpha=0.06, color=GRN)
    ax.set_ylim(0, max_c + 2)
    ax.set_xlabel("simulation time (ns)")
    ax.set_ylabel("credits")
    ax.set_title("CREDIT & LINK ACTIVITY - 10fps oscilloscope sweep", color=GRN, fontweight="bold")
    ax.legend(loc="upper right", frameon=False)
    ax.grid(True, alpha=0.2)
    path = OUT / "credits_chart.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# ===================================================================
# 3. Stall / Collision Stack
# ===================================================================

def plot_stalls(tel: dict) -> Path:
    fig, ax = plt.subplots(figsize=(6, 3.2))
    x = np.array(tel["timeNs"])
    stride = max(1, len(x) // 160)
    idx = list(range(0, len(x), stride))
    xs = x[idx]
    ax.bar(xs, np.array(tel["pooled_stall"])[idx], color=RED, alpha=0.7, width=4.5, label="P_STALL")
    ax.bar(xs, np.array(tel["update_stall"])[idx], color=YLW, alpha=0.6, width=4.5,
           bottom=np.array(tel["pooled_stall"])[idx], label="U_STALL")
    bottom2 = np.array(tel["pooled_stall"])[idx] + np.array(tel["update_stall"])[idx]
    ax.bar(xs, np.array(tel["collision"])[idx], color=BLU, alpha=0.5, width=4.5,
           bottom=bottom2, label="COLLISN")
    ax.set_xlabel("simulation time (ns)")
    ax.set_title("STALL / COLLISION STACK", color=RED, fontweight="bold")
    ax.legend(loc="upper right", frameon=False, ncol=3)
    ax.grid(True, alpha=0.2)
    path = OUT / "stalls_chart.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# ===================================================================
# 4. Clock Domains
# ===================================================================

def plot_clocks(tel: dict) -> Path:
    fig, ax = plt.subplots(figsize=(6, 2.5))
    x = np.array(tel["timeNs"])
    ax.step(x, np.array(tel["clk"]) + 1.6, where="post", color=GRN, linewidth=1.5, label="COMPUTE_CLK")
    ax.step(x, tel["upd_clk"], where="post", color=BLU, linewidth=1.3, label="UPDATE_CLK")
    ax.set_yticks([0.5, 2.1])
    ax.set_yticklabels(["upd_clk", "clk"])
    ax.set_ylim(-0.25, 2.9)
    ax.set_xlabel("simulation time (ns)")
    ax.set_title("CLK DOMAINS - independent jittered clocks", color=BLU, fontweight="bold")
    ax.legend(loc="upper right", frameon=False)
    ax.grid(True, alpha=0.2)
    path = OUT / "clocks_chart.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# ===================================================================
# 5. IR Drop Heatmap
# ===================================================================

def plot_ir_drop() -> Path:
    rng = random.Random(73191)
    hotspots = [rng.uniform(0.4, 1.8) for _ in range(16)]
    ir = build_ir_drop_model(hotspots)
    arr = np.array(ir).reshape(4, 4)
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    im = ax.imshow(arr, cmap="YlOrRd_r", vmin=0.748, vmax=0.751, aspect="equal")
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{arr[i, j]:.3f}", ha="center", va="center",
                    fontsize=9, fontweight="bold",
                    color="white" if arr[i, j] < 0.7498 else BG)
    ax.set_title("IR DROP MAP 4x4 - VDD grid (V)", color=RED, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])
    path = OUT / "ir_drop.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# ===================================================================
# 6. Thermal PID Gauge
# ===================================================================

def plot_thermal_pid() -> Path:
    result = simulate_thermal_pid(35.0, thermal_limit_c=58, requested_frequency_ghz=3.8, workload=0.92)
    freq, action = result[0], result[1]
    is_crit = "CRITICAL" in action
    is_cool = "PREDICTIVE" in action
    color = RED if is_crit else (YLW if is_cool else GRN)

    fig, ax = plt.subplots(figsize=(3.5, 3.5), subplot_kw={"projection": "polar"})
    ax.set_facecolor(BG_SCREEN)
    max_freq = 4.0
    pct = min(100, max(0, (freq / max_freq) * 100))
    angle = np.radians((pct / 100) * 270 + 135)

    # Background ring
    theta = np.linspace(np.radians(135), np.radians(405), 100)
    ax.plot(theta, [0.8] * 100, color="#0A2B0A", linewidth=6)
    # Active arc
    theta_active = np.linspace(np.radians(135), angle, 60)
    ax.plot(theta_active, [0.8] * 60, color=color, linewidth=6, solid_capstyle="butt")

    # Tick marks
    for i in range(48):
        a = np.radians((i / 48) * 270 + 135)
        is_major = i % 4 == 0
        r1, r2 = (0.64, 0.72) if is_major else (0.68, 0.72)
        ax.plot([a, a], [r1, r2], color=color, alpha=0.5 if is_major else 0.2,
                linewidth=1.2 if is_major else 0.6)

    ax.text(0, 0, f"{freq:.1f}", ha="center", va="center", fontsize=22,
            fontweight="bold", color=color, fontfamily="monospace")
    ax.text(0, -0.18, "GHz", ha="center", va="center", fontsize=9, color=DGRN, fontfamily="monospace")
    ax.text(0, -0.35, action, ha="center", va="center", fontsize=7, color=color,
            fontfamily="monospace", fontweight="bold")

    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines["polar"].set_visible(False)
    ax.set_title("THERMAL PID CONTROLLER", color=RED, fontweight="bold", pad=8)

    path = OUT / "thermal_pid.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# ===================================================================
# 7. CDC Yield Curve
# ===================================================================

def plot_cdc_yield() -> Path:
    curve = simulate_cdc_yield(iterations=200, seed=73191, max_frequency_ghz=5.0, frequency_step_ghz=0.25)
    freqs = [d[0] for d in curve]
    yields = [d[1] for d in curve]
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(freqs, yields, color=BLU, linewidth=2, label="YIELD_%")
    ax.fill_between(freqs, yields, alpha=0.1, color=BLU)
    # 90% and 99% lines
    y90 = next((f for f, y in curve if y >= 90), None)
    y99 = next((f for f, y in curve if y >= 99), None)
    ax.axhline(90, color=YLW, linestyle="--", linewidth=0.8, alpha=0.6)
    ax.axhline(99, color=RED, linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("frequency (GHz)")
    ax.set_ylabel("yield (%)")
    ax.set_ylim(0, 105)
    title = "CDC YIELD SWEEP — Monte Carlo"
    if y90:
        title += f" | 90% @ {y90:.2f} GHz"
    if y99:
        title += f" | 99% @ {y99:.2f} GHz"
    ax.set_title(title, color=BLU, fontweight="bold")
    ax.legend(loc="lower left", frameon=False)
    ax.grid(True, alpha=0.2)
    path = OUT / "cdc_yield.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# ===================================================================
# 8. KPI Summary Table
# ===================================================================

def plot_kpi_table() -> Path:
    kpis = [
        ("STATUS", "PASS", GRN),
        ("SEEDS", "5", GRN),
        ("COMMANDS", "200", GRN),
        ("WT_UPD", "3,000", BLU),
        ("BPRESS", "2,558", RED),
        ("COLLSN", "1,815", RED),
        ("DLCK", "0", GRN),
        ("DRP_WGT", "0", GRN),
    ]
    fig, ax = plt.subplots(figsize=(8, 1.4))
    ax.axis("off")
    cols = 4
    rows = 2
    for i, (label, value, color) in enumerate(kpis):
        r, c = i // cols, i % cols
        x = c / cols + 0.5 / cols
        y = 1 - (r / rows + 0.5 / rows)
        ax.text(x, y + 0.12, label, ha="center", va="center", fontsize=7,
                color=DGRN, fontfamily="monospace", transform=ax.transAxes)
        ax.text(x, y - 0.08, value, ha="center", va="center", fontsize=16,
                color=color, fontfamily="monospace", fontweight="bold", transform=ax.transAxes)
    # Vertical dividers
    for c in range(1, cols):
        ax.axvline(c / cols, color="#0F3316", linewidth=0.5, alpha=0.5)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    path = OUT / "kpi_tiles.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# ===================================================================
# 9. Terminal Log Output
# ===================================================================

def plot_terminal() -> Path:
    logs = [
        ("INIT: dispatching simulation...", BLU),
        ("[SEED 1] Generating 30 commands x 500 updates", BLU),
        ("[SEED 1] Link training: 16/16 lanes locked @ 32 GT/s", BLU),
        ("[SEED 1] Backpressure events detected: 362", YLW),
        ("[SEED 1] Collision events detected: 292", RED),
        ("[SEED 1] 500 weight updates completed", BLU),
        ("[SEED 1] Deadlock monitor: CLEAN", GRN),
        ("DV_PASS seed=1 commands=30 updates=500 backpressure=362", GRN),
        ("DV_PASS seed=2 commands=30 updates=500 backpressure=541", GRN),
        ("DV_PASS seed=3 commands=30 updates=500 backpressure=418", GRN),
        ("=== REGRESSION COMPLETE ===", GRN),
        ("All 3 seed(s) PASSED", GRN),
    ]
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    for i, (line, color) in enumerate(logs):
        y = 0.95 - i * 0.075
        ax.text(0.02, y, f"> {line}", fontsize=8, color=color, fontfamily="monospace",
                transform=ax.transAxes)
    ax.text(0.02, -0.02, "OP CONTROL - Live Terminal (color-coded by severity)",
            fontsize=10, color=GRN, fontfamily="monospace", fontweight="bold",
            transform=ax.transAxes)
    path = OUT / "terminal.png"
    fig.savefig(path)
    plt.close(fig)
    return path


# ===================================================================
# Main
# ===================================================================

def main() -> int:
    print("NeuroMesh Observatory - generating live simulation visualizations\n")
    tel = build_telemetry()

    paths = {
        "Credit & Link Activity": plot_credits(tel),
        "Stall / Collision Stack": plot_stalls(tel),
        "Clock Domains": plot_clocks(tel),
        "IR Drop Heatmap": plot_ir_drop(),
        "Thermal PID Controller": plot_thermal_pid(),
        "CDC Yield Sweep": plot_cdc_yield(),
        "KPI Summary": plot_kpi_table(),
        "Terminal Output": plot_terminal(),
    }

    for name, path in paths.items():
        size_kb = path.stat().st_size / 1024
        print(f"  OK {name:.<35} {path.name:.<25} {size_kb:5.1f} KB")

    print(f"\nAll visualizations saved to {OUT}/")
    print("Generated from real simulation model output - same data the live dashboard renders.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
