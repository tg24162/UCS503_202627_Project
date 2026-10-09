# WEEK 7

### **What We Did This Week:**

1. **Bill Detection**
- Performed **Transfer Learning** on a pretrained yolo26s model
- Used large **Receipt Detection** dataset found online

2. **Finetuning Blur threshold for "Acquisition" Process**
- Decided to use Laplacian operator's variance as blur estimate
- Used a small custom dataset of blurred and non blurred text to get an idea of a threshold
- Tried testing using phone and OpenCV live feed

3. **Finetuning Illumination threshold for "Acquisition" Process**
- Used hit and trial testing (temporary) to infer a minimum illumination value suitable for OCR
- This was subject to immense variation, hence selected a range instead of a single numeric limit

4. **Attempted Integrating "Acquisition" process with PaddleOCR**



 






