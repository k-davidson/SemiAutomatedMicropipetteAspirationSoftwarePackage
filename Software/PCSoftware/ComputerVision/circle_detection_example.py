import SoftwareDrivers.image_processing_driver as imd 

def circle_detection_example():
    #cam = imd.cv2.VideoCapture(0)
    img = imd.open_image('sample1.jpg')
    
    currArea = imd.sampleArea(0, [0,0],[10,10], img)
    image = currArea.display_cell(indexList= [0,1,2,3,4,5])
    print(repr(currArea))

    #return_value, image = cam.read()


if __name__ == "__main__":
    circle_detection_example()