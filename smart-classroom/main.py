import cv2
import argparse
from config import MODEL_PATH, CONF_THRESHOLD, CAMERA_INDEX
from detector.yolo_detector import YOLODetector
from utils.visualizer import Visualizer

# ── CLI ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--source", type=str, default="webcam",
                    help="webcam | path to image | path to video")
args = parser.parse_args()

# ── Init ─────────────────────────────────────────────────────────────────────
detector   = YOLODetector(MODEL_PATH, CONF_THRESHOLD)
visualizer = Visualizer()

# ── Quadrant helpers ─────────────────────────────────────────────────────────
def get_quadrant_counts(frame, detections):
    """
    Divide the frame into 4 equal quadrants and count persons in each.

    Layout (mid_x / mid_y split):
        Q1 = top-left      Q2 = top-right
        Q3 = bottom-left   Q4 = bottom-right

    A person is assigned to the quadrant that contains its bounding-box centre.
    Only detections whose label is 'person' are counted.

    Returns
    -------
    dict  {q: int}   e.g. {"Q1": 2, "Q2": 0, "Q3": 1, "Q4": 3}
    """
    h, w = frame.shape[:2]
    mid_x, mid_y = w // 2, h // 2

    counts = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}

    for det in detections:
        if det["label"].lower() != "person":
            continue

        x1, y1, x2, y2 = det["bbox"]
        cx = (x1 + x2) // 2   # bounding-box centre
        cy = (y1 + y2) // 2

        if cx < mid_x and cy < mid_y:
            counts["Q1"] += 1   # top-left
        elif cx >= mid_x and cy < mid_y:
            counts["Q2"] += 1   # top-right
        elif cx < mid_x and cy >= mid_y:
            counts["Q3"] += 1   # bottom-left
        else:
            counts["Q4"] += 1   # bottom-right

    return counts


def print_quadrant_counts(counts, frame_id=None):
    """Pretty-print the per-quadrant counts on the terminal."""
    total = sum(counts.values())
    tag   = f"Frame {frame_id:>5} | " if frame_id is not None else ""
    print(
        f"{tag}"
        f"Q1(top-left)={counts['Q1']}  "
        f"Q2(top-right)={counts['Q2']}  "
        f"Q3(bot-left)={counts['Q3']}  "
        f"Q4(bot-right)={counts['Q4']}  "
        f"| Total persons={total}"
    )


# ── Run modes ────────────────────────────────────────────────────────────────
def run_image(path):
    frame = cv2.imread(path)
    if frame is None:
        print("❌ Error loading image:", path)
        return

    detections = detector.detect(frame)
    counts     = get_quadrant_counts(frame, detections)

    # Terminal output
    print("\n── Quadrant Person Count ──────────────────────────────")
    print_quadrant_counts(counts)
    print("───────────────────────────────────────────────────────\n")

    # Visual overlay
    frame = visualizer.draw(frame, detections)
    visualizer.draw_quadrants(frame, counts)

    cv2.imshow("Smart Classroom — Image", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def run_video(source):
    cap = cv2.VideoCapture(CAMERA_INDEX if source == "webcam" else source)
    if not cap.isOpened():
        print("❌ Error opening source:", source)
        return

    print("\n[INFO] Running — press  q / ESC  to quit\n")
    print(f"{'Frame':>7}  Q1  Q2  Q3  Q4  Total")
    print("─" * 40)

    frame_id = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        detections = detector.detect(frame)
        counts     = get_quadrant_counts(frame, detections)

        # Terminal output (every frame)
        print_quadrant_counts(counts, frame_id)

        # Visual overlay
        frame = visualizer.draw(frame, detections)
        visualizer.draw_quadrants(frame, counts)
        visualizer.draw_fps(frame)

        cv2.imshow("Smart Classroom — Detection", frame)

        if cv2.waitKey(1) & 0xFF in (27, ord("q")):
            break

        frame_id += 1

    cap.release()
    cv2.destroyAllWindows()
    print("\n[INFO] Done.")


# ── Route ────────────────────────────────────────────────────────────────────
src = args.source.lower()
if src == "webcam":
    run_video("webcam")
elif src.endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
    run_image(args.source)
else:
    run_video(args.source)