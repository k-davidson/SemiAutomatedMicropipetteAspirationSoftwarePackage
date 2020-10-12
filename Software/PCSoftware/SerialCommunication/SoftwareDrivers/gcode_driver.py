from .ConfigFiles.config import *
from .serial_driver import *
import time

class GCodeSegment:
    """ Provides interface for altered G-Code segments for communicating
    position commands throughout the system. Allows for tool selection,
    absolute/relative coordinates, rate of motion and position.
    """
    def __init__(self, code ,pos = None, tool = None, 
    rate = None, reset = None):
        """ Initialise state of G-Code segment

        Args:
            code (String): String representation of G-Code identifier
            pos (int, optional): Integer position (in steps). Defaults to None.
            tool (int, optional): Tool to be selected for following positioning 
            command. Defaults to None.
            rate (int, optional): Rate of movement (in steps per second). 
            Defaults to None.
            reset (int, optional): Reset command. Defaults to None.
        """
        self.code = code
        self.pos = pos if type(pos) == int else None
        self.tool = tool
        self.rate = rate

        # Look up the format of the G-Code command
        self.valid_codes = {
            #Rapid incremental positioning
            "G00":"G00 %d %d"%(self.pos, self.rate) \
            if type(self.pos) == int and type(self.rate) == int else None,
            #Linear positioning
            "G01":"G01 %d"%(self.pos) if type(self.pos) == int else None,
            #Positioning defined in abs coordinates
            "G90":"G90",
            #Positioning defined in relative coordinates
            "G91":"G91",
            #Select tool
            "T":"T %d"%(self.tool) if type(self.tool) == int else None,
            #Start/End of sequence code
            START_END_SEQ:"%c"%(START_END_SEQ),
            #Reset position/pressure
            "#":"# %d"%(reset) if (reset != None) else None
        }

    def serial_cmd(self):
        """ Get the G-Code command to be transmitted.

        Returns:
            String: G-Code command to be transmitted.
        """
        return self.valid_codes[self.code]

    def __repr__(self):
        """ Override of string representation (human readable) of the G-Code
        segment. 

        Returns:
            String: Human-readable format of G-Code segment
        """
        if(self.code == "G00"):
            return "Positioned at %d [steps], %d [steps/sec]" \
                %(self.pos, self.rate)
        
        if(self.code == "T"):
            return "Selecting Tool %d"%(self.tool)

        if(self.code == START_END_SEQ):
            return "Start/End of communication segment"

class SCodeSegment:
    """ Provides interface for S-Code segments (based on G-Code) for 
    communicating pressure commands throughout the system. Allows pressure 
    command.
    """
    def __init__(self, code, volume = None):
        """ Initialise state of S-Code segment

        Args:
            code (String): String representation of S-Code identifier
            volume (int, optional): Volume (in increments of the 
            minimum volume) to pump/withdraw. Negative value indicates withdraw.
            Positive value indicates pumping. Defaults to None.
        """
        self.code = code
        self.volume = volume

        # Look up the format of the S-Code command
        self.valid_codes = {
            #Pumping direction setting
            "S00":"S00 %d"%(self.volume) if type(self.volume == int) else None,
            "S01":"S01 %d"%(self.volume) if type(self.volume == int) else None
        }
    
    def serial_cmd(self):
        """ Get the S-Code segment to be transmitted.

        Returns:
            String: Human-readable format of S-Code segment
        """
        return self.valid_codes[self.code]

    def __repr__(self):
        """ Override of string representation (human readable) of the S-Code
        segment. 

        Returns:
            String: Human-readable format of S-Code segment
        """
        if("S01" == self.code):
            return "Pumping %d uL of fluid"%(self.volume)

class codeSequence:
    """ Provides methods to transmit the contents of a given G-Code/S-Code
    sequence. Handles recieving ACK/NACK and retransmitting upon failure.
    """
    def __init__(self, sequence = []):
        """ Initialise code sequence with list of G-Code/S-Code segments.

        Args:
            sequence (list, optional): List of G-Code/S-Code segments to be 
            transmitted. Defaults to [].
        """
        self.startEnd = GCodeSegment(START_END_SEQ)
        self.sequence = [self.startEnd] + sequence + [self.startEnd]

    def transmit_sequence(self, ser, retransmission = 0, transmit_disp = None):
        """ Transmit the G-Code/S-Code sequence via serial device.

        Args:
            ser (serial): Serial device object to transmit sequence over
            retransmission (int, optional): Number of retransmissions upon
            failure to transmit/recieve ACK. Defaults to 0.
            transmit_disp (Queue, optional): Queue of strings display serial 
            output via a user interface. Defaults to None.

        Returns:
            bool: True iff transmission was successful. Otherwise, false.
        """
        
        for N, code in enumerate(self.sequence):
            errNo = 0
            for a in range(retransmission + 1):
                #Transmit code
                serialCode = "N%d %s"%(N, code.serial_cmd())

                if(transmit_disp):
                    transmit_disp.put("Transmitting > %s"%(serialCode))

                if not transmit_serial(errNo, ser, serialCode + "\n"):
                    if(transmit_disp):
                        transmit_disp.put("Result > Unsuccessful transmission")
                    return False   

                time.sleep(0.25)
                #Await acknowledgment
                if not await_conf(errNo, ser):
                    if a < retransmission:
                        time.sleep(0.5)
                        continue
                    #Reach maximum retransmission with no acknowledgment
                    if(transmit_disp):
                        transmit_disp.put("Result > Did not recieve" + \
                             "ACK\" after maximum retransmissions")
                    return False
                #Successfully transmitted sequnece
                if(transmit_disp):
                    transmit_disp.put("Result > Recieved \"ACK\" packet")
                    transmit_disp.put("%s\n"%(str(code)))
                break
            
        return True

    def isEmpty(self):
        """ Check method for if the code sequence is empty.

        Returns:
            bool: True iff the sequence is empty. Otherwise false.
        """
        return True if len(self.sequence) == 2 else False

    def add_sequence(self, segment):
        """ Add G-Code/S-Code segments to the code sequence

        Args:
            segment (List): List of G-Code/S-Code segments to add
        """
        for a in segment:
            self.sequence.insert(-1, segment)

    def remove_sequence(self, index):
        """ Remove G-Code/S-Code segments from the code sequence

        Args:
            index (int): Index of code segment to remove within the sequence
        """
        del self.sequence[index]

    def len(self):
        """ Override of code sequence len method

        Returns:
            int: Length of sequence (number of segments in the sequence)
        """
        return len(self.sequence)
