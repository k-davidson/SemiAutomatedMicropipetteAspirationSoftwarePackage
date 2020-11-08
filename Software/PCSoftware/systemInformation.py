from math import *
import cv2
import copy
import numpy as np
from settings import *
import time
from enum import Enum

class basic_track_state(Enum):
    """ Initialise valid states for all trackers

    Args:
        Enum: Inheret from Enum class
    """
    NO_ACTIVE_TRACK = 0
    ACTIVE_TRACK = 1

class asp_track_state(Enum):
    """ Initialise additional valid states for an aspiration tracker

    Args:
        Enum: Inheret from Enum class
    """
    ACTIVE_ASP_TRACK = 1
    ACTIVE_FULL_ASP_TRACK = 2

class basicTracker():
    """ Basic tracker used in accessing pixels directly to find significant
    edges between neighbouring pixels.
    """

    def __init__(self):
        """ Initialisation of Basic Tracker positions and states
        """
        self.trackPosition = [None, None, None, None]
        self.movingTrack = True
        self.lastTimeUpdate = time.time()
        self.stationaryFrames = 0
        self.movingTrack = True
        self.lostTrack = False

        self.mu_grad = 0
        self.mu_offset = 0

        self.trackState = basic_track_state.NO_ACTIVE_TRACK

    def active_track(self):
        """ Check if the tracker is currently active.

        Returns:
            bool: True iff the tracker is active. False otherwise.
        """
        # If the track position is not None
        if((self.trackPosition[0] is not None) and 
            (self.trackPosition[1] is not None)):
            return True

        return False

    def get_state(self):
        """ Returns the current tracker state. Valid states are depdendent
        on the tracker type. 

        Returns:
            enum: Tracker state
        """
        return self.trackState

    def set_state(self, state):
        """ Set the current tracker state. Valid states are dependent on the
        the tracker type.

        Args:
            enum state: The state to set the current tracker to.
        """
        self.trackState = state

    def get_track_center(self):
        """ Getter method for the current track centre.

        Returns:
            list: Current centre position of the tracker [X, Y].
        """
        # Find the centre of the track position [X + W/2, Y + H/2]
        return [int(self.trackPosition[0] + self.trackPosition[2]/2),
                int(self.trackPosition[1] + self.trackPosition[3]/2)]

    def get_track_range(self):
        """ Getter method for the current track range.

        Returns:
            list: Current track range [X, Y, W, H].
        """
        return self.trackPosition

    def set_track_position(self, position):
        """ Settr method for the track position

        Args:
            position (list): Updated track position [X, Y, W, H]
        """

        # If previously active and update position is None, track was lost
        if(self.active_track() and position is None):
            self.lostTrack = True
        else:
            self.lostTrack = False
        
        if(position is None):
            # Clear the position and state of the tracker
            self.trackPosition = [position, position]
            self.stationaryFrames = 0
            self.set_state(basic_track_state.NO_ACTIVE_TRACK)
            return

        # If the tracker is active, check if it has moved between frames
        if(self.active_track()):
            diffSum = abs(position[0] - self.trackPosition[0]) + \
                        abs(position[1] - self.trackPosition[1])
            
            if(diffSum != 0):
                self.stationaryFrames = 0
            else:
                self.stationaryFrames += 1

            self.lastTimeUpdate = time.time()

        # Update the track position
        self.trackPosition = position
        
        # If stationary for 50 frames, consider it stationary
        if(self.stationaryFrames < 50):
            self.set_moving_track(True)
        else:
            self.stationaryFrames = 0
            self.set_moving_track(False)

    def update_basic_track(self, img, thresh, startPos, step):
        """ Update Basic tracker position.

        Args:
            img (numpy.ndarray): 3 by 2D array representing RGB image
            thresh (int): Threshold required for an edge between pixels
            startPos (int): Starting position for tracker search
            step (int): Step taken per one iteration

        Returns:
            list: Updated Basic Tracker position. None if no position is found.
        """
        # Convert the frame to grayscale and display grayscale frame
        gray_frame = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply canny edge detection, display edge detected frame
        cannyFrame = cv2.Canny(gray_frame, 20, 60)

        # Apply the Hough transform to the frame (finding prominent lines)
        hough_lines = cv2.HoughLinesP(cannyFrame,1,np.pi/180, 50, None, 50, 5)

        if hough_lines is None:
            return

        # Iterate over the lines, noting the frequency of rho
        lineAngles = dict()
        for i in range(len(hough_lines)):
            # Display the line in the hough frame
            line = hough_lines[i][0]

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

        for line in hough_lines:
            line = line[0]

            if(line[2] - line[0] == 0):
                continue

            rho = round(float((line[3] - line[1])/(line[2] - line[0])),1)

            # Ensure the line matches the most frequent angle
            if rho != max_freq_angle:
                continue

            maxY = max(line[1], line[3])
            minY = min(line[1], line[3])
            # Set to max line if greater Y than current maxline
            if (None in max_line) or (max_line[1] < maxY):
                max_line = line

            # Set to min line if smaller Y than current minline
            if (None in min_line) or (minY < min_line[1]):
                min_line = line

        if (None in max_line) or (None in min_line):
            return

        # Create line functions that represent the top and bottom pipette edges
        mu_grad = max_freq_angle
        max_offset = max_line[3] - max_line[2] * mu_grad
        min_offset = min_line[3] - min_line[2] * mu_grad
        mu_offset = int((max_offset + min_offset)/2)

        self.mu_grad = mu_grad
        self.mu_offset = mu_offset

        # Iterate horizontally to find the pipette tip
        tipX = None
        x = startPos
        COMP_DIST = 5
        maxThresh = -1

        while ((x + COMP_DIST) > 0) and ((x + COMP_DIST) < img.shape[1]):
            x1 = x
            x2 = x + COMP_DIST
            y1 = x1 * mu_grad + mu_offset
            y2 = x2 * mu_grad + mu_offset
            if (y1 < 0) or (img.shape[0] <= y1):
                x = x + step
                continue

            if (y2 < 0) or (img.shape[0] <= y2):
                x = x + step
                continue

            currentPixel = int(gray_frame[int(y1), x1])
            compPixel = int(gray_frame[int(y2), x2])
            
            # If the edge is sufficient, this is the pipette tip
            if(maxThresh < abs(currentPixel - compPixel)):
                tipX = int(x + COMP_DIST/2)
                maxThresh = abs(currentPixel - compPixel)

                if(thresh < maxThresh):
                    break
            x = x + step
        
        if(tipX is None):
            return 
        return [tipX, int(tipX * mu_grad + min_offset), 0, max_offset - min_offset]

    def kill_track(self):
        """ Kill the current track, clearning position and state.
        """
        self.trackPosition = [None, None]

    def moving_track(self):
        """ Check if the Basic Tracker position has moved in previous 50 frames.

        Returns:
            bool: True iff the tracker has moved in the preious 90 frames. 
            Otherwise, False.
        """
        return self.movingTrack

    def set_moving_track(self, state):
        """ Sets the moving track state

        Args:
            state (bool): State of the moving track parameter.
        """
        self.movingTrack = state

    def lost_track(self):
        """ Getter method for whether the track was lost during this frame.

        Returns:
            bool: True iff the tracker was lost during this frame. Otherwise
            False.
        """
        return self.lostTrack

    def change_in_position(self, pos):
        """ Getter method for the difference in position between the current
        tracker position and any point in 2D space.

        Args:
            pos (List): Coordinates in 2D space to compare the current positon
            to, formatted in (X, Y)

        Returns:
            int: Distance (in micron) between the the current tracker positon
            and the given point.
        """
        # Get the current track range
        currPos = self.get_track_range()
        for p in currPos:
            if(p is None):
                return

        # Compute the change in position    
        changeX = pow(abs((pos[0] + pos[2]/2) - (currPos[0] + currPos[2]/2)), 2)
        changeY = pow(abs((pos[1] + pos[3]/2) - (currPos[1] + currPos[3]/2)), 2)
        return sqrt(changeX + changeY)

    def toBasic(self):
        """ Converts the tracker to a "BasicTracker" form.

        Returns:
            BasicTracker: Copied instance of the tracker in the BasicTracker
            class to ensure contents are picklable.
        """
        return self

class MOSSETracker(basicTracker):
    """ MOSSE tracker used in accessing OpenCV MOSSE tracker library.

    Args:
        basicTracker (basicTracker): Inherets methods and members from the 
        Basic Tracker class
    """

    def __init__(self):
        """ Initialise MOSSE Tracker instance position and states
        """
        basicTracker.__init__(self)
        self.MOSSETrack = None

    def create_mosse_track(self, img, boundBox):
        """ Create a MOSSE Tracker on the given image over a given bounding
        box. 

        Args:
            img (numpy.ndarray): 3 by 2D array representing RGB image
            boundBox (List): Bounding box in 2D space of the form [X, Y, W, H]

        Returns:
            bool: True iff an instance of the MOSSE tracker was sucessfully
            initialised.
        """
        # Attempt to initialise MOSSE tracker
        for n in range(5):
            self.MOSSETrack = cv2.TrackerMOSSE_create()
            self.MOSSETrack.init(img, boundBox)
            success, cellBox = self.MOSSETrack.update(img)

            # If not successful, increase bound box size
            if(not success):
                self.MOSSETrack = None
                boundBox = (boundBox[0] - boundBox[2]*0.1, 
                            boundBox[1] - boundBox[3]*0.1,
                            boundBox[2] * 1.1,
                            boundBox[3] * 1.1)
                continue
            
            # Set the MOSSE tracker
            self.set_track_position(cellBox)
            # Return successful
            return True
            
        # Return unsuccessful
        return False

    def kill_track(self):
        """ Kill the current tracker, clearing position and state.
        """
        basicTracker.kill_track(self)
        self.MOSSETrack = None
        self.set_state(basic_track_state.NO_ACTIVE_TRACK)

    def update_mosse_track(self, img):
        """ Update the current MOSSE tracker for a new frame.

        Args:
            img (numpy.ndarray): 3 by 2D array representing RGB image

        Returns:
            bool: True iff the MOSSE tracker was successfully updated.
        """
        if(self.MOSSETrack is None):
            return
        # Attempt to update the tracker
        success, cellBox = self.MOSSETrack.update(img)
        # If not successful, clear position
        if(not success):
            self.set_track_position(None)
        else:
            self.set_track_position(cellBox)
        
        return success

    def active_mosse_track(self):
        """ Getter method for the state of a trackers MOSSE tracker.

        Returns:
            bool: True iff a MOSSE tracker is active. Otherwise, False.
        """
        if(self.MOSSETrack is not None):
            return True
        return False

    def toBasic(self):
        """ Converts the tracker to a "BasicTracker" form.

        Returns:
            BasicTracker: Copied instance of the tracker in the BasicTracker
            class to ensure contents are picklable.
        """
        # Create copy that is picklable and return basicTracker
        basic = copy.copy(self)
        basic.MOSSETrack = None
        basic.__class__ = basicTracker
        return basic

class systemInformation():

    def __init__(self):
        """ Initialise the state of system wide information.
        """
        # Initialise trackers to None
        self.pipetteTracker = None
        self.cellTracker = None
        self.aspTracker = None

    def set_trackers(self, pipetteTracker, cellTracker, aspTracker):
        """ Update the tracker instances for a new frame

        Args:
            pipetteTracker (basicTracker): New pipette tracker instance
            cellTracker (basicTracker): New cell tracker instance
            aspTracker (basicTracker): New aspiration tracker instance
        """
        self.pipetteTracker = pipetteTracker
        self.cellTracker = cellTracker
        self.aspTracker = aspTracker

    def observed_pipette_position(self, factor):
        """ Compute the observed pipette position for the given config.

        Returns:
            List: Position of the pipette tracker instance.
        """
        # If active tracker
        if(self.pipetteTracker.get_state()):
            # Convert the pixel position to micron position
            position = self.pipetteTracker.get_track_range()
            return [((position[0])/(factor)), 
                    ((position[1])/(factor)),
                    ((position[2])/(factor)), 
                    ((position[3])/(factor))]

    def observed_cell_position(self, pToM):
        """ Compute the observed cell position for a given config.

        Returns:
            List: Position of the cell tracker instance.
        """
        # If active tracker
        print("This is ptom %.2f"%(pToM))
        if(self.cellTracker.get_state()):
            # Convert the pixel position to micron position
            position = self.cellTracker.get_track_range()
            return [((position[0])/(pToM)), 
                    ((position[1])/(pToM)),
                    ((position[2])/(pToM)), 
                    ((position[3])/(pToM))]

    def observed_asp_position(self):
        """ Compute the observed aspiration position for a given config.

        Returns:
            List: Position of the aspiration tracker instance.
        """
        # If active tracker
        if(self.aspTracker.get_state()):
            # Convert the pixel position to micron position
            position = self.aspTracker.get_track_center()
            return [(abs(position[0]))/(PIXEL_PER_MICRON),
                    (abs(position[1]))/(PIXEL_PER_MICRON)]

    def desired_to_observed_pipette(self, desired, factor):
        """ Compute the difference between the observed and desired 
        pipette position resulting from user input.

        Args:
            desired (List): Desired position of the pipette

        Returns:
            int: Difference in position between the desired and observed 
            pipette position.
        """
        difference = []
        print("Factor is %.12f"%(factor))
        observed = self.observed_pipette_position(factor)

        # Compute the difference for all positions
        for n,point in enumerate(desired):
            print("Clicked %.2f, Observed %.2f"%(point, observed[n]))
            difference.append(point - observed[n])
        print("\n\n\n\n")
        return [(desired[0] + desired[2]/2) - (observed[0] + observed[2]/2),
                (desired[1] + desired[3]/2) - (observed[1] + observed[3]/2)]

    def cell_to_pipette(self):
        """ Compute the difference between the observed pipette and observed
        cell position.

        Returns:
            int: Difference in position between the observed pipette and 
            the observed cell position.
        """
        pipCenter = self.pipetteTracker.get_track_center()
        cellCenter = self.cellTracker.get_track_center()

        # Compute the difference in position
        difference =  sqrt(pow(pipCenter[0]-cellCenter[0],2) 
        + pow(pipCenter[1]-cellCenter[1],2))
        return (difference/PIXEL_PER_MICRON)

    def asp_to_pipette(self):
        """ Compute the difference between the observed pipette and observed
        aspirated cell position.

        Returns:
            int: Difference in position between the observed pipette and the
            observed aspiration cell position.
        """
        pipCenter = self.pipetteTracker.get_track_center()
        aspRange = self.aspTracker.get_track_range()

        # Compute the difference in positon
        difference =  abs(pipCenter[0] - aspRange[0])
        return difference/PIXEL_PER_MICRON

    def active_pipette(self):
        """ Getter method for the active state of the pipette tracker instance.

        Returns:
            enum: Return state of the pipette tracker.
        """
        return self.pipetteTracker.active_track()

    def active_cell(self):
        """ Getter method for the active state of the cell tracker instance.

        Returns:
            enum: Return state of the cell tracker.
        """
        return self.cellTracker.get_state()

    def active_asp_cell(self):
        """ Getter method for the active state of the aspirated cell tracker
        instance.

        Returns:
            enum: Return state of the aspirated cell tracker.
        """
        return self.aspTracker.get_state()
