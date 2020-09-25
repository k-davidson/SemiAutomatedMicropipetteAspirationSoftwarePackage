from multiprocessing import *
from .image_processing_driver import *
import time
from Emulator.emulator_os import CaptureEmulator

path  = "/Users/kelbiedavidson/Desktop/ThesisUQ/Micropipette Acculation Thesis/Software/PCSoftware/ComputerVision/SampleImages/"

def initialise_computer_vision(pixQ, posQ, capSem, emulation):
    imageProcess = Process(target = imageProcesser, args=(pixQ, posQ, capSem, emulation))
    imageProcess.start()

    #Should never get here
    return imageProcess.pid

def imageProcesser(pixQ, posQ, capSem, emulation):
    if(not emulation):
        cap = cv2.VideoCapture(0)
    else:
        cap = emulation

    frameCount = 0

    cell = None
    
    #Create config consts for each
    dim = [10,10]
    row = 1
    column = 1
    currArea = sampleArea(dim)
    #time.sleep(1)
    frameCount = 0

    while(1):
        '''
        if frameCount == cap.get(cv2.CAP_PROP_FRAME_COUNT):
            frameCount = 0
            cap = cv2.VideoCapture(path + "vid3.mp4")
        '''
        
        if not capSem.empty():
            auto, sensitivity = capSem.get()
            while(1):
                ret, frame = cap.read()
                if(ret):
                    break

            #frame = cv2.imread(path + "fail4.png")
            #frame = cv2.imread(path + "%d,%d"%(2,2) + ".jpg")

            frameCount += 1
            currArea.update_img(frame, auto, sensitivity)
            width, height, channel = frame.shape
            
            '''
            column = 1 if column + 1 > 3 else column + 1
            row = row + 1 if column == 1 else row
            row = 1 if row > 4 else row
            '''
            
            if not ret:
                print("Error reading")
                continue

            pixQ.put(currArea.get_image_info())
                #(sampleArea.get_index(), sampleArea.display_cell([], ALL = True)))
        
        if not posQ.empty():
            sel, position = posQ.get()
            currArea.init_track_at(sel, position)
