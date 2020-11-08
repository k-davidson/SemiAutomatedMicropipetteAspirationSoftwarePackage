import sys

import cv2
import numpy as np

FONT_SIZE = 0.4 # Font size used in displaying text
INITIAL_X = 20 # Minimum X coordinate for iteration
COMP_DIST = 20 # Pipette tip comparison distance
ASP_COMP_DIST = 10 # Aspirated cell comparison distance
THRESHOLD = 30 # Pipette tip edge threshold
ASP_THRESHOLD = 18 # Aspirated cell edge threshold
FULL_ASP_DIST = 40 # Minimum length of the cell when fully aspirated


def aspiration_identification(video_path, startFrame, disp):
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
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()

    disp = int(disp)

    frame_count = 1
    pass_frames = True

    # If unsucessful, print and return
    if not ret:
        print("Unsuccessful in reading from the video %s\n"%(video_path))
        return

    # Convert the frame to grayscale and display grayscale frame
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    kernel = np.ones((5,5),np.float32)/25
    filtered = cv2.filter2D(gray_frame,-1,kernel)

    # Apply canny edge detection, display edge detected frame
    cannyFrame = cv2.Canny(filtered, 15, 20)

    # Apply the Hough transform to the frame (finding prominent lines)
    hough_lines = cv2.HoughLinesP(cannyFrame,1,np.pi/180, 20, None, 30, 5)

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

        if 100 < abs(line[1] - medianY):
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

    # Create line functions that represent the top and bottom pipette edges
    mu_grad = max_freq_angle
    max_offset = max_line[3] - max_line[2] * mu_grad
    min_offset = min_line[3] - min_line[2] * mu_grad
    mu_offset = int((max_offset + min_offset)/2)

    # Iterate horizontally to find the pipette tip
    tipX = INITIAL_X
    maxThresh = -1
    
    for x in range(INITIAL_X, np.size(gray_frame, 1) - COMP_DIST):
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


    while(frame_count < int(startFrame)):
        ret, frame = cap.read()
        frame_count += 1


    # Iterate over the reamining video frames
    while frame_count < cap.get(cv2.CAP_PROP_FRAME_COUNT):
        # Read next frame, apply grayscale, and draw the pipette tip
        ret, frame = cap.read()
        frame_count += 1
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        asp_frame = gray_frame.copy()
        cv2.line(asp_frame,
                 (int(x_min), int(y_min)),
                 (int(x_max), int(y_max)),
                 (0, 0, 0), 2)
            
        title = ""

        tip_x = int((x_min + x_max)/2)

        # Check if this frame should be skipped
        if not pass_frames:
            
            # Iterate from base to pipette tip to find asp cell edge
            print("forward")
            forward_iter = asp_inter(gray_frame, asp_frame,[
            INITIAL_X, tip_x - ASP_COMP_DIST], 1, ASP_COMP_DIST, mu_grad,
            mu_offset, disp)
            # Iterate from pipette tip to base to find asp cell edge
            print("back")
            back_iter = asp_inter(gray_frame, asp_frame,
            [tip_x - 5, INITIAL_X - ASP_COMP_DIST], -1, ASP_COMP_DIST, mu_grad,
            mu_offset, disp, intensity=(255, 255, 255))
            back_iter -= ASP_COMP_DIST

            
            print(back_iter)
            print(forward_iter)
            # If the pipette tip and base are reached, no cell edge was found
            if (abs(back_iter - (INITIAL_X)) < 3 * ASP_COMP_DIST) \
            and (abs(forward_iter - (tip_x - ASP_COMP_DIST)) < 3 * ASP_COMP_DIST):
                title = "No aspirated cell found"
            
            # If only one distinct edge was found, the cell is aspirating
            elif abs(back_iter - forward_iter) < FULL_ASP_DIST:
                title = "Aspirated cell @ %d pixels" % (back_iter)
                aspiration_X = int((forward_iter + back_iter)/2)
                cv2.line(asp_frame, \
                         (aspiration_X, int(aspiration_X * mu_grad + min_offset)), \
                         (aspiration_X, int(aspiration_X * mu_grad + max_offset)), \
                         (255, 255, 255), 2)
                if not disp:
                    cv2.line(asp_frame, \
                            (tip_x, int(tip_x * mu_grad + int(max_offset + min_offset)/2)), \
                            (aspiration_X, int(aspiration_X * mu_grad + int(max_offset + min_offset)/2)), \
                            (255, 255, 255), 2)
            
            # If two distinct edges were found, the cell is fully aspirated
            else:
                y1 = back_iter * mu_grad + min_offset
                y2 = forward_iter * mu_grad + max_offset
                cv2.rectangle(asp_frame, (back_iter,int(y1)), (forward_iter, int(y2)), (255, 255, 255), 2)
                title = "Full aspirated cell from [%d,%d] pixels" %(forward_iter, back_iter)

        # Draw the aspirated cell on a gray frame
        pass_frames = wait_frame(asp_frame, title +
        " - Frame:%d" % (frame_count), pass_frames)


def asp_inter(src, dest, x_range, step, comp_dist, mu_grad, mu_offset, vis,
intensity=(0, 0, 0)):
    """ Iterate horizontally through the pipette to find the aspirated cell 
        edge. Return the coorinate (in pixels) of the edge.

    Args:
        src ([numpy.ndarray]): Frame to be searched.
        dest ([numpy.ndarray]): Frame to be modified for display.
        x_range ([int[]]): The range over which the iteration will occur.
        step ([int]): The number of pixels to step per iteration.
        comp_dist ([int]): Distance to compare pixels over.
        mu_grad (int): Gradient of the average line
        mu_offset (int): Offset of the average line
        intensity (tuple, optional): [R,G,B] of the line displayed. Defaults to (0, 0, 0).

    Returns:
        [int]: Coordinate of the first edge found when iterating over the average line.
    """

    # Start X-iterations at initial condition
    iteration = x_range[0]
    max_thresh = 0
    aspX = 0

    # Iterate horizontally in the X-range to find egde
    for x_coord in range(x_range[0], x_range[1], step):
        curr_pixel = int(src[int(x_coord * mu_grad + mu_offset), x_coord])
        comp_pixel = int(src[int((x_coord + step*comp_dist) * mu_grad + mu_offset),
                                 x_coord + step*comp_dist])

        if max_thresh < abs(curr_pixel - comp_pixel):
            max_thresh = abs(curr_pixel - comp_pixel)
            aspX = x_coord
        
        # If difference meets the threshold, this is the edge
        if ASP_THRESHOLD < abs(curr_pixel - comp_pixel):
            break
            

        # Step iteration
        iteration += step

        if vis:
            # Display current iteration every 8 frames
            if not x_coord % 8:
                cv2.line(dest,
                    (iteration - 5, int((iteration - 5) * mu_grad + mu_offset)),
                    (iteration, int(iteration * mu_grad + mu_offset)), intensity, 2)

                wait_frame(
                    dest, "Iterating forward to Aspirated Cell", 0, delay=1)

    if max_thresh < ASP_THRESHOLD:
        return x_range[1]

    # Return position of edge
    return aspX


def wait_frame(frame, title, skips, delay=None):
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

    # Adds additional text to display use instructions to the user
    height = np.size(frame, 0)
    cv2.putText(frame, "Hold 'S' to skip frames",
                (5, height - 40), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE,
                [255, 255, 255])
    cv2.putText(frame, "Press <Space> to view the next frame",
                (5, height - 25), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE,
                [255, 255, 255])
    cv2.putText(frame, "Press 'Q' to exit the video",
                (5, height - 10), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, 
                [255, 255, 255])

    # Displays the frame
    cv2.imshow(title, frame)

    # If no delay, display until input
    if delay is None:
        key_pressed = cv2.waitKey(60)
    # Otherwise, display until delay or input
    else:
        key_pressed = cv2.waitKey(delay)

    # Destroy window
    cv2.destroyAllWindows()

    # If input is the 's' key, user wishes to skip the next frame
    if (ord('s') == key_pressed) or (ord('S') == key_pressed):
        return True

    # If no key was pressed, continue to the next frame
    if key_pressed is None:
        return False

    # If input is the 'q' key, user wishes to quit the application
    if (ord('q') == key_pressed) or (ord('Q') == key_pressed):
        sys.exit(0)

    return False


if __name__ == "__main__":
    if (len(sys.argv) != 4) or (sys.argv[1] == "help"):
        print("\nThis program provides visualisation of " +
              "the computer vision algorithm identifying cell aspiration.\n" +
              "NOTE: The first frame is used to identify the micropipette.\n" +
              "Hence, no aspiration must occur until the second frame.\n\n" +
              "Program usage: python aspirationIdentification.py <filepath> " +
              "<startFrame> <display>\n")
    else:
        aspiration_identification(sys.argv[1], sys.argv[2], sys.argv[3])
