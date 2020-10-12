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
    global frame_count, gt, CLICKED
    
    gt = open(gt_filepath, "w")
    cap = cv2.VideoCapture(video_filepath)
    skip_frames = 1

    while(1):
        if(frame_count + 1 == cap.get(cv2.CAP_PROP_FRAME_COUNT)):
            print("Last frame of video. Press the 'Q' key to exit.")
        else:
            for i in range(skip_frames):
                if(frame_count + 1 == cap.get(cv2.CAP_PROP_FRAME_COUNT)):
                    print("Less than %d frames remain. Press the 'Q' key to exit."%(skip_frames))
                    break
                ret, frame = cap.read()
                frame_count += 1
            CLICKED = False

        title = "Video %s, Frame %d"%(video_filepath.split("/")[-1], frame_count)
        window = cv2.namedWindow(title)
        cv2.setMouseCallback(title, set_gt_pos)

        height = np.size(frame, 0)

        cv2.putText(frame, "Press <Space> to view the next frame", 
        (5, height - 25), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, [255,255,255])
        cv2.putText(frame, "Press 'Q' to exit the video", 
        (5, height - 10), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, [255,255,255])
        cv2.putText(frame, "Press 'S' to skip 10 frames", 
        (5, height - 40), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, [255,255,255])

        cv2.imshow(title, frame)
        
        keyPressed = cv2.waitKey(0)

        cv2.destroyAllWindows()

        if((ord('q') == keyPressed) or (ord('Q') == keyPressed)):
            gt.write("%d,%d,%d\n"%(latest_x, latest_y, cap.get(cv2.CAP_PROP_FRAME_COUNT)))
            gt.close()
            exit(0)

        if((ord('s') == keyPressed) or (ord('S') == keyPressed)):
            skip_frames = 10
        else:
            skip_frames = 1

    gt.write("%d,%d,%d\n"%(latest_x, latest_y, cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    gt.close()

def set_gt_pos(event, x, y, flags, param):
    global gt, CLICKED, frame_count, latest_x, latest_y

    if(gt is None):
        return


    if event == cv2.EVENT_LBUTTONDOWN:
        if(CLICKED):
            print("Ground truth already created for this frame. Press the <Space> key to continue to the next frame.")
            return

        print("Written ground truth position (%d %d) for frame %d"%(x,y, frame_count))
        latest_x = x
        latest_y = y
        gt.write("%d,%d,%d\n"%(x, y, frame_count))

        CLICKED = True


if __name__ == "__main__":
    if (len(sys.argv) != 3) or (sys.argv[1] == "help"):
        print("\nThis program provides a method for assisting in GT production; " +
        "Left click on the pipette tip to generate a ground truth for this frame. Only left click for a frame in the tip moves signficantly\n" +
        "Program usage: python videoMicropipetteIdentification.py <vid_filepath> <GT_output_filepath>\n")
    else:
        gt_helper(sys.argv[1], sys.argv[2])