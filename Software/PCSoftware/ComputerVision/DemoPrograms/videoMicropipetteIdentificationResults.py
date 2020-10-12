import sys
import math

import cv2
import numpy as np

FONT_SIZE = 0.4 # Font size used in displaying text
INITIAL_X = 20 # Minimum X coordinate for iteration
COMP_DIST = 5 # Pipette tip comparison distance
THRESHOLD = 20 # Pipette tip edge threshold

def videoMicropipetteIdentification(videoPath, gt_filename, dist_thresh, edge_thresh):
    """ Provides visulisation of the computer vision algorithm used in 
    automatically identifying cell aspiration. 
    
    NOTE: The video must meet the
    following qualifications: 
    1) The file must exist and be of .mp4 or .avi file format;
    2) The micropipette must enter from the left-hand side of frame; and
    3) The video must have no aspiration (for pipette tip identification)

    Args:
        video_path ([String]): [absolute filepath to video file]
    """
    gt = open(gt_filename, "r")
    gt_frame_count = 0

    raw_line = gt.readline()

    positions_per_frame = []

    dist_thresh = int(dist_thresh)
    edge_thresh = int(edge_thresh)

    errors = 0

    while(len(raw_line) != 0):
        line = raw_line.split(",")
        gt_frame_count = int(line[2])
        x_position = int(line[0])
        y_position = int(line[1])
        positions_per_frame.append((x_position, y_position, gt_frame_count))
        raw_line = gt.readline()


    # Create a and read from a capture of the video file via OpenCV
    cap = cv2.VideoCapture(videoPath)
    # Variable to indicate number of frames
    frame_count = 0
    gt_index = 0

    gt_x = positions_per_frame[gt_index][0]
    gt_y = positions_per_frame[gt_index][1]
    gt_frame = positions_per_frame[gt_index][2]

    if(gt_frame_count != cap.get(cv2.CAP_PROP_FRAME_COUNT)):
        print("ERROR: Ground Truth ends at frame %d but provided video file has %d frames\n"%(gt_frame_count, cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        return 1

    # Iterate over frames in the provided video
    while(frame_count < cap.get(cv2.CAP_PROP_FRAME_COUNT)):
        ret, frame = cap.read()
        frame_count += 1

        # If unsucessful, print and return
        if not ret:
            print("Unsuccessful in reading from the video %s\n"%(video_path))
            return

        # Display the raw frame

        pipetteX1, pipetteY1, pipetteX2, pipetteY2 = find_pipette_tip(frame, edge_thresh)

        if (gt_index < len(positions_per_frame) - 1) and (positions_per_frame[gt_index + 1][2] <= frame_count):
            gt_index += 1
            gt_x = positions_per_frame[gt_index][0]
            gt_y = positions_per_frame[gt_index][1]
            gt_frame = positions_per_frame[gt_index][2]

        cv2.line(frame, (pipetteX1, pipetteY1), (pipetteX2, pipetteY2), (255,128,128), 2)
        cv2.line(frame, (gt_x - 5, gt_y), (gt_x + 5, gt_y), (128, 255, 128), 2)
        cv2.line(frame, (gt_x, gt_y - 5), (gt_x, gt_y + 5), (128, 255, 128), 2)

        dist = math.sqrt(pow(gt_x - ((pipetteX1 + pipetteX2)/2), 2) +
                            pow(gt_y - ((pipetteY1 + pipetteY2)/2), 2))
        err_delay = 34
        
        if(dist_thresh <= dist):
            errors += 1
            err_delay = 0

        if(wait_frame(frame.copy(), "Video %s raw frame - Frame:%d"
        %(videoPath.split("/")[-1], frame_count), delay = err_delay)):
            return

    print("Performance: The algorithm incorrectly identified a position " + 
    "outside the threshold distance in %d of the %d"%(errors, frame_count) +
    " frames, resulting in an error rate of %.2f%%"
    %((errors * 100.0)/frame_count))
    

def find_pipette_tip(frame, edge_thresh):
        # Convert the frame to grayscale and display grayscale frame
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply canny edge detection, display edge detected frame
        cannyFrame = cv2.Canny(gray_frame, 60, 150,apertureSize = 3)

        # Apply the Hough transform to the frame (finding prominent lines)
        hough_lines = cv2.HoughLinesP(cannyFrame,1,np.pi/180, 30, 30, 50, 30)
        houghLineFrame = np.empty(cannyFrame.shape)

        # Iterate over the lines, noting the frequency of rho
        lineAngles = dict()
        for i in range(len(hough_lines)):
            # Display the line in the hough frame
            line = hough_lines[i][0]

            rho = str(int((line[3] - line[1])/(line[2] - line[0])))

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
                max_freq_angle = int(key)

        # Find the max/min (Y coordinate) lines that have the most frequent angle
        max_line = [None, None, None, None]
        min_line = [None, None, None, None]

        for line in hough_lines:
            line = line[0]

            rho = int((line[3] - line[1])/(line[2] - line[0]))

            # Ensure the line matches the most frequent angle
            if rho != max_freq_angle:
                break

            # Set to max line if greater Y than current maxline
            if (None in max_line) or (max_line[1] < line[1]):
                max_line = line

            # Set to min line if smaller Y than current minline
            if (None in min_line) or (line[1] < min_line[1]):
                min_line = line

        # Create line functions that represent the top and bottom pipette edges
        mu_grad = max_freq_angle
        max_offset = max_line[3] - max_line[2] * mu_grad
        min_offset = min_line[3] - min_line[2] * mu_grad
        mu_offset = int((max_offset + min_offset)/2)


        # Iterate horizontally to find the pipette tip
        tipX = INITIAL_X
        for x in range(INITIAL_X, np.size(gray_frame, 1) - COMP_DIST):
            currentPixel = int(gray_frame[int(x * mu_grad + mu_offset), x])
            compPixel = int(gray_frame[int((x + COMP_DIST) * mu_grad + mu_offset), 
                        x + COMP_DIST])
            
            # If the edge is sufficient, this is the pipette tip
            if(edge_thresh < abs(currentPixel - compPixel)):
                tipX = int(x + COMP_DIST/2)
                break
            else:
                tipX += 1

        return [tipX, max_offset + (mu_grad * tipX), 
        tipX, min_offset + (mu_grad * tipX)]



        

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
    cv2.putText(frame, "Press <Space> to view the next frame", 
        (5, height - 25), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, [255,255,255])
    cv2.putText(frame, "Press 'Q' to exit the video", 
        (5, height - 10), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, [255,255,255])

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
    if (len(sys.argv) != 5) or (sys.argv[1] == "help"):
        print("\nThis program provides performance statistics of pipette tip identification " +
        "by comparing the approximated position with the ground truth provided.\n" +
        "Program usage: python videoMicropipetteIdentification.py <video_filepath> <GT_filepath> <distance_thresh> <edge_thresh>\n")
    else:
        videoMicropipetteIdentification(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

