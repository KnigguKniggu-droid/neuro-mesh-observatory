import numpy as np
import random

def build_ir_drop_model(mesh_activity, base_voltage=0.75, resistance_per_segment=0.05):
    """Calculates dynamic VDD power grid voltage degradation (IR-Drop) across the 4x4 mesh."""
    # Safety check for empty data
    if mesh_activity is None or len(mesh_activity) == 0:
        return np.full((4, 4), base_voltage)
        
    activity_matrix = np.asarray(mesh_activity, dtype=float)
    if activity_matrix.size == 0:
        return np.full((4, 4), base_voltage)
        
    current_draw = activity_matrix * 12.5  # mA drawn based on work spikes
    voltage_drop = current_draw * resistance_per_segment / 1000.0  # V = I * R
    actual_voltage = base_voltage - voltage_drop
    return np.clip(actual_voltage, 0.62, base_voltage)

def simulate_thermal_pid(current_temp, target_frequency_ghz=3.8, max_safe_temp=44.0,
                          thermal_limit_c=None, requested_frequency_ghz=None,
                          duration_us=180, ambient_c=40.0, workload=0.92):
    """Predictive throttling loop to dynamically preserve silicon thermal limits.
    Accepts both legacy (target_frequency_ghz, max_safe_temp) and dashboard-style
    (thermal_limit_c, requested_frequency_ghz, etc.) parameter names.
    duration_us influences temperature ramp rate for transient analysis."""
    # Map dashboard-style params to the canonical argument names
    if thermal_limit_c is not None:
        max_safe_temp = thermal_limit_c
    if requested_frequency_ghz is not None:
        target_frequency_ghz = requested_frequency_ghz

    # Apply workload factor: higher workload → higher effective temperature
    effective_temp_boost = workload * 8.0  # up to ~8°C extra at 100% load
    ambient_penalty = max(0.0, ambient_c - 25.0) * 0.15  # cooling efficiency loss

    # Convert lists or matrices to array safely
    if isinstance(current_temp, (list, np.ndarray)):
        current_temp = np.asarray(current_temp)
        if current_temp.size == 0:
            current_temp = 35.0
        else:
            current_temp = np.max(current_temp)

    # Apply environmental modifiers with duration-aware ramp
    ramp_factor = min(1.0, duration_us / 200.0)  # full effect after 200 µs
    current_temp = float(current_temp) + (effective_temp_boost + ambient_penalty) * ramp_factor
            
    if current_temp >= max_safe_temp:
        throttled_freq = target_frequency_ghz * (max_safe_temp / current_temp)
        action = "CRITICAL THROTTLE"
    elif current_temp > (max_safe_temp - 4.0):
        throttled_freq = target_frequency_ghz * 0.85
        action = "PREDICTIVE COOLING"
    else:
        throttled_freq = target_frequency_ghz
        action = "STABLE OPERATING FREQUENCY"
    return round(throttled_freq, 2), action

def simulate_cdc_yield(iterations=100, target_freq_ghz=3.8,
                        seed=None, min_frequency_ghz=2.5, max_frequency_ghz=5.0,
                        frequency_step_ghz=0.25):
    """Runs a statistical Monte Carlo loop simulating randomized gate propagation delays.
    Accepts dashboard-style range parameters (min_frequency_ghz, max_frequency_ghz, frequency_step_ghz)
    in addition to the legacy single-frequency target."""
    # Seed for reproducibility if provided
    if seed is not None:
        np.random.seed(int(seed))
        random.seed(int(seed))

    frequencies = np.arange(min_frequency_ghz, max_frequency_ghz + frequency_step_ghz * 0.5, frequency_step_ghz)
    if len(frequencies) == 0:
        frequencies = np.linspace(min_frequency_ghz, max_frequency_ghz, 20)
    yield_curve = []
    
    for f in frequencies:
        failures = 0
        for _ in range(iterations):
            jitter_delay = np.random.normal(loc=0.12, scale=0.04)
            cycle_time = 1000.0 / f
            if (cycle_time - jitter_delay) < 15.0:  # Timing threshold violation
                failures += 1
        success_rate = ((iterations - failures) / iterations) * 100.0
        yield_curve.append((f, success_rate))
    return yield_curve
