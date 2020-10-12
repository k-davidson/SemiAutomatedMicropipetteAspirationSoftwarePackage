import cv2
import time

from SerialCommunication.SoftwareDrivers.serial_driver import *
from SerialCommunication.SoftwareDrivers.serial_driver import *

from settings import *


POSITIONS = [0,3]

def repeatabilityExperiment(n):
    errNo = 0
    time.sleep(1)
    ser = initialise_serial(errNo, "/dev/cu.usbmodem14201", 57600)
    time.sleep(1)

    if(not ser):
        print("Unable to find serial device\n")
        return
    
    sel = 0
    cap = cv2.VideoCapture(0)
    currTime = time.time()
    if(cap == None):
        print("Unable to capture from camera 0\n")
        return
    for i in range(n):
        while(currTime - time.time() < 10):
            ret, frame = cap.read()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            cv2.imshow("Repeatability demo",gray)
            cv2.waitKey(34)
        segment = [GCodeSegment("G00", POSITIONS[sel]*settings.STEPS_PER_MICRON, 300)]
        sel = 0 if sel else 1
        segment.transmit_sequence(ser, errNo)



if __name__ == "__main__":
    repeatabilityExperiment(100)