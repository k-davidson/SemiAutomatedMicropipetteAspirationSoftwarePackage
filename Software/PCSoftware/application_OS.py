import qtpy
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtSvg import *
import sys
import os
import signal
import faulthandler

from ComputerVision.image_processing_OS import *
from UserInterface.SoftwareDrivers.GUI_Driver import *
from SerialCommunication.serial_os import *
from Emulator.emulator_os import *
from multiprocessing import *
from time import *
from pty import *

def image_processing_OS_example(args):
    faulthandler.enable()
    
    emOutQ = Queue()
    emInQ = Queue()

    context = AppContext(args[0])

    EMULATE = True

    serialEmulator = None
    captureEmulator = None

    if(EMULATE):
        commandQueue = Queue()
        captureQueue = Queue()

        captureEmulator = CaptureEmulator(captureQueue)
        serialEmulator = SerialEmulator(commandQueue)
        context.add_pid(initialise_emulation_process(commandQueue, captureQueue))
    
    deviceName = "/dev/cu.usbmodem14201"

    context.add_pid(initialise_serial_process(context, deviceName, serialEmulator))
    
    context.add_pid(initialise_computer_vision(context.pixQ, context.posQ, 
        context.capSem, captureEmulator))

    
    guiManagement(context, context.posQ)
    
    
    context.kill.wait()
    
    exit(0)
    
    '''
    errNo = 0
    sleep(5)
    gCodeCommand1 = GCodeSegment("G00", 200)
    gCodeCommand2 = SCodeSegment("S00", 0, 10)
    gCodeSequence = codeSequence([gCodeCommand1, gCodeCommand2])

    while(1):
        capSem.put(1)
        #gCodeSequence.transmit_sequence(ser, errNo)
        sleep(60)
    '''
        
class AppContext(object):
    def __init__(self, configFile):
        #Distribute images captured via the microscope
        self.pixQ = Queue()

        self.capSem = Queue()

        #
        self.posQ = Queue()

        self.sOut = Queue()
        self.sIn = Queue()
        self.sComplete = Queue()

        self.kill = Event()
        self.synch = Event()

        self.pid = []

        self.configFile = configFile
        
    def add_pid(self, pid):
        self.pid.append(pid)

    def put_comm_success(self, state):
        self.sComplete.put(state)

    def get_comm_success(self):
        if(self.sComplete.empty()):
            return None
        else:
            return self.sComplete.get()

    def end_program(self):
        for p in self.pid:
            os.kill(p, signal.SIGKILL)
            
    def add_pix(self, idx, img):
        self.pixQ.put((idx, img))

    def pix_available(self):
        if(self.pixQ.empty()):
            return 0
        return 1
    
    def get_pix(self):
        if(self.pixQ.empty()):
            return (None, None)
        return self.pixQ.get()

    def outEmpty(self):
        return self.sOut.empty()
    
    def getOut(self):
        if(self.sOut.empty()):
            return None
        return self.sOut.get()

    def putIn(self, command):
        self.sIn.put(command)
        return 0


if __name__ == "__main__":
    image_processing_OS_example(sys.argv)