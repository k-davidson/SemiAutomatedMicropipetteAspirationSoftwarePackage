import sys
import cv2
import numpy as np

frame_count = 0
gt = None
CLICKED = False
FONT_SIZE = 0.4 # Font size used in displaying text

latest_x = 0
latest_y = 0


def gt_helper(video_filepath, gt_filepath):
    """ Helper function to generate Ground truth files for pipette positions

    Args:
        video_filepath (String): Absolute filepath for video file
        gt_filepath (String): Absolute ground truth filepath
    """
    global frame_count, gt, CLICKED
    
    # Open file for writing
    gt = open(gt_filepath, "w")
    # Load video file
    cap = cv2.VideoCapture(video_filepath)
    skip_frames = 1
    prevFrame = None

    while(1):
        # Iterate over frames until last frame
        if(frame_count + 1 == cap.get(cv2.CAP_PROP_FRAME_COUNT)):
            print("Last frame of video. Press the 'Q' key to exit.")
        else:
            # For number of skip frames, sko[]
            for i in range(skip_frames):
                if(frame_count + 1 == cap.get(cv2.CAP_PROP_FRAME_COUNT)):
                    print("Less than %d frames remain."%(skip_frames) + \
                    "Press the 'Q' key to exit."%(skip_frames))
                    break
                ret, frame = cap.read()
                frame_count += 1

        
        if frame is None:
            frame = prevFrame

        CLICKED = False

        # Create window for current frame
        title = "Video %s, Frame %d" \
            %(video_filepath.split("/")[-1], frame_count)
        window = cv2.namedWindow(title)
        cv2.setMouseCallback(title, set_gt_pos)

        prevFrame = frame

        height = np.size(frame, 0)

        # Add text to display on frame
        cv2.putText(frame, "Press <Space> to view the next frame", 
        (5, height - 25), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, [255,255,255])
        cv2.putText(frame, "Press 'Q' to exit the video", 
        (5, height - 10), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, [255,255,255])
        cv2.putText(frame, "Press 'S' to skip 10 frames", 
        (5, height - 40), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, [255,255,255])

        # Show frame and check if user pressed key
        cv2.imshow(title, frame)
        keyPressed = cv2.waitKey(0)
        cv2.destroyAllWindows()

        # If the 'Q' key was pressed
        if((ord('q') == keyPressed) or (ord('Q') == keyPressed)):
            # Write to end of frame count
            gt.write("%d,%d,%d\n"%(latest_x, latest_y, \
            cap.get(cv2.CAP_PROP_FRAME_COUNT)))
            gt.close()
            exit(0)

        # If the 'S' key was pressed
        if((ord('s') == keyPressed) or (ord('S') == keyPressed)):
            # Skip 10 frames
            skip_frames = 10
        else:
            skip_frames = 1

    # Write group truth for latest X/Y position
    gt.write("%d,%d,%d\n"%(latest_x, latest_y, \
        cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    gt.close()

def set_gt_pos(event, x, y, flags, param):
    """ Set GT Position handling click event

    Args:
        event (Event): Event information
        x (int): [description]
        y (int): [description]
    """
    global gt, CLICKED, frame_count, latest_x, latest_y

    # If no GT, return
    if(gt is None):
        return

    # If left button pressed
    if event == cv2.EVENT_LBUTTONDOWN:
        # If already clicked this frame
        if(CLICKED):
            print("Ground truth already created for this frame. " \
                + "Press the <Space> key to continue to the next frame.")
            return

        # Otherwise, add GT for frame
        print("Written ground truth position(%d %d)"%(x,y) + \
            "for frame %d"%(frame_count))
        latest_x = x
        latest_y = y
        gt.write("%d,%d,%d\n"%(x, y, frame_count))

        # Set flag
        CLICKED = True


if __name__ == "__main__":
    if (len(sys.argv) != 3) or (sys.argv[1] == "help"):
        print("\nThis program provides a method for assisting in" + \
        " GT production; Left click on the pipette tip to generate a ground" + \
        " truth for this frame. Only left click for a frame in the tip" + \
        " moves signficantly\n Program usage: python " + \
        "videoMicropipetteIdentification.py <vid_filepath> " + \
        "<GT_output_filepath>\n")
    else:
        gt_helper(sys.argv[1], sys.argv[2])