import cv2
from ultralytics import YOLO
import numpy as np
import os
import time
from paddleocr import PaddleOCR

def variance_of_laplacian(img):
    return cv2.Laplacian(img, cv2.CV_64F).var()

def illumination_uniformity(gray, rows=8, cols=8):
    h, w = gray.shape
    means = []
    for r in range(rows):
        for c in range(cols):
            y1 = r * h // rows
            y2 = (r + 1) * h // rows
            x1 = c * w // cols
            x2 = (c + 1) * w // cols
            tile = gray[y1:y2, x1:x2]
            means.append(tile.mean())
    means = np.array(means)
    # metric = means.std() / (means.mean() + 1e-6)
    return means.mean(), means.std()

extraction_path = r"C:\Users\User\Documents\PrudenceMoney\Scripts\extracted_bills" #
illum = []
min_cov = 0.45 #FINAL
min_ill = 115 ; max_ill = 243 
min_lap = 400
max_duration = 100 #CHANGE
confidence = 0.9



def main():
    flag = 0 #to detect when a proper image was taken
    # 1. Load the pre-trained YOLO model (Nano version for speed)
    # You can also use a custom model by passing the path to 'best.pt'
    model = YOLO(r"C:\Users\User\Documents\PrudenceMoney\Scripts\yolo_transfer_learn\runs\detect\receipt_transfer_learning\yolo26s_v1\weights\best.pt") 
    class_names = model.names
    font = cv2.FONT_HERSHEY_SIMPLEX ; font_scale = 0.8 ; thickness = 3 ; font_col = (0,0,255) ; 

    # 2. Initialize the webcam feed (0 is usually the default internal webcam)
    cap = cv2.VideoCapture(2)

    # Check if the webcam opened successfully
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    duration = 0 #the number of frames for which acquisition conditions are continuously met
    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()
        H,W = frame.shape[:2] #for spatial coverage calculation
        if not ret:
            print("Error: Failed to grab frame.")
            break

        # 3. Run YOLO inference on the frame
        # stream=True utilizes a generator, making it highly memory efficient for video
        results = model(frame, conf = confidence, stream=True)

        # 4. Extract and plot the predictions onto the frame
        for r in results:
            # .plot() returns a NumPy array containing the frame with visual annotations
            display_frame = frame.copy()
            annotated_frame = r.plot()
            bbox_list = r.boxes
            if len(bbox_list) == 0:
                cv2.putText(display_frame, "No Receipt Detected!", (10,30), font , font_scale, font_col, thickness)
                break
            for bbox in bbox_list:
                class_id = int(bbox.cls[0])
                if(bbox.conf < confidence): #to avoid misinterpretations
                    cv2.putText(display_frame, "No Receipt Detected!", (10,30), font , font_scale, font_col, thickness)
                    break
                class_name = class_names[class_id]
                if class_name == "receipt":
                    display_frame = annotated_frame
                    cds = bbox.xyxy[0].tolist() #top left and bottom right corner coordinates
                    x1,y1,x2,y2 = cds
                    x1,y1,x2,y2 = round(x1), round(y1), round(x2), round(y2)
                    bill_patch = frame[y1:y2, x1:x2]
                    gray_patch = cv2.cvtColor(bill_patch, cv2.COLOR_BGR2GRAY)

                    mean, std = illumination_uniformity(gray_patch)
                    score = variance_of_laplacian(gray_patch)
                    illum.append(mean)
                    coverage = coverage = (((x2-x1)*(y2-y1)) / (H*W))*100

                    #check if frame satisfies acquisition criteria
                    if(coverage >= min_cov and score > min_lap and (mean >= min_ill and mean <= max_ill)):
                        duration = duration + 1
                    else:
                        duration = 0 #reset cycle

                    #Displaying content across lines
                    x,y = (10,30) #starting point
                    (text_w, text_h), baseline = cv2.getTextSize("Hello there",font, font_scale, thickness )
                    gap_line = text_h + baseline + 10
                    lines = [f"Bill Detected  -  Mean : {mean}", f"Blur Score : {score}", f"Coverage : {coverage}"]

                    if(duration > max_duration):
                        lines.append("READY!")                        
                        #for now it caputes an image on its own, later will need to make the user click determine that
                        num_bills = len(os.listdir(extraction_path))
                        cv2.imwrite(rf"./extracted_bills/bill_{num_bills+1}.jpg", bill_patch)
                        print("Receipt Image Captured..............")
                        flag = 1 # so that now we can terminate video capture
                        time.sleep(3)

                    for idx in range(len(lines)) : 
                        cv2.putText(display_frame, lines[idx], (x,y), font , font_scale, font_col, thickness)
                        y = y + gap_line
               
        # 5. Display the resulting live feed
        cv2.imshow("YOLO Live Detection", display_frame)
        # 6. Break the loop if the 'q' key is pressed
        if (cv2.waitKey(1) & 0xFF == ord('q')) or flag == 1:
            break

    # Clean up and close windows properly
    
        
    cap.release()
    cv2.destroyAllWindows()

    #OCR Inference
    if flag==1:
        ocr = PaddleOCR(
            use_doc_orientation_classify=True, #automatically detects and corrects orientation
            use_doc_unwarping=True, #fixes orientation of the net receipt to make its front view rectangular
            use_textline_orientation=False,
            engine="paddle",
        )
        result = ocr.predict(os.path.join(extraction_path, "bill_1.jpg"))
        for res in result: #each res is a "results" object in PaddleOCR havint methods like .print(), .save_to_img() etc, you can also treat it like a dictionary
            res.print()
            res.save_to_img(r"C:\Users\User\Documents\PrudenceMoney\output")
            res.save_to_json(r"C:\Users\User\Documents\PrudenceMoney\output")
            arr = res["rec_scores"]
            avg_conf = sum(arr)/len(arr)
            print(f"Average Confidence of OCR prediction: {avg_conf}")

if __name__ == "__main__":
    main()


"""
Illumination with 4x4 grid: (setting both extreme thresholds)
Mean around 20 -> approx pitch black, the bill gets barely detected and content is not at all visible
Mean around 45-50 -> lighting is better, bill boundary is visible but content is not clear enough
even uptile 80 -> can identify bill by eye but still need more brightness for OCR
When under yellow light -> was around 180 - 200
Blur score in darknes reached max 230-240;

3 thresholds:
Spatial Coverage of Bill : 0.45
Laplacian Variance for blur : 400
Illumination via mean intensity : 115 - 243
"""