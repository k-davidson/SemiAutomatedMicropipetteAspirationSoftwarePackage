from .ConfigFiles.gcode_config import *
from .serial_driver import *
import time

class GCodeSegment:
    def __init__(self, code ,pos = None, tool = None, rate = None, reset = None):
        
        self.code = code

        self.pos = pos if type(pos) == int else None

        self.tool = tool
        
        self.rate = rate

        self.GCodes = {
            #Rapid incremental positioning
            "G00":"G00 %d %d"%(self.pos, self.rate) if type(self.pos) == int and type(self.rate) == int else None,
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
        return self.GCodes[self.code]

class SCodeSegment:
    def __init__(self, code, volume = None):
        self.code = code
        self.volume = volume
        if(volume != None):
            print("Code:%s, Volume:%d\n"%(self.code, self.volume))
        self.SCodes = {
            #Pumping direction setting
            "S00":"S00 %.2f"%(self.volume) if type(self.volume == int) else None,
            "S01":"S01 %.2f"%(self.volume) if type(self.volume == int) else None
        }
    
    def serial_cmd(self):
        return self.SCodes[self.code]

class codeSequence:
    def __init__(self, sequence = []):
        self.startEnd = GCodeSegment(START_END_SEQ)
        self.sequence = [self.startEnd] + sequence + [self.startEnd]

    def transmit_sequence(self, ser, errNo, retransmission = 0):
        for N, code in enumerate(self.sequence):
            for a in range(retransmission + 1):
                #Transmit code
                serialCode = "N%d %s"%(N, code.serial_cmd())
                if not transmit_serial(errNo, ser, serialCode + "\n"):
                    return None

                time.sleep(0.25)

                #Await acknowledgment
                if not await_conf(errNo, ser):
                    if a < retransmission:
                        time.sleep(0.5)
                        continue
                    #Reach maximum retransmission with no acknowledgment
                    return None
                break
            
        #Successfully transmitted sequnece
        return 1

    def isEmpty(self):
        return True if len(self.sequence) == 2 else False

    def add_sequence(self, segment):
        for a in segment:
            self.sequence.insert(-1, segment)

    def remove_sequence(self, index):
        del self.sequence[index]

    def len(self):
        return len(self.sequence)

    def get_comm_seq(self):
        transmitList = []
        for N, code in enumerate(self.sequence):
            transmitList.append("N%d %s"%(N, code.serial_cmd()))

        return transmitList
        

