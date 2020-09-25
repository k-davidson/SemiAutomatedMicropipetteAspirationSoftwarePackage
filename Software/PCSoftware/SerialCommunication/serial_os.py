from .SoftwareDrivers.gcode_driver import *
from Emulator.emulator_os import *
from multiprocessing import *
import time


def initialise_serial_process(context, deviceName, emulate):
    errNo = 0
    for port in source_com_ports(errNo):
        print("Port is:%s\n"%(port))
    serialProcess = Process(target = serial_comm_process, args =[context, deviceName, emulate])
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
    if(not emulate):
        ser = initialise_serial(errNo, deviceName, 57600)
    else:
        ser = emulate
    time.sleep(1)
    while(1):
        if(ser):
            #Prioritise transmission, check if anything to transmit
            while(not(context.outEmpty())):
                #Attempt to transmit sequence
                sequence = context.getOut()
                if not(sequence.transmit_sequence(ser, errNo)):
                    context.put_comm_success(False)
                else:
                    context.put_comm_success(True)

            #Check if anything to recieve
            if(command := recieve_serial(errNo, ser, 1)):
                context.putIn(command)