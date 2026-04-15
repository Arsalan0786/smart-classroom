# Place your YOLO weights file here as:  best.pt
#
# If you don't have custom weights yet, you can bootstrap with a
# pretrained model — Ultralytics will auto-download on first run:
#
#   from ultralytics import YOLO
#   model = YOLO("yolov8n.pt")      # nano
#   model = YOLO("yolov8s.pt")      # small
#
# Then fine-tune on your classroom dataset and save:
#   model.train(data="dataset.yaml", epochs=50)
#   # best weights land in runs/detect/train/weights/best.pt
#   # copy that file here as  models/best.pt
