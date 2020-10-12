import cv2
import time


from  SerialCommunication.SoftwareDrivers.gcode_driver import *
from SerialCommunication.SoftwareDrivers.serial_driver import *

from multiprocessing import *

import settings


POSITIONS = [0,5]
TIME_DELAY = 10

def transmission_process(sendQueue):
    sel = 1
    errNo = 0
    ser = initialise_serial(errNo, "/dev/cu.usbmodem14201", 57600)
    while(1):
        if(not sendQueue.empty()):
            msg = sendQueue.get()

            if(msg == -1):
                exit(0)

            segment = codeSequence([GCodeSegment("G00", 
            int(POSITIONS[sel]*settings.STEPS_PER_MICRON * 0.85 * settings.MICROSTEPPING), 
            rate = 300)])
            sel = 0 if sel else 1
            time.sleep(1)
            segment.transmit_sequence(ser, errNo)

def command_process(sendQueue, n):
    cap = cv2.VideoCapture(0)
    currTime = time.time()
    for i in range(n):
        print("Iteration %d of %d (approx %d seconds remaining)\n"%(i, n, (TIME_DELAY + 2)*(n-i)))
        while(time.time() - currTime < TIME_DELAY):
            ret, frame = cap.read()
            cv2.imshow("Repeatability demo",frame)
            if(cv2.waitKey(50) == ord("q")):
                sendQueue.put(-1)
                exit(0)
        
        sendQueue.put(1)
        currTime = time.time()
    
    sendQueue.put(-1)


if __name__ == "__main__":
    sendSemaphore = Queue()
    errNo = 0
    transmitProcess = Process(target = transmission_process, args =[sendSemaphore])
    transmitProcess.start()
    commandProcess = Process(target = command_process, args = [sendSemaphore, 100])
    commandProcess.start()
    commandProcess.join()