# 🧬 NeuroMesh Observatory

> **Real-time NPU Chiplet Simulation & Verification Dashboard**
>
> CRT Phosphor Oscilloscope UI · UCIe/CXL Stress Testing · IR Drop Modeling · Thermal PID · CDC Yield Sweep · UEFI Firmware · Voice Commands

---

## 🎯 What It Is

NeuroMesh Observatory is a hardware observability dashboard for simulating and verifying a next-generation **Neural Processing Unit (NPU)** built on a **4×4 chiplet mesh architecture**. It surfaces silicon-accurate telemetry, physical modeling, UEFI firmware control, and voice-command interaction in a CRT phosphor oscilloscope-styled interface.

The dashboard simulates a complete AI accelerator verification pipeline — from low-level UCIe link training and credit-based flow control, through physical IR drop and thermal modeling, to firmware-level UEFI POST sequences and frequency yield analysis. Every simulation produces live, animated telemetry.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- NumPy (`pip install numpy`)

### Run the dashboard (30 seconds)

```bash
# Clone the repo
git clone https://github.com/KnigguKniggu-droid/neuro-mesh-observatory.git
cd neuro-mesh-observatory

# Start the server
python serve_dashboard.py --port 8765

# Or on Windows — double-click:
launch_observatory.bat
```

Then open **http://127.0.0.1:8765** in Chrome.

### Run your first simulation

1. In the **OP CONTROL** panel, set: SEEDS=3, COMMANDS=30, UPDATES=500
2. Click **▶ EXEC_SIM**
3. Watch live simulation logs stream in the terminal
4. All 4 charts + 8 KPIs update in real-time

---

## 🖥️ Dashboard Architecture

The dashboard is a single HTML file (`dashboard/index.html`) with zero framework dependencies — just **Chart.js**, **Canvas API**, and **Web Speech API** loaded from CDN. The Python server (`serve_dashboard.py`) uses only the standard library.

```
┌──────────────────────────────────────────────────────────────┐
│  [HERO] > NEUROMESH OBSERVATORY                               │
│  Mock 3nm · 4×4 Mesh · HBM4/GDDR7 · UCIe/CXL · Voice Pipeline│
├──────────────────────────────────────────────────────────────┤
│  [TOPBAR] OBSERVATORY  [VOICE]  ···  TS: 14:32:01  STAT ● IDLE│
├──────────┬──────────┬──────────┬──────────────────────────────┤
│  SYS_CFG │REG_SUMMARY│ VCD_META │  CREDIT & LINK ACTIVITY       │
│  TECH    │ SEEDS    │ AVAILABLE│  ████████████░░░░ CREDITS     │
│  PRECIS. │ CMDS     │ DURATION │  ─ ─ ─ ─ ─ ─  LINK_ACTIVE  │
│  MESH    │ UPDATES  │ POINTS   │  10fps oscilloscope sweep     │
│  MEMORY  │ LOCAL_TX │ CRDT_MIN │                                │
│  INTERC. │ REMOTE_TX│ CRDT_MAX │                                │
├──────────┴──────────┴──────────┴──────────────────────────────┤
│  [KPI: STATUS] [SEEDS] [CMDS] [WT_UPD] [BPRESS] [COLLSN] ... │
├──────────────────────┬──────────────────────┬─────────────────┤
│  STALL/COLLISION     │  CLK DOMAINS         │  IR DROP MAP     │
│  ▓▓▓▓ P_STALL       │  ═══ COMPUTE_CLK    │  ┌──┬──┬──┬──┐  │
│  ▓▓▓▓ U_STALL       │  ─── UPDATE_CLK     │  │.75│.75│.75│.75│ │
│  ▓▓▓▓ COLLISN       │                      │  ├──┼──┼──┼──┤  │
│                      │                      │  │.75│.75│.75│.75│ │
├──────────────────────┴──────────────────────┴─────────────────┤
│  UEFI BOOT ROM       │  THERMAL PID CTRL   │  CDC YIELD SWEEP  │
│  > [0x00] SEC: OK   │      ╭──╮           │  ████████▌ YIELD  │
│  > [0x01] PEI: OK   │     ╱    ╲          │  Monte Carlo sweep│
│  > [0x02] DXE: OK   │    │ 3.2  │         │  90% @ 3.8 GHz   │
│  [▶ POST] [REGS]    │    │ GHz  │         │  99% @ 2.9 GHz   │
│                      │     ╲    ╱          │  [▶ SWEEP]        │
│                      │      ╰──╯           │                   │
├──────────────────────────────────────────────────────────────┤
│  OP CONTROL                                    [▶ EXEC_SIM]   │
│  SEEDS [3] CMDS [30] UPDATES [500]  [▶ EXEC_SIM] [↻ POLL]  │
│  > DV_PASS seed=1 commands=30 updates=500 backpressure=362   │
│  > DV_PASS seed=2 commands=30 updates=500 backpressure=541   │
│  > All 3 seed(s) PASSED                                      │
├──────────────────────────────────────────────────────────────┤
│  UCIE LINK LIVE  |  PLL 3.80 GHz  |  DIE 62°C  |  READY     │
└──────────────────────────────────────────────────────────────┘
```

---

## 📊 Live Dashboard Sections — In Detail

### 1. KPI Row (8 Real-time Tiles)

| KPI | What it tracks | Color |
|---|---|---|
| **STATUS** | Regression pass/fail state | 🟢 Green (PASS) / 🔴 Red (FAIL) |
| **SEEDS** | Number of random seeds tested | Green |
| **COMMANDS** | Compute commands dispatched per seed | Green |
| **WT_UPDATES** | Weight update operations completed | 🔵 Blue |
| **BACKPRESS** | Cycles where pooled memory stalled | 🔴 Red |
| **COLLISIONS** | Cross-domain traffic collision windows | 🔴 Red |
| **DEADLOCKS** | Deadlock monitor results (0 = clean) | 🔴 Red if > 0 |
| **DROPPED_WEIGHTS** | Weight counter drops (0 = clean) | 🔴 Red if > 0 |

### 2. Credit & Link Activity Chart (Live Oscilloscope)

**Two overlapping traces** swept at 10fps across 300 telemetry points:

- **CREDITS** (🟢 green line): UCIe available credit pool — drops when pooled memory transactions are in-flight. Simulates credit-based flow control between chiplets.
- **LINK_ACTIVE** (🔵 blue dashed line): UCIe link status — toggles when the physical link is trained and active (16 lanes @ 32 GT/s).

> **What it simulates**: UCIe credit arbitration — each remote memory request consumes 1 credit, released on response. Backpressure occurs when credits hit 0.

### 3. Stall / Collision Stack Chart

**Stacked bar chart** showing three categories of fabric congestion:

- **P_STALL** (🔴 red): Pooled memory request stalls — `req_valid && !req_ready`
- **U_STALL** (🟡 yellow): Update FIFO backpressure — `update_valid && !update_ready`
- **COLLISN** (🔵 blue): Cross-domain traffic collisions — `update_valid && link_active`

> **What it simulates**: Multi-port memory controller contention. When local compute and remote updates compete for the same memory bank, stalls and collisions cascade through the fabric.

### 4. Clock Domains Chart

**Two independent jittered clock domains** on the same timeline:

- **COMPUTE_CLK** (🟢 green): Main compute clock — toggles at ~1.5 GHz effective
- **UPDATE_CLK** (🔵 blue): Weight update clock — slower, independent domain

> **What it simulates**: CDC (Clock Domain Crossing) behavior. The two clocks are intentionally desynchronized with randomized jitter to stress-test CDC FIFOs and metastability hardening.

### 5. IR Drop Map (4×4 Heatmap)

A **4×4 grid** representing voltage degradation across the chiplet mesh power grid. Each cell shows the actual voltage at that tile location.

- **Bright green** → near nominal voltage (0.750V)
- **Darker green** → voltage droop (down to ~0.749V under load)

> **What it simulates**: Dynamic VDD power grid IR drop using `build_ir_drop_model()`. Per-tile activity hotspots draw current through the power delivery network, causing localized voltage droop. Critical for timing closure signoff.

### 6. UEFI Boot ROM Panel

A **firmware-level emulator** with:

- **POST sequence** (8 checkpoints): SEC → PEI → DXE → BDS → TSL → RT → AL → WRAPUP
- Each checkpoint animates in with fade-in, showing the phase name and result
- **Register dump modal**: Full UEFI register state (frequency, thermal, CDC, PLL, wrapup)
- **WRAPUP button**: 8-step emergency thermal shutdown sequence

> **What it simulates**: UEFI-style boot firmware for an AI accelerator. Configures PLL, trains CDC, runs thermal calibration loop, and performs frequency yield sweep — all before releasing the accelerator to the OS.

### 7. Thermal PID Controller

**Animated canvas ring gauge** showing real-time thermal throttling:

- 🟢 **STABLE** (green ring): Normal operation, frequency at target
- 🟡 **PREDICTIVE COOLING** (yellow ring): Approaching thermal limit, throttled to 85%
- 🔴 **CRITICAL THROTTLE** (red ring): Exceeded safe temperature, aggressively throttled

Controls: **LIMIT C** (thermal limit in °C), **CLK GHz** (target frequency), **LOAD a** (workload 0–1)

> **What it simulates**: Predictive thermal management with environmental modifiers. Ambient temperature penalty, workload-driven temp boost, and duration-aware ramp factor. The PID loop runs in continuous animation via `requestAnimationFrame`.

### 8. CDC Yield Sweep

**Monte Carlo statistical analysis** chart with blue fill:

- Sweeps frequency from 2.5–5.0 GHz
- At each frequency step, runs N iterations with randomized gate propagation delays (σ=0.04ns jitter)
- Reports **90% yield frequency** and **99% yield frequency**

Controls: **ITER/Pt** (Monte Carlo iterations per point), **SEED** (random seed), **GHZ MAX** (upper sweep bound), **STEP kHz** (frequency resolution)

> **What it simulates**: Statistical timing analysis for clock domain crossing. Randomized jitter models process variation. The yield curve shows what frequency the CDC can reliably operate at across manufacturing corners.

### 9. OP CONTROL + Live Terminal

The simulation command center:

- **SEEDS / COMMANDS / UPDATES** inputs with color-coded labels
- **▶ EXEC_SIM** launches multi-seed UCIe stress regression
- **↻ POLL** fetches latest snapshot
- **Live terminal** streams simulation output with color-coded log levels:
  - 🔵 Blue: info/status messages (link training, credit init, dispatch)
  - 🟢 Green: DV_PASS results
  - 🟡 Yellow: warnings/throttle events
  - 🔴 Red: errors, deadlocks, failures

### 10. Voice Command Pipeline

12+ voice commands via **Web Speech API** (Chrome only):

| Command | Action |
|---|---|
| "run simulation" | Execute regression |
| "run thermal" | Run thermal PID controller |
| "run sweep" | Run CDC yield sweep |
| "boot" | Execute UEFI POST |
| "show registers" | Open register dump modal |
| "refresh" | Poll latest snapshot |
| "shutdown" | Initiate thermal wrap-up |
| "show credits" | Display about/version info |
| "status" | Report system status |
| "help" | List all voice commands |

The voice button pulses green when listening, amber when processing.

---

## 🔬 Physical Models — How They Work

### IR Drop Model (`build_ir_drop_model`)

```python
# Per-tile activity → current draw → voltage drop
current_draw = activity_matrix * 12.5          # mA
voltage_drop = current_draw * resistance / 1000  # V = I × R
actual_voltage = base_voltage - voltage_drop     # clipped to [0.62, 0.75]V
```

Configurable: `base_voltage` (default 0.75V), `resistance_per_segment` (default 0.05Ω). Accepts any array shape — automatically reshapes to 4×4 grid.

### Thermal PID Controller (`simulate_thermal_pid`)

```python
# Environmental modifiers
effective_temp = hotspot_max + (workload × 8.0°C) + (ambient_penalty)
ramp_factor = min(1.0, duration_us / 200.0)

# Three-zone control
if temp >= max_safe:
    throttled = freq × (max_safe / temp)    # CRITICAL THROTTLE
elif temp > (max_safe - 4.0):
    throttled = freq × 0.85                 # PREDICTIVE COOLING
else:
    throttled = freq                        # STABLE
```

### CDC Yield Sweep (`simulate_cdc_yield`)

```python
# Monte Carlo per frequency step
for freq in sweep_range:
    failures = 0
    for _ in range(iterations):
        jitter = normal(μ=0.12ns, σ=0.04ns)    # gate delay variation
        cycle_time = 1000.0 / freq               # clock period in ps
        if (cycle_time - jitter) < 15.0ps:       # timing violation
            failures += 1
    yield% = (iterations - failures) / iterations × 100
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Simulation Engine | Python 3 | UCIe/CXL stress-test regression runner with VCD waveform parsing |
| Physical Models | NumPy | IR drop power grid, thermal PID, Monte Carlo CDC yield |
| UEFI Firmware | Python | Full Boot ROM emulation with POST checkpoints, register dump, thermal loop, frequency stepping, wrap-up sequence |
| Dashboard Frontend | Vanilla HTML/CSS/JS | Zero frameworks. Chart.js for oscilloscope traces, Canvas API for particle system + thermal ring gauge, Web Speech API for voice |
| Real-time Streaming | SSE + WebSocket | Simulation log streaming, voice transcript relay, telemetry push |
| Server | Python stdlib `http.server` | Zero-dependency, threaded, REST API + SSE event bus + WebSocket upgrade |
| VCD Parsing | Custom Python parser | Industry-standard Value Change Dump files — 13+ signals extracted into 300-point telemetry arrays |

---

## 🎨 Design System — CRT Phosphor Oscilloscope

| Color | Hex | CSS Variable | Usage |
|---|---|---|---|
| Neon Green | `#00FF41` | `--phos-bright` | Primary phosphor, CRT heritage, status OK |
| Dim Green | `#28A828` | `--phos-dim` | Secondary text, muted elements |
| Neon Blue | `#00BFFF` | `--trace-blue` | Data paths, clock domains, yield analysis, info logs |
| Cyan | `#00FFFF` | `--trace-cyan` | Datapath highlighting |
| Yellow | `#FFCC00` | `--trace-warn` | Warnings, predictive cooling, U_STALL |
| Red | `#FF3333` | `--trace-crit` | Critical alerts, P_STALL, thermal CRITICAL, errors |

**Fonts**: VT323 (hero/headings) · Share Tech Mono (labels/topbar) · JetBrains Mono (terminal/data)

**Effects**: CRT scanlines overlay · vignette gradient · graticule grid · hardware instrument topbar · rounded inset screen panels · brightness hover (no 3D tilt) · horizontal electron particles (green + blue + red)

---

## 📂 Project Structure

```
neuro-mesh-observatory/
├── serve_dashboard.py          # HTTP server + REST API + SSE + WebSocket
├── physical_models.py          # IR drop, thermal PID, CDC yield models
├── plot_ucie_waveforms.py      # VCD waveform parser + matplotlib plotter
├── uefi_firmware.py            # UEFI Boot ROM emulator (registers, POST, CDC, thermal, wrapup)
├── test_ucie_stress.py         # UCIe stress-test regression runner
├── launch_observatory.bat      # Windows one-click launcher
├── dashboard/
│   └── index.html              # CRT Phosphor dashboard (single-file, 800+ lines)
├── skills_reference.html       # 72-skills design catalog
├── skillforge.html             # Skill forge reference
├── artifact.html               # Build artifact viewer
├── HOW_ITS_MADE.md             # Development journey documentation
└── .agents/skills/             # Codebuff agent skills (banner-design, brand, design, etc.)
```

---

## 🔧 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/snapshot` | GET | Full dashboard state (regression, telemetry, physical models, UEFI) |
| `/api/status` | GET | Simulation runner status (running/phase/logs) |
| `/api/run` | POST | Launch UCIe stress regression with seeds/commands/updates |
| `/api/events` | GET | SSE stream — real-time simulation events + bootstrap snapshot |
| `/ws` | GET | WebSocket upgrade — voice transcript relay + live event push |
| `/api/uefi/boot` | POST | Execute UEFI POST sequence with clock/thermal config |
| `/api/uefi/status` | GET | UEFI register dump |
| `/api/uefi/thermal` | POST | Run thermal PID loop |
| `/api/uefi/cdc` | POST | Run CDC yield sweep |
| `/api/uefi/wrapup` | POST | Execute thermal wrap-up shutdown sequence |
| `/api/uefi/freq-step` | POST | Adjust PLL frequency by delta steps |

---

## 📄 License

MIT — see [LICENSE](LICENSE) file.

---

Built with ❤️ by [KnigguKniggu-droid](https://github.com/KnigguKniggu-droid)
