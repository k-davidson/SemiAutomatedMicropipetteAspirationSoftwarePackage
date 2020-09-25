import sys
import queue
import threading
from PySide2 import QtGui, QtCore, QtWidgets

from serial_interface import SerialPortCommunicator, SerialSimulator


class AppContext(object):
    # this class contains all of the shared objects between the various classes
    # by passing an instance to this class everywhere, you can access the objects in various threads

    def __init__(self):
        # here are some objects that could be accessed in multiple places
        self.picture_queue = queue.Queue()
        self.position_queue = queue.Queue()

        # by swapping out the self.serial instance, you can switch between using a simulated serial port or a real one
        # this is called "composition", and allows you to create modular code quite easily

        # if you want to use the simulator, uncomment the next line
        self.serial = SerialSimulator()
        # if you want to use the real hardware, comment the line above and uncomment the line below
        # self.serial = SerialPortCommunicator(...)


class EmulatorUI(QtWidgets.QMainWindow):
    _recv_command_signal = QtCore.Signal(str)

    def __init__(self, app_context: AppContext, *args, **kwargs):
        super().__init__(*args, **kwargs)  # call parent class constructor

        # store the context that we passed in
        self.app_context = app_context

        self._recv_command_signal.connect(self._process_command)

        self._generate_signals_thread_handle = threading.Thread(target=self._generate_command_signals_thread,
                                                                daemon=True)
        self._generate_signals_thread_handle.start()

        self.setWindowTitle("Emulator UI")

    def _generate_command_signals_thread(self):
        pending_data = ""
        while 1:
            # here we access the serial object in the context
            # this code doesn't know if it is taking to a fake or real serial port, and that's intended! This way,
            # we can use the same code whether we are using the fake or real serial port, which makes testing easier
            b = self.app_context.serial.read()

            if b == "\n":
                self._recv_command_signal.emit(pending_data)
                pending_data = ""
            else:
                pending_data += b

    def _process_command(self, command: str):
        print("got command:", command)


if __name__ == "__main__":
    app_context = AppContext()

    app = QtWidgets.QApplication()
    emulator_ui = EmulatorUI(app_context)
    emulator_ui.show()

    sys.exit(app.exec_())