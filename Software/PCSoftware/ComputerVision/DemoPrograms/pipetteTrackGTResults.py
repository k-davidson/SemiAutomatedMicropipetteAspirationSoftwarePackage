from videoMicropipetteIdentificationResults import *
import sys
from os import listdir

def generateResults(vid_filepath, gt_filepath, output_filepath, dist_thresh, edge_thresh):
    video_files = listdir(vid_filepath)
    gt_files = listdir(gt_filepath)

    header ="Video,# Errors,# Frames,Average Distance,Error run,Error run frame\n"
    
    # Open file for writing
    resultsFile = open(output_filepath, "w")
    resultsFile.write(header)

    for video in video_files:
        filename = video.split(".")

        if len(filename) != 2:
            continue

        is_vid = False

        is_vid = True if filename[1] == "mov" else is_vid
        is_vid = True if filename[1] == "mp4" else is_vid
        is_vid = True if filename[1] == "avi" else is_vid

        if not is_vid:
            continue

        print(filename[0])

        if filename[0] + "GT.txt" not in gt_files:
            continue

        print("Running accuracy test on video %s..."%(filename[0]))

        output = videoMicropipetteIdentification(vid_filepath + "/" + video, \
        gt_filepath + "/" + filename[0] + "GT.txt", \
        int(dist_thresh), int(edge_thresh), 0)

        if output is not None:
            resultsFile.write(output)

    resultsFile.close()




if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Generate results given foler of videos and folder of GT files. All files must use the naming convention:\n" + \
            "Video: <file_name>.mp4, Ground Truth: <file_name>GT.txt.\n" + \
                "Usage: python3 pipetteTrackGTResults <vid_dirpath> <gt_filepath> <output_dirpath> <dist_thresh> <edge_thresh>")
        exit(0)

    generateResults(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])