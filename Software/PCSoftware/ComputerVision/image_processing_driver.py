import cv2
import numpy as np
from .ConfigFiles.image_proc_config import *
from config import *


NON_ASPIRATING = 0
LATCHING = 1
ASPIRATING = 2
FULL_ASPIRATION = 3

class sample():
    def __init__(self, images):
        return

class sampleArea():
    def __init__(self, dim, n = NUM_DETECT):
        self.width = dim[0]
        self.height = dim[1]
        self.numCells = n
        self.discoveredCells = 0
        self.cells = []
        self.img = None
        self.imgW = None
        self.imgH = None

        self.systemInfo = imageInformation()

        self.trackerSet = [None,None,None]
        self.bBoxSet = [None,None,None]
        self.cellTracker = None
        self.cellBox = None
        self.cellStationaryFrame = 0
        self.pipStationaryFrame = 0

        self.aspirationTracker = None
        self.aspirationBox = None
        self.aspirating = False

        self.aspirationRange = [None,None]
        self.aspirationX = None

        self.tempTest = [None, None, None, None]

        self.frameCount = 0
        self.aspirationLine = None

    def update_img(self, img, auto, sensitivity):
        self.frameCount += 1

        self.img = img
        self.imgW = img.shape[1]
        self.imgH = img.shape[0]
        self.systemInfo.set_img(img)
        
        self.update_tracker(auto, sensitivity)
        self.systemInfo.set_display_img(self.display_img())

    def get_image_info(self):
        return self.systemInfo
              
    def check_aspiration(self):
        cellB = self.cellBox
        cellX, cellY, cellW, cellH = int(cellB[0]), int(cellB[1]), int(cellB[2]), int(cellB[3])
        
        muTipX = self.systemInfo.get_pipette_center()[0]
        
        tipY1 = self.systemInfo.get_pipette_range()[1]
        tipY2 = self.systemInfo.get_pipette_range()[3]

        #print("Cell @ [%d, %d, %d, %d] Tip @ [%d,[%d-%d]]"%(cellX, cellY, cellW, cellH, muTipX, tipY1, tipY2))
        
        if((cellX < muTipX) and (tipY2 < cellY + cellH/2) and (cellY + cellH/2 < tipY1)):
            return True
        else:
            return False

    def get_index(self):
        return self.num

    def find_aspirated_cell(self, thresh, startPos, step):
        
        grayscaleImg = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        dis = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)

        edges = cv2.Canny(grayscaleImg,60,150,apertureSize = 3)

        lines = cv2.HoughLinesP(edges,1,np.pi/180, 30, 30, 40, 70)

        minLine = [-1, -1, self.imgH, -1]
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

        while((c2[1] < self.imgW) and (c1[1] < self.imgW) 
        and (c2[0] < self.imgH) and (c1[0] < self.imgH)):
            disY = (c1[0] + c2[0])/2
            disX = (c1[1]+c2[1])/2
            if(0 < disY and disY < self.imgH and 0 < disX and self.imgW < disX):
                dis[int((c1[0]+c2[0])/2), int((c1[1]+c2[1])/2)] = 255
            if((c1[0] < 0) or (c1[1] < 0) or (c2[0]) < 0 or (c2[1] < 0)):
                break
            if(thresh < abs(int(grayscaleImg[c1[0], c1[1]]) - int(grayscaleImg[c2[0], c2[1]]))):
                disY = (c1[0] + c2[0])/2
                disX = (c1[1]+c2[1])/2
                if(0 < disY and disY < self.imgH and 0 < disX and self.imgW < disX):
                    dis[int((c1[0]+c2[0])/2), int((c1[1]+c2[1])/2)] = 255
                if(tipGrad != None):
                    tipOffset = c1[0] - tipGrad*c1[1]
                tipX = int((c1[1] + c2[1])/2)
                break
            
            c1[1] += step
            c1[0] = int(c1[1]*grad + offset)
            c2[1] += step
            c2[0] = int(c2[1]*grad + offset)
        
        '''
        cv2.imshow("Aspiration", dis)
        cv2.waitKey(0)
        '''
        
        
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


        if(tipGrad != None):
            return [int((y1 - tipOffset)/(tipGrad)), y1, 
                        int((y2 - tipOffset)/(tipGrad)), y2]
        else:
            return [tipX, y1, tipX, y2]
             
    def set_cells(self, cells):
        self.cells = cells

    def get_cell_list(self):
        return self.cells

    def detect_cells(self, offset, pos = None):
        self.cells = []
        self.cellTracker = cv2.TrackerMOSSE_create()

        if(pos):
            XOffset = min(max(int(pos[0]),offset), self.imgW - offset)
            YOffset = min(max(int(pos[1]),offset) , self.imgH - offset)
            print("Clicked at [%d,%d]\n"%(pos[0],pos[1]))
            print("X = [%d,%d], Y = [%d,%d]\n"%(XOffset-offset, XOffset+offset, YOffset-offset, YOffset+offset))
            croppedImg = self.img[YOffset-offset:YOffset+offset, XOffset-offset:XOffset+offset]
            
            #cv2.imshow('test',croppedImg)
            #cv2.waitKey(0)
            
        else:
            croppedImg = self.img
        
        self.cellbBox = cv2.selectROI(croppedImg)
        self.cellTracker.init(croppedImg, bBox)


        imCrop = self.img(self.cellbBox)
        #cv2.imshow("Window",self.img)
        #cv2.waitKey(0)
        
        positions = apply_cHough(croppedImg)

        if(positions == None):
            self.discoveredCells = 0
            return
        positions = sorted(positions, key=lambda x: x[1])
        
        for n,a in enumerate(positions):
            print("Found at %d,%d\n"%(a[1],a[0]))
            self.cells.append(cell((a[1] + XOffset - offset, a[0] + YOffset - offset),a[2], n, self)) 
        
        self.discoveredCells = len(positions)
    
    def display_img(self):
        RCOLOUR = ((255,128,128),(128,128,255), (128,255,128))
        TCOLOUR = ((255,0,0),(0,0,255), (0,255,0))
        TEXT = ("Cell", "Pipette", "Asp Cell")
        
        displayImage = np.copy(self.img)

        if(self.systemInfo.active_pipette()):
            displayImage = self.display_pipette_tip(displayImage)

        if(self.cellTracker):
            displayImage = self.display_cell(displayImage)
        
        if(self.aspirationTracker or self.systemInfo.active_asp_cell()):
            displayImage = self.display_aspirated_cell(displayImage)
        
        return displayImage

    def display_pipette_tip(self, img):
        pos = self.systemInfo.get_pipette_range()
        cv2.line(img, (pos[0],pos[1]), (pos[2],pos[3]), (128,128,255), 2)
        cv2.putText(img, "Pipette", (pos[2], pos[3] - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255),2)
        return img

    def display_cell(self, img):
        b = self.cellBox
        x, y, w, h = int(b[0]), int(b[1]), int(b[2]), int(b[3])
        cv2.rectangle(img, (x,y), (x+w, y+h), (255,128,128), 3, 1)
        cv2.putText(img, "Cell", (x+w,y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        return img

    def display_aspirated_cell(self, img):
        pipRange = self.systemInfo.get_pipette_range()
        cellRange = self.systemInfo.get_asp_cell_pos()

        state = self.systemInfo.active_asp_cell()

        if(state == ASPIRATING):
            x = pipRange[0] + cellRange[1]
            y = pipRange[3]
            w = 1
            h = abs(pipRange[1] - pipRange[3])
        else:
            b = self.aspirationBox
            x, y, w, h = int(b[0]), int(b[1]), int(b[2]), int(b[3])
        
        cv2.rectangle(img, (x,y), (x+w, y+h), (128,255,128), 3, 1)
        cv2.putText(img, "Asp Cell", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return img

    def init_track_at(self, isCell, pos):
        
        Y = min(int(pos[0][1]), int(pos[0][1] + pos[1][1]))
        X = min(int(pos[0][0]), int(pos[0][0] + pos[1][0]))
        H = int(abs(pos[1][1]))
        W = int(abs(pos[1][0]))
        
        if(isCell):
            self.cellTracker = cv2.TrackerMOSSE_create()
            self.cellBox = [X, Y, W, H]
            self.cellTracker.init(self.img, (X,Y,W,H))
        else:
            self.aspirationTracker = cv2.TrackerMOSSE_create()
            self.aspirationBox = [X, Y, W, H]
            self.aspirationTracker.init(self.img, (X,Y,W,H))
        
    def update_tracker(self, auto, sensitivity):
        self.systemInfo.clear_cell_lost()
        
        if(self.cellTracker):
            tempCellPos = self.cellBox
            success, self.cellBox = self.cellTracker.update(self.img)

            if(not success):
                print("Lost the fucker\n")
                self.cellBox = None
                self.cellTracker = None
                self.systemInfo.set_cell_position(None, False, True)

            else:
                if((self.cellBox[0] != tempCellPos[0]) or (self.cellBox[1] != tempCellPos[1])):
                    self.cellStationaryFrame = 0
                else:
                    self.cellStationaryFrame += 1

                self.systemInfo.set_cell_position(self.cellBox, self.cellStationaryFrame, False)

        if(self.aspirationTracker):
            tempAspirationBox = self.aspirationBox
            success, self.aspirationBox = self.aspirationTracker.update(self.img)

            if(not success):
                print("Lost aspiration tracker\n")
                self.aspirationBox = None
                self.aspirationTracker = None
                self.systemInfo.set_asp_cell_position(0, 200)
                self.systemInfo.set_asp_cell_state(NON_ASPIRATING)
                self.aspirating = False

            elif(self.aspirationBox[0] + self.aspirationBox[2]/2 <= 10):
                self.aspirationBox = None
                self.aspirationTracker = None
                self.systemInfo.set_asp_cell_position(0, 200)
                self.systemInfo.set_asp_cell_state(NON_ASPIRATING)
                self.aspirating = False

            else:
                if((self.aspirationBox[0] != tempAspirationBox[0]) or (self.aspirationBox[1] != tempAspirationBox[1])):
                    self.cellStationaryFrame = 0
                else:
                    self.cellStationaryFrame += 1

                self.systemInfo.set_asp_cell_position(
                    [self.aspirationBox[0] - int(self.systemInfo.get_pipette_center()[0]), 
                    self.aspirationBox[0] + self.aspirationBox[2] - int(self.systemInfo.get_pipette_center()[0])],
                    self.cellStationaryFrame)
                
        
        if((self.systemInfo.active_pipette()) and (self.cellTracker)):
            if(self.check_aspiration()):
                self.aspirating = True
                self.cellBox = None
                self.cellTracker = None 
                self.systemInfo.set_cell_position(None, True, False) 
                self.systemInfo.set_asp_cell_state(ASPIRATING) 

        if(auto and not (self.aspirating or self.aspirationTracker)):
            if(updateTip := self.find_aspirated_cell(30, 5, 1)):
                if(not self.systemInfo.active_pipette()):
                    self.pipStationaryFrame = 0
                elif(self.systemInfo.change_in_pipette(updateTip)):
                    self.pipStationaryFrame = 0
                else:
                    self.pipStationaryFrame += 1

                self.systemInfo.set_pipette_position(updateTip, self.pipStationaryFrame)
        
        if(self.aspirating and self.systemInfo.active_asp_cell() == ASPIRATING):
            aspiratedCellBackwardPos = self.find_aspirated_cell(10, 
            int(self.systemInfo.get_pipette_center()[0]) - 10, -1)
            
            aspiratedCellForwardPos = self.find_aspirated_cell(10, 5, 1)

            if(aspiratedCellForwardPos is not None and aspiratedCellBackwardPos is not None):
                
                #print("Forward %d, Backward, %d\n"%(aspiratedCellBackwardPos[0], aspiratedCellForwardPos[0]))
                if(abs(aspiratedCellBackwardPos[0] -aspiratedCellForwardPos[0]) < 20):
                    #print("Something here\n")
                    self.systemInfo.set_asp_cell_state(ASPIRATING) 
                    #self.dataQueue.put((0, aspiratedCellBackwardPos))
                else:
                    #Spawn a new MOSSE tracker
                    pipRange = self.systemInfo.get_pipette_range()
                    cellRange = self.systemInfo.get_asp_cell_pos()

                    self.init_track_at(False, [[aspiratedCellForwardPos[0] - 30, pipRange[3] - 10] ,
                        [abs(pipRange[0] - aspiratedCellForwardPos[0] + 20), 
                        abs(pipRange[3] - pipRange[1]) + 20]])
                    self.systemInfo.set_asp_cell_state(FULL_ASPIRATION)
                    '''
                    cv2.rectangle(img, (pipRange[0] + cellRange[0], pipRange[1]),
                            (pipRange[2] + cellRange[1], pipRange[3]), (128,255,128), 3, 1)
                    '''
                    #self.dataQueue.put((1, aspiratedCellBackwardPos))
                if(self.systemInfo.get_asp_cell_pos() is not None):

                    if(self.systemInfo.get_asp_cell_pos()[1] !=
                        aspiratedCellBackwardPos[0] - int(self.systemInfo.get_pipette_center()[0])):
                        self.cellStationaryFrame = 0

                    else:
                        self.cellStationaryFrame += 1
                else:
                    self.cellStationaryFrame += 1
                
                self.systemInfo.set_asp_cell_position(
                        [aspiratedCellForwardPos[0] - int(self.systemInfo.get_pipette_center()[0]), 
                        aspiratedCellBackwardPos[0] - int(self.systemInfo.get_pipette_center()[0])],
                        self.cellStationaryFrame)

            else:
                self.cellStationaryFrame += 1
                self.systemInfo.set_asp_cell_position([0, 0], self.cellStationaryFrame)
         
    def get_tracker_crop(self, idx):
        b = self.bBoxSet[idx]
        x, y, w, h = int(b[0]), int(b[1]), int(b[2]), int(b[3])
        if x < 0: x = 0
        if y < 0: y = 0
        return self.img[y:y+h, x:x+w]

    def __str__(self):
        printable = "Area [%d-%d,%d-%d] with %d cells."%(self.origin[0],
                    self.origin[1]+self.width, self.origin[1],
                    self.origin[1]+self.height, self.numCells)
        
        for cell in self.cells:
            printable = printable + ("\n\r" + str(cell) )
        
        return printable

    def __repr__(self):
        csvString = "A["
        for cell in self.cells:
            csvString = csvString + repr(cell)
            if cell == self.cells[-1]:
                continue
            csvString = csvString + ",\n"
        return csvString + "]\n"

class cell():
    def __init__(self, center, radius, index, sample):
        self.center = center
        self.radius = radius
        self.index = index
        self.sample = sample

    def get_center(self):
        return self.center

    def get_radius(self):
        return self.radius

    def get_strength(self):
        return self.strength

    def get_sample(self):
        return self.sample

    def get_index(self):
        return self.index

    def __str__(self):
        return ("Cell %d centered at [%d,%d] with radius %d" %(self.index, 
                self.center[0], self.center[1], self.radius))

    def __repr__(self):
        return "c%d,%d,%d,%d"%(self.index, self.center[0], 
                            self.center[1], self.radius)
'''
Function            apply_cHough
Debrief:            Applies circular Hough Transform to image to identify
                    circular bodies.
Arguments           image       Grayscale/BW Image to be processed
Optional Arguments  radius      Tuple of (min,max) radius
                    n           Number of objects to identify
Return value        circles     List of circles objects identified
                    None        Insufficent number of object identified
'''
def apply_cHough(image, radius = (MIN_R, MAX_R), n = NUM_DETECT):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    width, height = image.shape
    identifyingList = []
    

    circles = cv2.HoughCircles(image, cv2.HOUGH_GRADIENT, DP, 
                    2*radius[1],param1 = CANNY_THRESH, 
                    param2 = ACCUM_THRESH, minRadius = radius[0], 
                    maxRadius = radius[1])


    if circles is None:
        return []

    
    circles = np.uint16(np.around(circles))[0]
    
    for num,i in enumerate(circles[:n]):
        #Create list of all identified circles
        identifyingList.append(i)

    return identifyingList
    
'''
Function            open_image
Debrief:            Opens a image with a specified filename
Arguments           filename    Grayscale/BW Image to be processed
Optional Arguments  openType    setting for opening image. Default is grayscale.
Return value        image       Numpy array representing image
                    None        Error in reading the image
'''
def open_image(filename, prep = True):
    img = cv2.imread(filename)
    img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    if prep:
        img = cv2.medianBlur(img, BLUR_KERNEL)
        #Add more preperation to make edge detection easier
        
    return img
