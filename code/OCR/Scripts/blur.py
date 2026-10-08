import os
import cv2
import numpy as np
import matplotlib.pyplot as plt

data_path = r"path to blur_dataset"

def variance_of_laplacian(img):
    return cv2.Laplacian(img, cv2.CV_64F).var()


def main():
    labels = []
    scores = []

    for imgname in os.listdir(data_path):
        label_name = os.path.splitext(imgname)[0][-4:]
        label = "clear" if label_name == "orig" else "blur"
        labels.append(label)
        img = cv2.imread(os.path.join(data_path,imgname))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        score = variance_of_laplacian(gray)
        scores.append(score)
        # cv2.putText(img, "{}: {:.2f}".format(label, score), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)
        # cv2.imshow("Image", img)
        # key = cv2.waitKey(0) #waits until a key is pressed

    #store
    label_arr = np.array(labels)
    scores_arr = np.array(scores)
    np.save("blur_labels.npy", label_arr)
    np.save("blur_scores.npy", scores_arr)

    #plot
    for value, label in zip(scores, labels):
        color = 'red' if label == 'blur' else 'blue' #red for blur, blue for clear
        plt.scatter(value, 0, color=color)

    plt.yticks([])         
    plt.xlabel("Laplacian value")
    plt.axhline(0, color='black', linewidth=0.8)
    # plt.xticks(np.arange(0, 17500.1, 500)) #for increasing display points on x axis
    plt.show()

if __name__ == "__main__":
    main()


"""
INFERENCE OF EXPERIMENT
Blurry images gave laplacian values in the range (32, 2066) but most density was in (0,732)
Clear images ranged in (6000, 17250)
Estimated threshold for laplacian : around 4000 (quite approx)
"""


