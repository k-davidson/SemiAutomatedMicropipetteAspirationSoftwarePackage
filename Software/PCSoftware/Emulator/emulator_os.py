from multiprocessing import *
from multiprocessing.managers import *
from .SoftwareDrivers.ConfigFiles.config import *
import os
import numpy as np
import random
from systemInformation import *
from settings import *
from math import *
import time

# Mass of the cell to aspirate
CELL_MASS = 0.0000000000001
# Radius of the cell to aspirate
INTERNAL_RADIUS = 0.000002

class SerialEmulator:
    """ 
    Serial emulation class for serial communication validation
    """
    def __init__(self, commandQueue):
        """ Initialisation of Serial emulator class

        Args:
            commandQueue (Queue): Queue to recieve serial commands
        """
        # Acknowledgment packet
        self.ACKPACK = "ACK\n"
        self.recievedPacket = False
        self.commandQueue = commandQueue

        self.toolSelect = 0

    def inWaiting(self):
        """ Return true if in waiting for a packet.

        Returns:
            bool: True iff awaiting packet. Otherwise, false.
        """
        return self.recievedPacket

    def readline(self):
        """ 
        Encode acknowledgment packet for communications.

        Returns:
            String: Encoded acknowledgment ("ACK") packet.
        """
        self.recievedPacket = False
        return self.ACKPACK.encode()

    def close(self):
        """ 
        Close of Serial device. Stated to avoid complications when
        expecting a real serial device.
        """
        return
    
    def write(self, transmitted):
        """ 
        Write command called by software to append message to the Queue.
        Represents a "writing" to a real serial device.

        Args:
            transmitted (String): Encoded string to be transmitted.

        Returns:
            bool: True, indicating successful transmission
        """
        # Set recieving a packet
        self.recievedPacket = True
        # Put transmitted into the Queue
        self.commandQueue.put(transmitted.decode())
        return 1


class CaptureEmulator:
    """
    Capture emululation class for Image capturing class
    """
    def __init__(self, imageQueue):
        """
        Initialise Capture emulator object.

        Args:
            imageQueue (Queue): Queue to send captured images over
        """
        # Initialise empty image
        self.image = np.zeros((750,750,3), dtype = np.uint8)
        self.imageQueue = imageQueue

    def empty(self):
        """ 
        Declare empty method to reflect true Capture devices. Always return 
        False as a new image can always be generated.

        Returns:
            bool: False
        """
        return False

    def read(self):
        """
        Read method to access image via the Capture device.

        Returns:
            nd.array: Numpy array representing image.
        """
        # Check if the image Queue is non empty
        if(not self.imageQueue.empty()):
            # Update the image
            self.image = self.imageQueue.get()
        
        # Send the image to the application
        return True, self.image
 
def initialise_emulation_process(commandQueue, imageQueue):
    """ Initialisation of the Emulation process.

    Args:
        commandQueue (Queue): Queue to communicate Serial commands to emulator.
        imageQueue (Queue): Queue to communicate Images to the application.

    Returns:
        int: ID of the Emulator process
    """
    # Declare emulation process
    emulationProcess = Process(target = emulation_processer, 
        args=(commandQueue, imageQueue))
    emulationProcess.start()
    return emulationProcess.pid

def emulation_processer(commandQueue, imageQueue):
    """ 
    Process loop for Emulation software to update the Serial and Capture
    objects once per frame.

    Args:
        commandQueue (Queue): Queue to communicate Serial commands to emulator.
        imageQueue (Queue): Queue to communicate Images to the application.
    """
    # Initialise emulator state
    toolSel = 0
    initialPDist = 0

    yPipette = [-pipetteModel['pipetteHeight'], 
                pipetteModel['pipetteHeight']]
    xPipetteTip = 0
    theta = 0

    # Initialise emulator pipette tip origin
    yOrigin = int(pipetteModel['initPipetteY'])
    xOrigin = pipetteModel['initPipetteX']

    # Initialise cell origin
    cellPos = cellModel['initCellPos']
    
    # Initiaise position, velocity and acceleration based on pressure.
    absPosX = 0
    absPosY = 0
    cellAcceleration = 0
    cellVelocity = 0
    pipettePressure = 0

    # Set the update time for change in cell position
    updatePortionOfSecond = 1/10
    lastUpdateTime = time.time()*1000

    imageQueue.put(draw_frame(xPipetteTip, yPipette, xOrigin, yOrigin, cellPos))

    while(1):

        # If the change in time is sufficient for an update
        if(time.time()*1000 - lastUpdateTime > updatePortionOfSecond*1000):
            # If the cell is to move away from the micropipette
            if(0 < cellAcceleration):
                cellAcceleration = max(cellAcceleration - 
                    cellVelocity*updatePortionOfSecond, 0)
            # If the cell is to move towards the micropipette
            if(cellAcceleration < 0):
                cellAcceleration = min(cellAcceleration - 
                    cellVelocity*updatePortionOfSecond, 0)
            
            # Update the cell velocity
            cellVelocity += cellAcceleration*updatePortionOfSecond

            # If the cell is moving
            if(0 < cellVelocity):
                cellVelocity = max(cellVelocity - 1*updatePortionOfSecond, 0)
            if(cellVelocity < 0):
                cellVelocity = min(cellVelocity + 1*updatePortionOfSecond, 0)
            
            # If the cell is near the pipette tip, approach the base
            if((abs(cellPos[0][0] - xOrigin) < 3) and 
                (abs(cellPos[0][1] - yOrigin) < 5)):
                theta = cell_to_pipette_theta(-10, yOrigin, cellPos[0])
            # If the cell is away from the pipette tip, approach the tip
            else:
                theta = cell_to_pipette_theta(xOrigin, yOrigin, cellPos[0])

            # Calculate the required change in position
            moveX = cellVelocity*cos(theta)*updatePortionOfSecond
            moveY = cellVelocity*sin(theta)*updatePortionOfSecond

            # Ensure move to the target position, at most
            if((xOrigin < cellPos[0][0]) and (xOrigin > cellPos[0][0] + moveX)):
                cellPos[0][0] = xOrigin
            else:
                cellPos[0][0] += moveX
            
            if((yOrigin < cellPos[0][1]) and (yOrigin > cellPos[0][1] + moveY)):
                cellPos[0][1] = yOrigin
            else:
                cellPos[0][1] += moveY

            # Update the image to be displayed by the capture device
            imageQueue.put(draw_frame(xPipetteTip, yPipette, xOrigin, 
                        yOrigin, cellPos))            

            # Set update time
            lastUpdateTime = time.time()*1000
    
        # If a pending serial command exists
        if(not commandQueue.empty()):
            # Get and parse the serial command
            command = commandQueue.get()
            commandSections = (command.rstrip()).split(" ")
        
            # If the command is movement
            if(commandSections[1] == "G00"):
                # Move the selected tool by the required change in position
                pos = int(commandSections[2])
                if toolSel == 0:
                    pos -= absPosX
                
                else:
                    pos -= absPosY

                # Set the micropipette tip position
                xOrigin, yOrigin = set_pipette_position(toolSel, 
                    xPipetteTip, yPipette, int(pos),
                    xOrigin, yOrigin)

                # Assign absolute position for tool
                if toolSel == 0:
                    absPosX = pos
                
                else:
                    absPosY = pos

                # Update the image to be displayed by the capture device
                imageQueue.put(draw_frame(xPipetteTip, yPipette, xOrigin, 
                    yOrigin, cellPos))

            # If tool select command
            if(commandSections[1] == "T"):
                # Update the tool selection
                toolSel = int(commandSections[2])

            # If presssure command
            if(commandSections[1] == "S01"):
                # If cell is far away from the pipette tip
                if((cellPos[0][0] <= xOrigin) 
                    and (abs(cellPos[0][1] - yOrigin) < 5)):
                    # Calculate the cell acceleration to the pipette tip
                    cellAcceleration, initialPDist = updateCellPosition(
                        -10, yOrigin, cellPos[0], 
                        (float(commandSections[2]) - pipettePressure))
                else:
                    # Calculate the accleleration to the pipette base
                    cellAcceleration, initialPDist = updateCellPosition(xOrigin, 
                    yOrigin, cellPos[0], 
                    (float(commandSections[2]) - pipettePressure))
                pipettePressure = float(commandSections[2])
                
                if(commandSections[2] == 1):
                    cellAcceleration = -cellAcceleration



def updateCellPosition(xPip, yPip, cellPos, pressure):
    """
    Update cell positon recorded for the emulator

    Args:
        xPip (int): X-Position of the Micropipette tip (pixels)
        yPip (int): Y-Position of the Micropipette tip (pixels)
        cellPos (int[]): [x,y] position of the cell
        pressure (int): Pressure applied in the system (pascals)

    Returns:
        int, int: Acceleration,Distance of the cell to the micropipette tip
    """
    
    # Calculate difference in position in micrometers
    dist = sqrt(pow(xPip - cellPos[0], 2) + pow(yPip - cellPos[1], 2))
    micron = dist/(PIXEL_PER_MICRON)

    # Calculate volume from desired pressure
    crossSection = pi * pow((COLUMN_DIAMETER/2), 2)

    # Calculate the relative pressure at the cell
    pressureAtCell = (MIN_VOLUME_INCREMENT * pow(10, -6) * 
        pressure)/(crossSection * FLUID_DENSITY * pow(10, 1.5) * GRAVITY)

    # Calculate the relative force at the cell, undergoing the set pressure
    forceOnCell = pi*pow(INTERNAL_RADIUS, 2)*pressureAtCell

    # Calculare the acceleration of the cell, undergoing the set force
    acceleration = forceOnCell/(CELL_MASS)

    return acceleration*PIXEL_PER_MICRON, dist


def cell_to_pipette_theta(xPip, yPip, cellPos):
    """ 
    Calculate the relative angle between the micropipette tip and the cell.

    Args:
        xPip (int): X-Position of the Micropipette tip (pixels)
        yPip (int): Y-Position of the Micropipette tip (pixels)
        cellPos (int[]): [x,y] position of the cell

    Returns:
        int: Relative angle, theta, between the cell and micropipette tip
    """
    if(abs(cellPos[0] - xPip) < 3):
        return 90
    if(abs(cellPos[1] - yPip) < 3):
        return 0

    return atan((cellPos[1] - yPip)/(cellPos[0] - xPip))


def set_pipette_position(toolSel, xPip, yPip, pos, xOrigin, yOrigin):
    """
    Set the emulated micropipette tip position

    Args:
        toolSel (int): Tool selection value
        xPip (int): X-Position of the Micropipette tip (pixels)
        yPip (int): Y-Position of the Micropipette tip (pixels)
        cellPos (int[]): [x,y] position of the cell
        xOrigin (int): Initial X-Position of the micropipette tip
        yOrigin (int): Initial Y-Position of the micropipette tip

    Returns:
        int,int: XPosition,Yposition of the updated micropipette
    """

    # Calculate change in position in micrometers
    ptom = 14.4
    microns = pos/(STEPS_PER_MICRON * MICROSTEPPING)

    # Calculate change in position in pixels
    pixels = microns*ptom

    # Calculate the change in position
    pos = int((pos*ptom)/(STEPS_PER_MICRON * MICROSTEPPING))

    # Assign the change in position to the appropriate axis
    if(toolSel == 0):
        xOrigin += pos
    else:
        yOrigin += pos

    return xOrigin, yOrigin 

def draw_frame(xPip, yPip, xOrigin, yOrigin, cellPos):
    """[summary]

    Args:
        xPip (int): X-Position of the Micropipette tip (pixels)
        yPip (int): Y-Position of the Micropipette tip (pixels)
        cellPos (int[]): [x,y] position of the cell
        xOrigin (int): Initial X-Position of the micropipette tip
        yOrigin (int): Initial Y-Position of the micropipette tip

    Returns:
        nd.array: Updated frame with the set positions
    """
    # Create an empty image array
    image = np.zeros((emulatorModel['imgWidth'],
                        emulatorModel['imgHeight'],3), 
                        dtype = np.uint8)

    # Iterate over the pipette tip ranges to draw its representation
    for x in range(0, xPip + xOrigin):
        for y in range(max(int(yPip[1] + yOrigin - 1), 0), 
            min(int(yPip[1] + yOrigin + 2), 749)):
            image[y, x] = 255
        for y in range(max(int(yPip[0] + yOrigin - 1), 0), 
            min(int(yPip[0] + yOrigin + 2), 749)):
            image[y, x] = 255

    for x in range(max(int(xPip + xOrigin - 1), 0), 
        min(int(xPip +xOrigin + 2), 749)):
        for y in range(max(int(yPip[0] + yOrigin),0), 
            min(int(yPip[1] + yOrigin),749)):
            image[y, x] = 255

    # Iterate over the cell ranges to draw its representation
    for n,cell in enumerate(cellPos):
        standardCellDim = cellModel['standardCellDim'][n]
        aspiratedCellDim = cellModel['aspiratedCellDim'][n]
        if((cell[0] + standardCellDim[0]/2 <= xOrigin) 
        and (abs(yOrigin - cell[1]) < 10)):
            cellDim = aspiratedCellDim
        else:
            cellDim = standardCellDim
        for y in range(max(int(cell[1] - cellDim[1]),0), 
        min(int(cell[1] + cellDim[1] + 1), 749)):
            for x in range(max(int(cell[0]),0), 
            min(int(cell[0] + 2*cellDim[0] + 1), 749)):
                image[y,x] = 255

    # Return the updated image 
    return image





        




    