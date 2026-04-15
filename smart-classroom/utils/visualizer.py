import cv2
import time


class Visualizer:
    def __init__(self):
        self.prev_time = 0

    # ── Bounding boxes + labels ──────────────────────────────────────────────
    def draw(self, frame, detections):
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            label = f"{det['label']} {det['confidence']:.2f}"

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame

    # ── Quadrant lines + per-quadrant person counters ────────────────────────
    def draw_quadrants(self, frame, counts):
        """
        Overlay the 4-quadrant grid and person counts on *frame* (in-place).

        counts: dict returned by get_quadrant_counts()  →  {"Q1":n, ...}

        Layout:
            Q1 (top-left)  | Q2 (top-right)
            ───────────────+───────────────
            Q3 (bot-left)  | Q4 (bot-right)
        """
        h, w = frame.shape[:2]
        mid_x, mid_y = w // 2, h // 2

        line_color  = (255, 255, 0)   # cyan-yellow
        text_color  = (255, 255, 0)
        font        = cv2.FONT_HERSHEY_SIMPLEX
        font_scale  = 0.7
        thickness   = 2

        # Draw dividing lines
        cv2.line(frame, (mid_x, 0), (mid_x, h), line_color, 1)   # vertical
        cv2.line(frame, (0, mid_y), (w, mid_y), line_color, 1)   # horizontal

        # Q1 — top-left
        cv2.putText(frame,
                    f"Q1: {counts['Q1']} person(s)",
                    (10, mid_y - 10),
                    font, font_scale, text_color, thickness, cv2.LINE_AA)

        # Q2 — top-right
        label_q2 = f"Q2: {counts['Q2']} person(s)"
        (tw, _), _ = cv2.getTextSize(label_q2, font, font_scale, thickness)
        cv2.putText(frame,
                    label_q2,
                    (w - tw - 10, mid_y - 10),
                    font, font_scale, text_color, thickness, cv2.LINE_AA)

        # Q3 — bottom-left
        cv2.putText(frame,
                    f"Q3: {counts['Q3']} person(s)",
                    (10, mid_y + 30),
                    font, font_scale, text_color, thickness, cv2.LINE_AA)

        # Q4 — bottom-right
        label_q4 = f"Q4: {counts['Q4']} person(s)"
        (tw, _), _ = cv2.getTextSize(label_q4, font, font_scale, thickness)
        cv2.putText(frame,
                    label_q4,
                    (w - tw - 10, mid_y + 30),
                    font, font_scale, text_color, thickness, cv2.LINE_AA)

        # Total bar at bottom
        total = sum(counts.values())
        cv2.putText(frame,
                    f"Total persons: {total}",
                    (10, h - 15),
                    font, 0.7, (0, 200, 255), 2, cv2.LINE_AA)

        return frame

    # ── FPS counter ──────────────────────────────────────────────────────────
    def draw_fps(self, frame):
        curr_time = time.time()
        fps = 1 / (curr_time - self.prev_time) if self.prev_time else 0
        self.prev_time = curr_time
        cv2.putText(frame, f"FPS: {int(fps)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return frame