# System Startup Guide

If you restart your computer or close all your terminals, follow these 4 steps to spin everything back up.

You will need **3 separate terminal windows** open.

---

### Terminal 1: Start the Backend (FastAPI)
This runs the Python server that talks to your database.
1. Open a terminal.
2. Run:
```cmd
cd c:\fitness-monitoring-system-IOT\backend
uvicorn main:app --reload --port 8000
```
*Leave this terminal running.*

---

### Terminal 2: Start the Frontend (React / Vite)
This runs the website interface.
1. Open a new terminal.
2. Run:
```cmd
cd c:\fitness-monitoring-system-IOT\frontend
npm run dev
```
*Leave this terminal running. You can now access the site at `http://localhost:5173`.*

---

### Terminal 3: Start the Public Tunnel (localtunnel)
This exposes your local backend to the internet so AWS Lambda can send data to it.
1. Open a new terminal.
2. Run:
```cmd
cd c:\fitness-monitoring-system-IOT
npx localtunnel --port 8000
```
3. Copy the URL it gives you (e.g., `https://funny-cats-jump.loca.lt`).

**IMPORTANT UPDATES:**
Because the tunnel gives you a different random URL every time you run it, you must update two places with the new URL:
1. Go to your AWS Console → Lambda → Configuration → Environment Variables, and update `BACKEND_URL`.
2. Open `c:\fitness-monitoring-system-IOT\RASPBERRY_PI\config.json` and update `backend_url`.

*Leave this terminal running.*

---

### Step 4: Run a Workout (Raspberry Pi or PC)
Now that your servers are listening, you can generate workout data!

**To simulate a workout from your PC:**
Open a 4th terminal and run:
```cmd
curl -X POST https://z4mogo62zl.execute-api.eu-north-1.amazonaws.com/prod/workout -H "Content-Type: application/json" -d "{ \"user_id\": \"YOUR-USER-ID\", \"duration_mins\": 45.0, \"avg_hr\": 135.5, \"max_hr\": 172.0, \"hr_spikes\": 3, \"pct_time_low\": 12.5, \"avg_emg\": 450.0, \"emg_fatigue\": 18.5, \"total_reps\": 96 }"
```

**To run the actual Raspberry Pi Python script:**
*(Make sure to remove or comment out the `import board` lines if running on your PC, or just run it directly on the actual Raspberry Pi).*
```bash
python RASPBERRY_PI/workout_tracker.py
```
