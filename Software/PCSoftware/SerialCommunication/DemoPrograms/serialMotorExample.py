import os.path
import sys

modulePath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, modulePath)

from time import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from SoftwareDrivers.gcode_driver import *


def serialTransmissionProcess(port, baud, transmitQueue, successQueue):
    ser = initialise_serial(errNo, port, baudrate=baud)

    while(1):
        if(not transmitQueue.empty()):
            command = transmitQueue.get()
            successQueue.put(command.transmit_sequence(ser))

def serialMotorDemo(port, baud):
    errNo = 0
    ser = initialise_serial(errNo, port, baudrate=baud)

    app = QApplication([])
    window = QMainWindow()
    layout = QGridLayout()

    stepperLabel1 = QLabel("Stepper Absolute Position:")
    layout.addWidget(stepperLabel1)

    window.setLayout(layout)
    window.show()
    sys.exit(app.exec_())

    '''
    errNo = 0
    ser = initialise_serial(errNo, "/dev/cu.usbmodem14101", 57600)
    sleep(2)

    transmit_serial(errNo, ser, "%\n")
    await_ack(errNo, ser)
    sleep(1)
 
    transmit_serial(errNo, ser, "N0 G00 200\n")
    await_ack(errNo, ser)
    sleep(8)
    
    transmit_serial(errNo, ser, "N1 G01 -200\n")
    await_ack(errNo, ser)
    sleep(8)
    
    transmit_serial(errNo, ser, "N2 G91\n")
    await_ack(errNo, ser)
    sleep(8)

    transmit_serial(errNo, ser, "N3 G01 200\n")
    await_ack(errNo, ser)
    sleep(8)

    transmit_serial(errNo, ser, "N4 G01 200\n")
    await_ack(errNo, ser)
    sleep(8)

    transmit_serial(errNo, ser, "N5 T 1\n")
    await_ack(errNo, ser)
    sleep(8)

    transmit_serial(errNo, ser, "N6 G01 200\n")
    await_ack(errNo, ser)
    sleep(8)

    transmit_serial(errNo, ser, "N7 G10\n")
    await_ack(errNo, ser)
    sleep(8)

    transmit_serial(errNo, ser, "%\n")
    await_ack(errNo, ser)
    sleep(1)
    '''


if __name__ == "__main__":
    serialMotorDemo(sys.argv[1], sys.argv[2])