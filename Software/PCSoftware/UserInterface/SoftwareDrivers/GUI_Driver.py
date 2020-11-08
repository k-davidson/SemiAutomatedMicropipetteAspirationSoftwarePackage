import qtpy
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtSvg import *
from PyQt5.QtChart import *
import sys
import time
from math import *

from multiprocessing import *
import numpy as np

from SerialCommunication.SoftwareDrivers.gcode_driver import *
from systemInformation import *
from settings import *
from .ConfigFiles.config import *
from .ConfigFiles.settings import *

cellStationaryMutex = QMutex()
cellStationaryCondition = QWaitCondition()

approachCellMutex = QMutex()
approachCellCondition = QWaitCondition()

class updatedSpinboxWidget(QDoubleSpinBox):
    """ Improved spinbox to include update of state.

    Args:
        QDoubleSpinBox: Inheret from QDoubleSpinBox
    """
    def __init__(self, initValue):
        """ Initialise SpinBox with initial value and state.

        Args:
            initValue (int): Initial value of the spinbox
        """
        QDoubleSpinBox.__init__(self)
        self.updated = False
        self.currValue = initValue

    def getUpdated(self):
        """ Getter method for spinbox update.

        Returns:
            Bool: True iff spinbox has been updated. Otherwise, false.
        """
        if(self.value() != self.currValue):
            self.currValue = self.value()
            return True

        return False

class ControlWidget(QWidget):
    """ Low level control widget for value setting and communications.
    Inhereted behaviour for Stepper and Pressure positioning

    Args:
        QWidget: Inheret QWidget functionality.
    """
    def __init__(self, widget, idx):
        """ Initialise state and layout of the control widget.

        Args:
            idx (int): Value used as identifier for the widget
        """
        QWidget.__init__(self)

        self.widget = widget
        self.idx = idx

        # Create layout for control widget
        self.layout = QGridLayout()
        self.widget.setLayout(self.layout)

    def positioningControl(self, positionText, commandRange, \
    rateText, rateRange):
        """ Adding positioning control widget. 

        Args:
            positionText (String): Positioning command label text.
            commandRange (List): Max/Min value for positioning command.
            rateText (String): Rate command label text.
            rateRange (List): Max/Min value for the rate command.
        """

        self.synch_value = 0
        self.positionCommand = None

        # Initialise position command spinbox and labels
        if positionText and commandRange:
            self.positionLabel = QLabel(positionText)
            self.layout.addWidget(self.positionLabel, 1, 0)
            self.positionLabel.setSizePolicy(
                QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

            self.positionCommand = updatedSpinboxWidget(0)
            self.positionCommand.setSizePolicy(
                QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
            self.positionCommand.setRange(commandRange[0], commandRange[1])

            self.layout.addWidget(self.positionCommand, 1, 1)

        # Initialise rate command spinbox and labels
        if rateText and rateRange:
            self.rateLabel = QLabel(rateText)
            self.layout.addWidget(self.rateLabel, 3, 0)
            self.rateLabel.setSizePolicy(QSizePolicy(
                QSizePolicy.Fixed, QSizePolicy.Fixed))
            self.rateCommand = QDoubleSpinBox()
            self.rateCommand.setRange(rateRange[0], rateRange[1])
            self.rateCommand.setSizePolicy(QSizePolicy(
                QSizePolicy.Fixed, QSizePolicy.Fixed))
            self.layout.addWidget(self.rateCommand, 3, 1)

    def set_value(self, val):
        """ Setter method position command value

        Args:
            val (int): Value to set the position command to.
        """
        if self.positionCommand is not None:
            self.positionCommand.setValue(val)

    def get_value(self):
        """ Getter method for position command value

        Returns:
            int: Current value of the position command
        """
        return self.positionCommand.value()

    def increment_value(self, increment):
        """ Increment value of the position command

        Args:
            increment (int): Value to increment the position command by
        """
        if(self.positionCommand is not None):
            self.positionCommand.setValue(self.synch_value + increment)

    def synch_segment(self):
        """ Return of synch segment. Overriden by inhereted classes.
        """
        if(self.positionCommand is not None):
            self.synch_value = self.positionCommand.value()

class stepperWidget(ControlWidget):
    """ Stepper widget inhereting from the ControlWidget class. Provides
    functionality to set the position and rate of change of stepper motor.

    Args:
        ControlWidget: Inherets from the Control widget class
    """
    def __init__(self, widget, idx):
        """ Initialise Stepper widget states

        Args:
            widget (QWidget): QWidget instance to add contents for UI
            idx (int): Identifier for the widget instance
        """
        ControlWidget.__init__(self, widget, idx)

        # Add positioning command component
        self.positioningControl("Absolute Position:", [-6400, 6400], 
                                "Motion Rate (steps/sec):", [300, 30000])

    def synch_segment(self):
        """ Generate transmitable representation of Stepper widget state.

        Returns:
            String: Transmittable string representing widget state.
        """
        ControlWidget.synch_segment(self)
        # Only transmit if the position command has updated
        if(self.positionCommand.getUpdated()):
            # Transmit G00 command
            segment = GCodeSegment("G00", int((self.positionCommand.value()) 
            * STEPS_PER_MICRON * MICROSTEPPING), 
            rate=int(self.rateCommand.value()))

            # Select Tool. Set position.
            return [GCodeSegment("T", None, self.idx), segment]

class pumpWidget(ControlWidget):
    """ Pump widget inhereting from the ControlWidget class. Provides
    functionality to set the pressure of a syringe pump.

    Args:
        ControlWidget: Inheret from Control widget method.
    """
    def __init__(self, widget, idx):
        """ Initialise Pump widget states

        Args:
            widget (QWidget): QWidget instance to add contents for UI
            idx (int): Identifier for the widget instance
        """
        ControlWidget.__init__(self, widget, idx)

        # Add positioning control component
        self.positioningControl("Pressure (Pa):", [-100, 100], None, None)

    def synch_segment(self):
        """ Generate transmitable representation of Pump widget state.

        Returns:
            String: Transmittable string representing widget state.
        """
        ControlWidget.synch_segment(self)
        if(self.positionCommand.getUpdated()):
            # Calculate volume from desired pressure
            crossSection = pi * pow((COLUMN_DIAMETER/2), 2)
            deltaP = self.positionCommand.value()
            minDeltaV = MIN_VOLUME_INCREMENT*pow(10, -6)
            
            deltaV = (deltaP*crossSection)/(FLUID_DENSITY*GRAVITY)

            # Calculate iterations of the minimum pressure
            iterationsOfV = round(deltaV/minDeltaV)

            # Transmit tool select and pressure setting
            return [GCodeSegment("T", None, self.idx),
            SCodeSegment("S01", volume=iterationsOfV)]


class feedWidget(ControlWidget):
    """ Video feed widget to display incoming feed (30 FPS) and active
    trackers. Handles user input press events.

    Args:
        ControlWidget: Inherets basic functionality from the Control widget
    """

    # Cell or location selection signal, location and dimensions in frame
    select = pyqtSignal(bool, QPoint, QPoint, float, float)

    def __init__(self, widget, idx):
        """ Initialise video feed states and layout

        Args:
            widget (QWidget): QWidget instance to add contents for UI
            idx (int): Identifier for the widget instance
        """
        ControlWidget.__init__(self, widget, idx)
        
        # Create image feed label (to display images)
        self.imageFeedLabel = QLabel()
        self.layout.addWidget(self.imageFeedLabel, 1, 0, 4, 4)

        # Initialise scale
        self.scale = 1


        # Initialise image label via mouse inputs
        self.imageFeedLabel.mousePressEvent = self.pressEvent
        self.imageFeedLabel.mouseReleaseEvent = self.releaseEvent
        self.imageFeedLabel.mouseMoveEvent = self.moveEvent
        self.imageFeedLabel.setMouseTracking(True)
        self.imageFeedLabel.setSizePolicy(QSizePolicy.Minimum, \
            QSizePolicy.Minimum)
        self.cellPos = [QPoint(), QPoint()]
        self.config = [QLineF(), QLineF()]
        self.config[0].setP1(QPoint(10, 20))
        self.config[0].setP2(QPoint(20, 20))
        self.config[1].setP1(QPoint(10, 92))
        self.config[1].setP2(QPoint(20, 92))

        self.buttonFrame = QFrame()
        self.buttonLayout = QGridLayout(self.buttonFrame)

        self.configure = QCheckBox("Configure")
        self.buttonLayout.addWidget(self.configure, 0, 1)

        # Initialise sensitivity setting
        self.sensitivityLabel = QLabel("Edge Threshold:")
        self.buttonLayout.addWidget(self.sensitivityLabel, 0, 2)
        self.sensitivity = QSpinBox()
        self.buttonLayout.addWidget(self.sensitivity, 0, 3)

        self.LmouseHeld = False
        self.configLine = False

        self.mX = 0
        self.mY = 0

        self.time = time.time()

        # Add widgets in layout
        self.layout.addWidget(self.buttonFrame, 0, 0)

        # Create line for config
        self.micro_line = QLineF(
            self.config[0].center(), self.config[1].center())

        # Set pixels per micron
        PIXEL_PER_MICRON = self.getConfigLength()

    def get_sensitivity(self):
        """ Getter method for sensitivity current value

        Returns:
            int: Current sensitivity value
        """
        return int(self.sensitivity.value())

    def get_configure(self):
        """ Getter method for stae of configure checkbox

        Returns:
            bool: True iff the configure checkbox is checked. Otherwise, false.
        """
        return (self.configure.isChecked())

    def update_image(self, image, scale):
        """ Update image displayed in the video feed.

        Args:
            image (numpy.ndarray): 2D array representing Grayscale image
            scale (double): Scaling of the image from original to display
        """
        # Create pixmap given the image array at appropriate scaling
        height, width = image.shape[:2]
        self.scale = scale
        self.pix = cvtopixmap(image, [width, height], self.scale)
        PIXEL_PER_MICRON = self.getConfigLength()
        
        # Initialise painter font and colour
        painter = QPainter(self.pix)
        painter.setFont(QFont("Arial"))
        painter.setPen(QColor(255, 255, 255))
        
        # Set label height/width to fit pixmap
        self.imageFeedLabel.setFixedHeight(height * scale)
        self.imageFeedLabel.setFixedWidth(width * scale)

        # If not in configuration mode
        if(not self.get_configure()):
            painter.drawText(
                QPoint(10, self.pix.height()-10), 
                "Position [%.2f,%.2f]um, [%.2f,%.2f] pixels"
                % (self.mX/(self.scale*self.getConfigLength()),
                    self.mY /
                    (self.scale*self.getConfigLength()),
                    self.mX/(self.scale), self.mY/(self.scale)))
            painter.drawText(QPoint(10, self.pix.height()-25),
                             "FPS %d" % (round(1/(time.time()- self.time))))

        # If in configuration mode
        else:
            painter.drawText(QPoint(10, self.pix.height()-10),
                             "%.2f pixels/um" % (self.getConfigLength()))
            painter.drawText(QPoint(10, self.pix.height()-25),
                             "10um configuration")

        self.time = time.time()

        # If cell position exists, draw the cell
        if(self.cellPos[1].x() != -1 and self.cellPos[1].y() != -1):
            painter.setBrush(QColor(128, 128, 255, 128))
            painter.setPen(QColor(0, 0, 255))
            painter.drawRect(self.cellPos[0].x(), self.cellPos[0].y(),
                             self.cellPos[1].x(), self.cellPos[1].y())

        # If in configuration mode
        if(self.get_configure()):
            # Draw configuration line
            configX = self.config[0]
            configY = self.config[1]

            if(configX.p1().x() != -1 and configX.p2().x() != -1):
                painter.setBrush(QColor(128, 255, 128, 128))
                painter.setPen(QColor(0, 255, 0))
                painter.drawLine(configX.p1(), configX.p2())
            if(self.config[1].p1().x() != -1 and configY.p2().x() != -1):
                painter.setBrush(QColor(128, 255, 128, 128))
                painter.setPen(QColor(0, 255, 0))
                painter.drawLine(configY.p1(), configY.p2())
                painter.drawLine(configX.center(), configY.center())

        # Set the label pixmap to current pixmap
        self.imageFeedLabel.setPixmap(self.pix)

    def synch_segment(self):
        pass
    
    def pressEvent(self, event):
        """ Override of video feed press event interacting with image label

        Args:
            event (event): Event object generated during click callabck
        """
        # If not in configuration
        if(not self.get_configure()):
            # Left clicked, set cell position to clicked position
            if event.button() == Qt.LeftButton:
                self.cellPos[0].setX(event.pos().x())
                self.cellPos[0].setY(event.pos().y())
                self.cellPos[1].setX(-1)
                self.cellPos[1].setY(-1)
                self.LmouseHeld = True
        # In configuration
        else:
            # Clear config line
            if(self.configLine):
                self.micro_line = QLineF(
                    self.config[0].center(), self.config[1].center())
                self.configLine = False
                PIXEL_PER_MICRON = self.getConfigLength()

            # Left button, create config line
            elif event.button() == Qt.LeftButton:
                self.config[0].setP1(QPoint(event.pos().x(), event.pos().y()))
                self.config[0].setP2(QPoint(-1, -1))
                self.config[1].setP1(QPoint(-1, -1))
                self.config[1].setP2(QPoint(-1, -1))
                self.LmouseHeld = True

    def moveEvent(self, event):
        """ Override of video feed movement event interacting with image label

        Args:
            event (event): Event object generated during click callabck
        """

        # Set the motion points
        self.mX = event.x()
        self.mY = event.y()

        # If not in configuration
        if(not self.get_configure()):
            # If left mouse was pressed, not released
            if(self.LmouseHeld):
                # Set cell range
                self.cellPos[1].setX(event.pos().x() - self.cellPos[0].x())
                self.cellPos[1].setY(event.pos().y() - self.cellPos[0].y())
        
        # Otherwise, in configuration
        else:
            # If holding left mouse
            if(self.LmouseHeld):
                if(not self.configLine):
                    self.config[0].setP2(
                        QPoint(event.pos().x(), event.pos().y()))
            
            # If configuration line exists
            if self.configLine:
                
                # Display normal vector at distance to mouse
                norm = self.config[0].normalVector()
                self.micro_line = QLineF(
                    self.config[0].center(), self.config[1].center())

                # If change in X less than change in Y
                if(self.config[0].dx() < self.config[0].dy()):
                    distX = event.pos().x() - self.config[0].center().x()
                    if(not norm.dy() or not norm.dx()):
                        distY = 0
                    else:
                        distY = int((distX*norm.dy())/norm.dx())
                # If change in Y less than change in X
                else:
                    distY = event.pos().y() - self.config[0].center().y()
                    if(not norm.dx()):
                        distX = 0
                    else:
                        distX = int((distY*norm.dx())/(norm.dy()))

                # Set translation to the dimension parameters
                self.config[1] = self.config[0].translated(distX, distY)

    def releaseEvent(self, event):
        """ Override of video feed release event interacting with image label

        Args:
            event (event): Event object generated during click callabck
        """
        # If not in configuration
        if(not self.get_configure()):
            # If left mouse was released
            if event.button() == Qt.LeftButton:
                # Set cell position and dimensions
                self.cellPos[1].setX(event.pos().x() - self.cellPos[0].x())
                self.cellPos[1].setY(event.pos().y() - self.cellPos[0].y())
                self.LmouseHeld = False
                
                # Emit cell creation signal
                self.select.emit(True, self.cellPos[0], self.cellPos[1], \
                self.scale, self.getConfigLength())
                self.cellPos[1].setX(-1)
                self.cellPos[1].setY(-1)

        # In configuration
        else:
            if(event.button() == Qt.LeftButton and self.LmouseHeld):
                self.LmouseHeld = False
                self.configLine = True

    
    def getConfigLength(self):
        """ Getter method for current config line length

        Returns:
            double: Current config line length
        """
        return (self.micro_line.length())/(self.scale*10)


class resultsWidget(ControlWidget):
    """ Plotting of results of cell aspiration (aspiration and full aspiration)

    Args:
        ControlWidget: Inheret methods and members from ControlWidget
    """
    def __init__(self, widget, idx):
        """ Initialise result widget state.

        Args:
            widget (QWidget): Widget to add components to displayed in GUI
            idx (int): Integer index representing widget identifier
        """
        ControlWidget.__init__(self, widget, idx)

        # Initialise line series
        self.dataSeries = QLineSeries()

        # Initialise data number and data ranges
        self.numDataPoints = 0
        self.xRange = [0, 1]
        self.yRange = [0, 1]

        # Initialise offset
        self.offsetX = 0
        self.offsetY = 0

        # Initialise XAxis 
        self.xAxis = QValueAxis()
        self.xAxis.setTickCount(0.5)
        self.xAxis.setLabelFormat("%.2f")

        # Initialise YAxis 
        self.yAxis = QValueAxis()
        self.yAxis.setTickCount(0.5)
        self.yAxis.setLabelFormat("%.2f")

        # Initialise QChart
        self.dataModel = QChart()
        self.dataModel.setSizePolicy(QSizePolicy.Expanding, \
        QSizePolicy.Expanding)
        self.dataModel.legend().hide()
        self.dataModel.addSeries(self.dataSeries)

        # Conenct axis to chart
        self.dataModel.setAxisX(self.xAxis, self.dataSeries)
        self.dataModel.setAxisY(self.yAxis, self.dataSeries)

        # Add point (0,0)
        self.numDataPoints += 1
        self.dataSeries.append(0, 0)

        # Initialise chart view
        self.dataView = QChartView(self.dataModel)
        self.dataView.setMinimumHeight(400)
        self.dataView.setMinimumWidth(50)
        self.layout.addWidget(self.dataView)

        # Initialise primary/secondary axis titles
        self.primaryAxisTitle = "No axis title provided"
        self.secondaryAxisTitle = "No axis title provided"
        self.title = "No title provided"
        self.format_chart(self.title, [self.primaryAxisTitle, 
        self.secondaryAxisTitle])

        # Initialise alpha
        self.alpha = 0.0

        # Override secondary mouse event
        self.dataView.mousePressEvent = self.configure

    def format_chart(self, title, axistitles):
        """ Initialise format of chart

        Args:
            title (String): Title to use for chart
            axistitles (List): Primary and secondary chart axis titles
        """
        self.primaryAxisTitle = axistitles[0]
        self.secondaryAxisTitle = axistitles[1]
        self.dataModel.setTitle(title)
        
        self.title = title
        self.xAxis.setTitleText(self.primaryAxisTitle)
        self.yAxis.setTitleText(self.secondaryAxisTitle)

    def set_alpha(self, alpha):
        """ Setter method for the alpha value

        Args:
            alpha (int): Value to set for alpha
        """
        self.alpha = alpha

    def add_data(self, datapoint):
        """ Add datapoint to the data set of the chart series

        Args:
            datapoint (tuple): Tuple of (X,Y) values of datapoint
        """

        # Initialise "zero" value for offset (starting from 0)
        if(self.numDataPoints <= 1):
            self.offsetX = datapoint[0]
            self.offsetY = datapoint[1]

        # Calculate the relative positions
        relativeX = datapoint[0] - self.offsetX
        relativeY = datapoint[1] - self.offsetY

        # Ensure new datapoint within current data range
        if(relativeX < self.xRange[0]):
            self.xRange[0] = relativeX
        if(relativeX > self.xRange[1]):
            self.xRange[1] = relativeX

        if(relativeY < self.yRange[0]):
            self.yRange[0] = relativeY
        if(relativeY > self.yRange[1]):
            self.yRange[1] = relativeY

        # Update range
        self.dataModel.axisX().setRange(
            self.xRange[0] - 0.2, self.xRange[1] + 0.2)
        self.dataModel.axisY().setRange(
            self.yRange[0] - 0.2, self.yRange[1] + 0.2)

        # Replace the previous point in series
        if(self.numDataPoints > 1):
            latestDataPoint = self.dataSeries.at(self.numDataPoints - 1)

            if(abs(latestDataPoint.x() - relativeX) < self.alpha):
                if (latestDataPoint.y() < relativeY):
                    self.dataSeries.replace(
                        self.numDataPoints - 1, 
                        QPointF(latestDataPoint.x(), relativeY))
                return
        
        # Increment number of datapoints
        self.numDataPoints += 1
        self.dataSeries.append(relativeX, relativeY)

    def configure(self, event):
        """ Save content of chart to .PNG and .CSV file

        Args:
            event (Event): Event object containing event information
        """

        # If plot is right clicked
        if(event.button() == Qt.RightButton):
            # Get filename desired from the file dialog
            name = QFileDialog.getSaveFileName(self, 'Save Aspiration Charts')
            
            # If no name provided, return
            if(name == ""):
                return

            # Create image of chart and save
            chartImage = self.dataView.grab()
            chartImage.save(name[0] + ".png", "PNG")

            # Open CSV file
            csvFile = open(name[0] + ".txt", 'w')
            csvFile.write(self.primaryAxisTitle)

            # Add X values
            for point in range(self.numDataPoints):
                csvFile.write(",%.2f"%(self.dataSeries.at(point).x()))
            csvFile.write("\n")

            # Add Y values
            csvFile.write(self.secondaryAxisTitle)
            for point in range(self.numDataPoints):
                csvFile.write(",%.2f"%(self.dataSeries.at(point).y()))            

            csvFile.close()


class communicationWidget(ControlWidget):
    """ Communication display widget to display contents to the user 
    that is transmitted/recieved via serial.
    
    Args:
        ControlWidget: Inheret members and methods from ControlWidget
    """
    def __init__(self, widget, idx):
        """ Initialise communicationWidget members and states

        Args:
            widget (QWidget): QWidget displayed in the GUI
            idx (int): Index to be used as identifier for the widget
        """
        ControlWidget.__init__(self, widget, idx)

        # Initialise display widget
        self.commDisplay = QTextEdit()
        self.commDisplay.setReadOnly(True)
        self.commDisplay.setMinimumWidth(300)
        self.layout.addWidget(self.commDisplay)

    def append(self, commands):
        """ Append message to communication display

        Args:
            commands (String): Command to append to the communication display
        """
        self.commDisplay.append(commands)

class containerObj(QWidget):
    """ Container widget used in displaying object type

    Args:
        QWidget: Inherets from QWidget class
    """
    def __init__(self, n, names, parentIdx, childIdx, widgetType):
        """ Initialise container object contents and layout

        Args:
            n (List[int]): Number of widgets to be contained
            names (List[String]): List of Strings used as names in widgets tab
            parentIdx (List[int]): List of int identifiers for parent widgets
            childIdx (List[int]): List of int identifiers for children widgets
            widgetType (QWidget): Type of widget to be put in container
        """
        # Initialise QWidget
        QWidget.__init__(self)
        self.idx = parentIdx
        self.childIdx = childIdx

        # Inalise container
        self.initialise_container()

        # Iterate through widgets, appending to containers
        for i in range(0, n):
            self.widgetContainer.append(QWidget())
            self.widgets[childIdx[i]] = widgetType(
                self.widgetContainer[i], childIdx[i])
            self.tabWidget.addTab(self.widgetContainer[i], names[i])

    def initialise_container(self):
        """ Initialise layout of container. Add tab per widget.
        """
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.tabWidget = QTabWidget()

        self.widgetContainer = []
        self.widgets = {}

        self.layout.addWidget(self.tabWidget)

    def get_child_widget(self, idx):
        """ Getter method for the child widget within container.

        Args:
            idx (int): Index of the child widget to get

        Returns:
            QWidget: Child widget requested.
        """
        return self.widgets.get(idx)

    def get_idx(self):
        """ Get index of the container object.

        Returns:
            int: Container widget object index
        """
        return self.idx

    def get_container(self):
        """ Get container widget. A tab widget is used to to contain content.

        Returns:
            QTabWidget: Container widget
        """
        return self.tabWidget

    def synch_segment(self):
        """ Getter method for the synchronisation segments 

        Returns:
            List: List of G-Code/S-Code segments to transmit for 
            synchronisation.
        """
        sequence = []
        # Iterate over all children widgets
        for key, value in self.widgets.items():
            # Get individual synch segments
            seg = value.synch_segment()
            if seg:
                sequence = sequence + seg
        return sequence

class StepperObj(containerObj):
    """ Stepper widget container object, inhereting from basic container object.

    Args:
        containerObj: Inheret from container object.
    """
    def __init__(self, n, names, parentIdx, childIdx):
        """ Initialise container object contents and layout

        Args:
            n (List[int]): Number of widgets to be contained
            names (List[String]): List of Strings used as names in widgets tab
            parentIdx (List[int]): List of int identifiers for parent widgets
            childIdx (List[int]): List of int identifiers for children widgets
            widgetType (QWidget): Type of widget to be put in container
        """
        containerObj.__init__(self, n, names, parentIdx,
                              childIdx, stepperWidget)

class pumpObj(containerObj):
    """ Pump widget container object, inhereting from basic container object.

    Args:
        containerObj: Inheret from container object.
    """
    def __init__(self, n, names, parentIdx, childIdx):
        """ Initialise container object contents and layout

        Args:
            n (List[int]): Number of widgets to be contained
            names (List[String]): List of Strings used as names in widgets tab
            parentIdx (List[int]): List of int identifiers for parent widgets
            childIdx (List[int]): List of int identifiers for children widgets
            widgetType (QWidget): Type of widget to be put in container
        """
        containerObj.__init__(self, n, names, parentIdx, childIdx, pumpWidget)

    def increment_pressures(self, incrementVal, childIdx):
        """ Increment the pressure in a given child widget.

        Args:
            incrementVal (int): Value to increment the pressure widget by.
            childIdx (int): Index of the child widget to increment pressure.
        """
        for n, val in enumerate(incrementVal):
            self.widgets[childIdx[n]].increment_value(val)

class feedObj(containerObj):
    """ Feed widget container object, inhereting from basic container object.

    Args:
        containerObj: Inheret from container object.
    """
    def __init__(self, n, names, parentIdx, childIdx):
        """ Initialise container object contents and layout

        Args:
            n (List[int]): Number of widgets to be contained
            names (List[String]): List of Strings used as names in widgets tab
            parentIdx (List[int]): List of int identifiers for parent widgets
            childIdx (List[int]): List of int identifiers for children widgets
            widgetType (QWidget): Type of widget to be put in container
        """
        containerObj.__init__(self, n, names, parentIdx, childIdx, feedWidget)

    def update_feed(self, childIdx, img, scale):
        """ Update the image displayed in a child feed widget

        Args:
            childIdx (int): Index of child widget to update
            img (numpy.ndarray): 2D array representing grayscale image
            scale (double): Scale of image to display
        """
        self.widgets[childIdx].update_image(img, scale)

    def pixel_to_micron(self, childIdx):
        """ Conversion from pixel to micron distance for a given feed widget.

        Args:
            childIdx (int): Index of child widget

        Returns:
            double: Number of micron per pixel
        """
        return self.widgets[childIdx].getConfigLength()

class resultsObj(containerObj):
    """ Result widget container object, inhereting from basic container object.

    Args:
        containerObj: Inheret from container object.
    """
    def __init__(self, n, names, parentIdx, childIdx):
        """ Initialise container object contents and layout

        Args:
            n (List[int]): Number of widgets to be contained
            names (List[String]): List of Strings used as names in widgets tab
            parentIdx (List[int]): List of int identifiers for parent widgets
            childIdx (List[int]): List of int identifiers for children widgets
            widgetType (QWidget): Type of widget to be put in container
        """
        containerObj.__init__(self, n, names, parentIdx,
                              childIdx, resultsWidget)

class communicationObj(containerObj):
    """ Communication widget container object, inhereting from basic container 
    object.

    Args:
        containerObj: Inheret from container object.
    """
    def __init__(self, n, names, parentIdx, childIdx):
        """ Initialise container object contents and layout

        Args:
            n (List[int]): Number of widgets to be contained
            names (List[String]): List of Strings used as names in widgets tab
            parentIdx (List[int]): List of int identifiers for parent widgets
            childIdx (List[int]): List of int identifiers for children widgets
            widgetType (QWidget): Type of widget to be put in container
        """
        containerObj.__init__(self, n, names, parentIdx,
                              childIdx, communicationWidget)

class videoFeed(QThread):
    """ QThread to handle reqesting and distributing video frames.

    Args:
        QThread: Inheret behaviour from QThread class.
    """
    def __init__(self, pixQ, capSem, feedWidget, updateSystem):
        QThread.__init__(self)

        # Initialise variables and states
        self.pixQ = pixQ
        self.capSem = capSem
        self.feedWidget = feedWidget
        self.abort = False
        self.updateSystem = updateSystem

    def run(self):
        """ Processing loop for videoFeed thread. 
        """
        # Set initial time
        t = time.time()*1000
        
        # While not leaving thread
        while(not self.abort):
            # Wait for 40 ms between frame requests
            if(abs(time.time()*1000 - t) >= 40):
                t = time.time()*1000
                self.capSem.put((self.feedWidget.get_sensitivity()))
                while(1):
                    if(not self.pixQ.empty()):
                        img, trackers = self.pixQ.get()
                        self.updateSystem.emit(img, trackers[0], 
                        trackers[1], trackers[2])
                        break


def cvtopixmap(img, dim, scale):
    """ Convert numpy.ndarray to pixmap.

    Args:
        img (numpy.ndarray): 3 by 2D array representing image pixel intensities
        dim (List): Dimensions of original image [width, height]
        scale (double): Scaling factor of pixmap

    Returns:
        QPixmap: Pixmap version of the numpy.ndarray image
    """
    bperl = 3*dim[0]
    colorImage = QImage(img, dim[0], dim[1],
                        bperl, QImage.Format_RGB888).rgbSwapped()
    grayScaleImage = colorImage.convertToFormat(QImage.Format_Grayscale8)
    pixmap = QPixmap.fromImage(colorImage)
    pixmap = pixmap.scaledToWidth(scale*dim[0])
    pixmap = pixmap.scaledToHeight(scale*dim[1])
    return pixmap


class synchObj(QWidget):
    """[summary]

    Args:
        QWidget ([type]): [description]
    """
    def __init__(self, synchFunc, approachCellFunc, latchFunc, resetPFunc):
        QWidget.__init__(self)

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.container = QTabWidget()
        self.system1Tab = QWidget()
        self.container.addTab(self.system1Tab, "System 1 Control")

        self.synch = QPushButton("Synchronise", self)
        self.synch.clicked.connect(synchFunc)
        self.synch.setSizePolicy(QSizePolicy(
            QSizePolicy.Fixed, QSizePolicy.Fixed))

        self.approachCell = QPushButton("Approach Cell", self)
        self.approachCell.clicked.connect(approachCellFunc)

        self.latch = QPushButton("Aspirate Cell", self)
        self.latch.clicked.connect(latchFunc)

        self.resetPressure = QPushButton("Reset Pressure", self)
        self.resetPressure.clicked.connect(resetPFunc)

        self.layout.addWidget(self.synch, 0, 0)
        self.layout.addWidget(self.approachCell, 1, 0)
        self.layout.addWidget(self.latch, 2, 0)
        self.layout.addWidget(self.resetPressure, 3, 0)

        self.system1Tab.setLayout(self.layout)

    def get_container(self):
        return self.container


class AppView(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.layout = QGridLayout()
        self.layout.setSpacing(0)

        self.mainWidget = QWidget()

        self.feedContainer = None

        self.mainWidget.setLayout(self.layout)
        self.setCentralWidget(self.mainWidget)

    def add_widgets(self, widgets, pos, span):
        for n, a in enumerate(widgets):
            self.layout.addWidget(
                a, pos[n][0], pos[n][1], span[n][0], span[n][1])

    def set_feed_container(self, feedContainer):
        self.feedContainer = feedContainer

    def update_view(self, img, scale):
        self.feedContainer.update_feed(0, img, scale)


class AppController(QWidget):
    updateSystem = pyqtSignal(np.ndarray, basicTracker, basicTracker, basicTracker)
    approachCellSignal = pyqtSignal()
    controlSignal = pyqtSignal()

    def __init__(self, model, view, context):
        QWidget.__init__(self)

        self.systemInfo = systemInformation()

        self.initConfig = False

        self.originX = 0
        self.originXPixel = 0
        self.originY = 0
        self.originYPixel = 0

        self.model = model
        self.view = view
        self.threads = []
        self.pendingComms = False
        StepperContainer1 = StepperObj(
            2, ['Stepper-X', 'Stepper-Y'], "S0", [0, 1])
        PumpContainer1 = pumpObj(1, ['Syringe-1 Pump'], "P0", [0])
        SynchContainer1 = synchObj(self.synchronise_state,
                                   self.approachCellSignal.emit,
                                   self.controlSignal.emit,
                                   self.reset_pressure)
        CommunicationContainer1 = communicationObj(1, ['Serial Communication Transcript'],
                                                   "C0", [0])

        FeedContainer1 = feedObj(1, ['Microscope-1'], "M0", [0])
        FeedContainer1.get_child_widget(0).select.connect(self.cellSelection)

        ResultContainer1 = resultsObj(
            2, ['Aspiration Results', 'Velocity Results'], ["R1", "R2"], [0, 1])

        self.scale = IMG_SCALE
        self.updateSystem.connect(self.update)
        VidFeed1 = videoFeed(context.pixQ, context.capSem,
                             FeedContainer1.get_child_widget(0), self.updateSystem)

        VidFeed1.start()
        self.threads.append(VidFeed1)

        self.view.set_feed_container(FeedContainer1)

        self.stepperWidgets = StepperContainer1
        self.pumpWidgets = PumpContainer1
        self.synchWidgets = SynchContainer1
        self.feedWidgets = FeedContainer1
        self.dataWidgets = ResultContainer1

        self.dataWidgets.get_child_widget(0).format_chart(
            "Pressure versus cell aspiration", 
            ["Aspiration distance (\u03BCm)", "Pressure (Pa)"])
        self.dataWidgets.get_child_widget(0).set_alpha(0.1)

        self.dataWidgets.get_child_widget(1).format_chart(
            "Full cell aspiration position versus time", 
            ["Time (seconds)", "Position (\u03BCm)"])
        self.dataWidgets.get_child_widget(1).set_alpha(0.25)

        

        self.controlThread = QThread()
        self.controlProcessor = controlWorker(
            context.sDisp, CommunicationContainer1.get_child_widget(0))
        self.controlProcessor.moveToThread(self.controlThread)
        self.controlProcessor.latchingSignal.connect(self.aspirate_cell)
        self.controlProcessor.approachingSignal.connect(self.approach_stepping)
        self.controlSignal.connect(self.controlProcessor.update_control)
        self.approachCellSignal.connect(self.controlProcessor.approach_cell)
        self.controlThread.start()

        self.view.add_widgets([StepperContainer1, PumpContainer1,
                               FeedContainer1, ResultContainer1,
                               SynchContainer1.get_container(),
                               CommunicationContainer1],
                              [(0, 0), (0, 2), (1, 0), (1, 3), (0, 4), [0, 6]],
                              [(1, 2), (1, 2), (1, 3), (1, 3), (1, 2), (3, 2)])
        self.model.add_widgets(
            [StepperContainer1, PumpContainer1, FeedContainer1])
        self.view.show()

        self.context = context

    def reset_pressure(self):
        self.pumpWidgets.get_child_widget(0).set_value(0)
        self.synchronise_state()

    def update(self, img, pipetteTracker, cellTracker, aspTracker):

        if(cellTracker.lost_track()):
            errorPopup("Cell tracker lost its target.")

        self.systemInfo.set_trackers(pipetteTracker, cellTracker, aspTracker)
        
        self.controlProcessor.systemUpdateSignal.emit(
            pipetteTracker, cellTracker, aspTracker, self.pendingComms)

        self.view.update_view(img, self.scale)
        self.update_data()

        if(self.context.get_comm_success() is not None):
            self.pendingComms = False

    def approach_stepping(self):
        approachCellMutex.lock()
        if(not self.systemInfo.active_cell()):
            errorPopup("No active Cell tracker.")
            approachCellMutex.unlock()
            return
        if(not self.systemInfo.active_pipette()):
            errorPopup("No active Pipette tracker.")
            approachCellMutex.unlock()
            return
        pToM = self.feedWidgets.pixel_to_micron(0)

        if(abs(self.systemInfo.cell_to_pipette()) < 2):
            approachCellMutex.unlock()
            return
        cellPos = self.systemInfo.observed_cell_position(pToM)

        diffPipette = self.systemInfo.desired_to_observed_pipette([cellPos[0] - cellPos[2],
                                           cellPos[1] + cellPos[3]/2,
                                           cellPos[0] - cellPos[2],
                                           cellPos[1] + cellPos[3]/2], pToM)
        print(cellPos)
        print(diffPipette)
        self.model.update_positions("S0", [0, 1], [diffPipette[0], diffPipette[1]])
        self.synchronise_state()
        approachCellMutex.unlock()

    def aspirate_cell(self):
        cellStationaryMutex.lock()
        if((self.systemInfo.cellTracker.active_track())):
            if (2 < self.systemInfo.cell_to_pipette()):
                errorPopup("Cell must be closer to aspirate." +
                           "Position the pipette within 2um of the cell.")
                cellStationaryMutex.unlock()
                return
        elif(not self.systemInfo.active_asp_cell()):
            errorPopup("No active Cell tracker to aspirate")
            cellStationaryMutex.unlock()
            return

        self.pumpWidgets.increment_pressures([-2], [0])
        self.synchronise_state()

        cellStationaryMutex.unlock()

    def synchronise_state(self):
        synchSequence = self.model.synchWidgets()
        if(not synchSequence.isEmpty()):
            self.context.sOut.put(synchSequence)
            self.pendingComms = True
        else:
            errorPopup("No change in position/pressure state!\n")

    def terminate_threads(self):
        for t in self.threads:
            t.abort = True
            t.wait()

    def cellSelection(self, cell, point, dim, scale, config):
        pixelXPosition = point.x()/scale
        pixelYPosition = point.y()/scale

        pixelXDim = dim.x()/scale
        pixelYDim = dim.y()/scale

        trueXPosition = (pixelXPosition)/(config)
        trueYPosition = (pixelYPosition)/(config)


        if((not pixelXDim) and (not pixelYDim)):
            diff = self.systemInfo.desired_to_observed_pipette([trueXPosition, trueYPosition,
                                               0, 0], config)
            for n,i in enumerate(diff):
                self.model.update_positions("S0", [0, 1], [diff[0], diff[1]])

        else:
            self.context.sDisp.put("Initialise Cell at [%d,%d] to [%d, %d] pixels"
                                   % (pixelXPosition, pixelYPosition,
                                       pixelXPosition, pixelYDim))

            self.context.posQ.put((cell, [(pixelXPosition, pixelYPosition),
                                          (pixelXDim, pixelYDim)]))

    def update_data(self):
        aspCellState = self.systemInfo.active_asp_cell()

        if(aspCellState == basic_track_state.NO_ACTIVE_TRACK):
            return

        if(aspCellState == asp_track_state.ACTIVE_ASP_TRACK):
            dataWidget = self.dataWidgets.get_child_widget(0)
        elif(aspCellState == asp_track_state.ACTIVE_FULL_ASP_TRACK):
            dataWidget = self.dataWidgets.get_child_widget(1)

        aspCellPosition = self.systemInfo.asp_to_pipette()

        if(aspCellPosition is None):
            return

        pressureWidget = self.pumpWidgets.get_child_widget(0)
        if(aspCellState == asp_track_state.ACTIVE_ASP_TRACK):
            dataWidget.add_data(
                [abs(pressureWidget.get_value()), aspCellPosition])
        else:
            # Change this to be dependent in the change in postiion (velocity)
            dataWidget.add_data(
                [time.time(), aspCellPosition])


class controlWorker(QObject):
    latchingSignal = pyqtSignal()
    approachingSignal = pyqtSignal()
    systemUpdateSignal = pyqtSignal(basicTracker, basicTracker, basicTracker, bool)

    def __init__(self, sDispQueue, commWidget):
        QObject.__init__(self)
        self.systemInfo = None
        self.systemUpdateSignal.connect(self.update_system_info)
        self.waitingCellStationary = False
        self.waitingPipStationary = False

        self.cellTracker = None
        self.pipetteTracker = None
        self.aspTracker = None

        self.sDispQueue = sDispQueue
        self.commWidget = commWidget

    def approach_cell(self):
        global approachCellCondition
        global approachCellMutex

        for i in range(10):
            self.approachingSignal.emit()
            if(not self.cellTracker.active_track() and not self.aspTracker.active_track()):
                return
            approachCellMutex.lock()
            self.waitingPipStationary = True
            approachCellCondition.wait(approachCellMutex)
            self.waitingPipStationary = False
            approachCellMutex.unlock()

    def update_control(self):
        global cellStationaryCondition
        global cellStationaryMutex

        for i in range(10):
            self.latchingSignal.emit()

            if((i != 0) and (not self.pipetteTracker.active_track() or
                             not (self.aspTracker.active_track()
                                  or self.cellTracker.active_track()))):
                return

            if(self.cellTracker.active_track()):
                cellPos = self.cellTracker.get_track_center()
                pipPos = self.pipetteTracker.get_track_center()

                distance = sqrt(pow(pipPos[0] - cellPos[0], 2) 
                            + pow(pipPos[1] - cellPos[1], 2))/(PIXEL_PER_MICRON)

                if(distance > 2):
                    return

            elif(not self.aspTracker.active_track()):
                return

            cellStationaryMutex.lock()
            self.waitingCellStationary = True
            cellStationaryCondition.wait(cellStationaryMutex)
            cellStationaryCondition = QWaitCondition()
            self.waitingCellStationary = False
            cellStationaryMutex.unlock()


    def update_system_info(self, pipetteTracker, cellTracker, aspTracker, pendingComms):
        global cellStationaryCondition
        self.cellTracker = cellTracker
        self.pipetteTracker = pipetteTracker
        self.aspTracker = aspTracker

        cellMoving = False
        aspMoving = False

        if(not pendingComms):

            if(self.cellTracker.active_track() and
            self.cellTracker.moving_track()):
                cellMoving = True
                

            if (self.aspTracker.active_track() and 
            self.aspTracker.moving_track()):
                aspMoving = True
            
            if(self.waitingCellStationary and not aspMoving and not cellMoving):
                cellStationaryCondition.wakeAll()

            if(self.waitingPipStationary and
            not pipetteTracker.moving_track()):
                approachCellCondition.wakeAll()

        if(not self.sDispQueue.empty()):
            self.commWidget.append(self.sDispQueue.get())


class AppModel(object):
    def __init__(self):
        self.idx = {}

    def add_widgets(self, widgets):
        for a in widgets:
            self.idx[a.get_idx()] = a

    def synchWidgets(self):
        sequence = []
        for key, value in self.idx.items():
            sequence = sequence + (value.synch_segment())

        return codeSequence(sequence)

    def update_positions(self, containerID, widgetIDList, posList):
        widget = self.idx[containerID]

        for n, wID in enumerate(widgetIDList):
            widget.get_child_widget(wID).increment_value(posList[n])


class Application(QApplication):
    def __init__(self, context):
        super(Application, self).__init__([])
        self.context = context

        self.model = AppModel()
        self.view = AppView()
        self.controller = AppController(self.model, self.view, context)

    def end_program(self):
        self.controller.terminate_threads()
        self.context.end_program()
        exit(0)


def guiManagement(context):
    app = Application(context)
    app.aboutToQuit.connect(app.end_program)
    app.setStyleSheet(styleSheet.toString())
    sys.exit(app.exec_())

def errorPopup(msg):
    error = QMessageBox()
    error.setWindowTitle("An error occured")
    error.setText("Uh oh...")
    error.setStandardButtons(QMessageBox.Ok)
    error.setInformativeText(msg)

    x = error.exec_()