# 🧬 NeuroMesh Observatory

> **Real-time NPU Chiplet Simulation & Verification Dashboard**
> 
> CRT Phosphor Oscilloscope UI · UCIe/CXL Stress Testing · IR Drop Modeling · Thermal PID · CDC Yield Sweep · UEFI Firmware · Voice Commands

---

## 🎯 What It Is

NeuroMesh Observatory is a hardware observability dashboard for simulating and verifying a next-generation **Neural Processing Unit (NPU)** built on a **4×4 chiplet mesh** architecture. It surfaces silicon-accurate telemetry, physical modeling, UEFI firmware control, and voice-command interaction in a CRT phosphor oscilloscope-styled interface.

---

## 🖥️ Dashboard Preview

The dashboard features a **three-color neon palette** (green/blue/red) across:
- **8 KPI tiles** — STATUS, SEEDS, COMMANDS, WT_UPDATES, BACKPRESSURE, COLLISIONS, DEADLOCKS, DROPPED_WEIGHTS
- **4 live charts** with 10fps oscilloscope sweep animation
- **IR Drop heatmap** — 4×4 grid with per-cell RGB glow
- **Thermal PID ring gauge** — animated canvas dial with tick marks
- **UEFI Boot ROM** — step-by-step POST logging + register dump modal
- **Voice commands** — 12+ recognized phrases via Web Speech API
- **SSE + WebSocket** — real-time simulation log streaming

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Simulation Engine | Python — UCIe/CXL stress-test regression |
| Physical Models | NumPy — IR drop, thermal PID, Monte Carlo CDC yield |
| UEFI Firmware | Python — Boot ROM emulator with POST + registers + wrap-up |
| Dashboard Frontend | Vanilla HTML/CSS/JS — Chart.js, Canvas API, Web Speech API |
| Real-time Streaming | Server-Sent Events (SSE) + WebSocket |
| Server | Python stdlib `http.server` — zero-dependency |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- No pip installs required (stdlib only, plus NumPy for physical models)

### Run the dashboard

```bash
# Start the server
python serve_dashboard.py --port 8765

# Or use the launcher (Windows)
launch_observatory.bat
```

Then open **http://127.0.0.1:8765** in your browser.

### Run a simulation

1. Open the dashboard
2. In the **OP CONTROL** panel, set SEEDS / COMMANDS / UPDATES
3. Click **▶ EXEC_SIM**
4. Watch live logs stream in the terminal + charts animate

---

## 📂 Project Structure

```
neuro-mesh-observatory/
├── serve_dashboard.py          # HTTP server + REST API + SSE + WebSocket
├── physical_models.py          # IR drop, thermal PID, CDC yield models
├── plot_ucie_waveforms.py      # VCD waveform parser + matplotlib plotter
├── uefi_firmware.py            # UEFI Boot ROM emulator
├── test_ucie_stress.py         # UCIe stress-test regression runner
├── launch_observatory.bat      # Windows launcher
├── dashboard/
│   └── index.html              # CRT Phosphor dashboard (all-in-one)
├── skills_reference.html       # 72-skills design catalog
├── skillforge.html             # Skill forge reference
└── .agents/skills/             # Codebuff agent skills
```

---

## 🔬 Physical Models

### IR Drop Map
Calculates dynamic VDD power grid voltage degradation across the 4×4 mesh based on per-tile activity hotspots. Uses `build_ir_drop_model()` with configurable base voltage and resistance.

### Thermal PID Controller
Predictive throttling loop with environmental modifiers (ambient temperature, workload factor, ramp transients). Outputs throttled frequency + action state:
- 🟢 **STABLE** — normal operation
- 🟡 **PREDICTIVE COOLING** — approaching thermal limit
- 🔴 **CRITICAL THROTTLE** — exceeded safe temperature

### CDC Yield Sweep
Monte Carlo statistical analysis sweeping frequency from 2.5–5.0 GHz to find 90% and 99% yield points with randomized gate propagation delays.

---

## 🎨 Design System

The **CRT Phosphor Oscilloscope** design language uses:

| Color | Hex | Usage |
|---|---|---|
| Neon Green | `#00FF41` | Primary phosphor, CRT heritage |
| Neon Blue | `#00BFFF` | Data paths, clock domains, yield analysis |
| Red | `#FF3333` | Critical alerts, backpressure, thermal warnings |
| Yellow | `#FFCC00` | Warnings, predictive cooling |

Fonts: **VT323** · **Share Tech Mono** · **JetBrains Mono**

---

## 🗣️ Voice Commands

| Command | Action |
|---|---|
| "run simulation" | Execute regression |
| "run thermal" | Run thermal PID controller |
| "run sweep" | Run CDC yield sweep |
| "boot" | Execute UEFI POST |
| "show registers" | Open register dump modal |
| "refresh" | Poll latest snapshot |
| "shutdown" | Initiate thermal wrap-up |

---

## 📄 License

MIT — see [LICENSE](LICENSE) file.

---

Built with ❤️ by [KnigguKniggu-droid](https://github.com/KnigguKniggu-droid)
