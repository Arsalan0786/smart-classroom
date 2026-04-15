# Smart Classroom AI Dashboard 🎓

![Smart Classroom AI](https://github.com/Arsalan0786/smart-classroom/assets/placeholder.png) <!-- Update this with an actual screenshot from your repo -->

A comprehensive, real-time Computer Vision system and full-stack web dashboard designed for modern educational environments. It uses Yolov8 to actively monitor classroom occupancy, automatically manages energy-consuming appliances (fans & lights) to reduce power waste, and stores historical analytics data for institution-wide auditing.

---

## 🌟 Key Features

### 1. Real-Time Occupancy & Quadrant Analysis
- Powered by `Ultralytics YOLOv8`, delivering high-framerate edge inference to detect students.
- Mathematically divides room camera feeds into four distinct zones (Top-Left, Top-Right, Bottom-Left, Bottom-Right) to visualize where students cluster.
- Processes webcam, local `.mp4` video files, or individual `.jpg`/`.png` image uploads with near-zero latency.

### 2. Intelligent Energy Management (Automated Appliances)
- Prevents power waste by linking the live occupant count directly to physical room appliance rules:
  - **0 Students:** 0 Fans, 0 Lights _(Energy Saving Standby)_
  - **1–10 Students:** 2 Fans, 4 Lights _(Low Power Mode)_
  - **11–19 Students:** 4 Fans, 6 Lights _(Medium Power Mode)_
  - **20+ Students:** 6 Fans, 8 Lights _(Maximum Cooling Mode)_
- The unified web dashboard immediately visually glows and re-adjusts as these thresholds are dynamically crossed.

### 3. Persistent Analytics Backend (SQLite + CSV Export)
- Employs a thread-safe custom SQLite memory buffer utilizing Write-Ahead Logging (WAL) to record hundreds of detection metrics without lagging the video feed.
- Every detection session isolates its timestamps, peak human counts, and total processed frames.
- **Data Export:** Administrators can export the rolling 24-hour analytics direct to a spreadsheet via the **"Download CSV"** button, and visually embed the tracking chart using the **"Download Graph"** capability.

### 4. Interactive Web Dashboard
- Built using **Flask**, **Flask-SocketIO**, and raw modern CSS styling.
- Secure, lightning-fast websocket connections bypass network bottlenecks, streaming inference logic independent of the visual MJPEG video stream.

---

## 🛠️ Technology Stack
*   **Computer Vision:** OpenCV (`cv2`), Ultralytics YOLOv8 (`best.pt`)
*   **Backend Server:** Python 3, Flask, Flask-SocketIO
*   **Database:** SQLite (`sqlite3`)
*   **Frontend UI:** HTML5, Vanilla CSS, Vanilla JavaScript, Chart.js

---

## 🚀 Installation & Getting Started

**1. Clone the Repository:**
```bash
git clone https://github.com/Arsalan0786/smart-classroom.git
cd smart-classroom
```

**2. Install Dependencies:**
Ensure you have Python 3 installed. Run the following command to download the required libraries:
```bash
pip install -r requirements.txt
```

**3. Run the Smart Dashboard Server:**
If you are on macOS or Linux, use the provided helper script:
```bash
chmod +x run.sh
./run.sh
```
*Alternatively, you can manually run `python3 app.py`.*

**4. Open the Interface:**
Once you see the `* Running on http://127.0.0.1:5050` message, open your web browser and navigate to:
[http://localhost:5050](http://localhost:5050)

---

## 📁 Directory Structure

```text
smart-classroom/
│
├── app.py                # Main Flask/Socket.IO backend server
├── config.py             # Global configurations (Model paths, threshold limits)
├── run.sh                # Helper script to safely execute the app environment
├── requirements.txt      # Python package dependencies
│
├── db/                   # Database Layer
│   ├── database.py       # SQL Queries, memory buffers, & session logic
│   └── classroom.db      # Automatically generated SQLite storage file 
│
├── detector/             # Inference logic
│   └── yolo_detector.py  # Wrapper module for running the best.pt YOLO model
│
├── models/               # Model weights
│   └── best.pt           # The trained YOLOv8 PyTorch model
│
├── templates/            # Frontend Web UI
│   └── index.html        # The entire dashboard interface & Chart.js logic
│
└── utils/
    └── visualizer.py     # Drawing logic for bounding boxes, quadrant UI, and text
```

---

## 💡 How to Use

1. **Dashboard Controls (Top bar):** 
   Select your source ranging from `Webcam`, `Video File`, to uploading an `Image`.
2. **Video Playback:** If you selected a Video File, quickly type out the absolute path (e.g. `inputs/sample.mp4`) and hit **Start**.
3. **Automated Tracking:** As the models runs, watch the right-side quadrant counts, total count, and Automated Appliances immediately react to what is visually occurring on the video feed.
4. **Export Findings:** Scoll down to the **Historical Database Data** card to review institutional statistics. Hit the "⬇ CSV" button to download a spreadsheet report.

---

> _**Project Status:** Active Development & Maintained._
