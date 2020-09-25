from multiprocessing import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import sys
from datetime import *
from .ConfigFiles.generalconf import *

#Initialise the tool you are controlling with initial tool message


class emulationCommands(QThread):
    recvCommand =  pyqtSignal(str)

    def __init__(self, emOutQ, emInQ):
        QThread.__init__(self)
        self.emOutQ = emOutQ
        self.emInQ = emInQ

    def run(self):
        while(1):
            if not self.emInQ.empty():
                self.recvCommand.emit(self.emInQ.get())

class emulationWindow(QMainWindow):
    def __init__(self, emOutQ, emInQ):
        QMainWindow.__init__(self)
        self.setGeometry(0, 0, 2*(EM_OFFSET + SAMPLE_WIDTH), 2*(EM_OFFSET + SAMPLE_HEIGHT))

        self.title = "Hardware Emulation"

        self.commandThread = emulationCommands(emOutQ, emInQ)
        self.commandThread.recvCommand.connect(self.processCommand)
        self.commandThread.start()

        self.commandLabel = QLabel("Command window", self)
        self.commandLabel.setFixedWidth(150)

        self.commandLabel.move(EM_OFFSET + SAMPLE_WIDTH + 300, 15)

        self.commandBox = QTextEdit(self)
        self.commandBox.setFixedHeight(560)
        self.commandBox.setFixedWidth(350)
        self.commandBox.move(EM_OFFSET + SAMPLE_WIDTH + 200, 50)
        self.commandBox.setReadOnly(True)
        palette  = QPalette(Qt.black)
        self.commandBox.setPalette(palette)
        self.commandBox.setTextBackgroundColor(Qt.black)
        self.commandBox.setTextColor(Qt.white)

        self.paintContainer = QFrame()

        self.tool = None

    def processCommand(self, communication):
        command = communication.split(' ')
        time = datetime.now()
        self.commandBox.setFontItalic(True)
        self.commandBox.append("%s > "%(str(datetime.now())[10:-4]) + communication)
        self.commandBox.setFontItalic(False)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(Qt.red, 1, Qt.SolidLine))

        for r in range(0 + EM_OFFSET,SAMPLE_HEIGHT + EM_OFFSET, FINE_H_DIV):
            painter.drawLine(0 + EM_OFFSET,r,SAMPLE_WIDTH + EM_OFFSET,r)

        for c in range(0 + EM_OFFSET, SAMPLE_WIDTH + EM_OFFSET, FINE_W_DIV):
            painter.drawLine(c, 0 + EM_OFFSET, c, SAMPLE_HEIGHT + EM_OFFSET)

        painter.setPen(QPen(Qt.black, 1, Qt.SolidLine))

        for r in range(0 + EM_OFFSET,SAMPLE_HEIGHT + EM_OFFSET, GROSS_H_DIV):
            painter.drawLine(0 + EM_OFFSET,r,SAMPLE_WIDTH + EM_OFFSET,r)

        for c in range(0 + EM_OFFSET, SAMPLE_WIDTH + EM_OFFSET, GROSS_W_DIV):
            painter.drawLine(c, 0 + EM_OFFSET, c, SAMPLE_HEIGHT + EM_OFFSET)

        painter.drawLine(0 + EM_OFFSET,SAMPLE_HEIGHT + EM_OFFSET,
                            SAMPLE_WIDTH + EM_OFFSET,SAMPLE_HEIGHT + EM_OFFSET)

        painter.drawLine(SAMPLE_WIDTH + EM_OFFSET, 0 + EM_OFFSET, 
                            SAMPLE_WIDTH + EM_OFFSET, SAMPLE_HEIGHT + EM_OFFSET)

        self.draw_point_gridPos(painter, (NUM_W_SAMPLE_AREAS, 0), (1,3), brush = (Qt.blue, Qt.SolidPattern))
        self.draw_text_gridPos(painter, (NUM_W_SAMPLE_AREAS, 0), (2,3), "Microscope objective")

        self.draw_point_gridPos(painter, (NUM_W_SAMPLE_AREAS, 0), (1,4), brush = (Qt.green, Qt.SolidPattern))
        self.draw_text_gridPos(painter, (NUM_W_SAMPLE_AREAS, 0), (2,4), "Micropipette")


    def reset_painter(self, painter):
        painter.setPen(QPen(Qt.black, 1, Qt.SolidLine))
        painter.setBrush(QBrush(Qt.black, Qt.NoBrush))

    def draw_point_gridPos(self, painter, grossPos, finePos, pen = (Qt.black, 1, Qt.SolidLine), brush = (Qt.black, Qt.NoBrush)):
        painter.setPen(QPen(pen[0], pen[1], pen[2]))
        painter.setBrush(QBrush(brush[0], brush[1]))
        painter.drawEllipse(grossPos[0]*GROSS_W_DIV + finePos[0]*FINE_W_DIV
                            + EM_OFFSET - POINT_R/2, 
                            grossPos[1]*GROSS_H_DIV+finePos[1]*FINE_H_DIV
                            +EM_OFFSET - POINT_R/2,POINT_R,POINT_R)
        
        self.reset_painter(painter)

    def draw_text_gridPos(self, painter, grossPos, finePos, text, pen = (Qt.black, 1, Qt.SolidLine), brush = (Qt.black, Qt.NoBrush)):
        painter.setPen(QPen(pen[0], pen[1], pen[2]))
        painter.setBrush(QBrush(brush[0], brush[1]))
        painter.drawText(grossPos[0]*GROSS_W_DIV + finePos[0]*FINE_W_DIV
                            + EM_OFFSET - POINT_R, 
                            grossPos[1]*GROSS_H_DIV+finePos[1]*FINE_H_DIV
                            +EM_OFFSET + 5, text)
        
        self.reset_painter(painter)

    def set_objective_view(self, painter, origin, pen = (Qt.black, 1, Qt.SolidLine), brush = (Qt.black, Qt.NoBrush)):
        painter.setPen(QPen(pen[0], pen[1], pen[2]))
        painter.setBrush(QBrush(brush[0], brush[1]))
        painter.drawRect(origin[0]*GROSS_W_DIV + EM_OFFSET, 
                        origin[1]*GROSS_H_DIV + EM_OFFSET, 
                        GROSS_W_DIV, GROSS_H_DIV)

        self.reset_painter(painter)
        

    

def initialise_emulator(emOutQ, emInQ):
    emulator_process = Process(target = emulatorManagement, args =[emOutQ, emInQ])
    emulator_process.start()

def emulatorManagement(emOutQ, emInQ):
    app = QApplication(sys.argv)
    emulationInterface = emulationWindow(emOutQ, emInQ)
    emulationInterface.show()
    sys.exit(app.exec_())

