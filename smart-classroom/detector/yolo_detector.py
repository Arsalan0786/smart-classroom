from ultralytics import YOLO

class YOLODetector:
    def __init__(self, model_path, conf_threshold):
        self.model = YOLO(model_path)
        self.conf = conf_threshold
        self.class_names = self.model.names

    def detect(self, frame):
        results = self.model(frame, conf=self.conf)[0]
        detections = []

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])

            detections.append({
                "bbox": (x1, y1, x2, y2),
                "confidence": conf,
                "class_id": cls,
                "label": self.class_names[cls]
            })

        return detections