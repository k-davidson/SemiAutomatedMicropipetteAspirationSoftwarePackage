from .SoftwareDrivers.gcode_driver import *
from .SoftwareDrivers.ConfigFiles.settings import *
from Emulator.emulator_os import *
from multiprocessing import *
import time


def initialise_serial_process(context, emulate):
    serialProcess = Process(target = serial_comm_process, args =[context, SERIAL_PORT, emulate])
    serialProcess.start()

    return serialProcess.pid


'''
Function        serial_comm_process
Debrief         Manages sending and recieving of serial communications
Arguments       SOut (Queue) Queue of G-Code Sequences to transmit
                SIn (Queue)  Queue to put recieved command
                ser (Serial) Serial object to transmit/recv from
'''
def serial_comm_process(context, deviceName, emulate):
    errNo = 0
    if(SERIAL_EMULATOR):
        ser = emulate
    else:
        print("Device called:%s"%(deviceName))
        print("Baud:%d"%(BAUDRATE))
        ser = initialise_serial(errNo, deviceName, BAUDRATE)

    time.sleep(1)
    while(1):
        if(ser):
            #Prioritise transmission, check if anything to transmit
            while(not(context.sOut.empty())):
                #Attempt to transmit sequence
                sequence = context.sOut.get()
                if not(sequence.transmit_sequence(ser, transmit_disp = context.sDisp)):
                    context.put_comm_success(False)
                else:
                    context.put_comm_success(True)

            #Check if anything to recieve
            command = recieve_serial(errNo, ser, 1)
            if(command):
                context.sIn.put(command)