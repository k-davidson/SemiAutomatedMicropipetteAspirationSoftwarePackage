from time import *
from SoftwareDrivers.serial_driver import *

def serialPumpDemo():
    errNo = 0
    ser = initialise_serial(errNo, "/dev/cu.usbmodem14101", 57600)
    sleep(2)

    transmit_serial(errNo, ser, "%\n")
    await_ack(errNo, ser)
    sleep(1)
    
    transmit_serial(errNo, ser, "N0 S00 D0 V15\n")
    await_ack(errNo, ser)
    sleep(16)

    transmit_serial(errNo, ser, "N2 S01 D1 V15\n")
    await_ack(errNo, ser)
    sleep(6)

    transmit_serial(errNo, ser, "%\n")
    await_ack(errNo, ser)
    sleep(1)


if __name__ == "__main__":
    serialPumpDemo()