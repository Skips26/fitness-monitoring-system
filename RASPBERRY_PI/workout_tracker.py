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
import os

# ── Raspberry Pi hardware libraries ──────────────────────────────────────────
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Pin

# ── For sending data to AWS ──────────────────────────────────────────────────
import requests  # pip install requests

# =============================================================================
#  CONFIGURATION
# =============================================================================

# Load config from config.json (same directory as this script)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_SCRIPT_DIR, "config.json")

try:
    with open(_CONFIG_PATH, "r") as _f:
        _config = json.load(_f)
    AWS_API_ENDPOINT = _config.get("aws_api_url", "")
    BACKEND_URL = _config.get("backend_url", "http://localhost:8000")
except FileNotFoundError:
    print(f"[WARN] Config file not found at {_CONFIG_PATH}. Using defaults.")
    AWS_API_ENDPOINT = ""
    BACKEND_URL = "http://localhost:8000"

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

# MPU6050 rep detection  (dynamic peak-valley algorithm)
REP_DEVIATION_THRESH = 0.3      # g deviation from rest to start detecting a rep
REP_COOLDOWN         = 0.5      # seconds between valid reps
REP_SMOOTHING_ALPHA  = 0.25     # EMA smoothing factor for accel signal (0-1, lower = smoother)
REP_CALIBRATION_TIME = 1.0      # seconds spent calibrating rest magnitude at start

# HR zone threshold
LOW_HR_ZONE          = 100      # BPM below this is "low"

# HR spike definition
HR_SPIKE_DELTA       = 70       # BPM jump between consecutive readings

# Sampling interval (seconds) — shared across sensor threads
SAMPLE_INTERVAL      = 0.025    # 40 Hz — reduces I2C bus congestion with 3 threads

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

# Selected user (set at startup)
selected_user    = None         # dict with id, first_name, last_name

# Thread-safe lock for shared lists
data_lock = threading.Lock()

# Thread-safe lock for I2C bus access (ADS1115 + MPU6050 share the bus)
i2c_lock = threading.Lock()


# =============================================================================
#  USER SELECTION  —  Fetch users from backend and prompt for selection
# =============================================================================

def fetch_users():
    """Fetch the list of registered users from the backend API."""
    url = f"{BACKEND_URL}/profiles/list"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[USER]  ⚠️ Backend returned HTTP {response.status_code}")
            return []
    except requests.exceptions.ConnectionError:
        print(f"[USER]  ❌ Could not reach backend at {url}")
        return []
    except Exception as e:
        print(f"[USER]  ❌ Error fetching users: {e}")
        return []


def select_user():
    """Display a menu of registered users and let the operator pick one."""
    global selected_user

    print("\n" + "=" * 60)
    print("  👤  USER SELECTION")
    print("=" * 60)
    print("\n  Fetching registered users from the server …")

    users = fetch_users()

    if not users:
        print("\n  ❌  No users found or could not connect to the server.")
        print("      Make sure the backend is running and users are registered.")
        print("      Backend URL: " + BACKEND_URL)
        return False

    print(f"\n  Found {len(users)} registered user(s):\n")
    for i, user in enumerate(users, 1):
        name = f"{user.get('first_name', '?')} {user.get('last_name', '?')}"
        print(f"    [{i}]  {name}")

    print()
    while True:
        choice = input("  👉  Enter the number of your user: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(users):
                selected_user = users[idx]
                name = f"{selected_user.get('first_name', '?')} {selected_user.get('last_name', '?')}"
                print(f"\n  ✅  Selected user: {name}")
                print(f"      User ID: {selected_user['id']}")
                return True
            else:
                print(f"  ⚠️  Please enter a number between 1 and {len(users)}.")
        except ValueError:
            print("  ⚠️  Please enter a valid number.")


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
    Uses a dynamic peak-valley state-machine to count reps:

    1. Auto-calibrates the "rest" magnitude at start (~1g when still).
    2. Smooths the signal with an exponential moving average (EMA).
    3. Detects reps by tracking deviations from the rest baseline:
       - IDLE  → magnitude deviates beyond threshold → transition to PEAK
       - PEAK  → magnitude returns near rest         → REP COUNTED, back to IDLE

    This approach is far more sensitive than a fixed absolute threshold,
    because it adapts to the user's actual resting orientation and detects
    the full up-down cycle of a repetition.
    """
    global workout_running

    # ── Calibrate rest magnitude ──────────────────────────────────────
    print(f"[MPU]  Calibrating rest position ({REP_CALIBRATION_TIME}s) — hold still …")
    cal_readings = []
    cal_start = time.time()
    while time.time() - cal_start < REP_CALIBRATION_TIME:
        try:
            _, _, _, mag = mpu6050_read_accel(i2c_bus)
            cal_readings.append(mag)
        except Exception:
            pass
        time.sleep(SAMPLE_INTERVAL)

    if cal_readings:
        rest_magnitude = statistics.mean(cal_readings)
    else:
        rest_magnitude = 1.0  # fallback: 1g at rest

    print(f"[MPU]  Rest magnitude = {rest_magnitude:.3f} g  "
          f"(threshold ±{REP_DEVIATION_THRESH} g)")

    # ── State machine ─────────────────────────────────────────────────
    STATE_IDLE = 0   # waiting for movement to start
    STATE_PEAK = 1   # movement detected, waiting for return to rest

    state         = STATE_IDLE
    smoothed_mag  = rest_magnitude
    last_rep_time = 0.0
    peak_value    = 0.0

    print("[MPU]  Thread started — counting reps (peak-valley detection)")

    while workout_running:
        try:
            _, _, _, raw_mag = mpu6050_read_accel(i2c_bus)
            current_time = time.time()

            # Exponential moving average to smooth out noise
            smoothed_mag = (REP_SMOOTHING_ALPHA * raw_mag +
                            (1 - REP_SMOOTHING_ALPHA) * smoothed_mag)

            deviation = abs(smoothed_mag - rest_magnitude)

            if state == STATE_IDLE:
                # Waiting for the acceleration to deviate from rest
                if deviation > REP_DEVIATION_THRESH:
                    state = STATE_PEAK
                    peak_value = deviation

            elif state == STATE_PEAK:
                # Track the peak deviation
                if deviation > peak_value:
                    peak_value = deviation

                # When the acceleration returns close to rest → rep complete
                if deviation < REP_DEVIATION_THRESH * 0.5:
                    # Enforce cooldown to avoid double-counting
                    if (current_time - last_rep_time) > REP_COOLDOWN:
                        with data_lock:
                            rep_timestamps.append(current_time)
                        last_rep_time = current_time
                        rep_count = len(rep_timestamps)
                        print(f"[MPU]  🔄 Rep #{rep_count} detected  "
                              f"(peak deviation: {peak_value:.2f} g)")

                    state = STATE_IDLE
                    peak_value = 0.0

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
    POST the workout features to AWS API Gateway.
    The Lambda function will forward the data to the FastAPI backend.
    Falls back gracefully if the network is unreachable.
    """
    if not AWS_API_ENDPOINT or "YOUR_API_GATEWAY" in AWS_API_ENDPOINT:
        print("\n[AWS]  ⚠️ AWS API endpoint not configured in config.json.")
        print("       Skipping AWS upload. Data saved locally only.")
        return False

    # Include the selected user's ID in the payload
    payload = {
        "user_id": selected_user["id"],
        **{k: v for k, v in features.items() if k != "workout_id"},
    }

    print("\n[AWS]  Sending data to cloud …")
    try:
        response = requests.post(
            AWS_API_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if response.status_code in (200, 201):
            print(f"[AWS]  ✅ Data sent successfully (HTTP {response.status_code})")
            try:
                resp_data = response.json()
                if "workout" in resp_data:
                    workout_id = resp_data["workout"].get("id", "unknown")
                    print(f"[AWS]  📋 Workout ID in database: {workout_id}")
            except Exception:
                pass
            return True
        else:
            print(f"[AWS]  ⚠️ Server responded with HTTP {response.status_code}")
            print(f"       {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print("[AWS]  ❌ Could not reach the server. Data saved locally only.")
        return False
    except Exception as e:
        print(f"[AWS]  ❌ Error: {e}")
        return False


def save_locally(features: dict, filename="workout_log.json"):
    """Append the workout features to a local JSON-lines file as backup."""
    filepath = os.path.join(_SCRIPT_DIR, filename)
    with open(filepath, "a") as f:
        entry = {
            "user_id": selected_user["id"] if selected_user else "unknown",
            "user_name": f"{selected_user.get('first_name', '?')} {selected_user.get('last_name', '?')}" if selected_user else "unknown",
            **features,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        f.write(json.dumps(entry) + "\n")
    print(f"[LOG]  💾 Saved to {filepath}")


# =============================================================================
#  MAIN  —  INTERACTIVE WORKOUT LOOP
# =============================================================================

def main():
    global workout_running, workout_start, workout_end
    global ecg_bpm_log, emg_signal_log, rep_timestamps

    # ── User selection ───────────────────────────────────────────────────
    print("=" * 60)
    print("  🏋️  WORKOUT TRACKER  —  Starting up …")
    print("=" * 60)

    if not select_user():
        print("\n  ❌  Cannot proceed without selecting a user. Exiting.")
        return

    # ── Initialize hardware ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  🏋️  WORKOUT TRACKER  —  Initializing hardware …")
    print("=" * 60)

    i2c = busio.I2C(board.SCL, board.SDA)
    ads  = ADS1115(i2c, data_rate=ADS_DATA_RATE)

    # Initialize the MPU6050
    mpu6050_init(i2c)
    print("[HW]   ADS1115 ✅  (ECG on A0, EMG on A1)")
    print("[HW]   MPU6050 ✅  (Accelerometer + Gyro)")
    print("=" * 60)

    user_name = f"{selected_user.get('first_name', '?')} {selected_user.get('last_name', '?')}"

    # ── Workout loop ─────────────────────────────────────────────────────
    while True:
        print(f"\n📋  OPTIONS  (User: {user_name}):")
        print("    [1]  START WORKOUT")
        print("    [2]  SWITCH USER")
        print("    [3]  QUIT")
        choice = input("\n👉  Enter choice: ").strip()

        if choice == "3":
            print("\n👋  Goodbye!")
            break

        if choice == "2":
            if select_user():
                user_name = f"{selected_user.get('first_name', '?')} {selected_user.get('last_name', '?')}"
            continue

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
        print(f"  🟢  WORKOUT IN PROGRESS  (User: {user_name})")
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
        print(f"  🏁  WORKOUT COMPLETE  —  Feature Summary  (User: {user_name})")
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
        aws_success = send_to_aws(features)

        if aws_success:
            print("\n✅  Workout data sent to the cloud!")
            print("    Open the website to review, edit, and analyze this workout.")
        else:
            print("\n⚠️  Workout saved locally only. Check your AWS/network config.")

        print("\n✅  Ready for next workout.\n")


# =============================================================================
if __name__ == "__main__":
    main()
