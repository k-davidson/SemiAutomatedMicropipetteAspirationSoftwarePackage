import sys
import SoftwareDrivers.GUI_Driver as gui 
import site

class stepperWidgit(QWidget):
    def __init__(self, widget):
        QWidget.__init__(self)
        
        self.widget = widget

        self.layout = QGridLayout()
        self.layout.setVerticalSpacing(5)
        self.layout.setHorizontalSpacing(5)
 
        self.stepSizeLabel = QLabel("Step size:")
        self.layout.addWidget(self.stepSizeLabel, 1,0)

        self.stepSizeSpinbox = QDoubleSpinBox()
        self.layout.addWidget(self.stepSizeSpinbox, 1, 1)

        self.positionLabel = QLabel("Position:")
        self.layout.addWidget(self.positionLabel, 2,0)

        self.positionCommand = QDoubleSpinBox()
        self.layout.addWidget(self.positionCommand, 2, 1)

        self.synchronised = QRadioButton("Synchronised")
        self.layout.addWidget(self.synchronised, 3,0)

        self.configure = QPushButton("Configure")
        self.layout.addWidget(self.configure, 3, 1)
        self.configure.clicked.connect(self.configurationWindow)

        self.widget.setLayout(self.layout)
    
    def configurationWindow(self):
        print("yeet")

class StepperObj(QWidget):
    def __init__(self, n, names):
        if len(names) != n:
            return

        QWidget.__init__(self)
        self.initialise_container()

        for i in range(0,n):
            self.widgetContainer.append(QWidget())
            self.stepWidgets.append(stepperWidgit(self.widgetContainer[i]))
            self.tabWidget.addTab(self.widgetContainer[i], names[i])

        self.setFixedHeight(200)
        self.layout.addWidget(self.tabWidget)

    def initialise_container(self):
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.tabWidget = QTabWidget()

        self.widgetContainer = []
        self.stepWidgets = []

class mainWindow(QWidget):
    def __init__(self):
        self.layout = QGridLayout()
        self.mainWidget = QWidget()
        self.mainWidget.setLayout(self.layout)

    def addWidgets(self, widgets, pos, span):
        if len(widgets) != len(pos):
            return
        for n,a in enumerate(widgets):
            self.layout.addWidget(a, pos[n][0], pos[n][1], span[n][0], span[n][1])
    
    def show(self):
        self.mainWidget.show()

class sampleDisplay(QLabel):
    clicked = pyqtSignal()

    def __init__(self, pixmap):
        QLabel.__init__(self)
        self.Pixmap = pixmap
        self.focus = False

    def get_scale_pixmap(self, width):
        return self.Pixmap.scaledToWidth(width)

    def mousePressEvent(self, event):
        self.clicked.emit()



class imageGallery(QDialog):

    def __init__(self):
        QDialog.__init__(self)
        self.galleryBox = QGroupBox()
        self.gallerylayout = QGridLayout()
        self.galleryBox.setLayout(self.gallerylayout)

        self.focusBox = QGroupBox()
        self.focuslayout = QGridLayout()
        self.focusBox.setLayout(self.focuslayout)

        self.returnButton = QPushButton("Return to gallery")
        self.returnButton.clicked.connect(self.galleryDisplay)
        
        self.galleryScrollbar = QScrollArea()
        self.galleryScrollbar.setWidget(self.galleryBox)
        self.galleryScrollbar.setWidgetResizable(True)
        self.galleryScrollbar.setFixedWidth(550)
        self.galleryScrollbar.setFixedHeight(500)

        self.imageGrid = []
        
        self.containerLayout = QGridLayout()
        self.containerLayout.addWidget(self.galleryScrollbar,0,0,3,4)
        self.setLayout(self.containerLayout)

    def display_gallery_contents(self, imperrow = 3, width = 150):
        row = 0
        for n,image in enumerate(self.imageGrid):
            if not (n%imperrow):
                row = row + 1
            image.setPixmap(image.get_scale_pixmap(width))
            self.gallerylayout.addWidget(image,row, n%imperrow)
        
        self.galleryBox.setLayout(self.gallerylayout)    

    def add_image(self, pixmap):
        image = sampleDisplay(pixmap)
        image.clicked.connect(self.focusDisplay)
        self.imageGrid.append(image)
        
    def galleryDisplay(self, width = 150):
        self.returnButton.setParent(None)
        self.focusSample.setParent(None)
        self.galleryScrollbar.takeWidget()
        self.galleryScrollbar.setWidget(self.galleryBox)
        self.containerLayout.removeWidget(self.returnButton)
        self.display_gallery_contents()

    def focusDisplay(self, width=700):
        self.focusSample = self.sender()
        self.focusSample.setPixmap(self.focusSample.get_scale_pixmap(width))
        self.focuslayout.addWidget(self.focusSample,0,0)
        self.galleryScrollbar.takeWidget()
        self.galleryScrollbar.setWidget(self.focusBox)
        self.containerLayout.addWidget(self.returnButton, 0, 0, 1, 4)

def their_example():
    app = QApplication(sys.argv)
    contents = mainWindow()
    container1 = StepperObj(2, ['Stepper-X','Stepper-Y'])
    container2 = StepperObj(3, ['Stepper-X','Stepper-Y', 'Stepper-Z'])
    container3 = imageGallery()
    contents.addWidgets([container1, container2, container3], [(0,0), (1,0), (0,2)], [(1,2),(1,2),(2,3)])
    container3.add_image(QPixmap("/Users/kelbiedavidson/Desktop/sample1.jpg"))
    container3.add_image(QPixmap("/Users/kelbiedavidson/Desktop/sample2.jpg"))
    container3.add_image(QPixmap("/Users/kelbiedavidson/Desktop/sample3.jpg"))
    container3.display_gallery_contents()
    contents.show()
    sys.exit(app.exec_())





if __name__ == "__main__":
    their_example()