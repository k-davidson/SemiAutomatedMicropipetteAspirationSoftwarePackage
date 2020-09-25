from multiprocessing import *
from multiprocessing.managers import *
import Emulator.emulator_config as em_config
import os
import numpy as np
import random
import config
from math import *
import time

class SerialEmulator:
    def __init__(self, commandQueue):
        self.ACKPACK = "ACK\n"
        self.recievedPacket = False
        self.commandQueue = commandQueue

        self.toolSelect = 0

    def inWaiting(self):
        return self.recievedPacket

    def readline(self):
        self.recievedPacket = False
        return self.ACKPACK.encode()

    def close(self):
        return
    
    def write(self, transmitted):
        #print("Emulator >> Recieved: %s"%(transmitted.decode()))

        self.recievedPacket = True
        self.commandQueue.put(transmitted.decode())
        return 1

class CaptureEmulator:
    def __init__(self, imageQueue):
        self.image = np.zeros((750,750,3), dtype = np.uint8)
        self.imageQueue = imageQueue

    def empty(self):
        return False

    def read(self):
        if(not self.imageQueue.empty()):
            self.image = self.imageQueue.get()
        return True, self.image
    
def initialise_emulation_process(commandQueue, imageQueue):
    imageProcess = Process(target = emulation_processer, args=(commandQueue, imageQueue))
    imageProcess.start()
    return imageProcess.pid

def emulation_processer(commandQueue, imageQueue):
    toolSel = 0
    initialPDist = 0

    yPipette = [-em_config.pipetteModel['pipetteHeight'], 
                em_config.pipetteModel['pipetteHeight']]
    xPipetteTip = 0
    theta = 0

    yOrigin = int(em_config.pipetteModel['initPipetteY'])
    xOrigin = em_config.pipetteModel['initPipetteX']
    cellPos = em_config.cellModel['initCellPos']
    

    cellAcceleration = 0
    cellVelocity = 0

    pipettePressure = 0

    updatePortionOfSecond = 1/10
    lastUpdateTime = time.time()*1000

    imageQueue.put(draw_frame(xPipetteTip, yPipette, xOrigin, yOrigin, cellPos))

    while(1):

        if(time.time()*1000 - lastUpdateTime > updatePortionOfSecond*1000):
            if(0 < cellAcceleration):
                cellAcceleration = max(cellAcceleration - cellVelocity*updatePortionOfSecond, 0)
            if(cellAcceleration < 0):
                cellAcceleration = min(cellAcceleration - cellVelocity*updatePortionOfSecond, 0)
            
            cellVelocity += cellAcceleration*updatePortionOfSecond

            if(0 < cellVelocity):
                cellVelocity = max(cellVelocity - 1*updatePortionOfSecond, 0)
            if(cellVelocity < 0):
                cellVelocity = min(cellVelocity + 1*updatePortionOfSecond, 0)
            
            if((abs(cellPos[0][0] - xOrigin) < 3) and (abs(cellPos[0][1] - yOrigin) < 5)):
                theta = cell_to_pipette_theta(-10, yOrigin, cellPos[0])
            else:
                theta = cell_to_pipette_theta(xOrigin, yOrigin, cellPos[0])

            moveX = cellVelocity*cos(theta)*updatePortionOfSecond
            moveY = cellVelocity*sin(theta)*updatePortionOfSecond

            if((xOrigin < cellPos[0][0]) and (xOrigin > cellPos[0][0] + moveX)):
                cellPos[0][0] = xOrigin
            else:
                cellPos[0][0] += moveX
            
            if((yOrigin < cellPos[0][1]) and (yOrigin > cellPos[0][1] + moveY)):
                cellPos[0][1] = yOrigin
            else:
                cellPos[0][1] += moveY
            
            #print("Move x = %.2f, Move y = %.2f\n"%(moveX, moveY))

            imageQueue.put(draw_frame(xPipetteTip, yPipette, xOrigin, 
                        yOrigin, cellPos))            

            lastUpdateTime = time.time()*1000

            
                
        if(not commandQueue.empty()):
            command = commandQueue.get()
            commandSections = (command.rstrip()).split(" ")
        
            if(commandSections[1] == "G00"):
                xOrigin, yOrigin = set_pipette_position(toolSel, 
                xPipetteTip, yPipette, int(commandSections[2]),
                xOrigin, yOrigin)
                imageQueue.put(draw_frame(xPipetteTip, yPipette, xOrigin, yOrigin, cellPos))

            if(commandSections[1] == "T"):
                toolSel = int(commandSections[2])

            if(commandSections[1] == "S01"):
                if((cellPos[0][0] <= xOrigin) and (abs(cellPos[0][1] - yOrigin) < 5)):
                    cellAcceleration, initialPDist = updateCellPosition(-10, yOrigin, 
                    cellPos[0], (float(commandSections[2]) - pipettePressure))
                else:
                    cellAcceleration, initialPDist = updateCellPosition(xOrigin, 
                    yOrigin, cellPos[0], (float(commandSections[2]) - pipettePressure))
                pipettePressure = float(commandSections[2])
                print("Acceleration is %.2f"%(cellAcceleration))
                
                if(commandSections[2] == 1):
                    cellAcceleration = -cellAcceleration



def updateCellPosition(xPip, yPip, cellPos, pressure):
    dist = sqrt(pow(xPip - cellPos[0], 2) + pow(yPip - cellPos[1], 2))
    print("Distance is %.12f pixels\n"%(dist))

    micron = dist/(config.FineMotionConfig["pixelPerMicron"])
    print("Distance is %.12f microns\n"%(micron))

    pressureAtCell = pressure
    print("Pressure is %.2f and at cell %.12f"%(pressure, pressureAtCell))

    forceOnCell = pi*pow(config.FinePressureConfig['internalRadius'], 2)*pressureAtCell
    print("Internal radius of %.12f force on cell %.12f"%(config.FinePressureConfig['internalRadius'], forceOnCell))

    acceleration = forceOnCell/config.FinePressureConfig['cellMass']
    print("Acceleration is %.12f"%(acceleration))

    return acceleration*config.FineMotionConfig["pixelPerMicron"], dist

def cell_to_pipette_theta(xPip, yPip, cellPos):
    if(abs(cellPos[0] - xPip) < 3):
        return 90
    if(abs(cellPos[1] - yPip) < 3):
        return 0

    return atan((cellPos[1] - yPip)/(cellPos[0] - xPip))


def set_pipette_position(toolSel, xPip, yPip, pos, xOrigin, yOrigin):

        ptom = config.FineMotionConfig["pixelPerMicron"]
        sperm = config.FineMotionConfig["stepsPerMicron"]
        microstep = config.FineMotionConfig["microStepping"]

        microns = pos/(sperm*microstep)
        print("Microns of %.2f\n"%(microns))

        pixels = microns*ptom
        print("Pixels of %.2f\n"%(pixels))

        pos = int((pos*ptom)/(sperm*microstep)) #Replace 0.5 with scale

        if(toolSel == 0):
            xOrigin += pos
        else:
            yOrigin += pos
        print("%d\n", config.FineMotionConfig['pixelPerMicron'])
        print("X-pos = %d, Y-pos = [%d,%d]"%(xPip, yPip[0], yPip[1]))
        return xOrigin, yOrigin 

def draw_frame(xPip, yPip, xOrigin, yOrigin, cellPos):
        image = np.zeros((em_config.emulatorModel['imgWidth'],
                            em_config.emulatorModel['imgHeight'],3), 
                            dtype = np.uint8)

        for x in range(0, xPip + xOrigin):
            for y in range(max(int(yPip[1] + yOrigin - 1), 0), min(int(yPip[1] + yOrigin + 2), 749)):
                image[y, x] = 255
            for y in range(max(int(yPip[0] + yOrigin - 1), 0), min(int(yPip[0] + yOrigin + 2), 749)):
                image[y, x] = 255

        for x in range(max(int(xPip + xOrigin - 1), 0), min(int(xPip +xOrigin + 2), 749)):
            for y in range(max(int(yPip[0] + yOrigin),0), min(int(yPip[1] + yOrigin),749)):
                image[y, x] = 255

    

        for n,cell in enumerate(cellPos):
            standardCellDim = em_config.cellModel['standardCellDim'][n]
            aspiratedCellDim = em_config.cellModel['aspiratedCellDim'][n]
            if((cell[0] + standardCellDim[0]/2 <= xOrigin) and (abs(yOrigin - cell[1]) < 10)):
                cellDim = aspiratedCellDim
            else:
                cellDim = standardCellDim
            for y in range(max(int(cell[1] - cellDim[1]),0), min(int(cell[1] + cellDim[1] + 1), 749)):
                for x in range(max(int(cell[0]),0), min(int(cell[0] + 2*cellDim[0] + 1), 749)):
                    image[y,x] = 255
            
        return image





        




    