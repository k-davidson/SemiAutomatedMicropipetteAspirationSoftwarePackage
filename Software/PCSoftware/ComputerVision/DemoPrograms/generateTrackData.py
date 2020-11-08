from videoMicropipetteIdentificationResults import *
import sys

def generateResults(video_filepath, output_filepath, edge_thresh, watch):
    # Open output file
    output = open(output_filepath, "w")

    # Initialise frame count
    frame_count = 0

    edge_thresh = int(edge_thresh)
    watch = int(watch)

    mupipX1 = 0
    mupipX2 = 0

    mupipY1 = 0
    mupipY2 = 0

    output.write("XPosition,YPosition,Width,Height\n")

    # Create a and read from a capture of the video file via OpenCV
    cap = cv2.VideoCapture(video_filepath)

    # Iterate over frames in the provided video
    while(frame_count < cap.get(cv2.CAP_PROP_FRAME_COUNT)):
        ret, frame = cap.read()
        frame_count += 1

        tempX1, tempY1, tempX2, tempY2 = \
            find_pipette_tip(frame, edge_thresh)

        if (mupipX1 is None) and (tempX1 is not None):
            mupipX1 = tempX1
        
        if (mupipX2 is None) and (tempX2 is not None):
            mupipX2 = tempX2
        
        if (mupipY1 is None) and (tempY1 is not None):
            mupipY1 = tempY1

        if (mupipY2 is None) and (tempY2 is not None):
            mupipY2 = tempY2

        # If new point found, update
        if (tempX1 is not None):
            mupipX1 = tempX1

        if (tempX2 is not None):
            mupipX2 = tempX2

        if (tempY1 is not None):
            mupipY1 = tempY1

        if (tempY2 is not None):
            mupipY2 = tempY2

        if not (frame_count % 10):
            pos = "%d,%d,%d,%d\n"%((mupipX1 + mupipX2)/2, (mupipY1 + mupipY2)/2, abs(mupipX1 - mupipX2), abs(mupipY1 - mupipY2))
            output.write(pos)

        if not ((frame_count) % (int(0.01 * cap.get(cv2.CAP_PROP_FRAME_COUNT)))):
            print("@ Frame %d of %d (%.2f %% complete)"%(frame_count, cap.get(cv2.CAP_PROP_FRAME_COUNT), int(100*frame_count/cap.get(cv2.CAP_PROP_FRAME_COUNT))))

        if watch:
            cv2.line(frame, (mupipX1, mupipY1), (mupipX2, mupipY2), \
                    (255,128,128), 2)

            if(wait_frame(frame, "Video %s raw frame - Frame:%d"
                %(video_filepath.split("/")[-1], frame_count), delay = 30)):
                exit(0)

    print("Completed position data generation. Quitting program.")

if __name__ == "__main__":
    if (len(sys.argv) != 5) or (sys.argv[1] == "help"):
        print("\nThis program provides performance statistics of " + \
            "pipette tip identification by comparing the approximated " + \
                "position with the ground truth provided.\n Program usage:" + \
                    "python videoMicropipetteIdentification.py " + \
                        "<video_filepath> <output_filepath> " + \
                            "<edge_thresh> <watch_track>\n")
        exit(0)
    else:
        generateResults(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])

