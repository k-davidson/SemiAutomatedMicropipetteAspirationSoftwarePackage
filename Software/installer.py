
import os
import subprocess
import multiprocessing
import time

import qtpy
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtSvg import *
import serial.tools.list_ports

# Packages and versions required by the main program
PACKAGE_LIST = {"click":"7.1.2", "numpy":"1.19.2", "Pillow":"7.2.0", 
                "opencv-contrib-python-headless":"4.4.0.44", "PyQt5":"5.15:1", 
                "pyserial":"3.4", "PySide2":"5.14.2.1", "QtPy":"1.9.0"}

# Valid package managers
PACKAGE_MANAGER = {"PIP":"pip", "PIP3":"pip3", "Homebrew":"brew"}

# Settings file directories
ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = "/SoftwareDrivers/ConfigFiles/settings.py"
SETTING_PATH_MANAGER = {
    "Serial":ROOT + "/PCSoftware/SerialCommunication" + PATH,
    "UserInterface":ROOT + "/PCSoftware/UserInterface" + PATH,
    "ImagProc":ROOT + "/PCSoftware/ComputerVision" + PATH,
    "System":ROOT + "/PCSoftware/settings.py"}

class bashCommunicator(QThread):
    """ Create thread that facilitates executing bash commands

    Args:
        QThread: Inheret QThread behaviour
    """
    # Signal to update progress bar
    updateProgress = pyqtSignal(int, str)

    def __init__(self, packageStates, manager):
        """ Initialise bash communicator

        Args:
            packageStates (dict): States of each package (whether required)
            manager (dict): Package manager linking simple to true names
        """
        QThread.__init__(self)
        self.packageStates = packageStates
        self.manager = manager

    def run(self):
        """ Manager loop to manage executing bash commands
        """
        self.updateProgress.emit(0, "Sourcing")

        # Iterate over packages
        for n, p in enumerate(self.packageStates.keys()):
            # If package required
            if(self.packageStates[p].isChecked()):
                # Write command to bash
                command = "%s install %s==%s"%(PACKAGE_MANAGER[self.manager], \
                p,PACKAGE_LIST[p])
                process = subprocess.Popen(command, shell=True, \
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                process.communicate()
                self.updateProgress.emit(n, p)

class progressGroup(QGroupBox):
    """ Series of buttons managing installer page state and allowing the
    user to progress through the installer

    Args:
        QGroupBox: Inheret behaviour of QGroupBox
    """

    def __init__(self, nextFunc, backFunc, cancelFunc):
        """ Initialise progress group state and link progress functions

        Args:
            nextFunc (function): Function called when user progress' installer
            backFunc (function): Function called when user regresses installer
            cancelFunc (function): Function called when user cancels installer
        """
        QWidget.__init__(self)

        # Add all buttons to the GUI
        self.progressLayout = QGridLayout()
        self.backButton = QPushButton("Back")
        self.nextButton = QPushButton("Next")
        self.cancelButton = QPushButton("Cancel")
        self.finishedButton = QPushButton("Finish")

        self.progressLayout.addWidget(self.backButton, 0, 0)
        self.progressLayout.addWidget(self.nextButton, 0, 1)
        self.progressLayout.addWidget(self.cancelButton, 0, 2)
        self.progressLayout.addWidget(self.finishedButton, 0, 2)
        self.setLayout(self.progressLayout)

        # Only show finish on last state
        self.finishedButton.setVisible(False)

        # Connect functions to buttons
        self.nextButton.clicked.connect(lambda: nextFunc(1))
        self.backButton.clicked.connect(lambda: backFunc(-1))
        self.cancelButton.clicked.connect(cancelFunc)
        self.finishedButton.clicked.connect(cancelFunc)

        self.disable_backward()

    def disable_forward(self):
        """ Disable progress button
        """
        self.nextButton.setEnabled(False)

    def disable_backward(self):
        """ Disable regress button
        """
        self.backButton.setEnabled(False)

    def enable_all(self):
        """ Enable all buttons
        """
        self.backButton.setEnabled(True)
        self.nextButton.setEnabled(True)

    def finished(self):
        """ Last state, show finish button remove all other buttons
        """
        self.nextButton.setVisible(False)
        self.cancelButton.setVisible(False)
        self.backButton.setVisible(False)
        self.finishedButton.setVisible(True)

class setting(QWidget):
    """ Widget to manage single variable setting

    Args:
        QWidget: Inheret behaviour of QWidget class
    """
    def __init__(self, variableName, displayWidget, settingFunc):
        """ Initialise settings widget

        Args:
            variableName (String): Name of variable to be configured
            displayWidget (QWidget): Display information about setting
            settingFunc (function): Pointer to function connected to setting
        """
        QWidget.__init__(self)
        self.displayWidget = displayWidget
        self.settingFunc = settingFunc
        self.variableName = variableName

    def get_widget(self):
        """ Get the display widget

        Returns:
            QWidget: Widget used to display setting information
        """
        return self.displayWidget

    def __repr__(self):
        """ Get string format

        Returns:
            String: String format of variable to be written to config file
        """
        setValue = self.settingFunc()
        
        # If value is a string
        if(type(setValue) == str):
            return self.variableName + " = \"" + \
                str(self.settingFunc()) + "\"\n\n"
        else:
            return self.variableName + " = " + \
                str(self.settingFunc()) + "\n\n"

class settingsWidget(QGroupBox):
    """ Settings widget, grouping multiple individual settings 

    Args:
        QGroupBox: Inheret behaviour from QGroupBox
    """
    def __init__(self, filepath, additionalInfo = None):
        """ Initialise state of settings widget

        Args:
            filepath (Setting): Filepath to write all settings to
            additionalInfo (String[], optional): Any additional information
            not contained within registered settings. Defaults to None.
        """
        
        # Initialise group box state
        QGroupBox.__init__(self)
        self.layout = QGridLayout()
        self.row = 0
        self.setLayout(self.layout)
        self.filepath = filepath
        self.settings = []
        self.additionalInfo = additionalInfo
    
    def add_setting(self, setting, explanation):
        """ Add setting to the settings register

        Args:
            setting (Setting): Setting to be added to the register
            explanation (String): Explanation of setting (include units)
        """
        # Append setting to the registered settings
        self.settings.append(setting)
        settingLabel = QLabel(explanation)
        self.layout.addWidget(settingLabel, self.row, 0)
        self.layout.addWidget(setting.get_widget(), self.row, 1)
        self.row += 1

    def write_settings(self):
        """ Write settings to appropriate config file
        """

        # Open file to write
        f = open(self.filepath, "w")
        
        # Iterate through settings
        for setting in self.settings:
            # Write settings
            f.write(str(setting))
        
        # Write additional information
        if(self.additionalInfo is not None):
            for info in self.additionalInfo:
                f.write(info + "\n\n")

        # Close file
        f.close()

class Installer(QApplication):
    """ Main installer widget to display to the user

    Args:
        QApplication: Inheret behaviour from QApplication
    """
    def __init__(self, argv):
        """ Initialise state of installer

        Args:
            argv (String[]): Command line arguments passed to installer
        """
        QApplication.__init__(self, argv)
        self.window = QWidget()

        # Initialise QtPy window
        self.window.setWindowTitle("Installer & Setup Wizard")
        self.installerStates = []
        self.state = 0
        self.packagesRequested = 0
        self.progress = progressGroup(self.state_change,
                                    self.state_change,
                                    self.cancel_installer)
        
        # Set welcome screen text
        welcomeText1 = "Welcome to Semi-Automated Micropipette Aspiration setup"
        welcomeText2 = "This installer will assist in ensuring all " + \
        "program dependencies are met on your system.\n" + \
        " Please follow the prompts."

        # Create individual screens for installer
        self.installerStates.append(self.create_text_screen(welcomeText1, \
            welcomeText2))
        self.installerStates.append(self.create_install_selection_screen())
        self.installerStates.append(self.create_package_selector(PACKAGE_LIST))
        self.installerStates.append(self.create_install_screen())
        self.installerStates.append(self.create_settings_screen())
        
        # Set completion text
        completedText1 = "Successful installation"
        completedTex2 = "The requested packages and settings have " + \
            "successfully been installed. The application executble has " + \
                "been generated.\n"
        
        # Add all installer states
        self.installerStates.append(self.create_text_screen(completedText1, \
            completedTex2))

        # Add widgets to main window
        self.parentLayout = QGridLayout()
        self.parentLayout.addWidget(self.progress, 1, 0)

        for i in range(len(self.installerStates)):
            self.parentLayout.addWidget(self.installerStates[i], 0, 0)
        
        # Initialise state to 0
        self.state_change(0)

        # Show window
        self.window.setLayout(self.parentLayout)
        self.window.show()

    def create_text_screen(self, text1, text2):
        """ Create screen containing text (e.g Welcome or Completion)

        Args:
            text1 (String): Main text to display
            text2 (String): Secondary text

        Returns:
            QGroupBox: Groupbox containing text and layout
        """

        # Create group box
        self.welcomeGroup = QGroupBox()
        self.welcomeLayout = QGridLayout()

        # Create labels with text provided as arguments
        self.welcomeLabel = QLabel(text1)
        self.explanationLabel = QLabel(text2)
        self.welcomeLabel.setStyleSheet("font-weight: bold;")
        self.welcomeLayout.addWidget(self.welcomeLabel, 0, 0)
        self.welcomeLayout.addWidget(self.explanationLabel, 1, 0)
        self.welcomeGroup.setLayout(self.welcomeLayout)

        return self.welcomeGroup

    def create_package_selector(self, packageList):
        """Create package selector screen.

        Args:
            packageList (String[]): List of packages to select from

        Returns:
            QGroupBox: GroupBox containing package selector widget
        """

        # Create group box
        self.packageGroup = QGroupBox()
        self.packageLayout = QGridLayout()

        # Create explanation label
        self.packageSelectLabel = QLabel("Please select the packages you " + \
            "wish to install. Note, all packages are required to run " + \
                "the program.")
        self.packageSelectLabel.setStyleSheet("font-weight: bold;")
        self.packageLayout.addWidget(self.packageSelectLabel, 0, 0, 1, 2)

        self.packagesChecks = {}

        # Iterate over packages, adding all required
        for n, package in enumerate(packageList.keys()):
            self.packagesChecks[package] = QCheckBox(package)
            self.packageLayout.addWidget(self.packagesChecks[package], \
                1 + int(n/2), n % 2)
            self.packagesChecks[package].setChecked(True)

        # Set group box layout
        self.packageGroup.setLayout(self.packageLayout)

        return self.packageGroup

    def create_install_screen(self):
        """ Create install screen, displayed while packages being installed

        Returns:
            [type]: [description]
        """
        self.installGroup = QGroupBox()
        self.installLayout = QGridLayout()

        self.installLabel = QLabel("Please wait while your packages are installed...")
        self.installLayout.addWidget(self.installLabel)

        self.progressBar = QProgressBar()
        self.installLayout.addWidget(self.progressBar)

        self.currentPackageLabel = QLabel("Installing: ")
        self.installLayout.addWidget(self.currentPackageLabel)

        self.installGroup.setLayout(self.installLayout)

        return self.installGroup

    def create_install_selection_screen(self):
        self.settingsGroup = QGroupBox()
        self.settingsLayout = QGridLayout()

        self.settingsLabel = QLabel("Please select your preferred package managar:")
        self.settingsLayout.addWidget(self.settingsLabel)

        self.packManageSelection = QComboBox()
        self.packManageSelection.addItem("PIP")
        self.packManageSelection.addItem("PIP3")
        self.packManageSelection.addItem("Homebrew")

        self.settingsLayout.addWidget(self.packManageSelection)

        self.settingsGroup.setLayout(self.settingsLayout)

        return self.settingsGroup

    def create_settings_screen(self):
        self.masterSettingsGroup = QGroupBox()
        self.mastersettingsLayout = QGridLayout()
        self.masterSettingsGroup.setLayout(self.mastersettingsLayout)

        self.masterTabWidget = QTabWidget()

        SETTING_TABS = {"Serial":self.create_serial_settings, \
                        "UserInterface":self.create_UI_settings, \
                        "ImageProcessing":self.create_imag_proc_settings, \
                        "System": self.create_system_settings}

        for setting in SETTING_TABS.keys():
            self.masterTabWidget.addTab(SETTING_TABS[setting](), setting)
        
        self.mastersettingsLayout.addWidget(self.masterTabWidget)

        return self.masterSettingsGroup

    def create_serial_settings(self):
        serialSettingsWidget = settingsWidget(SETTING_PATH_MANAGER['Serial'])

        portSelection = QComboBox()
        commPorts = serial.tools.list_ports.comports()

        for port, desc, hwid in sorted(commPorts):
            portSelection.addItem(str(port))

        serialSettingsWidget.add_setting(
            self.create_checkbox_setting("SERIAL_EMULATOR", False), 
            "Use serial emulator")

        portSetting = setting("SERIAL_PORT", portSelection, portSelection.currentText)
        serialSettingsWidget.add_setting(portSetting, "Select Arduino serial port")

        serialSettingsWidget.add_setting(
            self.create_spinbox_setting("BAUDRATE", [0, 460800], 57600),
            "Specify the appropriate Baudrate (Bd)")

        seqCharSelection = QLineEdit()
        seqCharSelection.setMaxLength(1)
        seqCharSelection.setText("%")
        seqCharSetting = setting("START_END_SEQ", seqCharSelection, seqCharSelection.text)
        serialSettingsWidget.add_setting(seqCharSetting, "Specify the start/end sequence character")

        serialSettingsWidget.add_setting(
            self.create_spinbox_setting("RECV_ATTEMPTS", [1, 10], 1), 
            "Specify number of recieve attempts:")

        serialSettingsWidget.add_setting(
            self.create_spinbox_setting("TRANSMIT_ATTEMPTS", [1, 10], 1), 
            "Specify number of re-transmit attempts:")

        return serialSettingsWidget

    def create_UI_settings(self):
        UISettingsWidget = settingsWidget(SETTING_PATH_MANAGER['UserInterface'])

        UISettingsWidget.add_setting(
            self.create_spinbox_setting("IMG_SCALE", [0, 2], 0.25, double = True, step = 0.05, decimals=2), 
            "Select appropriate image scaling (%% area of original image)")

        return UISettingsWidget

    def create_imag_proc_settings(self):
        imagProcSettingsWidget = settingsWidget(SETTING_PATH_MANAGER['ImagProc'])

        imagProcSettingsWidget.add_setting(
            self.create_checkbox_setting("IMAG_EMULATOR", False), 
            "Use camera emulator")

        imagProcSettingsWidget.add_setting(
            self.create_checkbox_setting("IMAG_VIDEO", False), 
            "Use video recording")
        
        videoFileExplorer = QFileDialog()
        videoFileSelection = QPushButton("Select File")
        videoFileSelection.clicked.connect(
            lambda: self.set_video_filename(videoFileExplorer.getOpenFileName(caption = 'Select video file')[0]))
        self.set_video_filename(None)
        videoFileSetting = setting("VIDEO_PATH", videoFileSelection, self.get_video_filename)
        imagProcSettingsWidget.add_setting(videoFileSetting, "Specify the desired video file")
        
        imagProcSettingsWidget.add_setting(
            self.create_spinbox_setting("MIN_PIP_LEN", [5,50], 5), 
                "Specify the minimum pipette length in frame (pixels)")

        return imagProcSettingsWidget

    def create_system_settings(self):
        systemSettingsWidget = settingsWidget(SETTING_PATH_MANAGER['System'], 
            additionalInfo=["STEPS_PER_MICRON = STEPS_PER_REV/MICRON_PER_REV",
                                "GRAVITY = 9.8"])

        systemSettingsWidget.add_setting(
            self.create_spinbox_setting("PIXEL_PER_MICRON", [10,500], 72), 
            "Specify the number of pixels per micron (pixels)")

        systemSettingsWidget.add_setting(
            self.create_spinbox_setting("STEPS_PER_REV", [250,2000], 500), 
            "Specify the number of steps per revolution (steps)")

        systemSettingsWidget.add_setting(
            self.create_spinbox_setting("MICRON_PER_REV", [1,10000], 500), 
            "Specify the distance per revolution (\u03BCm)")
        
        systemSettingsWidget.add_setting(
            self.create_spinbox_setting("MICROSTEPPING", [1,32], 16), 
            "Specify the microstepping ratio (portion of full step)")

        systemSettingsWidget.add_setting(
            self.create_spinbox_setting("MIN_VOLUME_INCREMENT", [1,10000], 10),  
            "Specify the unit volume increment (\u03BCL)")
        
        systemSettingsWidget.add_setting(
            self.create_spinbox_setting("COLUMN_DIAMETER", [0.005,1], 0.032, double=True, step = 0.05, decimals = 4),  
            "Specify the water column diameter (meters)")

        systemSettingsWidget.add_setting(
            self.create_spinbox_setting("FLUID_DENSITY", [0.001, 100], 0.997, double = True, step = 0.001, decimals = 3),
            "Specify the fluid density (kg/cubic meter)")

        return systemSettingsWidget

    def create_checkbox_setting(self, variableName, state):
        boolWidget = QCheckBox()
        boolWidget.setChecked(state)

        return setting(variableName, boolWidget, boolWidget.isChecked)

    def create_spinbox_setting(self, variableName, varRange, initVal, double = False, step = None, decimals = None):
        if(double):
            valueWidget = QDoubleSpinBox()
        else:
            valueWidget = QSpinBox()
        
        valueWidget.setRange(varRange[0], varRange[1])
        valueWidget.setValue(initVal)

        if(double and step):
            valueWidget.setSingleStep(step)
        
        if(double and decimals):
            valueWidget.setDecimals(decimals)

        
        return setting(variableName, valueWidget, valueWidget.value)

    def set_video_filename(self, filename):
        self.videoFilename = filename
    
    def get_video_filename(self):
        return self.videoFilename

    def state_change(self, state):
        self.state += state
        
        if((self.state == 3) and (state == -1)):
            self.state -= 1

        for n in range(len(self.installerStates)):
            if(n == self.state):
                self.installerStates[n].setVisible(True)
            else:
                self.installerStates[n].setVisible(False)

        if((self.state == 3) and (state == 1)):
            self.progress.disable_backward()
            self.progress.disable_forward()
            self.packageInstaller = bashCommunicator(self.packagesChecks, self.packManageSelection.currentText())
            self.packageInstaller.updateProgress.connect(self.install_display)
            
            self.packagesRequested = 0
            for p in self.packagesChecks.keys():
                if(self.packagesChecks[p].isChecked()):
                    self.packagesRequested += 1
            
            self.progressBar.setMaximum(self.packagesRequested)
            self.packageInstaller.start()

        elif(self.state == 0):
            self.progress.disable_backward()
        
        elif(self.state == 5):
            self.execute_settings()
            self.progress.finished()
        
        else:
            self.progress.enable_all()

    def install_display(self, packageNo, packageName):
        self.progressBar.setValue(packageNo + 1)

        if((packageNo + 1) >= self.packagesRequested):
            self.state_change(1)
    
    def cancel_installer(self):
        self.window.close()

    def execute_settings(self):
        for tab in range(self.masterTabWidget.count()):
            settingSelect = self.masterTabWidget.widget(tab)
            settingSelect.write_settings()

if __name__ == "__main__":
    app = Installer([])
    app.exec()

