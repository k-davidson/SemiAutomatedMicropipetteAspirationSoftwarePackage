import cv2
import time

from  SerialCommunication.SoftwareDrivers.gcode_driver import *
from SerialCommunication.SoftwareDrivers.serial_driver import *

from multiprocessing import *
import settings


POSITIONS = [0,100] # Positions to move between
TIME_DELAY = 10 # Delay between movements

def transmission_process(sendQueue):
    """ Handles transmitting data via serial device

    Args:
        sendQueue (Queue): Queue of int, indicating quit or transmit conditions
    """

    # Select direction
    sel = 1
    errNo = 0

    # Create serial device
    ser = initialise_serial(errNo, "/dev/cu.usbmodem14201", 57600)
    
    # Select appropriate tool
    time.sleep(2)
    segment = codeSequence([GCodeSegment("T", tool = 1)])
    segment.transmit_sequence(ser, errNo)
    
    # Wait on codes to transmit
    while(1):

        # If recieved a code
        if(not sendQueue.empty()):
            # Check what the code is
            msg = sendQueue.get()

            # If -1, quit the process
            if(msg == -1):
                exit(0)

            # Otherwise, transmit a segment
            segment = codeSequence([GCodeSegment("G00", 
            int(POSITIONS[sel]*settings.STEPS_PER_MICRON * 
            settings.MICROSTEPPING), rate = 300)])

            # Change the direction
            sel = 0 if sel else 1

            # Transmit sequence
            segment.transmit_sequence(ser, errNo)

def command_process(sendQueue, n):
    """ Command manager process, handling iterating over number of codes

    Args:
        sendQueue (Queue): Queue to send commands
        n (int): Number of iterations of change in position
    """
    # Create capture device
    cap = cv2.VideoCapture(0)
    
    # Get current time
    currTime = time.time()
    time.sleep(10)

    # Iterate over number of iterations
    for i in range(n):
        print("Iteration %d of %d (approx %d seconds remaining)\n" \
        %(i, n, (TIME_DELAY + 2)*(n-i)))

        # Check the difference in time has sufficient delay
        while(time.time() - currTime < TIME_DELAY):
            # Display current frame
            ret, frame = cap.read()
            cv2.imshow("Repeatability demo",frame)
            # If 'Q' pressed, quit
            if(cv2.waitKey(50) == ord("q")):
                sendQueue.put(-1)
                exit(0)
        
        # Request command transmission
        sendQueue.put(1)
        currTime = time.time()
    
    # Send quit
    sendQueue.put(-1)


if __name__ == "__main__":
    sendSemaphore = Queue()
    errNo = 0
    transmitProcess = Process(target = transmission_process, \
    args =[sendSemaphore])
    transmitProcess.start()
    commandProcess = Process(target = command_process, \
    args = [sendSemaphore, 50])
    commandProcess.start()
    commandProcess.join()