"""
app.py — Smart Classroom AI Dashboard Backend
Flask + Socket.IO server: MJPEG stream, REST API, real-time events
"""

import os, sys, time, threading, base64

import cv2
import numpy as np
from flask import Flask, render_template, Response, jsonify, request, make_response
from flask_socketio import SocketIO
import csv
import datetime
from io import StringIO

# ── Resolve local imports ─────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from detector.yolo_detector import YOLODetector
from utils.visualizer import Visualizer
from config import MODEL_PATH, CONF_THRESHOLD, CAMERA_INDEX

from db.database import (
    init_db, start_session, end_session, record_frame, flush_all,
    get_sessions, get_session_frames, get_analytics, get_hourly_summary, get_session_timeline
)

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = "smart-classroom-2025"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Load model & init DB at startup ───────────────────────────────────────────
print("[APP] Loading YOLO model …")
detector   = YOLODetector(MODEL_PATH, CONF_THRESHOLD)
visualizer = Visualizer()
print("[APP] Model ready.")

print("[APP] Initializing Database …")
init_db()

# ── Shared mutable state ──────────────────────────────────────────────────────
state = {
    "running"      : False,
    "source_type"  : "idle",
    "session_id"   : None,
    "frame_count"  : 0,
    "fps"          : 0.0,
    "total_persons": 0,
    "quadrants"    : {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0},
    "history"      : [],          # rolling list of frame records
}

output_frame  = None              # latest JPEG bytes for MJPEG stream
frame_lock    = threading.Lock()
stop_event    = threading.Event()


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_quadrant_counts(frame, detections):
    h, w    = frame.shape[:2]
    mx, my  = w // 2, h // 2
    counts  = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    for det in detections:
        if det["label"].lower() != "person":
            continue
        x1, y1, x2, y2 = det["bbox"]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        if   cx < mx and cy < my:  counts["Q1"] += 1
        elif cx >= mx and cy < my: counts["Q2"] += 1
        elif cx < mx and cy >= my: counts["Q3"] += 1
        else:                      counts["Q4"] += 1
    return counts

def get_appliances_state(total):
    """Energy-saving rules: decide fan/light count based on occupancy."""
    if total == 0:
        return {"fans": 0, "lights": 0}
    elif total <= 10:
        return {"fans": 2, "lights": 4}
    elif total < 20:
        return {"fans": 4, "lights": 6}
    else:
        return {"fans": 6, "lights": 8}


def point_quadrant(frame, cx, cy):
    h, w = frame.shape[:2]
    if cx < w // 2 and cy < h // 2: return "Q1"
    if cx >= w // 2 and cy < h // 2: return "Q2"
    if cx < w // 2 and cy >= h // 2: return "Q3"
    return "Q4"


# ── Detection loop (runs in background thread) ────────────────────────────────
def detection_loop(source):
    global output_frame

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        state["running"] = False
        socketio.emit("srv_error", {"message": f"Cannot open source: {source}"})
        return

    prev_time   = time.time()
    frame_count = 0

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            if not isinstance(source, int):   # loop video files
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            break

        now      = time.time()
        dt       = now - prev_time
        fps      = 1.0 / dt if dt > 0 else 0.0
        prev_time = now
        frame_count += 1

        detections = detector.detect(frame)
        counts     = get_quadrant_counts(frame, detections)
        total      = sum(counts.values())

        # Annotate
        annotated  = visualizer.draw(frame.copy(), detections)
        visualizer.draw_quadrants(annotated, counts)

        # Update shared state
        state.update({
            "frame_count"  : frame_count,
            "fps"          : round(fps, 1),
            "total_persons": total,
            "quadrants"    : counts,
        })
        record = {
            "ts"   : round(now * 1000),
            "frame": frame_count,
            "fps"  : round(fps, 1),
            **counts,
            "total": total,
        }
        state["history"].append(record)
        if len(state["history"]) > 500:
            state["history"].pop(0)

        # Record to database
        if state["session_id"] is not None:
            record_frame(state["session_id"], frame_count, fps,
                         counts["Q1"], counts["Q2"], counts["Q3"], counts["Q4"])

        # Encode JPEG for MJPEG stream
        _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 78])
        with frame_lock:
            output_frame = buf.tobytes()

        # Push real-time update to all connected clients
        socketio.emit("update", {
            "frame": frame_count,
            "fps"  : round(fps, 1),
            "Q1"   : counts["Q1"],
            "Q2"   : counts["Q2"],
            "Q3"   : counts["Q3"],
            "Q4"   : counts["Q4"],
            "total": total,
            "appliances": get_appliances_state(total)
        })

    cap.release()
    
    if state["session_id"] is not None:
        flush_all()
        end_session(state["session_id"])
        state["session_id"] = None

    state["running"] = False
    with frame_lock:
        output_frame = None
    socketio.emit("srv_stopped", {})


# ── MJPEG generator ───────────────────────────────────────────────────────────
def mjpeg_stream():
    while True:
        with frame_lock:
            data = output_frame
        if data is None:
            time.sleep(0.04)
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n")
        time.sleep(0.033)   # cap at ~30 fps pushed to client


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(mjpeg_stream(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/start", methods=["POST"])
def api_start():
    data        = request.json or {}
    source_type = data.get("source", "webcam")

    if state["running"]:
        return jsonify({"error": "Detection already running"}), 400

    if source_type == "webcam":
        source = CAMERA_INDEX
    elif source_type == "video":
        path = data.get("path", "").strip()
        if not path:
            return jsonify({"error": "No video path provided"}), 400
        source = path
    else:
        return jsonify({"error": "Invalid source type"}), 400

    # Reset
    session_id = start_session(source_type)
    state.update({
        "running"      : True,
        "source_type"  : source_type,
        "session_id"   : session_id,
        "frame_count"  : 0,
        "fps"          : 0.0,
        "total_persons": 0,
        "quadrants"    : {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0},
        "history"      : [],
    })
    stop_event.clear()
    threading.Thread(target=detection_loop, args=(source,), daemon=True).start()
    return jsonify({"status": "started", "source": source_type})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    stop_event.set()
    state["running"] = False
    return jsonify({"status": "stopped"})


@app.route("/api/detect_image", methods=["POST"])
def api_detect_image():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    img_bytes = request.files["file"].read()
    nparr     = np.frombuffer(img_bytes, np.uint8)
    frame     = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"error": "Cannot decode image"}), 400

    detections = detector.detect(frame)
    counts     = get_quadrant_counts(frame, detections)
    total      = sum(counts.values())

    annotated  = visualizer.draw(frame.copy(), detections)
    visualizer.draw_quadrants(annotated, counts)

    _, buf    = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
    img_b64   = "data:image/jpeg;base64," + base64.b64encode(buf).decode()

    # Log to DB as a single-frame session
    sid = start_session("image")
    record_frame(sid, 1, 0.0, counts["Q1"], counts["Q2"], counts["Q3"], counts["Q4"])
    flush_all()
    end_session(sid)

    det_list = []
    for i, d in enumerate(detections):
        x1, y1, x2, y2 = d["bbox"]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        det_list.append({
            "id"        : i + 1,
            "label"     : d["label"],
            "confidence": round(d["confidence"] * 100, 1),
            "bbox"      : list(d["bbox"]),
            "quadrant"  : point_quadrant(frame, cx, cy),
        })

    return jsonify({
        "image"          : img_b64,
        "quadrants"      : counts,
        "total"          : total,
        "appliances"     : get_appliances_state(total),
        "detection_count": len(detections),
        "detections"     : det_list,
    })


@app.route("/api/status")
def api_status():
    s = {k: v for k, v in state.items() if k != "history"}
    return jsonify(s)


@app.route("/api/history")
def api_history():
    return jsonify(state["history"])


@app.route("/api/db/analytics")
def api_db_analytics():
    return jsonify({
        "analytics": get_analytics(),
        "hourly"   : get_hourly_summary()
    })

@app.route("/api/db/sessions")
def api_db_sessions():
    limit = int(request.args.get("limit", 20))
    return jsonify(get_sessions(limit))


@app.route("/api/db/export_csv")
def api_db_export_csv():
    data = get_hourly_summary()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["Date/Time", "Average Persons", "Peak Persons", "Total Frames Processed"])
    for r in data:
        dt = datetime.datetime.fromtimestamp(r["hour_ts"]).strftime('%Y-%m-%d %H:%M:%S')
        cw.writerow([dt, r["avg_persons"], r["peak_persons"], r["frame_count"]])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=classroom_hourly_stats.csv"
    output.headers["Content-type"] = "text/csv"
    return output


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "═" * 52)
    print("  🎓  Smart Classroom AI Dashboard")
    print("  ➜  Open: http://localhost:5050")
    print("═" * 52 + "\n")
    socketio.run(app, host="0.0.0.0", port=5050, debug=False, use_reloader=False)
