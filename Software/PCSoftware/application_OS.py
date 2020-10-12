import os
import signal

from ComputerVision.image_processing_OS import initialise_computer_vision
from UserInterface.SoftwareDrivers.GUI_Driver import guiManagement
from SerialCommunication.serial_os import initialise_serial_process
from Emulator.emulator_os import \
CaptureEmulator, SerialEmulator, initialise_emulation_process
from multiprocessing import Queue, Event

def launch_application():
    """ Launcher entry function. Initialise program wide state and process'.
    Initialise means of communication between process'. 
    """
    # Initialise application context object
    context = AppContext()

    # Initialise emulation command queue (serial emulation)
    commandQueue = Queue()
    # Initialise emulation capture queue (capture emulation)
    captureQueue = Queue()

    # Initialise capture emulation instance
    captureEmulator = CaptureEmulator(captureQueue)
    # Initialise serial emulation instance
    serialEmulator = SerialEmulator(commandQueue)

    # Start emulation process
    context.add_pid(initialise_emulation_process(commandQueue, captureQueue))
    # Start serial communication process
    context.add_pid(initialise_serial_process(context, serialEmulator))
    # Start computer vision process
    context.add_pid(initialise_computer_vision(context.pixQ, context.posQ,
                                               context.capSem, captureEmulator))
    # Start UI process
    guiManagement(context)

    # Await kill process event (when exiting application)
    context.kill.wait()


class AppContext(object):
    def __init__(self):
        """ Initialise Application context. Contains queues distributed
        throughout the mutli-process program, used in communication.
        """
        # Computer vision communicators
        # Distribute images captured via the microscope
        self.pixQ = Queue()
        # Request image capture from computer vision process
        self.capSem = Queue()
        # Distribute user input to the computer vision process
        self.posQ = Queue()

        # Serial communication communicators
        # Distribute G-Code segments to be transmitted
        self.sOut = Queue()
        # Distribute recieved segments
        self.sIn = Queue()
        # Distribute human readable serial comms strings to display to the user
        self.sDisp = Queue()
        # Semaphore to communicate serial communication completion
        self.sComplete = Queue()

        # Event, triggered when the user exits the GUI
        self.kill = Event()

        # List of generated process ID's
        self.pid = []

    def add_pid(self, pid):
        """ Add a process id to the registered process ID's

        Args:
            pid (int): Identifier of the process to add to process ID's
        """
        self.pid.append(pid)

    def put_comm_success(self, state):
        """ Add state to the communication success queue

        Args:
            state (bool): Current state of serial communications
        """
        self.sComplete.put(state)

    def get_comm_success(self):
        """ Get state of the communication success queue

        Returns:
            bool: True iff communication is completed successfully. Otherwise
            false.
        """
        if(self.sComplete.empty()):
            return None
        else:
            return self.sComplete.get()

    def end_program(self):
        """ End the program by sending signal to exit all registered process'
        """
        for p in self.pid:
            os.kill(p, signal.SIGKILL)

if __name__ == "__main__":
    launch_application()
