import sys
import math

import cv2
import numpy as np
import statistics

FONT_SIZE = 0.4 # Font size used in displaying text
INITIAL_X = 20 # Minimum X coordinate for iteration
COMP_DIST = 10 # Pipette tip comparison distance
THRESHOLD = 50 # Pipette tip edge threshold

def videoMicropipetteIdentification(videoPath, startFrame):
    """ Provides visulisation of the computer vision algorithm used in 
    automatically identifying cell aspiration. 
    
    NOTE: The video must meet the
    following qualifications: 
    1) The file must exist and be of .mp4 or .avi file format;
    2) The micropipette must enter from the left-hand side of frame; and
    3) The first frame must have no aspiration (for pipette tip identification)

    Args:
        video_path ([String]): [absolute filepath to video file]
    """
    # Create a and read from a capture of the video file via OpenCV

    cap = cv2.VideoCapture(videoPath)
    # Variable to indicate number of frames
    frame_count = 0

    # Iterate over frames in the provided video

    for i in range(int(startFrame)):
        ret, frame = cap.read()
    
    while(1):
        ret, frame = cap.read()
        frame_count += 1

        # If unsucessful, print and return
        if not ret:
            print("Unsuccessful in reading from the video %s\n"%(videoPath))
            return

        # Display the raw frame
        if(wait_frame(frame.copy(), "Video %s raw frame - Frame:%d"
            %(videoPath.split("/")[-1], frame_count))):
            return

        # Convert the frame to grayscale and display grayscale frame
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if(wait_frame(gray_frame.copy(), "Grayscale raw frame - Frame:%d"
            %(frame_count))):
            return

        kernel = np.ones((5,5),np.float32)/25
        filtered = cv2.filter2D(gray_frame,-1,kernel)

        # Apply canny edge detection, display edge detected frame
        cannyFrame = cv2.Canny(filtered, 15, 20) 
        if(wait_frame(cannyFrame.copy(), "Canny edge detected frame - Frame:%d"
            %(frame_count))):
            return

        # Apply the Hough transform to the frame (finding prominent lines)
        hough_lines = cv2.HoughLinesP(cannyFrame,1,np.pi/180, 20, None, 30, 5)
        houghLineFrame = np.empty(gray_frame.shape)

        #print("Number of lines is %d"%(len(hough_lines)))

        # Iterate over the lines, noting the frequency of rho
        lineAngles = dict()


        lines = []

        for line in hough_lines:
            lines.append(line[0])

        lines = sorted(lines, key=lambda x:x[1])
        if len(lines) % 2:
            medianY = lines[int((len(lines) - 1)/2)][1]
        else:
            medianY = int((lines[int((len(lines) - 1)/2)][1] + lines[int((len(lines) - 1)/2 + 1)][1])/2) 

        for line in lines:
            # Display the line in the hough frame
            cv2.line(houghLineFrame, (line[0], line[1]), (line[2], line[3]), 
            (255,255,255), 2)

            if(line[2] - line[0] == 0):
                continue
            rho = str(round(float((line[3] - line[1])/(line[2] - line[0])),1))

            if rho in lineAngles.keys():
                lineAngles[rho] = lineAngles[rho] + 1
            else:
                lineAngles[rho] = 1


        # Find the most frequent rho in the image
        maxFrequency = -1
        max_freq_angle = 0
        for key in lineAngles.keys():
            if(maxFrequency < lineAngles[key]):
                maxFrequency = lineAngles[key]
                max_freq_angle = float(key)


        # Display the Hough lines in the Hough frame
        if(wait_frame(houghLineFrame.copy(), 
        "Hough lines detected frame - Frame:%d"%(frame_count))):
            return

        print("Most frequent rate of change is %.2f"%(max_freq_angle))
        culledFrame = gray_frame.copy()

        # Find the max/min (Y coordinate) lines that have the most frequent angle
        max_line = [None, None, None, None]
        min_line = [None, None, None, None]



        for n,line in enumerate(lines):

            if(line[2] - line[0] == 0):
                continue

            rho = round(float((line[3] - line[1])/(line[2] - line[0])),1)
            offset = lines[3] - rho * line[2]

            if 500 < abs(line[1] - medianY):
                continue

            # Ensure the line matches the most frequent angle
            if abs(rho - max_freq_angle) > 0.1:
                continue

            cv2.line(culledFrame, (line[0], line[1]), (line[2], line[3]), 
            (255,255,255), 2)

            muY = (line[3] + line[1])/2
            # Set to max line if greater Y than current maxline
            if (None in max_line) or ((max_line[3] + max_line[1])/2 < muY):
                max_line = line

            # Set to min line if smaller Y than current minline
            if (None in min_line) or (muY < (min_line[3] + min_line[1])/2):
                min_line = line

        # Display the Hough lines in the Hough frame
        if(wait_frame(culledFrame.copy(), 
        "Remaining culled lines detected frame - Frame:%d"%(frame_count))):
            return
        
        # Create line functions that represent the top and bottom pipette edges
        mu_grad = max_freq_angle
        if max_freq_angle > 0.12:
            max_grad = float((max_line[3] - max_line[1])/(max_line[2] - max_line[0]))
            min_grad = float((min_line[3] - min_line[1])/(min_line[2] - min_line[0]))
            mu_grad = (max_grad + min_grad)/2
        max_offset = max_line[3] - max_line[2] * mu_grad
        min_offset = min_line[3] - min_line[2] * mu_grad
        mu_offset = int((max_offset + min_offset)/2)

        pipetteEdgeLinesFrame = gray_frame.copy()
        cv2.line(pipetteEdgeLinesFrame, (max_line[0], max_line[1]), (max_line[2], max_line[3]), (255,255,255), 2)
        cv2.line(pipetteEdgeLinesFrame, (min_line[0], min_line[1]), (min_line[2], min_line[3]), (255,255,255), 2)

        if(wait_frame(pipetteEdgeLinesFrame.copy(),
         "Maximum/Minimum paralell line of threshold length - Frame:%d"%(frame_count))):
            return

        # Iterate horizontally to find the pipette tip
        tipX = INITIAL_X
        maxThresh = -1
        
        for x in range(INITIAL_X, np.size(pipetteEdgeLinesFrame, 1) - COMP_DIST):
            x1 = x
            x2 = x + COMP_DIST

            y1 = x1 * mu_grad + mu_offset
            y2 = x2 * mu_grad + mu_offset

            if (y1 < 0) or (gray_frame.shape[0] <= y1):
                continue

            if (y2 < 0) or (gray_frame.shape[0] <= y2):
                continue
            
            currentPixel = int(gray_frame[int(x * mu_grad + mu_offset), x])
            compPixel = int(gray_frame[int((x + COMP_DIST) * mu_grad + mu_offset), 
                        x + COMP_DIST])
            
            if maxThresh < abs(currentPixel - compPixel):
                maxThresh = abs(currentPixel - compPixel)
                tipX = x + COMP_DIST

            if THRESHOLD < maxThresh:
                break

            """
            # If the edge is sufficient, this is the pipette tip
            if(THRESHOLD < abs(currentPixel - compPixel)):
                tipX = int(x + COMP_DIST/2)
                maxThresh = abs(currentPixel - compPixel)
                break
            """

            """
            if(THRESHOLD < maxThresh):
                break
            """

            # Every 10th frame, display the current position
            if(not (x % 10)):
                cv2.line(pipetteEdgeLinesFrame, 
                (int(x - 10), int((x - 10) * mu_grad + mu_offset)),
                (int(x), int(x * mu_grad + mu_offset)), (0,0,0), 2)

                if(wait_frame(pipetteEdgeLinesFrame, 
                "Finding pipette tip edge - Frame:%d"%(frame_count), 1)):
                    return


        # Add a line to show the iterations
        cv2.line(pipetteEdgeLinesFrame,
        (0, int(0 * mu_grad + mu_offset)), (int(tipX), int(tipX * mu_grad + mu_offset)),
        (0,0,0), 2) 

        x_max = None
        y_max = None

        x_min = None
        y_min = None

        if(mu_grad == 0):
            x_max = tipX
            y_max = tipX * mu_grad + max_offset

            x_min = tipX
            y_min = tipX * mu_grad + min_offset
        
        else:
            perp_grad = -1/(mu_grad)
            perp_offset = (tipX * mu_grad + mu_offset) - (perp_grad * tipX)

            x_max = (perp_offset - max_offset)/(mu_grad - perp_grad)
            y_max = mu_grad * x_max + max_offset

            x_min = (perp_offset - min_offset)/(mu_grad - perp_grad)
            y_min = mu_grad * x_min + min_offset

        if (x_max is not None) and (x_min is not None):
            # Add a line to the frame where the pipette is detected
            cv2.line(pipetteEdgeLinesFrame,
            (int(x_max), int(y_max)), 
            (int(x_min), int(y_min)),
            (0,0,0), 2) 

        # Display the tip edge frame
        if(wait_frame(pipetteEdgeLinesFrame, 
        "Pipette tip detection - Frame:%d"%(frame_count))):
            return 

        

def wait_frame(frame, title, delay = None):
    """ Add additional features to gray frame for display. Check user input to 
        determine how to proceed with subsequent frames.

    Args:
        frame ([numpy.ndarray]): [Frame to be displayed to the user]
        title ([string]): [Title of the display window]
        skips ([bool]): [True if the current frame should be skipped]
        delay ([int], optional): [Window life in milliseconds]. Defaults to None.

    Returns:
        [bool]: True if the next frame should be skipped. Otherwise, False.
    """
    height = np.size(frame, 0)
    width = np.size(frame, 1)

    # Adds additional text to display use instructions to the user
    '''
    cv2.putText(frame, "Press <Space> to view the next frame", 
        (5, height - 25), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, [255,255,255])
    cv2.putText(frame, "Press 'Q' to exit the video", 
        (5, height - 10), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, [255,255,255])
    '''
    # Displays the frame
    cv2.imshow(title, frame)
    
    # If no delay, display until input
    if(delay is None):
        keyPressed = cv2.waitKey(0)
    # Otherwise, display until delay or input
    else:
        keyPressed = cv2.waitKey(delay)

    # Destroy window
    cv2.destroyAllWindows()

    # If no key was pressed, continue to the next frame
    if(keyPressed is None):
        return False

    # If input is the 'q' key, user wishes to quit the application
    if((ord('q') == keyPressed) or (ord('Q') == keyPressed)):
        return True
    
    return False


if __name__ == "__main__":
    if (len(sys.argv) != 3) or (sys.argv[1] == "help"):
        for st in sys.argv:
            print(st)
        print("\nThis program provides visualisation of " +
        "the computer vision algorithm identifying the micropipette.\n" +
        "Program usage: python videoMicropipetteIdentification.py <filepath> <startframe>\n")
        exit(0)
    else:
        videoMicropipetteIdentification(sys.argv[1], sys.argv[2])

