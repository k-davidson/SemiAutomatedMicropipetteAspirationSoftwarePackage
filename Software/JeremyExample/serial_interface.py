import threading
import queue
import time
from abc import ABC, abstractmethod

import serial


class SerialCommunicator(ABC):
    # this is an abstract class, it can't be used to create an instance, it is only for inheritance

    # the "@abstractmethod" decorator means that you *must* override this method in a subclass
    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self, data):
        pass


class SerialPortCommunicator(SerialCommunicator):
    def __init__(self, port, baudrate):
        self._serial = serial.Serial(port, baudrate)
        self._serial.open()

    def read(self):
        return self._serial.read(1).decode()

    def write(self, data):
        return self._serial.write(data)


class SerialSimulator(SerialCommunicator):
    def __init__(self):
        self._data_to_pc_queue = queue.Queue()
        self._data_to_arduino_queue = queue.Queue()

        self._background_thread = threading.Thread(target=self._background_thread, daemon=True)
        self._background_thread.start()

    def read(self):
        return self._data_to_pc_queue.get()

    def write(self, data):
        for d in data:
            self._data_to_arduino_queue.put(d)

    def _background_thread(self):
        while True:
            # simulate sending the text "hello\n" every 5 seconds
            for c in "hello\n":
                self._data_to_pc_queue.put(c)
            time.sleep(5)
