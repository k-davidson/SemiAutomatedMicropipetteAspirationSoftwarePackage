from SoftwareDrivers.gcode_driver import *
from multiprocessing import *
from time import *

'''
Function        serial_comm_process
Debrief         Managers sending and recieving of serial commands
Arguments       serialOut   Queue of <codeSequence> objects to transmit
                serialIn    Queue of strings from the incoming serial
                ser         Serial communication object
                errNo       Error indicator
'''
def serial_comm_process(errNo, ser, serialOut, serialIn):
    while(1):
        #Prioritise transmission, check if anything to transmit
        while(not(serialOut.empty())):
            #Attempt to transmit sequence
            if not(serialOut.get()).transmit_sequence(ser, errNo):
                return errNo
            

        #Check if anything to recieve
        if(command := recieve_serial(errNo, ser, 1)):
            serialIn.put(command)

def serialProcessExample():
    serialOut = Queue()
    serialIn = Queue()
    errNo = 0
    ser  = initialise_serial(errNo, "/dev/cu.usbmodem14101")
    sleep(1)
    testSeg = GCodeSegment("G00", 10)
    testSeq = codeSequence([testSeg])
    #Prioritise transmission, check if anything to transmit
    #Attempt to transmit sequence
    transmit_serial(errNo, ser, "VOL 30\n")
    
if __name__ == "__main__":
    serialProcessExample()