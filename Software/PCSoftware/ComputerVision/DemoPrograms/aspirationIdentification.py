import sys

import cv2
import numpy as np

FONT_SIZE = 0.4 # Font size used in displaying text
INITIAL_X = 20 # Minimum X coordinate for iteration
COMP_DIST = 5 # Pipette tip comparison distance
ASP_COMP_DIST = 10 # Aspirated cell comparison distance
THRESHOLD = 20 # Pipette tip edge threshold
ASP_THRESHOLD = 10 # Aspirated cell edge threshold
FULL_ASP_DIST = 30 # Minimum length of the cell when fully aspirated


def aspiration_identification(video_path):
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

    # If unsucessful, print and return
    if not ret:
        print("Unsuccessful in reading from the video %s\n"%(video_path))
        return

    # Variable to indicate number of frames
    frame_count = 1
    # Flag to indicate if a frame is to be skipped
    pass_frames = True

    # Convert BGR frame to grayscale
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Apply edge detection to grayscale image
    canny_frame = cv2.Canny(gray_frame, 60, 150, apertureSize=3)
    # Apply hough transform to edge image (to find lines)
    hough_lines = cv2.HoughLinesP(canny_frame, 1, np.pi/180, 30, 30, 70, 20)
    hough_line_frame = np.empty(canny_frame.shape)

    # Iterate over the lines to find greatest number of paralell lines
    line_angles = dict()
    for line in hough_lines:
        line = line[0]

        # Increment frequency in dictionary for a given rho
        rho = str(int((line[3] - line[1])/(line[2] - line[0])))
        if rho in line_angles.keys():
            line_angles[rho] = line_angles[rho] + 1
        else:
            line_angles[rho] = 1
        # Add new line to the display image
        cv2.line(hough_line_frame, (line[0], line[1]), (line[2], line[3]),
                 (255, 255, 255), 2)

    # Find the angle that occurs most frequently
    max_frequency = -1
    max_freq_angle = 0
    for key in line_angles.keys():
        if max_frequency < line_angles[key]:
            max_frequency = line_angles[key]
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

    # Iterate horizontally at the mean line to find the pipette tip
    tip_x = INITIAL_X
    for x_coord in range(INITIAL_X, np.size(gray_frame, 1) - COMP_DIST):
        curr_pixel = int(gray_frame[int(x_coord * mu_grad + mu_offset), x_coord])
        comp_pixel = int(gray_frame[int((x_coord + COMP_DIST) * mu_grad + mu_offset),
                                  x_coord + COMP_DIST])

        # If the edge meets the threshold, this is the tip
        if ASP_THRESHOLD < abs(curr_pixel - comp_pixel):
            tip_x = x_coord + COMP_DIST
            break
        tip_x += 1

    # Iterate over the reamining video frames
    while frame_count < cap.get(cv2.CAP_PROP_FRAME_COUNT):
        # Read next frame, apply grayscale, and draw the pipette tip
        ret, frame = cap.read()
        frame_count += 1
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        asp_frame = gray_frame.copy()
        cv2.line(asp_frame,
                 (tip_x, int(tip_x * mu_grad + min_offset)),
                 (tip_x, int(tip_x * mu_grad + max_offset)),
                 (0, 0, 0), 2)
            
        title = ""

        # Check if this frame should be skipped
        if not pass_frames:
            
            # Iterate from base to pipette tip to find asp cell edge
            forward_iter = asp_inter(gray_frame, asp_frame,[
            INITIAL_X, tip_x - ASP_COMP_DIST], 1, ASP_COMP_DIST, mu_grad,
            mu_offset)
            # Iterate from pipette tip to base to find asp cell edge
            back_iter = asp_inter(gray_frame, asp_frame,
            [tip_x - 5, INITIAL_X - ASP_COMP_DIST], -1, ASP_COMP_DIST, mu_grad,
            mu_offset, intensity=(255, 255, 255))

            
            # If the pipette tip and base are reached, no cell edge was found
            if (abs(back_iter - (INITIAL_X - ASP_COMP_DIST))
                < 3 * ASP_COMP_DIST) and \
                (abs(forward_iter - (tip_x - ASP_COMP_DIST))
                 < 3 * ASP_COMP_DIST):
                title = "No aspirated cell found"
            
            # If only one distinct edge was found, the cell is aspirating
            elif abs(back_iter - forward_iter) < FULL_ASP_DIST:
                title = "Aspirated cell @ %d pixels" % (back_iter)
                aspiration_X = int((forward_iter + back_iter)/2)
                cv2.line(asp_frame,
                         (aspiration_X, aspiration_X * mu_grad + min_offset),
                         (aspiration_X, aspiration_X * mu_grad + max_offset),
                         (255, 255, 255), 2)
            
            # If two distinct edges were found, the cell is fully aspirated
            else:
                cv2.rectangle(asp_frame,
                (back_iter,back_iter * mu_grad + min_offset),
                (forward_iter, forward_iter * mu_grad + max_offset),
                (255, 255, 255), 2)
                title = "Full aspirated cell from [%d,%d] pixels" %(forward_iter, back_iter)

        # Draw the aspirated cell on a gray frame
        pass_frames = wait_frame(asp_frame, title +
        " - Frame:%d" % (frame_count), pass_frames)


def asp_inter(src, dest, x_range, step, comp_dist, mu_grad, mu_offset,
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

    # Iterate horizontally in the X-range to find egde
    for x_coord in range(x_range[0], x_range[1], step):
        curr_pixel = int(src[int(x_coord * mu_grad + mu_offset), x_coord])
        comp_pixel = int(src[int((x_coord + step*comp_dist) * mu_grad + mu_offset),
                                 x_coord + step*comp_dist])

        # If difference meets the threshold, this is the edge
        if ASP_THRESHOLD < abs(curr_pixel - comp_pixel):
            iteration = int(x_coord + step*comp_dist/2)
            break

        # Step iteration
        iteration += step

        # Display current iteration every 8 frames
        if not x_coord % 8:
            cv2.line(dest,
                     (iteration - 5, (iteration - 5) * mu_grad + mu_offset),
                     (iteration, iteration * mu_grad + mu_offset), intensity, 2)

            wait_frame(
                dest, "Iterating forward to Aspirated Cell", 0, delay=1)

    # Return position of edge
    return iteration


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
    # If this frame should be skipped
    if skips:
        return False

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
        key_pressed = cv2.waitKey(0)
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
    if (len(sys.argv) != 2) or (sys.argv[1] == "help"):
        print("\nThis program provides visualisation of " +
              "the computer vision algorithm identifying cell aspiration.\n" +
              "NOTE: The first frame is used to identify the micropipette.\n" +
              "Hence, no aspiration must occur until the second frame.\n\n" +
              "Program usage: python aspirationIdentification.py <filepath>\n")
    else:
        aspiration_identification(sys.argv[1])
