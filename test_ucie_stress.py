#!/usr/bin/env python3
"""Minimal mock UCIe stress-test runner for the NeuroMesh dashboard.
Generates realistic-looking DV log output when no real simulator is available.
Accepts the same CLI flags as a real regression runner.
"""

import argparse
import random
import sys
import time


CHECKPOINTS = [
    ("0x0000_0000", "ROM_INIT"),
    ("0x0000_0010", "CLOCK_TREE_LOCK"),
    ("0x0000_0020", "PLL_CALIBRATE"),
    ("0x0000_0030", "DRAM_INIT"),
    ("0x0000_0040", "MEM_BIST"),
    ("0x0000_0050", "FABRIC_INIT"),
    ("0x0000_0060", "UCIE_LINK_TRAIN"),
    ("0x0000_0070", "CREDIT_POOL_INIT"),
    ("0x0000_0080", "CXL_ENUMERATE"),
    ("0x0000_0090", "WEIGHT_LOAD"),
    ("0x0000_00A0", "NPU_ACTIVATE"),
    ("0x0000_00B0", "DV_READY"),
]

SEED_LOG_TEMPLATES = [
    "[SEED {seed}] Generating {cmds} commands x {upds} updates",
    "[SEED {seed}] Weight update engine ONLINE",
    "[SEED {seed}] Initialising UCIe link lanes 0-15",
    "[SEED {seed}] Link training: 16/16 lanes locked @ 32 GT/s",
    "[SEED {seed}] Credit pool: rx_credits={cr} tx_credits={cr}",
    "[SEED {seed}] Dispatching {cmds} compute commands",
    "[SEED {seed}] Command queue depth: {qdepth}",
    "[SEED {seed}] Backpressure events detected: {bp}",
    "[SEED {seed}] Collision events detected: {col}",
    "[SEED {seed}] Remote transactions: {rtx}",
    "[SEED {seed}] Local transactions: {ltx}",
    "[SEED {seed}] {upds} weight updates completed",
    "[SEED {seed}] Dropped weight counter: 0",
    "[SEED {seed}] Deadlock monitor: CLEAN",
    "[SEED {seed}] Finalising...",
]


def run_seed(seed: int, commands: int, updates: int) -> None:
    """Run one seed and print formatted DV log lines."""
    credits = random.randint(4, 16)
    bp = random.randint(200, 600)
    col = random.randint(100, 400)
    rtx = random.randint(80, 150)
    ltx = random.randint(90, 160)

    for template in SEED_LOG_TEMPLATES:
        line = template.format(
            seed=seed,
            cmds=commands,
            upds=updates,
            cr=credits,
            bp=bp,
            col=col,
            rtx=rtx,
            ltx=ltx,
            qdepth=random.randint(2, 8),
        )
        print(line, flush=True)
        time.sleep(random.uniform(0.01, 0.06))
    print(f"DV_PASS seed={seed} commands={commands} updates={updates} backpressure={bp} collisions={col} deadlocks=0", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Mock UCIe stress-test regression runner")
    parser.add_argument("--seeds", type=int, default=1, help="Number of seeds (1-5)")
    parser.add_argument("--commands", type=int, default=10, help="Commands per seed")
    parser.add_argument("--updates", type=int, default=120, help="Weight updates per seed")
    parser.add_argument("--waves", action="store_true", help="(ignored — no real VCD)")
    parser.add_argument("--keep-build", action="store_true", help="(ignored — no real build)")
    args = parser.parse_args()

    random.seed(73191)

    print(f"=== UCIe Stress Regression ===", flush=True)
    print(f"Seeds: {args.seeds}  Commands: {args.commands}  Updates: {args.updates}", flush=True)
    print(f"Simulator: Mock (no real RTL available)", flush=True)
    print(f"---", flush=True)

    for s in range(args.seeds):
        print(f"\n=== SEED {s} ===", flush=True)
        run_seed(s, args.commands, args.updates)
        time.sleep(0.05)

    print(f"\n=== REGRESSION COMPLETE ===", flush=True)
    print(f"All {args.seeds} seed(s) PASSED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
