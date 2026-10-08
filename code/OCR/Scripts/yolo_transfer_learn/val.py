from ultralytics import YOLO

model = YOLO("runs/detect/train/weights/best.pt") #check

metrics = model.val(data=r"...\Receipt Detection Dataset for YOLO\dataset.yaml") 

print(metrics)