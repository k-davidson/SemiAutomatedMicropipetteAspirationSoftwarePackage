from math import *
import random

# Seed the RNG
random.seed()

# Declare constants relating the emulator model
emulatorModel = dict( 
    imgWidth = 750,
    imgHeight = 750
)

# Declare constants relating to the pipette model
pipetteModel = dict(
    pipetteHeight = 25,
    initPipetteX = random.randrange(75,int(emulatorModel['imgWidth']/2)),
    initPipetteY = random.randrange(75,int(emulatorModel['imgHeight']/2)),
)

# Declare contstants relating to the cell model
cellModel = dict(
    initCellPos = [[random.randrange(int(emulatorModel['imgWidth']/2) - 50, 
        emulatorModel['imgWidth'] - 50),
        random.randrange(int(emulatorModel['imgHeight']/2) - 50, 
        emulatorModel['imgHeight'] - 50)]],
    standardCellDim = [[15, 15]],
    aspiratedCellDim = [[30, pipetteModel['pipetteHeight'] - 5]],
    standardCellIntensity = [255],
    aspiratedCellIntensity = [150]
)