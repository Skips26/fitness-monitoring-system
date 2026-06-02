#!/usr/bin/env python3
"""
=============================================================================
  WORKOUT TRACKER  —  Unified Sensor Script
  Reads ECG (AD8232), EMG, and MPU6050 simultaneously during a workout
  and computes aggregate features on STOP.
=============================================================================

Hardware wiring (recap):
    AD8232 (ECG)  ->  ADS1115 channel A0  (I2C 0x48)
    EMG sensor    ->  ADS1115 channel A1  (through voltage divider)
    MPU6050       ->  direct I2C          (address 0x68)

Features produced per workout:
    workout_id     – auto-generated UUID
    duration_mins  – length of workout in minutes
    avg_hr         – average heart rate (BPM)
    max_hr         – maximum heart rate (BPM)
    hr_spikes      – count of sudden HR jumps (>20 BPM between consecutive readings)
    pct_time_low   – % of workout time spent in a "low" HR zone (<100 BPM)
    avg_emg        – average EMG activation level (arbitrary units 0-1000)
    emg_fatigue    – fatigue index: % drop in EMG amplitude from first quarter to last quarter
    total_reps     – repetitions detected by the MPU6050 accelerometer
=============================================================================
"""

import time
import uuid
import json
import math
import threading
import statistics

# ── Raspberry Pi hardware libraries ──────────────────────────────────────────
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Pin

# ── For sending data to AWS (prepared, not active yet) ───────────────────────
import requests  # pip install requests

# =============================================================================
#  CONFIGURATION
# =============================================================================

# ADS1115
ADS_DATA_RATE    = 250          # samples per second (860 max, but 250 is stable on shared I2C)
ECG_CHANNEL      = Pin.A0       # AD8232 output
EMG_CHANNEL      = Pin.A1       # EMG sensor output

# MPU6050 I2C address
MPU6050_ADDR     = 0x68

# ECG beat detection
ECG_BASELINE_ALPHA   = 0.99     # moving-average smoothing (slow adaptation)
ECG_THRESHOLD_OFFSET = 0.06     # volts above baseline to detect a beat
ECG_BEAT_COOLDOWN    = 0.5      # seconds between valid beats
ECG_BPM_MIN          = 40
ECG_BPM_MAX          = 200

# EMG signal processing
EMG_BASELINE_ALPHA   = 0.99     # moving-average smoothing for EMG baseline
EMG_NOISE_DEFAULT    = 0.03     # default noise floor in volts

# MPU6050 rep detection
REP_ACCEL_THRESHOLD  = 1.6      # g-force magnitude spike to count a rep
REP_COOLDOWN         = 0.8      # seconds between valid reps

# HR zone threshold
LOW_HR_ZONE          = 100      # BPM below this is "low"

# HR spike definition
HR_SPIKE_DELTA       = 70       # BPM jump between consecutive readings

# Sampling interval (seconds) — shared across sensor threads
SAMPLE_INTERVAL      = 0.025    # 40 Hz — reduces I2C bus congestion with 3 threads

# AWS endpoint (placeholder — fill in with your actual API Gateway / IoT endpoint)
AWS_API_ENDPOINT = "https://YOUR_API_GATEWAY_URL.amazonaws.com/prod/workout"

# =============================================================================
#  GLOBAL STATE
# =============================================================================

workout_running = False         # flag controlled by main thread

# Collected data (written by sensor threads, read at summary time)
ecg_bpm_log      = []           # list of (timestamp, bpm)
emg_signal_log   = []           # list of (timestamp, activation_value)
rep_timestamps   = []           # list of timestamps when a rep was detected
workout_start    = 0.0
workout_end      = 0.0

# Thread-safe lock for shared lists
data_lock = threading.Lock()

# Thread-safe lock for I2C bus access (ADS1115 + MPU6050 share the bus)
i2c_lock = threading.Lock()


# =============================================================================
#  MPU6050  —  Low-level I2C helpers  (no external library required)
# =============================================================================

def mpu6050_init(i2c_bus):
    """Wake up the MPU6050 and set full-scale range to ±4g."""
    with i2c_lock:
        while not i2c_bus.try_lock():
            pass
        try:
            # Wake up (write 0 to PWR_MGMT_1 register 0x6B)
            i2c_bus.writeto(MPU6050_ADDR, bytes([0x6B, 0x00]))
            time.sleep(0.1)
            # Set accelerometer full-scale to ±4g (register 0x1C, value 0x08)
            i2c_bus.writeto(MPU6050_ADDR, bytes([0x1C, 0x08]))
        finally:
            i2c_bus.unlock()


def mpu6050_read_accel(i2c_bus):
    """Read raw accelerometer X, Y, Z and return magnitude in g units."""
    buf = bytearray(6)
    with i2c_lock:
        while not i2c_bus.try_lock():
            pass
        try:
            i2c_bus.writeto_then_readfrom(MPU6050_ADDR, bytes([0x3B]), buf)
        finally:
            i2c_bus.unlock()

    # Each axis is a signed 16-bit value, MSB first
    ax = _to_signed_16(buf[0], buf[1])
    ay = _to_signed_16(buf[2], buf[3])
    az = _to_signed_16(buf[4], buf[5])

    # Convert to g  (±4g range → sensitivity 8192 LSB/g)
    scale = 8192.0
    gx = ax / scale
    gy = ay / scale
    gz = az / scale

    magnitude = math.sqrt(gx**2 + gy**2 + gz**2)
    return gx, gy, gz, magnitude


def _to_signed_16(msb, lsb):
    """Combine two bytes into a signed 16-bit integer."""
    val = (msb << 8) | lsb
    if val >= 0x8000:
        val -= 0x10000
    return val


# =============================================================================
#  SENSOR THREADS
# =============================================================================

def ecg_thread(ads):
    """
    Continuously reads the ECG channel on ADS1115 A0.
    Detects heartbeats using a dynamic moving-average baseline + threshold.
    Logs every valid BPM reading with its timestamp.
    """
    global workout_running

    chan = AnalogIn(ads, ECG_CHANNEL)

    # Seed the moving baseline
    with i2c_lock:
        moving_baseline = chan.voltage
    last_beat_time  = 0.0

    print("[ECG]  Thread started — monitoring heart rate")

    while workout_running:
        try:
            with i2c_lock:
                voltage = chan.voltage
            current_time = time.time()

            # Slow-moving baseline absorbs breathing/drift
            moving_baseline = (moving_baseline * ECG_BASELINE_ALPHA) + \
                              (voltage * (1 - ECG_BASELINE_ALPHA))

            dynamic_threshold = moving_baseline + ECG_THRESHOLD_OFFSET

            # Beat detection with cooldown
            if voltage > dynamic_threshold and \
               (current_time - last_beat_time) > ECG_BEAT_COOLDOWN:

                if last_beat_time != 0:
                    interval = current_time - last_beat_time
                    bpm = 60.0 / interval

                    if ECG_BPM_MIN <= bpm <= ECG_BPM_MAX:
                        with data_lock:
                            ecg_bpm_log.append((current_time, bpm))

                last_beat_time = current_time

            time.sleep(SAMPLE_INTERVAL)

        except Exception as e:
            print(f"[ECG]  ⚠️ Read error: {e}")
            time.sleep(0.1)

    print("[ECG]  Thread stopped")


def emg_thread(ads):
    """
    Continuously reads the EMG channel on ADS1115 A1.
    Uses a high-pass filter (moving baseline subtraction) to extract
    the active muscle signal, then logs the activation magnitude.
    """
    global workout_running

    chan = AnalogIn(ads, EMG_CHANNEL)

    # Calibration phase: measure resting noise for 2 seconds
    print("[EMG]  Calibrating noise floor (2 s) — keep arm relaxed …")
    cal_start = time.time()
    min_v, max_v = 5.0, 0.0
    while time.time() - cal_start < 2.0:
        with i2c_lock:
            v = chan.voltage
        if v > max_v: max_v = v
        if v < min_v: min_v = v
        time.sleep(SAMPLE_INTERVAL)

    noise_barrier = ((max_v - min_v) / 2.0) + 0.015
    if noise_barrier > 0.145:
        noise_barrier = 0.145
    print(f"[EMG]  Noise barrier = {noise_barrier:.4f} V")

    with i2c_lock:
        baseline = chan.voltage

    print("[EMG]  Thread started — monitoring muscle activation")

    while workout_running:
        try:
            with i2c_lock:
                voltage = chan.voltage
            current_time = time.time()

            # High-pass: track slow drift
            baseline = (baseline * EMG_BASELINE_ALPHA) + \
                       (voltage * (1 - EMG_BASELINE_ALPHA))

            raw_deviation = abs(voltage - baseline)
            active_signal = max(0.0, raw_deviation - noise_barrier)

            # Scale to 0-1000 range (adjust multiplier to your sensor gain)
            activation = min(active_signal * 5000, 1000.0)

            with data_lock:
                emg_signal_log.append((current_time, activation))

            time.sleep(SAMPLE_INTERVAL)

        except Exception as e:
            print(f"[EMG]  ⚠️ Read error: {e}")
            time.sleep(0.1)

    print("[EMG]  Thread stopped")


def mpu_thread(i2c_bus):
    """
    Continuously reads the MPU6050 accelerometer.
    Counts a 'rep' every time the total g-force magnitude exceeds
    the threshold, with a cooldown to avoid double-counting.
    """
    global workout_running

    # Establish a resting magnitude baseline (should be ~1.0 g at rest)
    _, _, _, rest_mag = mpu6050_read_accel(i2c_bus)

    last_rep_time = 0.0

    print("[MPU]  Thread started — counting reps")

    while workout_running:
        try:
            _, _, _, mag = mpu6050_read_accel(i2c_bus)
            current_time = time.time()

            # A rep is detected when the acceleration magnitude deviates
            # significantly from the resting ~1g
            if mag > REP_ACCEL_THRESHOLD and \
               (current_time - last_rep_time) > REP_COOLDOWN:
                with data_lock:
                    rep_timestamps.append(current_time)
                last_rep_time = current_time

            time.sleep(SAMPLE_INTERVAL)

        except Exception as e:
            print(f"[MPU]  ⚠️ Read error: {e}")
            time.sleep(0.1)

    print("[MPU]  Thread stopped")


# =============================================================================
#  FEATURE COMPUTATION
# =============================================================================

def compute_features():
    """
    Aggregate all sensor logs into the 9 required features.
    Returns a dictionary ready for JSON serialization.
    """
    w_id = f"w_{uuid.uuid4().hex[:8]}"

    # ── Duration ─────────────────────────────────────────────────────────
    duration_secs = workout_end - workout_start
    duration_mins = round(duration_secs / 60.0, 2)

    # ── Heart-rate features ──────────────────────────────────────────────
    if ecg_bpm_log:
        bpm_values = [bpm for _, bpm in ecg_bpm_log]

        avg_hr = round(statistics.mean(bpm_values), 1)
        max_hr = round(max(bpm_values), 1)

        # HR spikes: count of consecutive readings that jump > HR_SPIKE_DELTA
        hr_spikes = 0
        for i in range(1, len(bpm_values)):
            if abs(bpm_values[i] - bpm_values[i - 1]) > HR_SPIKE_DELTA:
                hr_spikes += 1

        # Pct time in low HR zone
        low_count = sum(1 for b in bpm_values if b < LOW_HR_ZONE)
        pct_time_low = round((low_count / len(bpm_values)) * 100, 1)
    else:
        avg_hr       = 0
        max_hr       = 0
        hr_spikes    = 0
        pct_time_low = 100.0

    # ── EMG features ─────────────────────────────────────────────────────
    if emg_signal_log:
        emg_values = [val for _, val in emg_signal_log]
        avg_emg = round(statistics.mean(emg_values), 1)

        # Fatigue index: compare average activation in the first 25% vs last 25%
        n = len(emg_values)
        quarter = max(1, n // 4)
        first_quarter_avg = statistics.mean(emg_values[:quarter])
        last_quarter_avg  = statistics.mean(emg_values[-quarter:])

        if first_quarter_avg > 0:
            emg_fatigue = round(
                ((first_quarter_avg - last_quarter_avg) / first_quarter_avg) * 100, 1
            )
        else:
            emg_fatigue = 0.0

        # Fatigue can be negative if you got stronger at the end — clamp to 0
        emg_fatigue = max(0.0, emg_fatigue)
    else:
        avg_emg     = 0
        emg_fatigue = 0.0

    # ── Rep count ────────────────────────────────────────────────────────
    total_reps = len(rep_timestamps)

    return {
        "workout_id":    w_id,
        "duration_mins": duration_mins,
        "avg_hr":        avg_hr,
        "max_hr":        max_hr,
        "hr_spikes":     hr_spikes,
        "pct_time_low":  pct_time_low,
        "avg_emg":       avg_emg,
        "emg_fatigue":   emg_fatigue,
        "total_reps":    total_reps,
    }


# =============================================================================
#  AWS DATA TRANSMISSION
# =============================================================================

def send_to_aws(features: dict):
    """
    POST the workout features to AWS API Gateway / IoT endpoint.
    Falls back gracefully if the network is unreachable.
    """
    print("\n[AWS]  Sending data to cloud …")
    try:
        response = requests.post(
            AWS_API_ENDPOINT,
            json=features,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code in (200, 201):
            print(f"[AWS]  ✅ Data sent successfully (HTTP {response.status_code})")
        else:
            print(f"[AWS]  ⚠️ Server responded with HTTP {response.status_code}")
            print(f"       {response.text[:200]}")
    except requests.exceptions.ConnectionError:
        print("[AWS]  ❌ Could not reach the server. Data saved locally only.")
    except Exception as e:
        print(f"[AWS]  ❌ Error: {e}")


def save_locally(features: dict, filename="workout_log.json"):
    """Append the workout features to a local JSON-lines file as backup."""
    with open(filename, "a") as f:
        f.write(json.dumps(features) + "\n")
    print(f"[LOG]  💾 Saved to {filename}")


# =============================================================================
#  MAIN  —  INTERACTIVE WORKOUT LOOP
# =============================================================================

def main():
    global workout_running, workout_start, workout_end
    global ecg_bpm_log, emg_signal_log, rep_timestamps

    # ── Initialize hardware ──────────────────────────────────────────────
    print("=" * 60)
    print("  🏋️  WORKOUT TRACKER  —  Initializing hardware …")
    print("=" * 60)

    i2c = busio.I2C(board.SCL, board.SDA)
    ads  = ADS1115(i2c, data_rate=ADS_DATA_RATE)

    # Initialize the MPU6050
    mpu6050_init(i2c)
    print("[HW]   ADS1115 ✅  (ECG on A0, EMG on A1)")
    print("[HW]   MPU6050 ✅  (Accelerometer + Gyro)")
    print("=" * 60)

    # ── Workout loop ─────────────────────────────────────────────────────
    while True:
        print("\n📋  OPTIONS:")
        print("    [1]  START WORKOUT")
        print("    [2]  QUIT")
        choice = input("\n👉  Enter choice: ").strip()

        if choice == "2":
            print("\n👋  Goodbye!")
            break

        if choice != "1":
            print("⚠️  Invalid choice, try again.")
            continue

        # ── Reset data stores ────────────────────────────────────────────
        with data_lock:
            ecg_bpm_log.clear()
            emg_signal_log.clear()
            rep_timestamps.clear()

        workout_running = True
        workout_start   = time.time()

        # ── Launch sensor threads ────────────────────────────────────────
        # EMG starts first (alone) so its 2s calibration doesn't collide
        t_emg = threading.Thread(target=emg_thread, args=(ads,), daemon=True)
        t_emg.start()
        # Wait for EMG calibration to finish before launching others
        time.sleep(2.5)

        t_ecg = threading.Thread(target=ecg_thread, args=(ads,), daemon=True)
        t_mpu = threading.Thread(target=mpu_thread, args=(i2c,), daemon=True)
        t_ecg.start()
        t_mpu.start()

        print("\n" + "=" * 60)
        print("  🟢  WORKOUT IN PROGRESS")
        print("  Press ENTER at any time to STOP the workout.")
        print("=" * 60 + "\n")

        # ── Wait for the user to press ENTER to stop ─────────────────────
        input()

        # ── Stop all threads ─────────────────────────────────────────────
        workout_running = False
        workout_end     = time.time()

        t_ecg.join(timeout=3)
        t_emg.join(timeout=3)
        t_mpu.join(timeout=3)

        # ── Compute and display features ─────────────────────────────────
        features = compute_features()

        print("\n" + "=" * 60)
        print("  🏁  WORKOUT COMPLETE  —  Feature Summary")
        print("=" * 60)
        header = ",".join(features.keys())
        values = ",".join(str(v) for v in features.values())
        print(f"\n  {header}")
        print(f"  {values}\n")

        for key, val in features.items():
            print(f"    {key:20s} : {val}")

        print("\n" + "-" * 60)

        # ── Data collection stats ────────────────────────────────────────
        print(f"  [STATS]  ECG readings : {len(ecg_bpm_log)}")
        print(f"  [STATS]  EMG samples  : {len(emg_signal_log)}")
        print(f"  [STATS]  Reps counted : {len(rep_timestamps)}")
        print("-" * 60)

        # ── Save locally + send to AWS ───────────────────────────────────
        save_locally(features)
        send_to_aws(features)

        print("\n✅  Ready for next workout.\n")


# =============================================================================
if __name__ == "__main__":
    main()
