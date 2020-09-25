import cv2
import time


from  SerialCommunication.SoftwareDrivers.gcode_driver import *
from SerialCommunication.SoftwareDrivers.serial_driver import *

import config


POSITIONS = [0,5]
TIME_DELAY = 2

def repeatabilityExperiment(n):
    errNo = 0
    
    ser = initialise_serial(errNo, "/dev/cu.usbmodem14201", 57600)
    sel = 1
    cap = cv2.VideoCapture(0)
    cap.read()
    cv2.waitKey(3000)
    '''
    if(ser):
        print("Unable to find serial device\n")
        return
    '''
    
    currTime = time.time()
    if(cap == None):
        print("Unable to capture from camera 0\n")
        return
    for i in range(n):
        print("Iteration %d of %d (approx %d seconds remaining)\n"%(i, n, (TIME_DELAY + 2)*(n-i)))
        while(time.time() - currTime < TIME_DELAY):
            ret, frame = cap.read()
            cv2.imshow("Repeatability demo",frame)
            cv2.waitKey(50)
        segment = codeSequence([GCodeSegment("G00", 
        int(POSITIONS[sel]*config.FineMotionConfig['stepsPerMicron']*config.FineMotionConfig['microStepping']), 
        rate = 10)])
        sel = 0 if sel else 1
        segment.transmit_sequence(ser, errNo)
        currTime = time.time()



if __name__ == "__main__":
    repeatabilityExperiment(100)