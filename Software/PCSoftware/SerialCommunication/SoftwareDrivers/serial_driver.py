from .ConfigFiles.serial_config import *
import sys
import serial.tools.list_ports
import time



'''
Libraries:         PYSERIAL: Python serial library
CONFIG             SERIAL.config        
'''


'''
Define:             commands    Dict of recognised commands and related queues

'''

'''
Function            transmit_serial
Debrief:            Transmits string over serial and returns ERR_CODE. Not
                    accessed directly.
Arguments           buffer      String to be transmitted
                    ser         Serial object
Optional Arguments  attempts    Number of attempts to transmit upon failure.
                                Default value configured in SERIAL.config.
Return value        0           if the string was transmitted successfully
                    ...
'''
def transmit_serial(errNo, ser, buffer, attempts = TRANSMIT_ATTEMPTS):
    #Iterate over attempts
    for a in range(attempts):
        try:
            write = ser.write(buffer.encode())
            time.sleep(0.75)

            #Successful transmission
            print("> Transmitted %s"%(buffer))
            return write

        except(OSError, serial.SerialTimeoutException):
            continue
    
    #Reached limit of attempts
    print("ERR_CODE 05: Serial timeout after %d attempts."%(attempts))
    errNo = 5
    return None
    
'''
Function            await_conf
Debrief             Awaits ACK packet from microcontroller of GCODE sequence. 
                    Not acessed directly.
Arguments           ser         Serial object
Optional Arguments  conf_packet  Acknowledgment packet format. Default value
                                configured in SERIAL.config.
                    sec         Time to wait in seconds
Return value        None        Error, check errNo to specify
                    1           Successful acknowledgment
'''
def await_conf(errNo, ser, sec = 3, conf_packet = ACK_PACKET):
    time.sleep(0.75)
    #If no acknowledgment packet recieved
    if not (recvpacket := recieve_serial(errNo, ser, 1)):
        print("ERR_CODE 07: No ACK recieved before timeout.")
        errNo = 7
        return None
    #If packet recieved but is not acknowledgment
    if not (conf_packet == recvpacket[0]):
        print("ERR_CODE 08: Invalid acknowledgment packet." + 
        "Recieved %s instead of %s."%(repr(recvpacket), repr(conf_packet)))
        errNo = 8
        return None
    
    #Successfully recieved acknowledgment packet
    print("> Recieved ACK packet")
    return 1

'''
Function            recieve_serial
Debrief             Recieve serial transmission.
Arguments           ser         Serial object
                    seq_len     Maximum number of strings expected. Default 
                                value configured in SERIAL.config.
Optional Arguments  attempts    Number of attempts to recieve upon timeout.
                                Default value configured in SERIAL.config.
Return value        buffer      Array of strings, serial contents
                    None        Insufficent serial commands recieved
'''
def recieve_serial(errNo, ser, seq_len, attempts = RECV_ATTEMPTS):
    buffer = []
    
    #Iterate over sequence
    for a in range(seq_len):
        #Iterate over the attempts
        for b in range(attempts):
            if(ser.inWaiting()):
            #Verify returned with contents
                incoming = ser.readline().decode()
                buffer.append(incoming.rstrip("\n"))
                break
            if b == attempts - 1:
                '''
                print("ERR_CODE 06: Failed attempting to recieve command (%d) "%(a + 1) +
                        "in sequence of length (%d)."%(seq_len))
                '''
                errNo = 6
                return None
    return buffer

'''
Function            intialise_serial
Debrief             Initialise a serial object
Arguments           port:       Port specifier

Optional Arguments  ser         Empty serial object
                    baudrate    Baud rate of serial communication. Default value
                                configured in SERIAL.config.
                    exclusive   Exclusive access mode. Default value configured
                                in SERIAL.config.
Return value        0           No error in serial initialisation
                    7           ValueError raised in initialisation
                    8           Serial Exception raised in initialisation                     
'''
def initialise_serial(errNo, port, baudrate = BAUDRATE, exclusive = EXCLUSIVE):
    print("Baudrate is %d\n"%(BAUDRATE))
    
    #Attempt to initialise serial on specified port
    try:
        ser = serial.Serial(port, baudrate, exclusive = exclusive, 
                            timeout = READ_TIMEOUT, write_timeout = WRITE_TIMEOUT)
        time.sleep(0.5)
    
    #Serial exception raied
    except(OSError, serial.SerialException):
        print("ERR_CODE 03: Serial exception, the device can not be found or " +
                "can not be configured. ")
        errNo = 3
        return None
    
    #Value error raised
    except ValueError as e:
        print("ERR_CODE 04: Value error: %s" %(e))
        errNo = 4
        return None
    

    #Successful intialisation
    return ser

'''
Function            source_com_ports
Debrief             Find all available COMM ports
Arguments           portDict    Empty dictionary object
Optional Arguments  supported   Array of compatable platforms. Default value
                                configured in SERIAL.config.
Return value        0           Successful sourcing of COMM ports
                    1           No COMM ports detected
                    2           The system is not compatiable                   
'''
def source_com_ports(errNo, supported = SUPPORTED):
    #Initialise array of ports
    portDict = {}

    #Check if LINUX system
    if sys.platform.startswith('linux') and 'linux' in supported:
        #Need to verify how to get ports for system
        pass

    #Check if MAC system
    elif sys.platform.startswith('darwin') and 'darwin' in supported:
        ports = list(serial.tools.list_ports.comports())

    #Check if WINDOWS system
    elif sys.platform.startswith('win') and 'win' in supported:
        #Need to verify how to get ports for system
        pass
    
    #System is not supported
    else:
        print("ERR_CODE 1: Current system is not supported.")
        errNo = 1
        return None

    if not len(ports):
        print("ERR_CODE 02: No serial communication devices detected.")
        errNo = 2
        return None

    #Create dictionary with device names as the keys
    for port in ports:
        portDict[port.device] = port

    return portDict

'''
Function            deinitialise_serial
Debrief             Deinitialise a serial object
Arguments           ser         Serial object

Optional Arguments  closing     String for shutdown transmission. Default value
                                configured in SERIAL.config.
                    close_fail  Set if continue to close if fail shutdown 
                                transmission. Default value configured
                                in SERIAL.config.
Return value        0           Successful close and shutdown transmission
                    1           Failed to transmit shutdown transmission                     
'''
def deinitialise_serial(errNo, ser, closing = END_PACKET, close_fail = CLOSE_FAIL):
    
    #Transmit closing command
    transmit_serial(errNo, ser, closing)

    #No acknowledgment of closing
    if not(await_conf(errNo, ser, 3)):
        print("ERR_CODE 09: Failed to communicate port close.")

        #Check if port should remain open
        if not close_fail:
            ser.close()
    
        return None
    
    #Successful communication of closing
    ser.close()
    return 1

'''
Function            set_read_timeout
Debrief             Set read serial timeout in seconds
Arguments           ser         Serial object
                    timeout     Seconds before read timeout                  
'''
def set_read_timeout(ser, sec):
    #Set read timeout in serial object
    ser.timeout = sec

'''
Function            set_write_timeout
Debrief             Set write serial timeout in seconds
Arguments           ser        Serial object
                    timeout    Seconds before write timeout                  
'''
def set_write_timeout(ser, sec):
    #Set write timeout in serial object
    ser.write_timeout = sec


'''
Function            set_rts           
Debrief             Sets the serial RTS pin
Arguments           ser        Serial object  
                    state      State to set RTS pin         

'''
def set_rts(ser, state):
    ser.rts = state

'''
Function            set_cts          
Debrief             Sets the serial CTS pin
Arguments           state      State to set CTS pin   
                        
'''
def set_cts(ser, state):
    ser.cts = state


'''
Function            get_rts           
Debrief             Gets the serial RTS pin
Arguments           ser        Serial object
Return              state      State to set RTS pin   

'''
def get_rts(ser):
    return ser.rts


'''
Function            get_cts          
Debrief             Gets the serial CTS pin
Return              state      State to set CTS pin   
                        
'''
def get_cts(ser):
    return ser.cts


'''
Function            
Debrief             
Arguments           
Optional Arguments  
Return value                           
'''
