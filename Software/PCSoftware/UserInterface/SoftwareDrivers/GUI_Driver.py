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
import config
from UserInterface.SoftwareDrivers.GUI_config import *

import cProfile




cellStationaryMutex = QMutex()
cellStationaryCondition = QWaitCondition()

approachCellMutex = QMutex()
approachCellCondition = QWaitCondition()

class updatedSpinboxWidget(QDoubleSpinBox):
    def __init__(self, initValue):
        QDoubleSpinBox.__init__(self)
        self.updated = False
        self.currValue = initValue

    def getUpdated(self):
        if(self.value() != self.currValue):
            self.currValue = self.value()
            return True
        
        return False

class ControlWidget(QWidget):
    def __init__(self, widget, idx):
        QWidget.__init__(self)

        self.widget = widget
        self.idx = idx

        self.layout = QGridLayout()
        #self.layout.setVerticalSpacing(5)
        #self.layout.setHorizontalSpacing(5)
        
        self.layout.setRowStretch(0, 0)
        self.layout.setRowStretch(1, 0)
        self.layout.setRowStretch(2, 0)
        self.layout.setRowStretch(3, 0)
        self.layout.setRowStretch(4, 0)

        self.widget.setLayout(self.layout)
    
    def positioningControl(self):
        self.positionLabel = QLabel()
        self.layout.addWidget(self.positionLabel, 1,0)
        self.positionLabel.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

        self.positionCommand = updatedSpinboxWidget(0)
        self.positionCommand.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.layout.addWidget(self.positionCommand, 1, 1)

        self.rateLabel = QLabel()
        self.layout.addWidget(self.rateLabel, 3, 0)
        self.rateLabel.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.rateCommand = QDoubleSpinBox()
        self.rateCommand.setMinimum(1.0)
        self.rateCommand.setValue(10.0)
        self.rateCommand.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.layout.addWidget(self.rateCommand, 3, 1)


        self.positionLabel.setText("Absolute Position (um):")
        self.rateLabel.setText("Motion Rate (um/sec):")

    def feedControl(self):
        self.imageFeedLabel = QLabel()
        self.layout.addWidget(self.imageFeedLabel, 1, 0, 4, 4)
        #self.imageFeedLabel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        #self.imageFeedLabel.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        #self.imageFeedLabel.setScaledContents(False)
        #self.imageFeedLabel.setFixedWidth(480)
        #self.imageFeedLabel.setFixedHeight(9/16*480)

    def configurationWindow(self):
        print("yeet")

    def get_idx(self):
        return self.idx

    def synch_segment(self):
        pass

class stepperWidget(ControlWidget):
    def __init__(self, widget, idx):
        ControlWidget.__init__(self, widget, idx)
        self.positioningControl()
        
        self.rate = "G00"

        self.positionLabel.setText("Absolute Position:")

        self.position = 0
        self.dir = 1
        self.origin = 0

        self.positionCommand.setMinimum(-6400)
        self.positionCommand.setMaximum(6400)
        self.positionCommand.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

        #self.stepSizeLabel = QLabel()
        #self.layout.addWidget(self.stepSizeLabel, 2,0)

        #self.stepSizeSpinbox = QSpinBox()
        #self.layout.addWidget(self.stepSizeSpinbox, 2, 1)
        #self.stepSizeLabel.setText("Step size:")

    def setOrigin(self, origin):
        self.origin = origin

    def synch_segment(self):
        if(self.positionCommand.getUpdated()):
            print("Adding segment\n")
            self.rate = "G00"
            return [GCodeSegment("T",None,self.idx),GCodeSegment("G00", 
                    int(((self.positionCommand.value() - self.origin))
                    *config.FineMotionConfig['stepsPerMicron']
                    *config.FineMotionConfig['microStepping']), 
                    rate = int(self.rateCommand.value()))]
        return None

    def set_position(self, pos):
        self.positionCommand.setValue(pos)

class pumpWidget(ControlWidget):
    def __init__(self, widget, idx):
        ControlWidget.__init__(self, widget, idx)
        self.positioningControl()
        
        self.rate = "S01"
        self.dir = 0

        self.positionLabel.setText("Volume (mm):")

        self.positionCommand.setMinimum(-10)
        self.positionCommand.setMaximum(10)

    def increase_pressure(self, val):
        self.positionCommand.setValue(self.positionCommand.value() + val)

    def get_pressure(self):
        return self.positionCommand.value()
    
    def synch_segment(self):
        if(self.positionCommand.getUpdated()):
            print("Adding pressure segment\n")
            self.rate = "S01"
            return [GCodeSegment("T",None,self.idx),SCodeSegment(self.rate, volume = self.positionCommand.value())]

        return None

class feedWidget(ControlWidget, QLabel):
    select = pyqtSignal(bool,QPoint, QPoint, int, int)
    
    
    def __init__(self, widget, idx):
        ControlWidget.__init__(self, widget, idx)
        QLabel.__init__(self)
        self.feedControl()
        self.selBegin = QPoint()
        self.selEnd = QPoint()

        self.scale = 1

        self.sensitivityLabel = QLabel("Edge Threshold:")
        self.layout.addWidget(self.sensitivityLabel, 5, 0)
        self.sensitivity = QSpinBox()
        self.layout.addWidget(self.sensitivity, 5,1)

        self.imageFeedLabel.mousePressEvent = self.pressEvent
        self.imageFeedLabel.mouseReleaseEvent = self.releaseEvent
        self.imageFeedLabel.mouseMoveEvent = self.moveEvent
        self.imageFeedLabel.setMouseTracking(True)
        self.cellPos = [QPoint(),QPoint()]
        self.pipPos = [QPoint(),QPoint()]
        self.config = [QLineF(),QLineF()]
        self.config[0].setP1(QPoint(10,20))
        self.config[0].setP2(QPoint(20,20))
        self.config[1].setP1(QPoint(10,92))
        self.config[1].setP2(QPoint(20,92))

        self.buttonFrame = QFrame()
        self.buttonLayout = QGridLayout(self.buttonFrame)

        self.automate = QCheckBox("Automate")
        self.buttonLayout.addWidget(self.automate, 0, 0)
        self.automate.setChecked(True)

        self.configure = QCheckBox("Configure")
        self.buttonLayout.addWidget(self.configure, 0, 1)

        self.LmouseHeld = False
        self.RmouseHeld = False
        self.configLine = False

        self.mX = 0
        self.mY = 0

        self.time = time.time()

        self.layout.addWidget(self.buttonFrame, 0, 0)

        self.micoMeterLine = QLineF(self.config[0].center(), self.config[1].center())
    
    def get_automate(self):
        return (self.automate.isChecked())

    def get_sensitivity(self):
        return int(self.sensitivity.value())

    def get_configure(self):
        return (self.configure.isChecked())
            
    def update_image(self, image, scale):
        height, width = image.shape[:2]
        self.scale = scale
        self.pix = cvtopixmap(image, [width, height], self.scale, 1)
        painter = QPainter(self.pix)
        painter.setFont(QFont("Arial"))
        painter.setPen(QColor(255,255,255))
        if(not self.get_configure()):
            painter.drawText(QPoint(10, self.pix.height()-10), "Position [%.2f,%.2f]um, [%.2f,%.2f] pixels"
                                        %(self.mX/(self.scale*self.getConfigLength()*10),
                                            self.mY/(self.scale*self.getConfigLength()*10),
                                            self.mX/(self.scale), self.mY/(self.scale)))
            painter.drawText(QPoint(10, self.pix.height()-25), "FPS %d"%(round(1/(time.time()-self.time))))
        else:
            painter.drawText(QPoint(10, self.pix.height()-10), "%.2f pixels/um"%(self.getConfigLength()*10))
            painter.drawText(QPoint(10, self.pix.height()-25), "10um configuration")
        
        self.time = time.time()
        
        if(self.cellPos[1].x() != -1 and self.cellPos[1].y() != -1):
            painter.setBrush(QColor(128,128,255,128))
            painter.setPen(QColor(0,0,255))
            painter.drawRect(self.cellPos[0].x(),self.cellPos[0].y(),
                        self.cellPos[1].x(),self.cellPos[1].y())
        if(self.pipPos[1].x() != -1 and self.pipPos[1].y() != -1):
            painter.setBrush(QColor(255,128,128,128))
            painter.setPen(QColor(255,0,0))
            painter.drawRect(self.pipPos[0].x(),self.pipPos[0].y(),
                        self.pipPos[1].x(),self.pipPos[1].y())
        
        if(self.config[0].p1().x() != -1 and self.config[0].p2().x() != -1 and self.get_configure()):
            painter.setBrush(QColor(128,255,128,128))
            painter.setPen(QColor(0,255,0))
            painter.drawLine(self.config[0].p1(), self.config[0].p2())
        
        if(self.config[1].p1().x() != -1 and self.config[1].p2().x() != -1 and self.get_configure()):
            painter.setBrush(QColor(128,255,128,128))
            painter.setPen(QColor(0,255,0))
            painter.drawLine(self.config[1].p1(), self.config[1].p2())

            painter.drawLine(self.config[0].center(), self.config[1].center())
        
        self.imageFeedLabel.setPixmap(self.pix)
        #self.imageFeedLabel.setFixedWidth(pix.width())
        #self.imageFeedLabel.setFixedHeight(pix.height())

    def pressEvent(self, event):
        
        if(not self.get_configure()):
            if event.button() == Qt.LeftButton:
                self.cellPos[0].setX(event.pos().x())
                self.cellPos[0].setY(event.pos().y())
                self.cellPos[1].setX(-1)
                self.cellPos[1].setY(-1)
                self.LmouseHeld = True

            if event.button() == Qt.RightButton and not self.get_automate():
                self.pipPos[0].setX(event.pos().x())
                self.pipPos[0].setY(event.pos().y())
                self.pipPos[1].setX(-1)
                self.pipPos[1].setY(-1)
                self.RmouseHeld = True
        else:
            if(self.configLine):
                self.micoMeterLine = QLineF(self.config[0].center(), self.config[1].center())
                # Set pixels length here
                self.configLine = False
                config.FineMotionConfig['pixelPerMicron'] = self.getConfigLength()*10

            elif event.button() == Qt.LeftButton:
                self.config[0].setP1(QPoint(event.pos().x(), event.pos().y()))
                self.config[0].setP2(QPoint(-1, -1))
                self.config[1].setP1(QPoint(-1,-1))
                self.config[1].setP2(QPoint(-1,-1))
                self.LmouseHeld = True

    def getConfigLength(self):
        return (self.micoMeterLine.length())/(self.scale*10)
        
    def moveEvent(self, event):
        self.mX = event.x()
        self.mY = event.y()
        if(not self.get_configure()):
            if(self.LmouseHeld):
                self.cellPos[1].setX(event.pos().x() - self.cellPos[0].x())
                self.cellPos[1].setY(event.pos().y() - self.cellPos[0].y())

            if(self.RmouseHeld and not self.get_automate()):
                self.pipPos[1].setX(event.pos().x() - self.pipPos[0].x())
                self.pipPos[1].setY(event.pos().y() - self.pipPos[0].y())
        else:
            if(self.LmouseHeld):
                if(not self.configLine):
                    self.config[0].setP2(QPoint(event.pos().x(), event.pos().y()))
                
            if self.configLine:
                norm = self.config[0].normalVector()
                self.micoMeterLine = QLineF(self.config[0].center(), self.config[1].center())
                
                if(self.config[0].dx() < self.config[0].dy()):
                    distX = event.pos().x() - self.config[0].center().x()
                    if(not norm.dy() or not norm.dx()):
                        distY = 0
                    else:
                        distY = int((distX*norm.dy())/norm.dx())
                else:
                    distY = event.pos().y() - self.config[0].center().y()
                    if(not norm.dx()):
                        distX = 0
                    else:
                        distX = int((distY*norm.dx())/(norm.dy()))
                
                self.config[1] = self.config[0].translated(distX,distY)
                
    def releaseEvent(self, event):
        if(not self.get_configure()):
            if event.button() == Qt.LeftButton:
                self.cellPos[1].setX(event.pos().x() - self.cellPos[0].x())
                self.cellPos[1].setY(event.pos().y() - self.cellPos[0].y())
                self.LmouseHeld = False
                self.select.emit(True,self.cellPos[0], self.cellPos[1], self.scale, self.getConfigLength())
                self.cellPos[1].setX(-1)
                self.cellPos[1].setY(-1)
            
            if event.button() == Qt.RightButton and not self.get_automate():
                self.pipPos[1].setX(event.pos().x() - self.pipPos[0].x())
                self.pipPos[1].setY(event.pos().y() - self.pipPos[0].y())
                self.RmouseHeld = False
                self.select.emit(False, self.pipPos[0], self.pipPos[1], self.scale, self.getConfigLength()*10)
                self.pipPos[1].setX(-1)
                self.pipPos[1].setY(-1)

        else:
            if(event.button() == Qt.LeftButton and self.LmouseHeld):
                self.LmouseHeld = False
                self.configLine = True

class resultsWidget(ControlWidget):
    def __init__(self, widget, idx):
        ControlWidget.__init__(self, widget, idx)
        
        self.dataSeries = QLineSeries()

        self.numDataPoints = 0

        self.xRange = [0, 1]
        self.yRange = [0, 1]

        self.xAxis = QValueAxis()
        self.xAxis.setTickCount(0.5)
        self.xAxis.setLabelFormat("%.2f")

        self.yAxis = QValueAxis()
        self.yAxis.setTickCount(0.5)
        self.yAxis.setLabelFormat("%.2f")
    
        self.dataModel = QChart()
        self.dataModel.legend().hide()
        self.dataModel.addSeries(self.dataSeries)
        self.dataModel.setAxisX(self.xAxis, self.dataSeries)
        self.dataModel.setAxisY(self.yAxis, self.dataSeries)

        self.numDataPoints += 1
        self.dataSeries.append(0, 0)

        self.dataView = QChartView(self.dataModel)
        self.dataView.setMinimumHeight(300)
        self.dataView.setMinimumWidth(300)
        self.layout.addWidget(self.dataView)

        self.dataView.mousePressEvent= self.configure

    def add_data(self, datapoint):
        if(datapoint[0] < self.xRange[0]):
            self.xRange[0] = datapoint[0]
        if(datapoint[0] > self.xRange[1]):
            self.xRange[1] = datapoint[0]
        
        if(datapoint[1] < self.yRange[0]):
            self.yRange[0] = datapoint[1]
        if(datapoint[1] > self.yRange[1]):
            self.yRange[1] = datapoint[1]

        self.dataModel.axisX().setRange(self.xRange[0] - 0.2, self.xRange[1] + 0.2)
        self.dataModel.axisY().setRange(self.yRange[0] - 0.2, self.yRange[1] + 0.2)

        if(self.numDataPoints > 1):
            latestDataPoint = self.dataSeries.at(self.numDataPoints - 1)
            
            if((latestDataPoint.x() == datapoint[0])):
                if (latestDataPoint.y() < datapoint[1]):
                    self.dataSeries.replace(self.numDataPoints - 1, QPointF(datapoint[0], datapoint[1]))
                return
        
        self.numDataPoints += 1
        self.dataSeries.append(datapoint[0], datapoint[1])
    
    


        #print("Adding data point %.2f,%.2f\n"%(datapoint[0], datapoint[1]))
        
    def configure(self, event):
        if(event.button() == Qt.RightButton):
            name = QFileDialog.getSaveFileName(self, 'Save Aspiration Charts')
            chartImage = self.dataView.grab()
            chartImage.save(name[0] + ".png", "PNG")
            


class containerObj(QWidget):
    def __init__(self, n, names, parentIdx, childIdx):
        QWidget.__init__(self)
        self.idx = parentIdx
        self.childIdx = childIdx

        self.initialise_container()
    
    def initialise_container(self):
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.tabWidget = QTabWidget()

        self.widgetContainer = []
        self.widgets = {}

        self.layout.addWidget(self.tabWidget)

    def get_child_widget(self, idx):
        return self.widgets.get(idx)
    
    def get_idx(self):
        return self.idx

    def get_container(self):
        return self.tabWidget
    
    def synch_segment(self):
        sequence = []
        for key, value in self.widgets.items():
            if seg := value.synch_segment():
                sequence = sequence + seg
        return sequence

class StepperObj(containerObj):
    def __init__(self, n, names, parentIdx, childIdx):
        containerObj.__init__(self, n, names, parentIdx, childIdx)

        for i in range(0,n):
            self.widgetContainer.append(QWidget())
            self.widgets[childIdx[i]] = stepperWidget(self.widgetContainer[i], childIdx[i])
            self.tabWidget.addTab(self.widgetContainer[i], names[i])
    
    def update_origin(self, origins, childIdx):
        for n,idx in enumerate(childIdx):
            self.widgets[idx].setOrigin(origins[n])

class pumpObj(containerObj):
    def __init__(self, n, names, parentIdx, childIdx):
        containerObj.__init__(self, n, names, parentIdx, childIdx)

        for i in range(0,n):
            self.widgetContainer.append(QWidget())
            self.widgets[childIdx[i]] = pumpWidget(self.widgetContainer[i], childIdx[i])
            self.tabWidget.addTab(self.widgetContainer[i], names[i])

    def increment_pressures(self, incrementVal, childIdx):
        for n, val in enumerate(incrementVal):
            self.widgets[childIdx[n]].increase_pressure(val)

class feedObj(containerObj):
    def __init__(self, n, names, parentIdx, childIdx):
        containerObj.__init__(self, n, names, parentIdx, childIdx)

        for i in range(0,n):
            self.widgetContainer.append(QWidget())
            self.widgets[childIdx[i]] = feedWidget(self.widgetContainer[i], childIdx[i])
            self.tabWidget.addTab(self.widgetContainer[i], names[i])
    
    def update_feed(self, childIdx, img, scale):
        self.widgets[childIdx].update_image(img,scale)

    def pixel_to_micron(self, childIdx):
        return self.widgets[childIdx].getConfigLength()

class resultsObj(containerObj):
    def __init__(self, n, names, parentIdx, childIdx):
        containerObj.__init__(self, n, names, parentIdx, childIdx)

        for i in range(0,n):
            self.widgetContainer.append(QWidget())
            self.widgets[childIdx[i]] = resultsWidget(self.widgetContainer[i], childIdx[i])
            self.tabWidget.addTab(self.widgetContainer[i], names[i])

class videoFeed(QThread):
    def __init__(self, pixQ, capSem, feedWidget, scale, updateSystem):
        QThread.__init__(self)
        self.pixQ = pixQ
        self.capSem = capSem
        self.feedWidget = feedWidget
        self.scale = scale
        self.abort = False
        self.updateSystem = updateSystem
    
    def run(self):
        t = time.time()*1000
        while(not self.abort):
            if(abs(time.time()*1000 - t) >= 40):
                t = time.time()*1000
                self.capSem.put((self.feedWidget.get_automate(), self.feedWidget.get_sensitivity()))
                while(1):
                    if(not self.pixQ.empty()):
                        imageInfo = self.pixQ.get()
                        self.updateSystem.emit(imageInfo)
                        break

def cvtopixmap(img, dim, scale, flag):
    if flag:
        bperl = 3*dim[0]
        colorImage = QImage(img, dim[0], dim[1], bperl, QImage.Format_RGB888).rgbSwapped()
        grayScaleImage = colorImage.convertToFormat(QImage.Format_Grayscale8)
    pixmap = QPixmap.fromImage(colorImage)
    pixmap = pixmap.scaledToWidth(scale*dim[0])
    pixmap = pixmap.scaledToHeight(scale*dim[1])
    return pixmap

class synchObj(QWidget):
    def __init__(self, synchFunc, approachCellFunc, latchFunc):
        QWidget.__init__(self)
        
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.container = QGroupBox()

        self.synch = QPushButton("Synchronise", self)
        self.synch.clicked.connect(synchFunc)
        self.synch.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

        self.approachCell = QPushButton("Approach Cell", self)
        self.approachCell.clicked.connect(approachCellFunc)

        self.latch = QPushButton("Aspirate Cell", self)
        self.latch.clicked.connect(latchFunc)


        self.layout.addWidget(self.synch, 0, 0)
        self.layout.addWidget(self.approachCell, 0, 1)
        self.layout.addWidget(self.latch, 0 , 2)
        self.container.setLayout(self.layout)
    
    def get_container(self):
        return self.container

class AppView(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.layout = QGridLayout()
        self.layout.setRowStretch(0,0)
        self.layout.setRowStretch(1,1)

        self.window = QMainWindow()


        #self.window.setFixedWidth(1200)
        #self.window.setFixedHeight(600)

        #self.window.setFixedSize(1000,600)
        self.mainWidget = QWidget()

        self.feedContainer = None

        self.mainWidget.setLayout(self.layout)
        self.window.setCentralWidget(self.mainWidget)

    
    def add_widgets(self, widgets, pos, span):
        for n,a in enumerate(widgets):
             self.layout.addWidget(a, pos[n][0], pos[n][1], span[n][0], span[n][1])

    def show(self):
        self.window.show()

    def set_feed_container(self, feedContainer):
        self.feedContainer = feedContainer

    def update_view(self, img, scale):
        self.feedContainer.update_feed(0, img, scale)

class AppController(QWidget):
    updateSystem = pyqtSignal(config.imageInformation)
    approachCellSignal = pyqtSignal()
    controlSignal = pyqtSignal()
    
    def __init__(self, model, view, context):
        QWidget.__init__(self)

        self.systemInfo = config.systemInformation()
        self.systemInfo.set_pipette_range([0, 0, 0, 0])

        self.initConfig = False

        self.originX = 0
        self.originXPixel = 0
        self.originY = 0
        self.originYPixel = 0
        
        self.model = model
        self.view = view
        self.threads = []
        self.pendingComms = False
        StepperContainer1 = StepperObj(2, ['Stepper-X', 'Stepper-Y'], "S0", [0,1])
        PumpContainer1 = pumpObj(1, ['Syringe-1 Pump'],"P0",[0])
        SynchContainer1 = synchObj(self.synchronise_state, 
                                    self.approachCellSignal.emit,
                                    self.controlSignal.emit)

        FeedContainer1 = feedObj(1, ['Microscope-1'], "M0",[0])
        FeedContainer1.get_child_widget(0).select.connect(self.cellSelection)

        ResultContainer1 = resultsObj(2, ['Aspiration Results','Velocity Results'], ["R1","R2"], [0,1])

        self.scale = 0.5
        self.updateSystem.connect(self.update)
        VidFeed1 = videoFeed(context.pixQ, context.capSem, 
        FeedContainer1.get_child_widget(0), self.scale, self.updateSystem)

        '''
        DataFeed = dataFeed(
            [ResultContainer1.get_child_widget(0),
            ResultContainer1.get_child_widget(1)])
        '''

        VidFeed1.start()
        self.threads.append(VidFeed1)

        '''
        DataFeed.start()
        self.threads.append(DataFeed)

        '''

        self.view.set_feed_container(FeedContainer1)
        
        self.stepperWidgets = StepperContainer1
        self.pumpWidgets = PumpContainer1
        self.synchWidgets = SynchContainer1
        self.feedWidgets = FeedContainer1
        self.dataWidgets = ResultContainer1

        self.controlThread = QThread()
        self.controlProcessor = controlWorker()
        self.controlProcessor.moveToThread(self.controlThread)
        self.controlProcessor.latchingSignal.connect(self.aspirate_cell)
        self.controlProcessor.approachingSignal.connect(self.approach_stepping)
        self.controlSignal.connect(self.controlProcessor.update_control)
        self.approachCellSignal.connect(self.controlProcessor.approach_cell)
        self.controlThread.start()

        self.view.add_widgets([StepperContainer1, PumpContainer1, FeedContainer1, ResultContainer1,
                                SynchContainer1.get_container()], [(0,0), (0,2),(1,0),(1,3),(0,4)], [(1,2),(1,2),(1,3),(1,3),(1,2)])
        self.model.add_widgets([StepperContainer1, PumpContainer1, FeedContainer1])
        self.view.show()

        self.context = context
    
    def update(self, imageInfo):

        if(imageInfo.is_cell_lost()):
            errorPopup("Cell tracker lost its target.")

        #NOTE - USE *10 WHEN LOOKING AT PIXELS
        self.systemInfo.set_observed_info(imageInfo)
        self.controlProcessor.systemUpdateSignal.emit(imageInfo, self.pendingComms)
        #print("%s\n"%("Moving" if(imageInfo.moving_cell()) else "Stationary"))
        self.view.update_view(imageInfo.get_display_img(), self.scale)
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
        cellPos = self.systemInfo.observed_cell_position()
        print(cellPos)

        self.systemInfo.set_pipette_range([cellPos[0] - cellPos[2], 
                                            cellPos[1] + cellPos[3]/2, 
                                            cellPos[0] - cellPos[2],
                                            cellPos[1] + cellPos[3]/2])
        
        diffPipette = self.systemInfo.desired_to_observed_pipette()
        self.model.update_positions("S0", [0,1], diffPipette)
        self.synchronise_state()
        approachCellMutex.unlock()

    def aspirate_cell(self):
        cellStationaryMutex.lock()
        if((self.systemInfo.active_cell())):
                if (2 < self.systemInfo.cell_to_pipette()):
                    errorPopup("Cell must be closer to aspirate." +
                    "Position the pipette within 2um of the cell.")
                    cellStationaryMutex.unlock()
                    return
        elif(not self.systemInfo.active_asp_cell()):
            errorPopup("No active Cell tracker to aspirate")
            cellStationaryMutex.unlock()
            return
        
        self.pumpWidgets.increment_pressures([-0.25], [0])
        self.synchronise_state()
        
        cellStationaryMutex.unlock()

    def initialise_system_state(self):
        imgWidth, imgHeight, channels = self.systemInfo.get_img_dim()
        pToM = self.feedWidgets.pixel_to_micron(0)

        print("Gui's ptoM is %d\n"%(pToM))

        self.originXPixel = config.FineMotionConfig['originXOfWidth']*imgWidth
        self.originYPixel = config.FineMotionConfig['originYOfHeight']*imgHeight

        print("Sending to pixel %d %d with dim [%d,%d]"%(config.FineMotionConfig['originXOfWidth']*imgWidth, 
        config.FineMotionConfig['originYOfHeight']*imgHeight, imgWidth, imgHeight))
        self.originX = (self.originXPixel)/(self.scale*pToM)
        self.originY = (self.originYPixel)/(self.scale*pToM)

        self.systemInfo.set_pipette_range([self.originX,
                                            self.originY,
                                            self.originX,
                                            self.originY])


        if(not self.systemInfo.active_pipette()):
            print("No active pipette tracker or system pipette position exists." + 
            "Cannot initialise system state.")
            return

        diffPipette = self.systemInfo.desired_to_observed_pipette()
        print(diffPipette)
        self.model.update_positions("S0", [0,1], diffPipette)
        self.synchronise_state()
        
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
        print("PIXELS: point at [%d,%d], dimensions [%d,%d]\n" %(point.x()/self.scale, point.y()/self.scale, dim.x(),dim.y()))
        if((dim.x() == 0) or (dim.y() == 0)):
            desiredX = ((point.x())/(config*self.scale))/10
            desiredY = ((point.y())/(config*self.scale))/10
            print("%.2f, %.2f"%(desiredX, desiredY))

            self.systemInfo.set_pipette_range([desiredX,
                                                desiredY,
                                                desiredX,
                                                desiredY])
            posDifference = self.systemInfo.desired_to_observed_pipette()
            print(posDifference)
            self.model.update_positions("S0", [0,1], posDifference)
            
        else:
            self.context.posQ.put((cell,[(point.x()/(self.scale), point.y()/(self.scale)),
                                (dim.x()/(self.scale), dim.y()/(self.scale))]))

    def update_data(self):
        aspCellState = self.systemInfo.active_asp_cell()

        pressureWidget = self.pumpWidgets.get_child_widget(0)

        if(not aspCellState):
            return
        
        if(aspCellState == 2):
            dataWidget = self.dataWidgets.get_child_widget(0)
        elif(aspCellState == 3):
            dataWidget = self.dataWidgets.get_child_widget(1)

        aspCellPosition = self.systemInfo.observed_asp_position()

        if(aspCellPosition is None):
            #print("Returning because of None\n")
            return 

        #print("um difference is %.2f\n"%(aspCellPosition[0]))
        if(aspCellState == 1):
            dataWidget.add_data([abs(pressureWidget.get_pressure()), aspCellPosition[0]])
        else:
            #Change this to be dependent in the change in postiion (velocity)
            dataWidget.add_data([abs(pressureWidget.get_pressure()), aspCellPosition[0]])


class controlWorker(QObject):
    latchingSignal = pyqtSignal()
    approachingSignal = pyqtSignal()
    systemUpdateSignal = pyqtSignal(config.imageInformation, bool)
    
    def __init__(self):
        QObject.__init__(self)
        self.systemInfo = None
        self.systemUpdateSignal.connect(self.update_system_info)
        self.waitingCellStationary = False
        self.waitingPipStationary = False

    def approach_cell(self):
        global approachCellCondition
        global approachCellMutex

        for i in range(10):
            approachCellMutex.lock()
            self.waitingPipStationary = True
            approachCellCondition.wait(approachCellMutex)
            self.waitingPipStationary = False
            self.approachingSignal.emit()
            approachCellMutex.unlock()
            if(not self.systemInfo.active_cell() and not self.systemInfo.active_asp_cell()):
                return
            
    def update_control(self):
        global cellStationaryCondition
        global cellStationaryMutex

        for i in range(10):
            cellStationaryMutex.lock()
            self.waitingCellStationary = True
            cellStationaryCondition.wait(cellStationaryMutex)
            cellStationaryCondition = QWaitCondition()
            self.waitingCellStationary = False

            if((i != 0) and (not self.systemInfo.active_pipette() or
                not (self.systemInfo.active_asp_cell() 
                or self.systemInfo.active_cell()))):
                return

            self.latchingSignal.emit()
            cellStationaryMutex.unlock()

            if(self.systemInfo.active_cell()):
                if(self.systemInfo.cell_to_pipette()/config.FineMotionConfig['pixelPerMicron'] > 2):
                    return
            
            elif(not self.systemInfo.active_asp_cell()):
                return

    def update_system_info(self, systemInfo, pendingComms):
        global cellStationaryCondition
        self.systemInfo = systemInfo
        if(not pendingComms):
            if(self.waitingCellStationary and not self.systemInfo.moving_cell()):
                cellStationaryCondition.wakeAll()
            
            if(self.waitingPipStationary and not self.systemInfo.moving_pipette()):
                approachCellCondition.wakeAll()

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
        if(type(widget) != StepperObj):
            print("Incorrect type for updating position\n")
            return
        for n,wID in enumerate(widgetIDList):
            widget.get_child_widget(wID).set_position(posList[n])

class Application(QApplication):
    def __init__(self, context, argv):
        super(Application, self).__init__(argv)
        
        self.context = context

        self.model = AppModel()

        self.view = AppView()

        self.controller = AppController(self.model, self.view, context)

    def end_program(self):
        self.controller.terminate_threads()
        self.context.end_program()
        exit(0)

def guiManagement(context,posQ):

    app = Application(context, sys.argv)
    app.aboutToQuit.connect(app.end_program)
    
    styleSheet = colourScheme()

    '''
    styleSheet.setWidgetStyle(
                "QPushButton", 
                backgroundColor = GUI_COLOURS["FOREGROUND2"],
                colour = GUI_COLOURS["WHITE"])
    '''
    
    styleSheet.setWidgetStyle(
                "QTabWidget_pane",
                backgroundColor = GUI_COLOURS["FOREGROUND1"],
                colour = GUI_COLOURS["WHITE"],
                borderColor= GUI_COLOURS["WHITE"],
                borderWidth= 2, borderRadius = 12)
    
    styleSheet.setWidgetStyle(
                "QTabBar_tab_selected",
                backgroundColor = GUI_COLOURS["FOREGROUND2"],
                colour = GUI_COLOURS["WHITE"])

    styleSheet.setWidgetStyle(
                "QTabBar_tab",
                backgroundColor = GUI_COLOURS["BACKGROUND2"],
                colour = GUI_COLOURS["WHITE"])
    
    styleSheet.setWidgetStyle(
                "QGroupBox",
                backgroundColor = GUI_COLOURS["FOREGROUND1"],
                colour = GUI_COLOURS["WHITE"],
                borderColor= GUI_COLOURS["WHITE"],
                borderWidth= 2, borderRadius = 12)
    
    styleSheet.setWidgetStyle(
                "QLabel",
                colour = GUI_COLOURS["BACKGROUND2"])

    styleSheet.setWidgetStyle(
        "QMainWindow",
        backgroundColor = GUI_COLOURS["BACKGROUND1"],
        colour = GUI_COLOURS["WHITE"])
    
    print(styleSheet.toString())
    
    app.setStyleSheet(styleSheet.toString())
    

    sys.exit(app.exec_())

def errorPopup(msg):
        error = QMessageBox()
        error.setWindowTitle("An error occured")
        error.setText("Uh oh...")
        error.setStandardButtons(QMessageBox.Ok)
        error.setInformativeText(msg)

        x = error.exec_()
    