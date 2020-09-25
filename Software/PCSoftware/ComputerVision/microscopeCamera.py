import time
import cv2

def cameraDemo():
    cap = cv2.VideoCapture(0)
    while(1):
        ret, frame = cap.read()
        cv2.imshow("Test",frame)
        cv2.waitKey()



if __name__ == "__main__":
    cameraDemo()