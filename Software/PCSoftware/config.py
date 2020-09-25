from math import *

STEPS_PER_REV = 500
MICRON_PER_REV = 50

FineMotionConfig = dict(
    stepsPerMicron = STEPS_PER_REV/MICRON_PER_REV,
    microStepping = 16,
    originXOfWidth = 1/3,
    originYOfHeight = 1/3,
    pixelPerMicron = 72
)

FinePressureConfig = dict(
    internalRadius = 2*pow(10, -6),
    cellMass = 27*pow(10, -12),
    minPascalIncrement = 0.25
)

class systemInformation():
    def __init__(self):
        self.pipettePosition = None
        self.observedInformation = None
        self.cellPosition = None
        self.dataInformation = None

    def set_observed_info(self, observed):
        self.observedInformation = observed

    def set_pipette_range(self, pos):
        self.pipettePosition = pos

    def set_desired_cell_pos(self, pos):
        self.cellPosition = pos

    def desired_pipette_range(self):
        return self.pipettePosition

    def get_desired_cell_pos(self):
        return [(self.cellPosition[0] + self.cellPosition[2])/2, (self.cellPosition[1] + self.cellPosition[3])/2]
    
    def desired_pipette_center(self):
        return [(self.pipettePosition[0] + self.pipettePosition[2])/2,
                (self.pipettePosition[1] + self.pipettePosition[3])/2]
    
    def observed_pipette_position(self):
        if(self.observedInformation):
            pixelPos = self.observedInformation.get_pipette_range()
            print(pixelPos)
            return [(((pixelPos[0] + pixelPos[2])/2)/(FineMotionConfig['pixelPerMicron'])),
                    (((pixelPos[1] + pixelPos[3])/2)/(FineMotionConfig['pixelPerMicron']))]
        else:
            return None

    def observed_cell_position(self):
        if(self.observedInformation):
            pixelPos = self.observedInformation.get_cell_range()
            return [((pixelPos[0])/(FineMotionConfig['pixelPerMicron'])), 
                    ((pixelPos[1])/(FineMotionConfig['pixelPerMicron'])),
                    ((pixelPos[2])/(FineMotionConfig['pixelPerMicron'])), 
                    ((pixelPos[3])/(FineMotionConfig['pixelPerMicron']))]

        return None

    def observed_asp_position(self):
        if(self.observedInformation):
            pixelPos = self.observedInformation.get_asp_cell_pos()
            if(pixelPos == None):
                return None

            #print("Pixel difference is %d\n"%(pixelPos))
            return [(abs(pixelPos[0]))/(FineMotionConfig['pixelPerMicron']),
                    (abs(pixelPos[1]))/(FineMotionConfig['pixelPerMicron'])]
        else:
            return None

    def desired_to_observed_pipette(self):
        if(self.observedInformation):
            
            difference = []
            observed = self.observed_pipette_position()

            for n,point in enumerate(self.desired_pipette_center()):
                print("Observed at position %.2f"%(observed[n]))
                print("Comparison is %.2f to %.2f\n" %(point, (observed[n])))
                difference.append(point - observed[n])

            return difference

    def desired_to_observed_cell(self):
        if(self.observedInformation):
            difference = []
            observed = self.observed_cell_position()

            if(not observed):
                print("No active cell exists to latch\n")
                return None

            for n,point in enumerate(self.get_desired_cell_pos()):
                print("Actual cell at position %.2f\n"%(point))
                print("Observed cell at pixel %.2f\n"%((observed[n])))
                #print("Comparison is %d to %d\n" %(point, (observed[n])/(config*scale))/10)
                difference.append(point - (observed[n]))

            return difference

    def cell_to_pipette(self):
        return (self.observedInformation.cell_to_pipette()/FineMotionConfig['pixelPerMicron'])

    def active_pipette(self):
        if(self.observedInformation.active_pipette()):
            return True
        else:
            return False

    def active_cell(self):
        return self.observedInformation.active_cell()

    def active_asp_cell(self):
        return self.observedInformation.active_asp_cell()

    def get_img_dim(self):
        if(self.observedInformation):
            return self.observedInformation.get_img_dim()
        else:
            return None

class imageInformation():
    def __init__(self):
        self.pipetteTipPosition = None
        self.cellPosition = None
        self.aspCellPosition = None
        self.aspCellState = 0

        self.cellStationaryFrame = 0
        self.pipetteStationaryFrame = 0

        self.cellLost = False

        self.img = None
        self.displayImg = None

    def set_img(self, img):
        self.img = img

    def cell_to_pipette(self):
        if(self.cellPosition is None):
            return None
        if(self.pipetteTipPosition is None):
            return None
        
        pipCenter = self.get_pipette_center()
        cellCenter = self.get_cell_center()

        return sqrt(pow(pipCenter[0]-cellCenter[0],2) + pow(pipCenter[1]-cellCenter[1],2))

    def get_img(self):
        return self.img

    def get_img_dim(self):
        if(self.img is not None):
            return self.img.shape
        else:
            return None

    def set_display_img(self, img):
        self.displayImg = img
    
    def get_display_img(self):
        return self.displayImg

    def set_micron_per_pixel(self, config):
        self.micronPerPixel = config
    
    def active_pipette(self):
        if self.pipetteTipPosition:
            return True

        return False

    def active_cell(self):
        if self.cellPosition:
            return True
        return False

    def set_asp_cell_state(self, state):
        self.aspCellState = state

    def moving_cell(self):
        if self.active_cell() or self.active_asp_cell():
            if self.cellStationaryFrame < 60:
                return True
        return False

    def moving_pipette(self):
        if self.pipetteStationaryFrame < 10:
            return True
        return False

    def get_pipette_center(self):
        return ((self.pipetteTipPosition[0] + self.pipetteTipPosition[2])/2,
                   (self.pipetteTipPosition[1] + self.pipetteTipPosition[3])/2)
    
    def get_pipette_range(self):
        return self.pipetteTipPosition

    def get_cell_range(self):
        return self.cellPosition

    def get_asp_cell_pos(self):
        return self.aspCellPosition

    def is_cell_lost(self):
        return self.cellLost
    
    def clear_cell_lost(self):
        self.cellLost = False

    def get_cell_center(self):
        if(self.cellPosition):
            return (self.cellPosition[0] + (self.cellPosition[2])/2,
                   self.cellPosition[1] + (self.cellPosition[3])/2)
        return None

    def get_cell_radius(self):
        return int((self.cellPosition[2] + self.cellPosition[3])/2)

    def set_pipette_position(self, pipetteLine, pipetteStationaryFrame):
        self.pipetteTipPosition = pipetteLine
        self.pipetteStationaryFrame = pipetteStationaryFrame

    def set_cell_position(self, cellBox, cellStationaryFrame, cellLost):
        self.cellPosition = cellBox
        self.cellStationaryFrame = cellStationaryFrame
        self.cellLost = cellLost

    def set_asp_cell_position(self, aspCellLine, aspStationaryFrame):
        self.aspCellPosition = aspCellLine
        self.cellStationaryFrame = aspStationaryFrame

    def change_in_pipette(self, newPos):
        for n,pos in enumerate(newPos):
            if(abs(pos - self.pipetteTipPosition[n]) > 50):
                return True

        return False

    def active_asp_cell(self):
        return self.aspCellState