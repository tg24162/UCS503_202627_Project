from ultralytics import YOLO

def main():
    # Load COCO-pretrained model
    model = YOLO(r"...\weights\yolo26s.pt")
    print(f"MODEL USED IS : {model}")
    #Transfer Learning
    results = model.train(
        data=r"...\Receipt Detection Dataset for YOLO\dataset.yaml",
        epochs=8, #keeping time constraint in mind and drop in number of workers
        imgsz=640, #the input size to yolo, large gives more details (smaller objects not missed) but consumes more VRAM
        batch=8,
        workers=0, # RAM wasnt sufficient for 8 workers
        device=0,
        project="receipt_transfer_learning",
        name="yolo26s_v1"
    )

    print(f"All Transfer learning metrics are saved to : {results.save_dir}")
    print("Transfer Learning Complete")

if __name__ == '__main__': #this guard is necessary for python to use >1 workers!
    main()

#Ensuring GPU existence
# import torch
# print("CUDA available:", torch.cuda.is_available())
# print("GPU count:", torch.cuda.device_count())
# if torch.cuda.is_available():
#     print("GPU:", torch.cuda.get_device_name(0))

"""
Final Validation Results after training for 8 epochs (duration : 1.32 hours):
Total Images : 3731
Precision :  0.994 ; Recall : 0.983 ; mAP50 : 0.992 ; mAP50-95 : 0.961;
Speed: 0.2ms preprocess, 3.7ms inference, 0.0ms loss, 1.2ms postprocess per image;
"""
