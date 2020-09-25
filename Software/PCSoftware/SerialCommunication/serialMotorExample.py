from time import *
from SoftwareDrivers.serial_driver import *
from SoftwareDrivers.gcode_driver import *

def serialMotorDemo():
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


if __name__ == "__main__":
    serialMotorDemo()