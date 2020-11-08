import sys
import math

import cv2
import numpy as np

FONT_SIZE = 0.4 # Font size used in displaying text
INITIAL_X = 10 # Minimum X coordinate for iteration
COMP_DIST = 20 # Pipette tip comparison distance

def videoMicropipetteIdentification(videoPath, gt_filename, dist_thresh, 
edge_thresh, human_readable):
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

    visulisation = int(human_readable)

    raw_line = gt.readline()

    mu_dist = 0
    max_run_frame = 0
    max_run_len = 0
    run_len = 0

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
        print("ERROR: Ground Truth ends at frame %d\n" \
        %(gt_frame_count, cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        return 1

    pastPipetteX1 = None
    pastPipetteX2 = None

    pastPipetteY1 = None
    pastPipetteY2 = None

    # Iterate over frames in the provided video
    while(frame_count + 5 < cap.get(cv2.CAP_PROP_FRAME_COUNT)):
        ret, frame = cap.read()
        frame_count += 1

        # If unsucessful, print and return
        if not ret:
            print("Unsuccessful in reading from the video %s\n"%(videoPath))
            break

        pipetteX1, pipetteY1, pipetteX2, pipetteY2 = \
            find_pipette_tip(frame, edge_thresh)

        if pipetteX1 is None:
            pipetteX1 = pastPipetteX1
        
        if pipetteX2 is None:
            pipetteX2 = pastPipetteX2

        if pipetteY1 is None:
            pipetteY1 = pastPipetteY1
            
        if pipetteY2 is None:  
            pipetteY2 = pastPipetteY2

        # Display the raw frame
        pastPipetteX1 = pipetteX1
        pastPipetteX2 = pipetteX2

        pastPipetteY1 = pipetteY1
        pastPipetteY2 = pipetteY2

        if pipetteX1 is not None:
            if (gt_index < len(positions_per_frame) - 1) and \
                (positions_per_frame[gt_index + 1][2] <= frame_count):
                gt_index += 1
                gt_x = positions_per_frame[gt_index][0]
                gt_y = positions_per_frame[gt_index][1]
                gt_frame = positions_per_frame[gt_index][2]

            cv2.line(frame, (pipetteX1, pipetteY1), (pipetteX2, pipetteY2), \
                (255,128,128), 2)
        cv2.line(frame, (gt_x - 5, gt_y), (gt_x + 5, gt_y), (128, 255, 128), 2)
        cv2.line(frame, (gt_x, gt_y - 5), (gt_x, gt_y + 5), (128, 255, 128), 2)

        err_delay = 34
        if pipetteX1 is not None:
            dist = max(gt_x - ((pipetteX1 + pipetteX2)/2), (gt_y - ((pipetteY1 + pipetteY2)/2)))
            mu_dist += abs(dist)
            if(dist_thresh <= dist):
                run_len += 1
                errors += 1
                err_delay = 0
            else:
                run_len = 0
        else:
            run_len += 1
            errors += 1
            err_delay = 0
        
        if max_run_len < run_len:
            max_run_len = run_len
            max_run_frame = frame_count

        if visulisation:
            if(wait_frame(frame.copy(), "Video %s raw frame - Frame:%d"
            %(videoPath.split("/")[-1], frame_count), delay = err_delay)):
                return

    mu_dist /= frame_count

    output = "%s,%d,%d,%d,%d,%d\n"%(videoPath.split("/")[-1], errors, \
    frame_count, mu_dist, max_run_len, max_run_frame)

    print(output)

    cap.release()
    return output
    

def find_pipette_tip(frame, edge_thresh):
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

    # Convert the frame to grayscale and display grayscale frame
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    kernel = np.ones((5,5),np.float32)/25
    filtered = cv2.filter2D(gray_frame,-1,kernel)

    # Apply canny edge detection, display edge detected frame
    cannyFrame = cv2.Canny(filtered, 15, 20)

    # Apply the Hough transform to the frame (finding prominent lines)
    hough_lines = cv2.HoughLinesP(cannyFrame,1,np.pi/180, 20, None, 30, 5)

    if hough_lines is None:
        return [None, None, None, None]

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

    # Find the max/min (Y coordinate) lines that have the most frequent angle
    max_line = [None, None, None, None]
    min_line = [None, None, None, None]

    for n,line in enumerate(lines):

        if(line[2] - line[0] == 0):
            continue

        rho = round(float((line[3] - line[1])/(line[2] - line[0])),1)

        if 500 < abs(line[1] - medianY):
            continue

        # Ensure the line matches the most frequent angle
        if abs(rho - max_freq_angle) > 0.1:
            continue

        muY = (line[3] + line[1])/2
        # Set to max line if greater Y than current maxline
        if (None in max_line) or ((max_line[3] + max_line[1])/2 < muY):
            max_line = line

        # Set to min line if smaller Y than current minline
        if (None in min_line) or (muY < (min_line[3] + min_line[1])/2):
            min_line = line

    if None in max_line or None in min_line:
        return [None, None, None, None]

    # Create line functions that represent the top and bottom pipette edges
    mu_grad = max_freq_angle
    if max_freq_angle != 0:
        max_grad = float((max_line[3] - max_line[1])/(max_line[2] - max_line[0]))
        min_grad = float((min_line[3] - min_line[1])/(min_line[2] - min_line[0]))
        mu_grad = (max_grad + min_grad)/2
    max_offset = max_line[3] - max_line[2] * mu_grad
    min_offset = min_line[3] - min_line[2] * mu_grad
    mu_offset = int((max_offset + min_offset)/2)

    max_offset = max_line[3] - max_line[2] * mu_grad
    min_offset = min_line[3] - min_line[2] * mu_grad
    mu_offset = int((max_offset + min_offset)/2)

    # Iterate horizontally to find the pipette tip
    edges = [INITIAL_X, INITIAL_X, INITIAL_X]
    offsets = [int(max_offset - (max_offset - min_offset)/8), 
                int(min_offset + (max_offset - min_offset)/8), 
                mu_offset]

    for n, c in enumerate(offsets):
        maxThresh = -1
        for x in range(INITIAL_X, np.size(gray_frame, 1) - COMP_DIST):
            x1 = x
            x2 = x + COMP_DIST

            y1 = x1 * mu_grad + c
            y2 = x2 * mu_grad + c

            if (y1 < 0) or (gray_frame.shape[0] <= y1):
                continue

            if (y2 < 0) or (gray_frame.shape[0] <= y2):
                continue
            
            currentPixel = int(gray_frame[int(y1), x1])
            compPixel = int(gray_frame[int(y1), x2])
            
            if maxThresh < abs(currentPixel - compPixel):
                maxThresh = abs(currentPixel - compPixel)
                edges[n] = x +COMP_DIST/2

            
            if edge_thresh < maxThresh:
                edges[n] = x + COMP_DIST
                break
    
        if maxThresh < 0.25 * edge_thresh:
            edges[n] = None
    
    if None in edges:
        return [None, None, None, None]

    tipX = edges[2]
    if (abs(edges[2] - edges[0]) > 20) and (abs(edges[2] - edges[1]) > 20):
        tipX = edges[0]

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

    return [int(x_min), int(y_min), int(x_max), int(y_max)]


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
    if (len(sys.argv) != 6) or (sys.argv[1] == "help"):
        print("\nThis program provides performance statistics of " + \
            "pipette tip identification by comparing the approximated " + \
                "position with the ground truth provided.\n Program usage:" + \
                    "python videoMicropipetteIdentification.py " + \
                        "<video_filepath> <GT_filepath> <distance_thresh> " + \
                            "<edge_thresh> <human_readable>\n")
    else:
        videoMicropipetteIdentification(sys.argv[1], sys.argv[2], \
            sys.argv[3], sys.argv[4], sys.argv[5])

