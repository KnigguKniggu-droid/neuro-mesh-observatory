from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np

from physical_models import simulate_cdc_yield, simulate_thermal_pid


# ═══ REGISTER MAP — 0xF000_0000 base ═══
class UEFIRegister(IntEnum):
    """16-bit register offsets from the UEFI MMIO base (0xF000_0000)."""
    # Identification
    FIRMWARE_REV      = 0x000   # RO  — firmware version (major.minor)
    CHIP_ID           = 0x002   # RO  — die identifier
    POST_STATUS        = 0x004   # RO  — boot status word
    # Clock / PLL
    PLL_CTRL           = 0x010   # RW  — PLL enable / lock
    PLL_MULTIPLIER     = 0x012   # RW  — integer multiplier (20–63, default 38 → 3.8 GHz)
    PLL_DIVIDER        = 0x014   # RW  — post-divider (1–8)
    FREQ_STEP_KHZ      = 0x016   # RW  — frequency granularity in kHz (default 25000)
    FREQ_TARGET_GHZ_Q8 = 0x018   # RW  — target freq in GHz × 256 (Q8.8 fixed-point)
    # Thermal
    THERM_LIMIT_C_Q8   = 0x020   # RW  — thermal limit °C × 256 (Q8.8)
    THERM_AMBIENT_C_Q8 = 0x022   # RW  — ambient temp °C × 256
    THERM_WORKLOAD_Q8  = 0x024   # RW  — workload α × 256 (0.0–1.0)
    THERM_DURATION_US  = 0x026   # RW  — transient ramp duration in µs
    THERM_STATE        = 0x028   # RO  — current thermal state (see ThermalState)
    THERM_CURRENT_C_Q8 = 0x02A   # RO  — current die temp °C × 256
    THERM_THROTTLE_GHZ_Q8 = 0x02C  # RO  — throttled frequency × 256
    # CDC Yield
    CDC_ITERATIONS     = 0x030   # RW  — Monte Carlo iterations per freq point
    CDC_SEED           = 0x032   # RW  — random seed
    CDC_MIN_GHZ_Q8     = 0x034   # RW  — sweep floor GHz × 256
    CDC_MAX_GHZ_Q8     = 0x036   # RW  — sweep ceiling GHz × 256
    CDC_STEP_GHZ_Q8    = 0x038   # RW  — frequency step GHz × 256
    CDC_YIELD_90PCT    = 0x03A   # RO  — frequency where yield ≥ 90% (GHz × 256)
    CDC_YIELD_99PCT    = 0x03C   # RO  — frequency where yield ≥ 99% (GHz × 256)
    # Thermal wrap-up
    WRAPUP_CTRL        = 0x040   # RW  — trigger / abort wrap-up sequence
    WRAPUP_STEP        = 0x042   # RO  — current wrap-up step (0–15)
    WRAPUP_TIMEOUT_MS  = 0x044   # RW  — max wraps-up duration in ms


class POSTCode(IntEnum):
    """Power-On Self-Test checkpoint codes (16-bit)."""
    BOOT_ROM_START         = 0x0001
    PLL_LOCK_ACQUIRED      = 0x0010
    VOLTAGE_RAILS_OK       = 0x0020
    THERM_SENSOR_CAL       = 0x0030
    CDC_TABLE_LOADED       = 0x0040
    MEM_BIST_PASS          = 0x0050
    INTERCONNECT_READY     = 0x0060
    BOOT_COMPLETE          = 0x00FF
    # Error codes (0x8000 range)
    ERR_PLL_UNLOCK         = 0x8010
    ERR_VOLTAGE_OOR        = 0x8020
    ERR_THERM_SENSOR_FAIL  = 0x8030
    ERR_CDC_CHECKSUM        = 0x8040
    ERR_MEM_BIST_FAIL      = 0x8050


class ThermalState(IntEnum):
    """Thermal management state machine states."""
    NOMINAL            = 0
    WARNING            = 1   # approaching limit
    THROTTLE_ACTIVE    = 2   # frequency has been reduced
    CRITICAL           = 3   # near shutdown threshold
    EMERGENCY_SHUTDOWN = 4   # thermal wrap-up in progress
    SHUTDOWN_COMPLETE  = 5   # wrap-up finished, chip halted


# ═══ Q8.8 FIXED-POINT HELPERS ═══
def _to_q8(value: float) -> int:
    """Convert float to Q8.8 fixed-point (16-bit signed)."""
    return int(round(value * 256)) & 0xFFFF


def _from_q8(raw: int) -> float:
    """Convert Q8.8 fixed-point to float."""
    if raw >= 0x8000:
        raw -= 0x10000
    return raw / 256.0


# ═══ THERMAL FUSE TABLE ═══
@dataclass
class ThermalFuseTable:
    """Calibration data burned into e-fuses during manufacturing test."""
    calibration_offset_c: float = 1.2      # sensor offset trim
    calibration_gain: float = 0.985         # sensor gain trim
    hotspot_rows: list[int] = field(default_factory=lambda: [3, 7, 11, 15])
    hotspot_weights: list[float] = field(default_factory=lambda: [0.4, 0.3, 0.2, 0.1])


@dataclass
class CDCYieldTable:
    """CDC yield calibration burned during ATE characterization."""
    nominal_jitter_ps: float = 0.12
    jitter_sigma_ps: float = 0.04
    timing_threshold_ps: float = 15.0
    per_die_offset_ps: float = 0.0     # die-specific adjustment
    checksum: int = 0xA5C0


# ═══ UEFI BOOT ROM ═══
class UEFIBootROM:
    """Simulated UEFI firmware for the NeuroMesh NPU chiplet.

    Models the full boot sequence: POST, clock tree init, thermal calibration,
    CDC yield table loading, and thermal management state machine.
    """

    CHIP_ID = 0x4E4D  # "NM" — NeuroMesh
    FIRMWARE_REV = 0x0103  # v1.3

    def __init__(self) -> None:
        self._reg: dict[int, int] = {}
        self._reg[UEFIRegister.FIRMWARE_REV]  = self.FIRMWARE_REV
        self._reg[UEFIRegister.CHIP_ID]       = self.CHIP_ID
        self._reg[UEFIRegister.POST_STATUS]   = 0
        # Clock defaults — 3.8 GHz, 25 kHz steps
        self._reg[UEFIRegister.PLL_CTRL]       = 0
        self._reg[UEFIRegister.PLL_MULTIPLIER] = 38
        self._reg[UEFIRegister.PLL_DIVIDER]    = 1
        self._reg[UEFIRegister.FREQ_STEP_KHZ]  = 25000
        self._reg[UEFIRegister.FREQ_TARGET_GHZ_Q8] = _to_q8(3.8)
        # Thermal defaults
        self._reg[UEFIRegister.THERM_LIMIT_C_Q8]   = _to_q8(58.0)
        self._reg[UEFIRegister.THERM_AMBIENT_C_Q8] = _to_q8(40.0)
        self._reg[UEFIRegister.THERM_WORKLOAD_Q8]  = _to_q8(0.92)
        self._reg[UEFIRegister.THERM_DURATION_US]  = 180
        self._reg[UEFIRegister.THERM_STATE]         = ThermalState.NOMINAL
        self._reg[UEFIRegister.THERM_CURRENT_C_Q8]  = _to_q8(35.0)
        self._reg[UEFIRegister.THERM_THROTTLE_GHZ_Q8] = _to_q8(3.8)
        # CDC defaults
        self._reg[UEFIRegister.CDC_ITERATIONS]  = 200
        self._reg[UEFIRegister.CDC_SEED]        = 73191
        self._reg[UEFIRegister.CDC_MIN_GHZ_Q8]  = _to_q8(2.5)
        self._reg[UEFIRegister.CDC_MAX_GHZ_Q8]  = _to_q8(5.0)
        self._reg[UEFIRegister.CDC_STEP_GHZ_Q8] = _to_q8(0.25)
        self._reg[UEFIRegister.CDC_YIELD_90PCT] = 0
        self._reg[UEFIRegister.CDC_YIELD_99PCT] = 0
        # Wrap-up
        self._reg[UEFIRegister.WRAPUP_CTRL]       = 0
        self._reg[UEFIRegister.WRAPUP_STEP]       = 0
        self._reg[UEFIRegister.WRAPUP_TIMEOUT_MS] = 500

        # Fuse-loaded calibration tables
        self.thermal_fuse: ThermalFuseTable = ThermalFuseTable()
        self.cdc_yield_table: CDCYieldTable = CDCYieldTable()

        # Boot log
        self.post_log: list[tuple[int, str]] = []
        self.booted: bool = False

    # ── Register access ──
    def read_reg(self, offset: int) -> int:
        return self._reg.get(UEFIRegister(offset), 0)

    def write_reg(self, offset: int, value: int) -> None:
        reg = UEFIRegister(offset)
        self._reg[reg] = value & 0xFFFF
        if reg == UEFIRegister.WRAPUP_CTRL and value == 1:
            self._trigger_wrapup()

    def read_q8(self, offset: int) -> float:
        return _from_q8(self._reg.get(UEFIRegister(offset), 0))

    def write_q8(self, offset: int, value: float) -> None:
        self._reg[UEFIRegister(offset)] = _to_q8(value)

    # ── Power-On Self-Test ──
    def run_post(self) -> dict:
        """Execute the full UEFI boot sequence. Returns POST summary."""
        self.post_log.clear()
        self.booted = False

        def checkpoint(code: POSTCode, msg: str) -> None:
            self._reg[UEFIRegister.POST_STATUS] = code
            self.post_log.append((code, msg))

        checkpoint(POSTCode.BOOT_ROM_START, "Boot ROM entry at 0xFFFF0000")

        # 1. PLL lock
        self._reg[UEFIRegister.PLL_CTRL] = 0x0003  # enabled + locked
        checkpoint(POSTCode.PLL_LOCK_ACQUIRED,
                   f"PLL locked: {self.read_q8(UEFIRegister.FREQ_TARGET_GHZ_Q8):.2f} GHz "
                   f"(mult={self._reg[UEFIRegister.PLL_MULTIPLIER]}, "
                   f"div={self._reg[UEFIRegister.PLL_DIVIDER]}, "
                   f"step={self._reg[UEFIRegister.FREQ_STEP_KHZ]} kHz)")

        # 2. Voltage rail check
        rails = {"VDD_CORE": 0.75, "VDD_IO": 1.2, "VDD_PLL": 1.8}
        for name, expected in rails.items():
            actual = expected + np.random.normal(0, 0.005)
            if abs(actual - expected) > 0.05:
                checkpoint(POSTCode.ERR_VOLTAGE_OOR, f"{name}: {actual:.3f}V (expected {expected:.3f}V)")
                return self._post_summary(False, f"voltage rail {name} out of range")
        checkpoint(POSTCode.VOLTAGE_RAILS_OK,
                   f"Voltage rails nominal: {', '.join(f'{k}={v:.3f}V' for k, v in rails.items())}")

        # 3. Thermal sensor calibration from fuses
        if not self._calibrate_thermal():
            checkpoint(POSTCode.ERR_THERM_SENSOR_FAIL, "Thermal sensor failed calibration")
            return self._post_summary(False, "thermal sensor calibration failure")
        checkpoint(POSTCode.THERM_SENSOR_CAL,
                   f"Thermal sensor calibrated: offset={self.thermal_fuse.calibration_offset_c}°C, "
                   f"gain={self.thermal_fuse.calibration_gain}")

        # 4. CDC yield table load
        if self.cdc_yield_table.checksum != 0xA5C0:
            checkpoint(POSTCode.ERR_CDC_CHECKSUM, "CDC yield table checksum mismatch")
            return self._post_summary(False, "CDC checksum failure")
        checkpoint(POSTCode.CDC_TABLE_LOADED,
                   f"CDC table loaded: jitter={self.cdc_yield_table.nominal_jitter_ps}ps, "
                   f"threshold={self.cdc_yield_table.timing_threshold_ps}ps")

        # 5. Memory BIST
        bist_pass = np.random.random() > 0.001  # 0.1% simulated failure rate
        if not bist_pass:
            checkpoint(POSTCode.ERR_MEM_BIST_FAIL, "Memory BIST detected stuck-at fault at row 0x3A2F")
            return self._post_summary(False, "memory BIST failure")
        checkpoint(POSTCode.MEM_BIST_PASS, "Memory BIST: all banks passed")

        # 6. Interconnect ready
        checkpoint(POSTCode.INTERCONNECT_READY, "UCIe/CXL link training complete — 16 lanes @ 32 GT/s")
        checkpoint(POSTCode.BOOT_COMPLETE, "UEFI boot complete — handing off to runtime")

        self.booted = True
        return self._post_summary(True, "boot complete")

    def _calibrate_thermal(self) -> bool:
        """Simulate thermal sensor self-calibration from fuse data."""
        try:
            raw = np.random.normal(loc=35.0, scale=2.0)
            calibrated = (raw + self.thermal_fuse.calibration_offset_c) * self.thermal_fuse.calibration_gain
            self._reg[UEFIRegister.THERM_CURRENT_C_Q8] = _to_q8(max(0, calibrated))
            return True
        except Exception:
            return False

    def _post_summary(self, success: bool, message: str) -> dict:
        return {
            "success": success,
            "message": message,
            "chipId": f"0x{self.CHIP_ID:04X}",
            "firmwareRev": f"v{(self.FIRMWARE_REV >> 8) & 0xFF}.{self.FIRMWARE_REV & 0xFF}",
            "checkpoints": [{"code": f"0x{c:04X}", "name": c.name, "msg": m}
                            for c, m in self.post_log],
            "clockConfig": {
                "frequencyGHz": self.read_q8(UEFIRegister.FREQ_TARGET_GHZ_Q8),
                "pllMultiplier": self._reg[UEFIRegister.PLL_MULTIPLIER],
                "pllDivider": self._reg[UEFIRegister.PLL_DIVIDER],
                "frequencyStepKHz": self._reg[UEFIRegister.FREQ_STEP_KHZ],
            },
            "thermalConfig": {
                "limitC": self.read_q8(UEFIRegister.THERM_LIMIT_C_Q8),
                "ambientC": self.read_q8(UEFIRegister.THERM_AMBIENT_C_Q8),
                "workload": self.read_q8(UEFIRegister.THERM_WORKLOAD_Q8),
                "currentC": self.read_q8(UEFIRegister.THERM_CURRENT_C_Q8),
            },
        }

    # ── Frequency step control ──
    def set_frequency_step_khz(self, step_khz: int) -> None:
        """Configure the PLL frequency granularity in kHz."""
        self._reg[UEFIRegister.FREQ_STEP_KHZ] = max(1000, min(100000, step_khz))

    def adjust_frequency(self, delta_steps: int) -> float:
        """Step the target frequency by N steps. Returns new frequency in GHz."""
        step_ghz = self._reg[UEFIRegister.FREQ_STEP_KHZ] / 1_000_000.0
        current = self.read_q8(UEFIRegister.FREQ_TARGET_GHZ_Q8)
        new_freq = max(0.5, min(6.0, current + delta_steps * step_ghz))
        self._reg[UEFIRegister.FREQ_TARGET_GHZ_Q8] = _to_q8(new_freq)
        return new_freq

    # ── Thermal management ──
    def run_thermal_loop(self) -> dict:
        """Execute one thermal management cycle. Returns state + throttle info."""
        current_temp = self.read_q8(UEFIRegister.THERM_CURRENT_C_Q8)
        limit = self.read_q8(UEFIRegister.THERM_LIMIT_C_Q8)
        target = self.read_q8(UEFIRegister.FREQ_TARGET_GHZ_Q8)

        throttled_freq, action = simulate_thermal_pid(
            current_temp,
            target_frequency_ghz=target,
            max_safe_temp=limit,
            duration_us=self._reg[UEFIRegister.THERM_DURATION_US],
            ambient_c=self.read_q8(UEFIRegister.THERM_AMBIENT_C_Q8),
            workload=self.read_q8(UEFIRegister.THERM_WORKLOAD_Q8),
        )

        self._reg[UEFIRegister.THERM_THROTTLE_GHZ_Q8] = _to_q8(throttled_freq)

        # State machine transitions
        if "CRITICAL" in action:
            self._reg[UEFIRegister.THERM_STATE] = ThermalState.CRITICAL
        elif "COOLING" in action or "PREDICTIVE" in action:
            self._reg[UEFIRegister.THERM_STATE] = ThermalState.THROTTLE_ACTIVE
            if self.read_q8(UEFIRegister.THERM_CURRENT_C_Q8) > limit - 6:
                self._reg[UEFIRegister.THERM_STATE] = ThermalState.WARNING
        else:
            self._reg[UEFIRegister.THERM_STATE] = ThermalState.NOMINAL

        return {
            "state": ThermalState(self._reg[UEFIRegister.THERM_STATE]).name,
            "currentC": current_temp,
            "limitC": limit,
            "requestedGHz": target,
            "throttledGHz": throttled_freq,
            "action": action,
        }

    # ── CDC yield sweep ──
    def run_cdc_sweep(self) -> dict:
        """Run a Monte Carlo CDC yield sweep using register-configured parameters."""
        results = simulate_cdc_yield(
            iterations=self._reg[UEFIRegister.CDC_ITERATIONS],
            seed=self._reg[UEFIRegister.CDC_SEED],
            min_frequency_ghz=self.read_q8(UEFIRegister.CDC_MIN_GHZ_Q8),
            max_frequency_ghz=self.read_q8(UEFIRegister.CDC_MAX_GHZ_Q8),
            frequency_step_ghz=self.read_q8(UEFIRegister.CDC_STEP_GHZ_Q8),
        )

        # Find yield threshold frequencies
        freq_90 = None
        freq_99 = None
        for f, y in results:
            if y >= 90 and freq_90 is None:
                freq_90 = f
            if y >= 99 and freq_99 is None:
                freq_99 = f
        if freq_90 is not None:
            self._reg[UEFIRegister.CDC_YIELD_90PCT] = _to_q8(freq_90)
        if freq_99 is not None:
            self._reg[UEFIRegister.CDC_YIELD_99PCT] = _to_q8(freq_99)

        return {
            "curve": [(float(f), float(y)) for f, y in results],
            "params": {
                "iterations": self._reg[UEFIRegister.CDC_ITERATIONS],
                "seed": self._reg[UEFIRegister.CDC_SEED],
                "minGHz": self.read_q8(UEFIRegister.CDC_MIN_GHZ_Q8),
                "maxGHz": self.read_q8(UEFIRegister.CDC_MAX_GHZ_Q8),
                "stepGHz": self.read_q8(UEFIRegister.CDC_STEP_GHZ_Q8),
            },
            "yield90GHz": freq_90,
            "yield99GHz": freq_99,
        }

    # ── Thermal wrap-up ──
    def _trigger_wrapup(self) -> None:
        """Initiate thermal wrap-up emergency shutdown sequence."""
        self._reg[UEFIRegister.THERM_STATE] = ThermalState.EMERGENCY_SHUTDOWN

    def run_wrapup_sequence(self) -> dict:
        """Execute the thermal wrap-up shutdown sequence."""
        steps = [
            (1, "Halt systolic array"),
            (2, "Flush HBM4 write buffers"),
            (3, "Gate compute clock"),
            (4, "Park UCIe PHY in L0s"),
            (5, "Ramp VDD_CORE to 0.60V"),
            (6, "Assert reset to mesh fabric"),
            (7, "Disable PLL"),
            (8, "Signal shutdown complete"),
        ]

        seq = []
        for step_num, description in steps:
            self._reg[UEFIRegister.WRAPUP_STEP] = step_num
            seq.append({"step": step_num, "action": description, "complete": True})

        self._reg[UEFIRegister.THERM_STATE] = ThermalState.SHUTDOWN_COMPLETE
        self._reg[UEFIRegister.WRAPUP_CTRL] = 2  # completed
        self.booted = False

        return {
            "sequence": seq,
            "totalSteps": len(steps),
            "durationMs": self._reg[UEFIRegister.WRAPUP_TIMEOUT_MS],
            "finalState": "SHUTDOWN_COMPLETE",
        }

    # ── Register dump ──
    def dump_registers(self) -> dict[str, int | float | str]:
        """Return all readable register values as a JSON-compatible dict."""
        return {
            "firmwareRev": f"v{(self.FIRMWARE_REV >> 8) & 0xFF}.{self.FIRMWARE_REV & 0xFF}",
            "chipId": f"0x{self.CHIP_ID:04X}",
            "booted": self.booted,
            "postCode": f"0x{self._reg[UEFIRegister.POST_STATUS]:04X}",
            "pllLocked": bool(self._reg[UEFIRegister.PLL_CTRL] & 0x0002),
            "frequencyGHz": self.read_q8(UEFIRegister.FREQ_TARGET_GHZ_Q8),
            "frequencyStepKHz": self._reg[UEFIRegister.FREQ_STEP_KHZ],
            "pllMultiplier": self._reg[UEFIRegister.PLL_MULTIPLIER],
            "pllDivider": self._reg[UEFIRegister.PLL_DIVIDER],
            "thermalState": ThermalState(self._reg[UEFIRegister.THERM_STATE]).name,
            "thermalLimitC": self.read_q8(UEFIRegister.THERM_LIMIT_C_Q8),
            "thermalCurrentC": self.read_q8(UEFIRegister.THERM_CURRENT_C_Q8),
            "thermalThrottleGHz": self.read_q8(UEFIRegister.THERM_THROTTLE_GHZ_Q8),
            "cdcYield90GHz": self.read_q8(UEFIRegister.CDC_YIELD_90PCT) if self._reg.get(UEFIRegister.CDC_YIELD_90PCT, 0) != 0 else None,
            "cdcYield99GHz": self.read_q8(UEFIRegister.CDC_YIELD_99PCT) if self._reg.get(UEFIRegister.CDC_YIELD_99PCT, 0) != 0 else None,
            "wrapupActive": self._reg[UEFIRegister.WRAPUP_CTRL] == 1,
            "wrapupStep": self._reg[UEFIRegister.WRAPUP_STEP],
        }
