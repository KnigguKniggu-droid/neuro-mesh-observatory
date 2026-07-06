#!/usr/bin/env python3
"""Plot UCIe credit, CDC, collision, and backpressure activity from a VCD.

The parser intentionally uses only the Python standard library; matplotlib is
the sole plotting dependency.  With no --vcd argument, the newest waveform
under work/ucie_stress/seed_*/ucie_stress.vcd is selected automatically.
"""

from __future__ import annotations

import argparse
import bisect
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent

SIGNALS = {
    "clk": "tb_ucie_stress.clk",
    "upd_clk": "tb_ucie_stress.upd_clk",
    "credits": "tb_ucie_stress.ucie_available_credits",
    "link_active": "tb_ucie_stress.ucie_link_active",
    "req_valid": "tb_ucie_stress.pooled_mem_req_valid",
    "req_ready": "tb_ucie_stress.pooled_mem_req_ready",
    "rsp_valid": "tb_ucie_stress.pooled_mem_rsp_valid",
    "rsp_ready": "tb_ucie_stress.pooled_mem_rsp_ready",
    "update_valid": "tb_ucie_stress.update_valid",
    "update_ready": "tb_ucie_stress.update_ready",
    "local_valid": "tb_ucie_stress.local_mem_req_valid",
    "local_ready": "tb_ucie_stress.local_mem_req_ready",
    "collision_count": "tb_ucie_stress.collision_cycles",
}


@dataclass
class VCDData:
    timescale_ns: float
    end_tick: int
    changes: dict[str, list[tuple[int, int | None]]]


def _timescale_to_ns(text: str) -> float:
    match = re.fullmatch(r"\s*(\d+)\s*(fs|ps|ns|us|ms|s)\s*", text)
    if not match:
        raise ValueError(f"unsupported VCD timescale: {text!r}")
    magnitude = int(match.group(1))
    unit_ns = {"fs": 1e-6, "ps": 1e-3, "ns": 1.0, "us": 1e3, "ms": 1e6, "s": 1e9}
    return magnitude * unit_ns[match.group(2)]


def _decode_binary(bits: str) -> int | None:
    bits = bits.lower()
    if "x" in bits or "z" in bits:
        return None
    return int(bits, 2)


def parse_vcd(path: Path, requested: dict[str, str] = SIGNALS) -> VCDData:
    """Parse selected scalar/vector traces without loading unrelated VCD data."""
    scopes: list[str] = []
    name_to_code: dict[str, str] = {}
    timescale_text = "1ns"
    reading_timescale = False

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("$scope"):
                parts = line.split()
                scopes.append(parts[2])
            elif line.startswith("$upscope"):
                if scopes:
                    scopes.pop()
            elif line.startswith("$var"):
                parts = line.split()
                if len(parts) >= 6:
                    code, reference = parts[3], parts[4]
                    name_to_code[".".join([*scopes, reference])] = code
            elif line.startswith("$timescale"):
                content = line.removeprefix("$timescale").replace("$end", "").strip()
                if content:
                    timescale_text = content
                else:
                    reading_timescale = True
            elif reading_timescale:
                if line != "$end":
                    timescale_text = line.replace("$end", "").strip()
                if "$end" in line or line == "$end":
                    reading_timescale = False
            elif line.startswith("$enddefinitions"):
                break

        selected_codes: dict[str, list[str]] = {}
        missing: list[str] = []
        for key, full_name in requested.items():
            code = name_to_code.get(full_name)
            if code is None:
                # Accept simulator-specific extra scopes by matching suffixes.
                matches = [candidate for name, candidate in name_to_code.items() if name.endswith("." + full_name.split(".")[-1])]
                code = matches[0] if matches else None
            if code is None:
                missing.append(full_name)
            else:
                selected_codes.setdefault(code, []).append(key)
        if missing:
            raise KeyError("signals absent from VCD: " + ", ".join(missing))

        changes: dict[str, list[tuple[int, int | None]]] = {key: [] for key in requested}
        current_tick = 0
        end_tick = 0
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line[0] == "#":
                current_tick = int(line[1:])
                end_tick = max(end_tick, current_tick)
                continue
            if line[0] in "01xXzZ":
                value = None if line[0].lower() in "xz" else int(line[0])
                code = line[1:].strip()
            elif line[0] in "bB":
                fields = line[1:].split(maxsplit=1)
                if len(fields) != 2:
                    continue
                value, code = _decode_binary(fields[0]), fields[1]
            else:
                continue
            for key in selected_codes.get(code, []):
                trace = changes[key]
                if not trace or trace[-1][1] != value:
                    trace.append((current_tick, value))

    return VCDData(_timescale_to_ns(timescale_text), end_tick, changes)


def find_latest_vcd() -> Path:
    candidates = list((ROOT / "work" / "ucie_stress").glob("seed_*/ucie_stress.vcd"))
    direct = ROOT / "ucie_stress.vcd"
    if direct.exists():
        candidates.append(direct)
    if not candidates:
        raise FileNotFoundError("no VCD found; run test_ucie_stress.py with waveform dumping enabled")
    return max(candidates, key=lambda item: item.stat().st_mtime)


def value_at(trace: list[tuple[int, int | None]], tick: int) -> int:
    if not trace:
        return 0
    index = bisect.bisect_right(trace, tick, key=lambda entry: entry[0]) - 1
    if index < 0:
        return 0
    value = trace[index][1]
    if value is not None:
        return value
    # Walk back to the most recent known value.
    while index >= 0:
        value = trace[index][1]
        if value is not None:
            return value
        index -= 1
    return 0


def union_ticks(changes: dict[str, list[tuple[int, int | None]]], extra: Iterable[int] = ()) -> list[int]:
    ticks = set(extra)
    for trace in changes.values():
        ticks.update(tick for tick, _ in trace)
    return sorted(ticks)


def choose_window(data: VCDData, window_ns: float, start_ns: float | None, full: bool) -> tuple[int, int]:
    if full:
        return 0, data.end_tick
    window_ticks = max(1, round(window_ns / data.timescale_ns))
    if start_ns is not None:
        start = max(0, round(start_ns / data.timescale_ns))
        return start, min(data.end_tick, start + window_ticks)

    credits_trace = data.changes["credits"]
    max_credits = max((value or 0) for _, value in credits_trace)
    all_ticks = union_ticks(data.changes, [0, data.end_tick])
    focus = None
    for tick in all_ticks:
        credits = value_at(credits_trace, tick)
        req_stall = value_at(data.changes["req_valid"], tick) and not value_at(data.changes["req_ready"], tick)
        overlap = value_at(data.changes["update_valid"], tick) and value_at(data.changes["link_active"], tick)
        if credits < max_credits and (req_stall or overlap):
            focus = tick
            break
    if focus is None:
        focus = next((tick for tick, value in credits_trace if value is not None and value < max_credits), data.end_tick // 2)
    start = max(0, focus - window_ticks // 4)
    end = min(data.end_tick, start + window_ticks)
    start = max(0, end - window_ticks)
    return start, end


def plot_waveforms(data: VCDData, source: Path, output: Path, window_ns: float, start_ns: float | None, full: bool) -> None:
    start_tick, end_tick = choose_window(data, window_ns, start_ns, full)
    ticks = union_ticks(data.changes, [start_tick, end_tick])
    ticks = [tick for tick in ticks if start_tick <= tick <= end_tick]
    x = np.asarray([tick * data.timescale_ns for tick in ticks])
    values = {
        key: np.asarray([value_at(trace, tick) for tick in ticks], dtype=float)
        for key, trace in data.changes.items()
    }

    max_credits = max(1.0, float(np.max(values["credits"])))
    credit_pressure = values["credits"] < max_credits
    pooled_stall = (values["req_valid"] > 0) & (values["req_ready"] == 0)
    update_stall = (values["update_valid"] > 0) & (values["update_ready"] == 0)
    collision = (values["update_valid"] > 0) & (values["link_active"] > 0)

    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.facecolor": "#f8fafc",
            "figure.facecolor": "white",
            "grid.color": "#cbd5e1",
            "grid.alpha": 0.45,
        }
    )
    fig, axes = plt.subplots(
        5,
        1,
        figsize=(15, 10),
        sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.15, 2.0, 1.3, 1.3]},
    )
    fig.suptitle(
        "UCIe Chiplet Credit and CDC Backpressure Timing",
        fontsize=16,
        fontweight="bold",
        color="#0f172a",
        y=0.985,
    )

    # Clock tracks.
    axes[0].step(x, values["clk"] + 1.6, where="post", color="#2563eb", linewidth=0.9, label="compute clk")
    axes[0].step(x, values["upd_clk"], where="post", color="#7c3aed", linewidth=0.9, label="update clk")
    axes[0].set_yticks([0.5, 2.1], ["upd_clk", "clk"])
    axes[0].set_ylim(-0.25, 2.9)
    axes[0].set_title("Independent jittered clock domains", loc="left", fontweight="bold")

    # Credits and occupied-credit shading.
    axes[1].step(x, values["credits"], where="post", color="#0f766e", linewidth=2.0, label="available credits")
    axes[1].fill_between(x, 0, max_credits + 0.3, where=credit_pressure, step="post", color="#f59e0b", alpha=0.17, label="credit occupied")
    axes[1].set_ylabel("credits")
    axes[1].set_ylim(-0.15, max_credits + 0.55)
    axes[1].set_yticks(range(int(max_credits) + 1))
    axes[1].set_title("Credit ownership (drop marks an in-flight pooled transaction)", loc="left", fontweight="bold")
    axes[1].legend(loc="upper right", ncol=2, frameon=False)

    # Link and endpoint control tracks.
    control_tracks = [
        ("link_active", "link active", "#0f766e"),
        ("req_valid", "request valid", "#2563eb"),
        ("req_ready", "request ready", "#60a5fa"),
        ("rsp_valid", "response valid", "#7c3aed"),
        ("rsp_ready", "response ready", "#a78bfa"),
    ]
    control_ticks, control_labels = [], []
    for index, (key, label, color) in enumerate(control_tracks):
        base = index * 1.45
        axes[2].step(x, values[key] + base, where="post", color=color, linewidth=1.25)
        control_ticks.append(base + 0.5)
        control_labels.append(label)
    axes[2].set_yticks(control_ticks, control_labels)
    axes[2].set_ylim(-0.25, len(control_tracks) * 1.45)
    axes[2].set_title("Pooled-memory request/response handshakes", loc="left", fontweight="bold")

    # Backpressure pulses, shaded whenever a credit is occupied.
    axes[3].fill_between(x, -0.15, 2.8, where=credit_pressure, step="post", color="#f59e0b", alpha=0.10)
    axes[3].step(x, pooled_stall.astype(float) + 1.5, where="post", color="#dc2626", linewidth=1.7)
    axes[3].step(x, update_stall.astype(float), where="post", color="#ea580c", linewidth=1.4)
    axes[3].set_yticks([0.5, 2.0], ["update FIFO stall", "pooled req stall"])
    axes[3].set_ylim(-0.25, 2.8)
    axes[3].set_title("Backpressure assertions (valid && !ready)", loc="left", fontweight="bold")

    # Derived collision/overlap plus cumulative counter from the testbench.
    axes[4].step(x, collision.astype(float), where="post", color="#be123c", linewidth=1.6, label="update × link overlap")
    axes[4].set_ylim(-0.15, 1.35)
    axes[4].set_yticks([0, 1], ["clear", "overlap"])
    axes[4].set_title("Cross-domain traffic collision window", loc="left", fontweight="bold")
    collision_axis = axes[4].twinx()
    collision_axis.step(x, values["collision_count"], where="post", color="#475569", linewidth=1.0, alpha=0.8, label="cumulative collisions")
    collision_axis.set_ylabel("cumulative")
    collision_axis.tick_params(axis="y", colors="#475569")

    for axis in axes:
        axis.grid(True, axis="x")
        axis.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("simulation time (ns)")
    axes[-1].set_xlim(start_tick * data.timescale_ns, end_tick * data.timescale_ns)

    fig.text(
        0.012,
        0.008,
        f"Source: {source.name}  |  shaded amber: available credits below maximum  |  red/orange: backpressure",
        color="#475569",
        fontsize=8,
    )
    fig.subplots_adjust(left=0.16, right=0.95, top=0.90, bottom=0.09, hspace=0.38)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vcd", type=Path, help="input VCD; defaults to newest stress-run VCD")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs" / "ucie_waveforms.png",
        help="output PNG path",
    )
    parser.add_argument("--window-ns", type=float, default=1200.0, help="automatic focus-window width")
    parser.add_argument("--start-ns", type=float, help="explicit window start")
    parser.add_argument("--full", action="store_true", help="plot the entire simulation")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = (args.vcd or find_latest_vcd()).resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    data = parse_vcd(source)
    plot_waveforms(data, source, args.output.resolve(), args.window_ns, args.start_ns, args.full)
    print(f"Waveform chart saved to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
