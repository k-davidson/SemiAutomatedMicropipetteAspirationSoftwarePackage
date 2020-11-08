from multiprocessing import *
from .SoftwareDrivers.image_processing_driver import *
from .SoftwareDrivers.ConfigFiles.settings import *

def initialise_computer_vision(pixQ, posQ, capSem, emulation):
    """ Initialise the Computer Vision process

    Args:
        pixQ (Queue): Queue to transfer observed information
        posQ (Queue): Queue to transfer user selection information
        capSem (Queue): Queue used as semaphore to request observed information
        emulation (bool): True iff emulator is used.

    Returns:
        int: Process ID for the computer vision process
    """
    
    imageProcess = Process(target = imageProcesser, args=(pixQ, posQ, capSem, emulation))
    imageProcess.start()

    return imageProcess.pid

def imageProcesser(pixQ, posQ, capSem, emulation):
    """ Process loop for processing computer vision content.

    Args:
        pixQ (Queue): Queue to transfer observed information
        posQ (Queue): Queue to transfer user selection information
        capSem (Queue): Queue used as semaphore to request observed information
        emulation (bool): True iff emulator is used.
    """

    # Default value initialisation
    using_video = False
    using_img = False
    frame_count = 0
    img = None
    
    # If emulator flag is true, use the emulator
    if(IMAG_EMULATOR):
        cap = emulation
    
    # Otherwise, if using video file load the video as the capture
    elif((IMAG_VIDEO) and (VIDEO_PATH != None)):
        split_path = VIDEO_PATH.split(".")
        if((split_path[-1] == "mp4") or (split_path[-1] == "avi")):
            cap = cv2.VideoCapture(VIDEO_PATH)
            using_video = True
        elif((split_path[-1] == "jpg") or (split_path[-1] == "png")):
            img = cv2.imread(VIDEO_PATH, cv2.IMREAD_COLOR)
            using_img = True
        else:
            cap = cv2.VideoCapture(0)
    
    # Otherwise, default to video capture 0 for feed
    else:
        cap = cv2.VideoCapture(0)
    
    # Initialise instance of a tracker manager
    track_manager = trackerManager()

    while(1):
        
        # If using video and reached the last frame, reset the video
        if (using_video) and (frame_count == cap.get(cv2.CAP_PROP_FRAME_COUNT)):
            frame_count = 0
            cap = cv2.VideoCapture(VIDEO_PATH)
        
        # If an image is requested
        if not capSem.empty():
            sensitivity = capSem.get()
            
            # Attempt to read a frame from the capture
            ret = False
            for attempts in range(5):
                if (not using_img):
                    ret, frame = cap.read()
                    if(ret):
                        break
                else:
                    frame = img
                    break
                
            # If a video is used, count the frame capture
            if(using_video):
                frame_count += 1
                
            # Update the trackers for the new frame
            track_manager.update(frame, sensitivity)

            # Communicate new observed info the the GUI
            pixQ.put(track_manager.get_image_info())
            
            # Clear all single frame states
            track_manager.clear_frame_states()
        
        # If the user has requested a cell track
        if not posQ.empty():
            sel, position = posQ.get()
            track_manager.init_cell_track_at(position)
