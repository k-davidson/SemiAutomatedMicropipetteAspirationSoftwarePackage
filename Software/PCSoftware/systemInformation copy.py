from math import *
import cv2
import copy
import time
import numpy as np
from settings import *

NO_ACTIVE_TRACK = 0

ACTIVE_TRACK = 1

ACTIVE_ASP_TRACK = 2
ACTIVE_FULL_ASP_TRACK = 3
#
class basicTracker():
#
    def __init__(self):
        self.trackPosition = [None, None, None, None]
        self.movingTrack = True
        self.lastTimeUpdate = time.time()
        self.stationaryFrames = 0
        self.movingTrack = True
        self.lostTrack = False
        self.lastCall = time.time()

        self.trackState = NO_ACTIVE_TRACK

    def active_track(self):
        if((self.trackPosition[0] is not None) and 
            (self.trackPosition[1] is not None)):
            return True

        return False
#
    def get_state(self):
        return self.trackState
#
    def set_state(self, state):
        self.trackState = state
#
    def set_track_state(self, state):
        self.trackState = state
#
    def get_track_center(self):
        return [int(self.trackPosition[0] + self.trackPosition[2]/2),
                int(self.trackPosition[1] + self.trackPosition[3]/2)]
#
    def get_track_range(self):
        return self.trackPosition
#
    def set_track_position(self, position):

        self.lastCall = time.time()
        if(self.active_track() and position is None):
            self.lostTrack = True
        else:
            self.lostTrack = False
        
        if(position is None):
            self.trackPosition = position
            self.stationaryFrames = 0
            self.set_state(NO_ACTIVE_TRACK)
            return

        if(self.active_track()):
            diffSum = abs(position[0] - self.trackPosition[0]) + \
                        abs(position[1] - self.trackPosition[1])
            
            if(diffSum != 0):
                self.stationaryFrames = 0
            else:
                self.stationaryFrames += 1

            self.lastTimeUpdate = time.time()


        self.trackPosition = position
        
        if(self.stationaryFrames < 50):
            self.set_moving_track(True)
        else:
            self.stationaryFrames = 0
            self.set_moving_track(False)
#
    def update_basic_track(self, img, thresh, startPos, step):
        grayscaleImg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        imgH, imgW, channels = img.shape

        dis = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        edges = cv2.Canny(grayscaleImg,60,150,apertureSize = 3)

        lines = cv2.HoughLinesP(edges,1,np.pi/180, 30, 30, 40, 70)

        minLine = [-1, -1, imgH, -1]
        minLineTheta = 0
        maxLine = [-1, -1, 0, -1]
        maxLineTheta = 0

        if(lines is None):
            return None

        for i in range(len(lines)):
            l = lines[i][0]
            
            if(maxLine[2] < l[1]):
                maxLine = [l[0], l[2], l[1], l[3]]
                
            if(l[1] < minLine[2]):
                minLine = [l[0], l[2], l[1], l[3]]


        cv2.line(dis,(minLine[0],minLine[2]),(minLine[1],minLine[3]),(0,0,255),2)
        cv2.line(dis,(maxLine[0],maxLine[2]),(maxLine[1],maxLine[3]),(0,0,255),2)

        if(len(lines) < 2):
            if(step < 1):
                print("less than two lines")
            return None

        if((maxLine[0] - maxLine[1]) == 0):
            if(step < 1):
                print("No difference between max line")
            return None
        
        maxGrad = (maxLine[2] - maxLine[3])/(maxLine[0] - maxLine[1])
        maxOffset = (maxLine[2] - maxGrad*maxLine[0])

        if((minLine[0] - minLine[1]) == 0):
            if(step < 1):
                print("No difference between min line")
            return None

        minGrad = (minLine[2] - minLine[3])/(minLine[0] - minLine[1])
        minOffset = (minLine[2] - minGrad*minLine[0])


        grad = (maxGrad + minGrad)/2
        offset = (minOffset + maxOffset)/2
        if (grad != 0):
            tipGrad = -1/grad
        else:
            tipGrad = None

        tipOffset = None
        tipX = None

        c1 = [int(startPos*grad + offset), startPos]
        c2 = [int((startPos+3)*grad + offset), startPos+3]

        while((c2[1] < imgW) and (c1[1] < imgW) 
        and (c2[0] < imgH) and (c1[0] < imgH)):
            disY = (c1[0] + c2[0])/2
            disX = (c1[1]+c2[1])/2
            if(0 < disY and disY < imgH and 0 < disX and imgW < disX):
                dis[int((c1[0]+c2[0])/2), int((c1[1]+c2[1])/2)] = 255
            if((c1[0] < 0) or (c1[1] < 0) or (c2[0]) < 0 or (c2[1] < 0)):
                break
            if(thresh < abs(int(grayscaleImg[c1[0], c1[1]]) - int(grayscaleImg[c2[0], c2[1]]))):
                disY = (c1[0] + c2[0])/2
                disX = (c1[1]+c2[1])/2
                if(0 < disY and disY < imgH and 0 < disX and imgW < disX):
                    dis[int((c1[0]+c2[0])/2), int((c1[1]+c2[1])/2)] = 255
                if(tipGrad != None):
                    tipOffset = c1[0] - tipGrad*c1[1]
                tipX = int((c1[1] + c2[1])/2)
                break
            
            c1[1] += step
            c1[0] = int(c1[1]*grad + offset)
            c2[1] += step
            c2[0] = int(c2[1]*grad + offset)
        
        if(tipX == None):
            '''
            if(step < 1):
                print("didnt find")
            '''
            return None
        y1 = int(maxGrad*tipX + maxOffset)
        y2 = int(minGrad*tipX + minOffset)

        if(tipGrad != None):
            cv2.line(dis, (int((y1 - tipOffset)/(tipGrad)), y1), 
                        (int((y2 - tipOffset)/(tipGrad)), y2), 
                        (255,0,0), 2)
        else:
            cv2.line(dis, (tipX, y1), (tipX, y2), (255,0,0), 2)

        '''
        cv2.imshow("Aspiration", dis)
        cv2.waitKey(0)
        '''

        if(tipGrad != None):
            tipX = int((y1 - tipOffset)/(tipGrad))
            y2 = y2
            width = abs(int(((y2 - tipOffset)/tipGrad) - ((y1 - tipOffset)/tipGrad)))
            height = abs(y2 - y1)
        else:
            tipX = tipX
            y2 = y2
            width = 0
            height = abs(y2-y1)
        return [tipX, y2, 0, abs(y2-y1)]
#
    def kill_track(self):
        self.trackPosition = [None, None]
#
    def moving_pipette(self):
        return self.movingTrack
#
    def set_moving_track(self, state):
        self.movingTrack = state
#
    def lost_track(self):
        return self.lostTrack
#
    def change_in_position(self, pos):
        currPos = self.get_track_range()
        for p in currPos:
            if(p is None):
                return 1000
            
        changeX = pow(abs((pos[0] + pos[2]/2) - (currPos[0] + currPos[2]/2)), 2)
        changeY = pow(abs((pos[1] + pos[3]/2) - (currPos[1] + currPos[3]/2)), 2)

        return sqrt(changeX + changeY)
#
    def toBasic(self):
        return self
#
class MOSSETracker(basicTracker):
#
    def __init__(self):
        basicTracker.__init__(self)
        self.MOSSETrack = None
#
    def create_mosse_track(self, img, boundBox):
        for n in range(5):
            self.MOSSETrack = cv2.TrackerMOSSE_create()
            self.MOSSETrack.init(img, boundBox)
            success, cellBox = self.MOSSETrack.update(img)

            if(not success):
                self.MOSSETrack = None
                boundBox = (boundBox[0] - boundBox[2]*0.1, 
                            boundBox[1] - boundBox[3]*0.1,
                            boundBox[2] * 1.1,
                            boundBox[3] * 1.1)
                continue
                
            self.set_track_position(cellBox)
            return True
            
        return False
#
    def kill_track(self):
        basicTracker.kill_track(self)
        self.MOSSETrack = None
        self.set_state(NO_ACTIVE_TRACK)
#
    def update_mosse_track(self, img):
        success, cellBox = self.MOSSETrack.update(img)
        if(not success):
            self.set_track_position(None)
        else:
            self.set_track_position(cellBox)
            
        
        return success
#
    def active_mosse_track(self):
        if(self.MOSSETrack is not None):
            return True
        return False
#
    def toBasic(self):
        basic = copy.copy(self)
        basic.MOSSETrack = None
        basic.__class__ = basicTracker
        return basic
#
class systemInformation():
#
    def __init__(self):
        self.pipettePosition = None
        self.observedInformation = None
        self.cellPosition = None
        self.dataInformation = None

        self.pipetteTracker = None
        self.cellTracker = None
        self.aspTracker = None

    def set_trackers(self, pipetteTracker, cellTracker, aspTracker):
        self.pipetteTracker = pipetteTracker
        self.cellTracker = cellTracker
        self.aspTracker = aspTracker
#
    def observed_pipette_position(self):
        if(self.pipetteTracker.get_state()):
            position =  self.get_pipette_center()
            return [(position[0]/PIXEL_PER_MICRON),
            (position[1]/PIXEL_PER_MICRON)]
#
    def observed_cell_position(self):
        if(self.cellTracker.get_state()):
            position = self.cellTracker.get_track_range()
            return [((pixelPos[0])/(PIXEL_PER_MICRON)), 
                    ((pixelPos[1])/(PIXEL_PER_MICRON)),
                    ((pixelPos[2])/(PIXEL_PER_MICRON)), 
                    ((pixelPos[3])/(PIXEL_PER_MICRON))]
#
    def observed_asp_position(self):
        if(self.aspTracker.get_state()):
            position = self.observedInformation.get_track_range()
            return [(abs(position[0]))/(PIXEL_PER_MICRON),
                    (abs(position[1]))/(PIXEL_PER_MICRON)]
#
    def desired_to_observed_pipette(self, desired):
        if(self.observedInformation):
            
            difference = []
            observed = self.pipetteTracker.get_track_range()

            for n,point in enumerate(desired):
                print("Observed at position %.2f"%(observed[n]))
                print("Comparison is %.2f to %.2f\n" %(point, (observed[n])))
                difference.append(point - observed[n])

            return difference
#
    def cell_to_pipette(self):
        pipCenter = self.pipetteTracker.get_track_center()
        cellCenter = self.cellTracker.get_track_center()

        difference =  sqrt(pow(pipCenter[0]-cellCenter[0],2) + pow(pipCenter[1]-cellCenter[1],2))
        return (difference/PIXEL_PER_MICRON)
#
    def asp_to_pipette(self):
        pipCenter = self.pipetteTracker.get_track_center()
        aspRange = self.aspTracker.get_track_range()

        difference =  abs(pipCenter[0] - aspRange[0])
        return difference/PIXEL_PER_MICRON
#
    def active_pipette(self):
        if(pipetteTracker.active_track()):
            return True
        else:
            return False
#Implemented

    def active_cell(self):
        return self.cellTracker.get_state()

#Implemented

    def active_asp_cell(self):
        return self.aspTracker.get_state()

    '''
    def get_img_dim(self):
        if(self.observedInformation):
            return self.observedInformation.get_img_dim()
        else:
            return None
    '''
#
class imageInformation():
#
    def __init__(self):
        self.pipetteTipPosition = None
        self.cellPosition = None
        self.aspCellPosition = None
        self.aspCellState = 0

        self.cellStationaryFrame = 0
        self.pipetteStationaryFrame = 0

        self.pipetteTrack = None
        self.cellTrack = None
        self.aspTrack = None

        self.cellLost = False

        self.img = None
        self.displayImg = None
#
    def set_img(self, img):
        self.img = img
#
    def cell_to_pipette(self):
        if(self.pipetteTrack is None or not self.pipetteTrack.active_track()):
            return None
        if(self.cellTrack is None or not self.cellTrack.active_track()):
            return None
        
        pipCenter = self.pipetteTrack.get_track_center()
        cellCenter = self.cellTrack.get_track_center()

        return sqrt(pow(pipCenter[0]-cellCenter[0],2) + pow(pipCenter[1]-cellCenter[1],2))
#
    def asp_to_pipette(self):
        if(self.pipetteTrack is None or not self.pipetteTrack.active_track()):
            return None
        if(self.aspTrack is None or not self.aspTrack.active_track()):
            return None

        pipCenter = self.pipetteTrack.get_track_center()
        aspRange = self.aspTrack.get_track_range()

        return abs(pipCenter[0] - aspRange[0])
#
    def get_img(self):
        return self.img
#
    def get_img_dim(self):
        if(self.img is not None):
            return self.img.shape
        else:
            return None
#
    def set_display_img(self, img):
        self.displayImg = img
#
    def get_display_img(self):
        return self.displayImg
#
    def set_micron_per_pixel(self, config):
        self.micronPerPixel = config
#
    def set_pipette_track(self, track):
        self.pipetteTrack = track
#
    def get_pipette_track(self):
        return self.pipetteTrack
#
    def set_cell_track(self, track):
        self.cellTrack = track
#
    def get_cell_track(self):
        return self.cellTrack
#
    def set_asp_track(self, track):
        self.aspTrack = track
#
    def get_asp_track(self):
        return self.aspTrack
#Implemented

    def active_pipette(self):
        return self.pipetteTrack.active_track()
#Implemented

    def active_cell(self):
        return self.cellTrack.active_track()
#Implemented

    def moving_cell(self):
        return self.cellTrack.moving_pipette() and self.aspTrack.moving_pipette()
#Implemented

    def moving_pipette(self):
        return self.pipetteTrack.moving_pipette()
#Implemented

    def get_pipette_center(self):
        return self.pipetteTrack.get_track_center()
#Implemented

    def get_pipette_range(self):
        return self.pipetteTrack.get_track_range()
#Implemented

    def get_cell_range(self):
        return self.cellTrack.get_track_range()
#Implemented

    def get_asp_cell_pos(self):
        print("Track range is %d, %d"%(self.aspTrack.get_track_range()[0], self.aspTrack.get_track_range()[1]))
        return self.aspTrack.get_track_range()
#Implemented

    def is_cell_lost(self):
        return self.cellTrack.lost_track()
#
    def clear_cell_lost(self):
        self.cellLost = False
#Implemented

    def get_cell_center(self):
        return self.cellTrack.get_track_center()
#
    def get_cell_radius(self):
        return int((self.cellPosition[2] + self.cellPosition[3])/2)
#Implemented

    def set_pipette_position(self, pipetteLine, pipetteStationaryFrame):
        self.pipetteTipPosition = pipetteLine
        self.pipetteStationaryFrame = pipetteStationaryFrame
#
    def change_in_pipette(self, newPos):
        for n,pos in enumerate(newPos):
            if(abs(pos - self.pipetteTrack.get_track_range()[n]) > 50):
                return True

        return False
#Implemented

    def active_asp_cell(self):
        return self.aspTrack.active_track()
