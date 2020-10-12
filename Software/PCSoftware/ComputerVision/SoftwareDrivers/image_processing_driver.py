import cv2
import numpy as np
from .ConfigFiles.config import *
from .ConfigFiles.settings import *
from systemInformation import *
import copy

class pipetteTracker(basicTracker):
    """ 
    Subclass of basicTracker containing logic relevant to tracking 
    of the micropipette tip.
    """
    def __init__(self):
        """ 
        Set the trackers initial state and members.
        """
        basicTracker.__init__(self)

    def update_track(self, img, sensitivity):
        """ 
        Update the Basic tracker to identify the objects position within the 
        incoming frame.

        Args:
            img (numpy.ndarray): Numpy array representing pixel values of the 
            new frame.
        """
        # Update position on basic tracker
        updatedPosition = self.update_basic_track(img, sensitivity, 20, 1)
        
        # Check if the track has moved significantly. If so, update position
        if updatedPosition is not None:
            self.set_state(basic_track_state.ACTIVE_TRACK)
            change_in_pos = self.change_in_position(updatedPosition)
            if change_in_pos is None or 20 < change_in_pos:
                    self.set_track_position(updatedPosition)


                

class cellTracker(MOSSETracker):
    """ 
    Subclass of MOSSETracker containing logic relevant to tracking of
    free moving cells. 
    """
    def __init__(self):
        """ 
        Set the trackers initial state and members.
        """
        MOSSETracker.__init__(self)

    def update_track(self, img):
        """ 
        Update the MOSSE tracker to identify the objects position within the 
        incoming frame.

        Args:
            img (numpy.ndarray): Numpy array representing pixel values of the 
            new frame.
        """
        self.update_mosse_track(img)
        

class aspTracker(MOSSETracker):
    """ 
    Subclass of MOSSETracker containing logic relevant to tracking of 
    aspirating and fully aspirated cells.
    """
    def __init__(self):
        """
        Set the trackers initial state and members.
        """
        MOSSETracker.__init__(self)

    def check_aspiration(self, pipRange, cellRange):
        """ 
        Check if a cell is being aspirated, given the position of the 
        Pipette tip and Cell trackers.

        Args:
            pipRange ([int[]]): [Range of the Pipette tip tracker]
            cellRange ([int[]]): [Range of the Cell tracker]

        Returns:
            [bool]: [True iff the Cell is aspirating. Otherwise, False]
        """
        
        # Ensure the Pipette tracker contains a valid position
        if None in pipRange:
            return False
        
        # Ensure the Cell tracker contains a valid position
        if None in cellRange:
            return False
    
        # Initialise Pipette and Cell positions
        pipX, pipY, pipW, pipH = pipRange
        cellX, cellY, cellW, cellH = cellRange

        
        # If the Cell tracker is overlapping with the pipette tracker
        if ((cellX - 5 <= pipX) 
        and (pipY < cellY + cellH) 
        and (pipY + pipH > cellY)):
            # Cell is being aspirated
            self.set_track_position(pipRange)
            # Update the tracker state
            self.set_state(asp_track_state.ACTIVE_ASP_TRACK)
            return True
        else:
            # Cell is not being aspirated
            return False

    def update_track(self, img, pipRange):
        """ 
        Update the MOSSE tracker to identify the objects position within the 
        incoming frame.

        Args:
            img (numpy.ndarray): Numpy array representing pixel values of the 
            new frame.
            pipRange (int[]): Current Pipette tracker range
        """
        # Check the current tracker state
        state = self.get_state()

        # If currently aspirating
        if state == asp_track_state.ACTIVE_ASP_TRACK:
            # Find first edge iterating from the Pipette tip to base
            backwardAspCheck = self.update_basic_track(img, 10, 
                int(pipRange[0] + pipRange[2]/2) - 10, -1)

            # Find first edge iterating from the Pipette base to tip
            forwardAspCheck = self.update_basic_track(img, 10, 5, 1)

            # If no edge was found in a direction: No cell was found
            if (backwardAspCheck is None) or (forwardAspCheck is None):
                self.set_track_position(pipRange)

            # If edges found were relatively close: Currently aspirating
            elif abs(forwardAspCheck[0] - backwardAspCheck[0]) < 20:
                self.set_track_position(backwardAspCheck)
            
            # If two distinct edges were found: The cell is fully aspirated
            else:
                # Initialise MOSSE tracker for the fully aspirated cell
                self.create_mosse_track(img, 
                (forwardAspCheck[0] - 20, pipRange[1],
                abs(pipRange[0] - forwardAspCheck[0] + 10), 
                abs(pipRange[3])))
                # Update the tracker state
                self.set_state(asp_track_state.ACTIVE_FULL_ASP_TRACK)

        # If fully aspirated
        if state == asp_track_state.ACTIVE_FULL_ASP_TRACK:
            self.update_mosse_track(img)

class trackerManager():
    """ 
    Manages all Pipette, Cell and Aspiration trackers. Called once per frame
    to update trackers and provide images to display to the user.
    """
    def __init__(self):
        """ 
        Initialise members of the trackerManager.
        """

        # Initialise the current image
        self.img = None

        # Initialise a Pipette, Cell and Aspiration tracker
        self.pipetteTracker = pipetteTracker()
        self.cellTracker = cellTracker()
        self.aspTracker = aspTracker()

    def update(self, img, sensitivity):
        """ 
        Update the current image and tracker states.

        Args:
            img (numpy.ndarray): Next frame to process.
            sensitivity (int): Threshold for the Pipette tracker
        """
        # Update the image member
        self.img = img
        
        # Update the trackers for the next frame
        self.update_asp_track()
        self.update_cell_track()
        self.update_pipette_track(sensitivity)
   
    def display_img(self):
        """ 
        Generates the image to display to the user.

        Returns:
            numpy.ndarray: The image to display to the user
        """

        # Create a copy of the current image
        displayImage = np.copy(self.img)

        # If a Pipette Tracker is active
        if self.pipetteTracker.active_track():
            # Add the Pipette tracker to the display image
            displayImage = self.display_track(displayImage, 
            self.pipetteTracker.get_track_range(), "Pipette", (128,128,255))

        # If a Cell Tracker is active
        if self.cellTracker.active_track():
            # Add the Cell tracker to the display image
            displayImage = self.display_track(displayImage, 
            self.cellTracker.get_track_range(), "Cell", (255,128,128))
        
        # If an Aspiration Tracker is active
        if self.aspTracker.active_track():
            # Add the Aspiration tracker to the display image
            displayImage = self.display_track(displayImage,
            self.aspTracker.get_track_range(), "Asp. Cell", (128, 255, 128))
        
        return displayImage


    def display_track(self, img, pos, name, colour):
        """ Append information about the specified track position to the image.

        Args:
            img (numpy.ndarray): Input image to append information to.

        Returns:
            numpy.ndarray: Output image, with tracker information appended.
        """
        # Get the current tracker position
        x, y, w, h = int(pos[0]), int(pos[1]), int(pos[2]), int(pos[3])

        # If this is a line track, ensure a minimum width/height
        if w == 0:
            w = 1

        if h == 0:
            h = 1

        # Draw the track on the image
        cv2.rectangle(img, (x,y), (x+w, y+h), colour, 3, 1)
        cv2.putText(img, name, (x+w,y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colour, 2)
        return img



    def init_cell_track_at(self,  pos):
        """ 
        Initialise a Cell track given the user input.

        Args:
            pos (int[]): Position to initialise the Cell tracker at.
        """
        # Get the desired track location.
        Y = min(int(pos[0][1]), int(pos[0][1] + pos[1][1]))
        X = min(int(pos[0][0]), int(pos[0][0] + pos[1][0]))
        H = int(abs(pos[1][1]))
        W = int(abs(pos[1][0]))

        # Ensure that trackbox has a minimum width and height
        if (not W) or (not H):
            return
        
        # Initialise a MOSSE track at the desired position
        if self.cellTracker.create_mosse_track(self.img, (X,Y,W,H)):
            self.cellTracker.set_state(basic_track_state.ACTIVE_TRACK)
 
    def update_pipette_track(self, sensitivity):
        """
        Update the Pipette tracker in the tracker manager.
        """
        # Only update the Pipette tracker if not currently aspirating
        if basic_track_state.NO_ACTIVE_TRACK == self.aspTracker.get_state():
            self.pipetteTracker.update_track(self.img, sensitivity)

    def update_asp_track(self):
        """
        Update the Asp tracker in the tracker manager.
        """
        # Get the current Asp tracker state
        trackState = self.aspTracker.get_state()

        # If no current Aspiration track
        if trackState == basic_track_state.NO_ACTIVE_TRACK:
            # Check for aspiration
            if self.aspTracker.check_aspiration( 
                self.pipetteTracker.get_track_range(),
                self.cellTracker.get_track_range()):
                self.cellTracker.kill_track()

        # If currently aspirating or fully aspirated
        if (trackState == asp_track_state.ACTIVE_ASP_TRACK) or (trackState == asp_track_state.ACTIVE_FULL_ASP_TRACK):
            # Update the Aspiration tracker
            self.aspTracker.update_track(self.img, self.pipetteTracker.get_track_range())

        # If the tracker has reached the left image border
        if ((trackState != basic_track_state.NO_ACTIVE_TRACK) and 
        (self.aspTracker.get_track_range()[0] < 10)):
            self.aspTracker.kill_track()

    def update_cell_track(self):
        """
        Update the Cell tracker in tracker manager.
        """
        # Check if there is an active Cell tracker
        if self.cellTracker.get_state() == basic_track_state.ACTIVE_TRACK:
            # Update Cell tracker
            self.cellTracker.update_track(self.img)

    def clear_frame_states(self):
        """
        Clear single frame states in each of the trackers
        """
        self.cellTracker.lostTrack = False
        self.pipetteTracker.lostTrack = False
        self.aspTracker.lostTrack = False

    def get_image_info(self):
        """
        Get image info to pass the the User Interface

        Returns:
            tuple: Tuple containing the current display image and basic forms
            of each of the trackers (as MOSSE Trackers are non-pickleable)
        """
        return (self.display_img(), 
        [self.pipetteTracker.toBasic(), self.cellTracker.toBasic(), 
        self.aspTracker.toBasic()])