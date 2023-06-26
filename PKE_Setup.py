from PyQt5.QtWidgets import (
    QMainWindow, QCheckBox, QVBoxLayout, 
    QApplication, QLabel, QHBoxLayout, 
    QWidget, QPushButton, QLineEdit, 
    QGroupBox, QSpacerItem, QSlider,
    QFrame, QTabWidget, QScrollArea,
    QComboBox
)
from PyQt5.QtGui import (
    QFont, QIntValidator
)
from PyQt5.QtCore import (
    Qt, QSize, QThread
)
import numpy as np
import time
import xlsxwriter
import logging
from CAN import CanSendRecv
from interactive_data import InteractiveData
import os
import yaml


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self._PowerMode = 0
        self._AntAmount = 6
        self._KeyAmount = 5
        self._store_data_path = "store_data"
        self._logs_path = "app_logs"
        self._PollingsDone = 0
        self._AuthsDone = 0
        self._authStatus = False
        self._pollingInProgress = False
        self._PollingsNeeded = 1

        self._InitLogger()
        self._Initworksheet()
        self._SetApp()
        self._CanInit()
        self._restoreData()

    def closeEvent(self, *args, **kwargs):
        self._StopPolling()

        try:
            self._workbook.close()
            self._logger.info("WorkBook Closed")
        except:
            self._logger.info("Error closing WorkBook")

        try:
            if (self._CanThread.isRunning()):
                self._CanThread.quit()
                self._CanThread.wait()

            self._logger.info("CAN thread terminated")
        except:
            self._logger.info("Error terminating CAN thread")

        to_yaml = {
            'ants': [],
            'keys': [],
            'auth': 0
        }
        for nCnt in range(0, len(self._widgetAntCheckBox)):
            if self._widgetAntCheckBox[nCnt].isChecked():
                to_yaml['ants'].append(nCnt)

        for nCnt in range(0, len(self._widgetKeyCheckBox)):
            if self._widgetKeyCheckBox[nCnt].isChecked():
                to_yaml['keys'].append(nCnt)

        if self._widgetAuthCheckBox.isChecked(): 
            to_yaml['auth'] = 1
           
        with open(f'{self._store_data_path}/keys_ants', 'w') as f:
            yaml.dump(to_yaml, f)

        super(QMainWindow, self).closeEvent(*args, **kwargs)

    def _InitLogger(self):
        try:
            os.mkdir(f"{self._logs_path}/")
        except: pass

        self._logger = logging.getLogger(__name__)
        f_handler = logging.FileHandler(f'{self._logs_path}/{__name__}.log')
        f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        f_handler.setFormatter(f_format)
        self._logger.addHandler(f_handler)
        self._logger.setLevel(logging.WARNING)

    def _Initworksheet(self):
        self._row = 0
        self._column = 0
        self._row_single = 0
        self._column_single = 0
    
        time_hms = time.strftime("%Hh_%Mmin", time.localtime())
        time_ymd = time.strftime("%Y-%m-%d", time.localtime())

        try:
            os.mkdir(f"logs/")
        except: pass

        try:
            self._workbook = xlsxwriter.Workbook(f'logs/logs_by_{time_ymd}_{time_hms}.xlsx')
            self._worksheet = self._workbook.add_worksheet(name="All_Data")
            self._worksheet_single = self._workbook.add_worksheet(name="Single Data")
        except:
            self._logger.warning("Error opening XLS")

    def _SetApp(self):
        self.setWindowTitle("PKE Setup")
        self.resize(QSize(1400, 800))
        # self.setStyleSheet("background-color: white;")

        self._layoutBig = QHBoxLayout()
        self._layoutAnts = QHBoxLayout()
        self._layoutAnts.setSpacing(0)

        self._layoutWidgets = QVBoxLayout()
        self._layoutWidgets.setSpacing(50)
        v_widget = QWidget()
        v_widget.setLayout(self._layoutWidgets)    
        scrollWidget = QScrollArea()
        scrollWidget.setWidget(v_widget)
        scrollWidget.setWidgetResizable(True) 
        scrollWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)     
        scrollWidget.setFixedWidth(400)   

        layoutWidgetsSpacer = QVBoxLayout()
        layoutWidgetsSpacer.addItem(QSpacerItem(0, 25))
        layoutWidgetsSpacer.addWidget(scrollWidget)
        layoutWidgetsSpacer.addItem(QSpacerItem(0, 4))
        
        self._layoutBig.addLayout(self._layoutAnts)
        self._layoutBig.addLayout(layoutWidgetsSpacer)

        self._SetDataTabs()
        self._SetCAN()
        self._SetStatuses()
        self._SetStartPolling()
        self._SetStartDiag()
        self._SetPowerMode()
        self._SetLogs()
        self._SetAntCheckBox()
        self._SetKeyCheckBox()
        self._SetAntCurrents()

        self._PrintData(False)
        
        widget = QWidget()
        widget.setLayout(self._layoutBig)
        self.setCentralWidget(widget)

        self.show()

    def _SetDataTabs(self):
        self._tabs = QTabWidget()
        self._tabs.addTab(self._SetAntsData(), "RSSIs")

        self._interactiveData = InteractiveData(askForPollingFunc = self._AskStartStopPolling)
        self._tabs.addTab(self._interactiveData.SetUpCalibrationDesk(), "Calibration")
        self._tabs.addTab(self._interactiveData.SetUpMeasureDesk(), "Measurement")
        
        self._layoutAnts.addWidget(self._tabs)

    def _SetAntsData(self): 
        self._antFrames = []
        self._keyFrames = []
        smallVLayout = []
        bigHLayout = QHBoxLayout()
        bigHLayout.setSpacing(0)
        for nAnt in range(self._AntAmount+1):
            smallVLayout.append(QVBoxLayout())
            self._antFrames.append(QFrame())
            self._antFrames[nAnt].setLayout(smallVLayout[nAnt])
            # self._antFrames[nAnt].setStyleSheet("border: 1px solid black")
            smallVLayout[nAnt].setContentsMargins(0,0,0,0)

            bigHLayout.addWidget(self._antFrames[nAnt])
            if nAnt == 0:
                bigHLayout.setStretch(nAnt, 0)
            else:
                bigHLayout.setStretch(nAnt, 1)


        self._RSSI_Widgets = []
        
        w = QLabel(f"")
        font = w.font()
        font.setPointSize(15)
        w.setFont(font)
        smallVLayout[0].addWidget(w)
        smallVLayout[0].setStretch(0, 0)
        smallVLayout[0].setSpacing(0)
        smallVLayout[0].setContentsMargins(0,0,0,0)

        keyFrameLocal = []
        for nKey in range(self._KeyAmount):
            keyFrameLocal.append(QFrame())

            w = QLabel(f"Key {nKey+1}")
            font = w.font()
            font.setPointSize(12)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            l = QVBoxLayout()
            l.addWidget(w)
            l.setSpacing(0)
            keyFrameLocal[nKey].setLayout(l)
            smallVLayout[0].addWidget(keyFrameLocal[nKey])
            smallVLayout[0].setStretch(nKey+1, 1)

        self._keyFrames.append(keyFrameLocal)

        for nAnt in range(1, self._AntAmount+1):
            w = QLabel(f"ANT {nAnt}")
            font = w.font()
            font.setPointSize(12)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            smallVLayout[nAnt].addWidget(w)
            smallVLayout[nAnt].setSpacing(0)

            templist = []
            keyFrameLocal = []
            for nKey in range(self._KeyAmount):
                keyFrameLocal.append(QFrame())

                k = QLabel()
                k.setFont(QFont('Courier', 14))
                k.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                
                groupbox = QGroupBox()
                font = groupbox.font()
                font.setPointSize(10)
                groupbox.setFont(font)
                Box = QVBoxLayout()
                Box.setSpacing(0)
                groupbox.setLayout(Box)
                Box.addWidget(k)

                l = QVBoxLayout()
                l.addWidget(groupbox)
                l.setSpacing(0)
                keyFrameLocal[nKey].setLayout(l)

                smallVLayout[nAnt].addWidget(keyFrameLocal[nKey])
                smallVLayout[nAnt].setStretch(nKey+1, 1)
                
                templist.append(k)

            self._keyFrames.append(keyFrameLocal)

            self._RSSI_Widgets.append(templist)

        w = QWidget()
        w.setLayout(bigHLayout)

        scrollAntsData = QScrollArea()
        scrollAntsData.setWidget(w)
        scrollAntsData.setWidgetResizable(True) 

        return scrollAntsData

    def _SetCAN(self):
        CANgroupbox = QGroupBox("CAN")
        font = CANgroupbox.font()
        font.setPointSize(10)
        CANgroupbox.setFont(font)
        CANbox = QVBoxLayout()
        CANbox.setSpacing(10)
        CANgroupbox.setLayout(CANbox)

        # Set USB port state Label
        self._widgetUsbState = QLabel("Systec Disconnected")
        font = self._widgetUsbState.font()
        font.setPointSize(12)
        self._widgetUsbState.setFont(font)
        self._widgetUsbState.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        CANbox.addWidget(self._widgetUsbState)

        # Set USB port connect button Label
        self._widgetUsbConnect = QPushButton("Connect")
        font = self._widgetUsbConnect.font()
        font.setPointSize(12)
        self._widgetUsbConnect.setFont(font)
        self._widgetUsbConnect.clicked.connect(self._BusInitHandler)
        self._widgetUsbConnect.setFlat(False)
        CANbox.addWidget(self._widgetUsbConnect)

        # Set USB port connect button Label
        widgetUsbDisConnect = QPushButton("Disconnect")
        font = widgetUsbDisConnect.font()
        font.setPointSize(12)
        widgetUsbDisConnect.setFont(font)
        widgetUsbDisConnect.clicked.connect(self._BusDeInitHandler)
        CANbox.addWidget(widgetUsbDisConnect)

        # Set msg receiving Period Label
        self._widgetCanMsgPeriod = QLabel()
        font = self._widgetCanMsgPeriod.font()
        font.setPointSize(12)
        self._widgetCanMsgPeriod.setFont(font)
        self._widgetCanMsgPeriod.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        CANbox.addWidget(self._widgetCanMsgPeriod)
     
        self._layoutWidgets.addWidget(CANgroupbox)

    def _SetStatuses(self):
        StatusGroupbox = QGroupBox("Statuses")
        font = StatusGroupbox.font()
        font.setPointSize(10)
        StatusGroupbox.setFont(font)
        StatusesBox = QVBoxLayout()
        StatusesBox.setSpacing(15)
        StatusGroupbox.setLayout(StatusesBox)
    
        # Set last key with pressed button num
        self._widgetLastKeyNum = QLabel()
        font = self._widgetLastKeyNum.font()
        font.setPointSize(12)
        self._widgetLastKeyNum.setFont(font)
        self._widgetLastKeyNum.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        StatusesBox.addWidget(self._widgetLastKeyNum)

        # Set was auth OK or not
        self._widgetAuth = QLabel() 
        font = self._widgetAuth.font()
        font.setPointSize(12)
        self._widgetAuth.setFont(font)
        self._widgetAuth.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        StatusesBox.addWidget(self._widgetAuth)

        horLayout = QHBoxLayout()

        self._widgetAuthsDone = QLabel()
        font = self._widgetAuthsDone.font()
        font.setPointSize(12)
        self._widgetAuthsDone.setFont(font)
        self._widgetAuthsDone.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        StatusesBox.addWidget(self._widgetAuthsDone)

        self._widgetAuthCheckBox = QCheckBox()
        font = self._widgetAuthCheckBox.font()
        font.setPointSize(11)
        self._widgetAuthCheckBox.setFont(font)
        self._widgetAuthCheckBox.setChecked(True)
        self._widgetAuthCheckBox.setText("Perform auth")
        self._widgetAuthCheckBox.stateChanged.connect(self._performAuthState)
        horLayout.addWidget(self._widgetAuthCheckBox)

        horLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        StatusesBox.addLayout(horLayout)

        self._layoutWidgets.addWidget(StatusGroupbox)

    def _SetStartPolling(self):
        StartPollingGroupbox = QGroupBox("Polling State")
        font = StartPollingGroupbox.font()
        font.setPointSize(10)
        StartPollingGroupbox.setFont(font)
        StartPollingBox = QVBoxLayout()
        StartPollingBox.setSpacing(15)
        StartPollingGroupbox.setLayout(StartPollingBox)
    
        widgetPollingsAmount = QLabel("Pollings Amount: ")
        font = widgetPollingsAmount.font()
        font.setPointSize(12)
        widgetPollingsAmount.setFont(font)
        widgetPollingsAmount.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        StartPollingBox.addWidget(widgetPollingsAmount)

        validator = QIntValidator(1, 250)
        self._widgetPollingAmount = QLineEdit("3")
        self._widgetPollingAmount.setValidator(validator)
        font = self._widgetPollingAmount.font()
        font.setPointSize(12)
        self._widgetPollingAmount.setFont(font)
        self._widgetPollingAmount.setMaximumHeight(200)
        self._widgetPollingAmount.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        StartPollingBox.addWidget(self._widgetPollingAmount)

        self._widgetPollingsDone = QLabel()
        font = self._widgetPollingsDone.font()
        font.setPointSize(12)
        self._widgetPollingsDone.setFont(font)
        self._widgetPollingsDone.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        StartPollingBox.addWidget(self._widgetPollingsDone)

        self._widgetStartPolling = QPushButton("Start Polling")
        font = self._widgetStartPolling.font()
        font.setPointSize(12)
        self._widgetStartPolling.setFont(font)
        StartPollingBox.addWidget(self._widgetStartPolling)
        self._widgetStartPolling.clicked.connect(self._StartPollingHandler)

        self._widgetStartRepeatPolling = QPushButton("Start Repeat Polling")
        font = self._widgetStartRepeatPolling.font()
        font.setPointSize(12)
        self._widgetStartRepeatPolling.setFont(font)
        StartPollingBox.addWidget(self._widgetStartRepeatPolling)
        self._widgetStartRepeatPolling.clicked.connect(self._StartRepeatPollingHandler)

        self._layoutWidgets.addWidget(StartPollingGroupbox)

    def _SetStartDiag(self):
        StartDiagGroupbox = QGroupBox("Ant impedances")
        font = StartDiagGroupbox.font()
        font.setPointSize(10)
        StartDiagGroupbox.setFont(font)
        StartDiagBox = QVBoxLayout()
        StartDiagBox.setSpacing(15)
        StartDiagGroupbox.setLayout(StartDiagBox)

        self._widgetAntImps = []

        inRow = 3
        for nAnt in range(0, int(self._AntAmount/inRow+1)):
            h = QHBoxLayout()
            added = False
            for nCnt in range(inRow):
                idx = nAnt*inRow + nCnt
                if(idx < self._AntAmount):
                    self._widgetAntImps.append(QLabel())
                    font = self._widgetAntImps[idx].font()
                    font.setPointSize(11)
                    self._widgetAntImps[idx].setFont(font)
                    h.addWidget(self._widgetAntImps[idx])
                    # h.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    added = True
            if added:
                StartDiagBox.addLayout(h)
                added = False
        
        self._antImpsUpdate([0,0,0,0,0,0])

        self._widgetDiagStatuses = QComboBox()
        StartDiagBox.addWidget(self._widgetDiagStatuses)

        self._widgetAntDiag = QPushButton("Get ants impedance and calibrate")
        font = self._widgetAntDiag.font()
        font.setPointSize(12)
        self._widgetAntDiag.setFont(font)
        StartDiagBox.addWidget(self._widgetAntDiag)
        self._widgetAntDiag.clicked.connect(self._PerformAntDiagHandler)

        self._layoutWidgets.addWidget(StartDiagGroupbox)

    def _SetPowerMode(self):
        PowerModeGroupbox = QGroupBox("Power Mode")
        font = PowerModeGroupbox.font()
        font.setPointSize(10)
        PowerModeGroupbox.setFont(font)
        StatusesBox = QVBoxLayout()
        StatusesBox.setSpacing(15)
        PowerModeGroupbox.setLayout(StatusesBox)

        # Show Power Mode
        self._widgetPwrMode = QLabel("Normal Mode")
        font =  self._widgetPwrMode.font()
        font.setPointSize(12)
        self._widgetPwrMode.setFont(font)
        self._widgetPwrMode.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        StatusesBox.addWidget(self._widgetPwrMode)

        # Set Change Power Mode button Label
        widgetChMode = QPushButton("Change Power Mode")
        font = widgetChMode.font()
        font.setPointSize(12)
        widgetChMode.setFont(font)
        StatusesBox.addWidget(widgetChMode)
        widgetChMode.clicked.connect(self._ChangeModeHandler)

        self._layoutWidgets.addWidget(PowerModeGroupbox)

    def _SetLogs(self):
        groupbox = QGroupBox("Logs")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        Logbox = QVBoxLayout()
        Logbox.setSpacing(10)
        groupbox.setLayout(Logbox)
    
        # Get log msg
        self._widgetLogMsg = QLineEdit()
        font = self._widgetLogMsg.font()
        font.setPointSize(12)
        self._widgetLogMsg.setFont(font)
        self._widgetLogMsg.setMaximumHeight(200)
        Logbox.addWidget(self._widgetLogMsg)

        # Set button to send log
        widgetAddLog = QPushButton("Add LOG")
        font = widgetAddLog.font()
        font.setPointSize(12)
        widgetAddLog.setFont(font)
        Logbox.addWidget(widgetAddLog)
        widgetAddLog.clicked.connect(self._PrintSigleLog)

        self._layoutWidgets.addWidget(groupbox)

    def _SetAntCurrents(self):
        groupbox = QGroupBox("Ants currents")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        Currbox = QVBoxLayout()
        Currbox.setSpacing(10)
        groupbox.setLayout(Currbox)
    
        self._widgetCurrSlider = QSlider(Qt.Horizontal)
        self._widgetCurrSlider.setRange(1, 0x40)
        self._widgetCurrSlider.setValue(0x20)
        self._widgetCurrSlider.setSingleStep(1)
        self._widgetCurrSlider.setPageStep(2)
        self._widgetCurrSlider.setTickInterval(0x1F)
        self._widgetCurrSlider.setTickPosition(QSlider.TicksBelow)
        self._widgetCurrSlider.valueChanged.connect(self._currentChangedHandler)
        Currbox.addWidget(self._widgetCurrSlider)

        self._widAntCurrValue = QLabel()
        font = self._widAntCurrValue.font()
        font.setPointSize(12)
        self._widAntCurrValue.setFont(font)
        self._widAntCurrValue.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        Currbox.addWidget(self._widAntCurrValue)
        self._currentChangedHandler()        

        self._layoutWidgets.addWidget(groupbox)

    def _SetAntCheckBox(self):
        groupbox = QGroupBox("Ants for polling")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        Choosebox = QVBoxLayout()
        Choosebox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        Choosebox.setSpacing(15)
        groupbox.setLayout(Choosebox)
    

        self._widgetAntCheckBox = []

        inRow = 3
        for nAnt in range(0, int(self._AntAmount/inRow+1)):
            h = QHBoxLayout()
            added = False
            for nCnt in range(inRow):
                idx = nAnt*inRow + nCnt
                if(idx < self._AntAmount):
                    self._widgetAntCheckBox.append(QCheckBox())
                    font = self._widgetAntCheckBox[idx].font()
                    font.setPointSize(11)
                    self._widgetAntCheckBox[idx].setFont(font)
                    self._widgetAntCheckBox[idx].setChecked(True)
                    self._widgetAntCheckBox[idx].stateChanged.connect(self._updateAntMask)
                    self._widgetAntCheckBox[idx].setText(f"Ant {idx+1}")
                    h.addWidget(self._widgetAntCheckBox[idx])
                    h.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    added = True

            if added:
                Choosebox.addLayout(h)
                added = False

        self._layoutWidgets.addWidget(groupbox)

    def _SetKeyCheckBox(self):
        groupbox = QGroupBox("Keys for polling")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        Choosebox = QVBoxLayout()
        Choosebox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        Choosebox.setSpacing(15)
        groupbox.setLayout(Choosebox)
    
        self._widgetKeyCheckBox = []

        inRow = 3
        for nKey in range(0, int(self._KeyAmount/inRow+1)):
            h = QHBoxLayout()
            added = False
            for nCnt in range(inRow):
                idx = nKey*inRow + nCnt
                if(idx < self._KeyAmount):
                    self._widgetKeyCheckBox.append(QCheckBox())
                    font = self._widgetKeyCheckBox[idx].font()
                    font.setPointSize(11)
                    self._widgetKeyCheckBox[idx].setFont(font)
                    self._widgetKeyCheckBox[idx].setChecked(True)
                    self._widgetKeyCheckBox[idx].stateChanged.connect(self._updateKeyMask)
                    self._widgetKeyCheckBox[idx].setText(f"Key {idx+1}")
                    h.addWidget(self._widgetKeyCheckBox[idx])
                    h.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    added = True
                
            if added:
                Choosebox.addLayout(h)
                added = False

        self._layoutWidgets.addWidget(groupbox)

    def _CanInit(self):
        # Create a QThread and Worker object
        self._CanThread = QThread()
        self._CanWorker = CanSendRecv(self._AntAmount, self._KeyAmount)
        self._CanWorker.moveToThread(self._CanThread)

        # Connect signals and slots
        self._CanThread.started.connect(self._CanWorker.Start)
        self._CanWorker.canInited.connect(self._BusInitedCallback)
        self._CanWorker.canDeInited.connect(self._BusDeInitedCallback)
        self._CanWorker.keyNumIdReceived.connect(self._LastKeyIdUpdate)
        self._CanWorker.keyAuthReceived.connect(self._LastAuthUpdate)
        self._CanWorker.canReceivedAll.connect(self._PrintData)
        self._CanWorker.antImpsReceived.connect(self._antImpsUpdate)
        self._CanWorker.antDiagStateReceived.connect(self._antDiagUpdate)
        
        self._CanThread.start()

    def _restoreData(self):
        try:
            os.mkdir(f"{self._store_data_path}/")
        except: pass

        try:
            keysAntsData = yaml.load(open(f'{self._store_data_path}/keys_ants'), yaml.SafeLoader)
            for nCnt in range(0, len(self._widgetAntCheckBox)):
                if nCnt not in keysAntsData['ants']:
                    self._widgetAntCheckBox[nCnt].setChecked(False)

            for nCnt in range(0, len(self._widgetKeyCheckBox)):
                if nCnt not in keysAntsData['keys']:
                    self._widgetKeyCheckBox[nCnt].setChecked(False)

            if keysAntsData['auth'] == 0:
                self._widgetAuthCheckBox.setChecked(False)

        except:
            self._logger.info("Create new \"keys_ants\" file")
            to_yaml = {
                'ants': [0, 1, 2, 3, 4, 5],
                'keys': [0, 1, 2, 3, 4],
                'auth': 1
            }
            with open(f'{self._store_data_path}/keys_ants', 'w') as f:
                yaml.dump(to_yaml, f)

    def _BusInitHandler(self):
        self._widgetUsbConnect.setFlat(True)
        self._CanWorker.BusInit()
        self._widgetUsbConnect.setFlat(False)

    def _BusDeInitHandler(self):
        self._StopPolling()
        self._CanWorker.BusDeInit()

    def _BusInitedCallback(self):
        self._widgetUsbState.setText("Systec Connected")
        self._widgetUsbState.setStyleSheet("color: green;")

    def _BusDeInitedCallback(self):
        self._widgetUsbState.setText("Systec Disconnected")
        self._widgetUsbState.setStyleSheet("color: black;")
        self._PrintData(False)
        
    def _updateAntMask(self):
        AntMask = 0
        for nCnt in range(0, len(self._widgetAntCheckBox)):
            if self._widgetAntCheckBox[nCnt].isChecked():
                AntMask |= 1 << nCnt
                self._antFrames[nCnt+1].show()
            else:
                self._antFrames[nCnt+1].hide()

        self._CanWorker.SetAntMask(AntMask)

    def _updateKeyMask(self):
        for nAnt in range(0, len(self._widgetAntCheckBox)+1):
            for nKey in range(0, len(self._widgetKeyCheckBox)):
                if self._widgetKeyCheckBox[nKey].isChecked():
                    self._keyFrames[nAnt][nKey].show()
                else:
                    self._keyFrames[nAnt][nKey].hide()

    def _LastKeyIdUpdate(self, lastPressedKey):
        self._widgetLastKeyNum.setText(f"Last Key Pressed Num: {lastPressedKey}\t\t")

    def _LastAuthUpdate(self, authStatus):
        if self._widgetAuthCheckBox.isChecked() and self._pollingInProgress:
            self._AuthsDone += 1
            if self._AuthsDone > 250:
                self._AuthsDone = 1

            self._widgetAuthsDone.setText(f'Auth msg got: {self._AuthsDone}')

            if authStatus:
                self._authStatus = True
                self._widgetAuth.setText(f'Auth: OK')
                self._widgetAuth.setStyleSheet("color: green;")
            else:
                self._authStatus = False
                self._widgetAuth.setText(f'Auth: Fail')
                self._widgetAuth.setStyleSheet("color: red;")

    def _antImpsUpdate(self, imps: list):
        for i in range(len(imps)):
            self._widgetAntImps[i].setText(f'Ant {i+1}: {imps[i]} Ω')

    def _antDiagUpdate(self, statuses: list):
        self._widgetDiagStatuses.clear()
        self._widgetDiagStatuses.addItems(statuses)                            

    def _currentChangedHandler(self):
        val = self._widgetCurrSlider.value()
        self._widAntCurrValue.setText('Current: %.2f mA' % (15.625*(val)))
        try:
            self._CanWorker.setCurrent(val)
        except: pass

    def _ChangeModeHandler(self):
        if self._PowerMode == 0:
            self._PowerMode = 1 #PowerDown
            self._widgetPwrMode.setText("Power Down")
        else:
            self._PowerMode = 0 #Normal Mode
            self._widgetPwrMode.setText("Normal Mode")
        
        self._CanWorker.SetPowerMode(self._PowerMode)

    def _StartPollingHandler(self):
        if(self._widgetStartPolling.text() == "Stop Polling"):
            self._StopPolling()
            return

        self._pollingInProgress = True
        self._PollingsNeeded = int(self._widgetPollingAmount.text())
        if(self._PollingsNeeded <= 0):
            self._PollingsNeeded = 1
            self._widgetPollingAmount.setText(str(self._PollingsNeeded))
        elif(self._PollingsNeeded >= 250):
            self._PollingsNeeded = 250
            self._widgetPollingAmount.setText(str(self._PollingsNeeded))

        self._widgetStartPolling.setText("Stop Polling")
        self._widgetStartRepeatPolling.setText("Start Repeat Polling")
        self._PollingsDone = 0
        self._AuthsDone = 0
        self._widgetPollingsDone.setText(f"Target: {self._PollingsNeeded}; Done: {self._PollingsDone}")
        self._widgetPollingsDone.setStyleSheet("color: black;")

        self._CanWorker.StartPoll(self._PollingsNeeded)

    def _StopPolling(self):
        self._pollingInProgress = False
        self._widgetStartPolling.setText("Start Polling")
        self._widgetStartRepeatPolling.setText("Start Repeat Polling")
        self._PollingsDone = 0
        self._widgetPollingsDone.setText(f"Target: - ; Done: -")
        self._widgetPollingsDone.setStyleSheet("color: black;")
        self._widgetAuthsDone.setText(f'Auth msg got: -')
        self._AuthsDone = 0
        self._PollingsNeeded = 0

        self._CanWorker.StartPoll(255)

    def _StartRepeatPollingHandler(self):
        if(self._widgetStartRepeatPolling.text() == "Stop Repeat Polling"):
            self._StopPolling()
            return
        
        self._pollingInProgress = True
        self._widgetStartPolling.setText("Start Polling")
        self._widgetStartRepeatPolling.setText("Stop Repeat Polling")
        self._PollingsDone = 0
        self._AuthsDone = 0
        self._widgetPollingsDone.setText(f"Target: ∞ ; Done: {self._PollingsDone}")
        self._widgetPollingsDone.setStyleSheet("color: black;")
        self._PollingsNeeded = 0

        self._CanWorker.StartPoll(254)

    def _PerformAntDiagHandler(self):
        self._CanWorker.performDiag()

    def _performAuthState(self):
        if self._widgetAuthCheckBox.isChecked():
            self._CanWorker.SetAuthMode(1)
        else:
            self._CanWorker.SetAuthMode(0)
            self._widgetAuth.setText(f'Auth: None\t')
            self._widgetAuth.setStyleSheet("color: black;")
            self._widgetAuthsDone.setText(f'Auth msg got: -')
            self._AuthsDone = 0

    def _AskStartStopPolling(self, start: bool = False):
        if(self._widgetStartPolling.text() == "Stop Polling"):
            self._StopPolling()

        if start:
            self._StartPollingHandler()

    def _PrintData(self, res: bool):
        if not res:
            self._widgetCanMsgPeriod.setText("Msg Period: 0 ms")
            self._widgetAuth.setText(f'Auth: None\t')
            self._widgetAuth.setStyleSheet("color: black;")
            self._widgetAuthsDone.setText(f'Auth msg got: -')
            self._widgetLastKeyNum.setText(f"Last Key Pressed Num: None\t")
            Data = np.zeros((((self._AntAmount, self._KeyAmount, 3))), dtype=int)
            self._widgetPollingsDone.setText(f"Target: - ; Done: -")
            self._PollingsDone = 0

        else:
            Data = self._CanWorker.Data
            self._widgetCanMsgPeriod.setText(f"Msg Period: {int(self._CanWorker.TimeBetweenMsgs)} ms")

            isPollDone = False
            if (self._PollingsNeeded != 0 and self._pollingInProgress):
                self._PollingsDone += 1
                self._widgetPollingsDone.setText(f"Target: {self._PollingsNeeded}; Done: {self._PollingsDone}")
        
                if (self._PollingsDone == self._PollingsNeeded):
                    self._widgetPollingsDone.setStyleSheet("color: green;")
                    isPollDone = True
                    self._widgetStartPolling.setText("Start Polling")
                else:
                    self._widgetPollingsDone.setStyleSheet("color: black;")

            elif (self._pollingInProgress):
                self._PollingsDone += 1
                if self._PollingsDone > 250:
                    self._PollingsDone = 1
                    
                self._widgetPollingsDone.setText(f"Target: ∞ ; Done: {self._PollingsDone}")

            self._interactiveData.RememberData(Data, isPollDone)
            self._PrintLogData()

        for nAnt in range(self._AntAmount):
            for nKey in range(self._KeyAmount):
                self._RSSI_Widgets[nAnt][nKey].setText(f"X: {' '*(3-len(str(Data[nAnt][nKey][0])))}{Data[nAnt][nKey][0]}\n" +
                                                       f"Y: {' '*(3-len(str(Data[nAnt][nKey][1])))}{Data[nAnt][nKey][1]}\n" +
                                                       f"Z: {' '*(3-len(str(Data[nAnt][nKey][2])))}{Data[nAnt][nKey][2]}")
   
    def _PrintLogData(self): 
        time_hms = time.strftime("%H:%M:%S", time.localtime())
        time_dmy = time.strftime("%d/%m/%Y", time.localtime())
        
        bold = self._workbook.add_format({'bold': True})

        self._worksheet.write(self._row, self._column,   'Time: ', bold)
        self._worksheet.write(self._row, self._column+1, f'{time_hms}')
        self._worksheet.write(self._row, self._column+2, 'Date: ', bold)
        self._worksheet.write(self._row, self._column+3, f'{time_dmy}')
        
        if self._authStatus:
            self._worksheet.write(self._row, self._column+5, 'Auth OK', bold)
        else:
            self._worksheet.write(self._row, self._column+5, 'Auth Fail', bold)

        for nKey in range(self._KeyAmount):
            self._worksheet.write(self._row+3+nKey, self._column, f"KEY {nKey+1}")
    
        Data = self._CanWorker.Data

        for i in range(self._AntAmount):
            self._worksheet.write(self._row+1, i*4+self._column+2, f"ANTENNA {i+1}")

            self._worksheet.write(self._row+2, i*4+self._column+1, "RSSI X")
            self._worksheet.write(self._row+2, i*4+self._column+2, "RSSI Y")
            self._worksheet.write(self._row+2, i*4+self._column+3, "RSSI Z")

            for nKey in range(self._KeyAmount):
                self._worksheet.write_number(self._row+3+nKey, i*4+self._column+1, Data[i][nKey][0])
                self._worksheet.write_number(self._row+3+nKey, i*4+self._column+2, Data[i][nKey][1])                 
                self._worksheet.write_number(self._row+3+nKey, i*4+self._column+3, Data[i][nKey][2])

        self._row += 9

    def _PrintSigleLog(self):
        time_hms = time.strftime("%H:%M:%S", time.localtime())
        time_dmy = time.strftime("%d/%m/%Y", time.localtime())
        
        bold = self._workbook.add_format({'bold': True})

        self._worksheet_single.write(self._row_single, self._column_single,   'Time: ', bold)
        self._worksheet_single.write(self._row_single, self._column_single+1, f'{time_hms}')
        self._worksheet_single.write(self._row_single, self._column_single+2, 'Date: ', bold)
        self._worksheet_single.write(self._row_single, self._column_single+3, f'{time_dmy}')

        if self._authStatus:
            self._worksheet_single.write(self._row_single, self._column_single+5, 'Auth OK', bold)
        else:
            self._worksheet_single.write(self._row_single, self._column_single+5, 'Auth Fail', bold)

        msg = self._widgetLogMsg.text()
        self._worksheet_single.write(self._row_single, self._column_single+7, 'Message: ', bold)
        self._worksheet_single.write(self._row_single, self._column_single+8, f'{msg}')

        for nKey in range(self._KeyAmount):
            self._worksheet_single.write(self._row_single+3+nKey, self._column_single, f"KEY {nKey+1}")

        printData = self._CanWorker.Data

        for i in range(6):
            self._worksheet_single.write(self._row_single+1, i*4+self._column_single+2, f"ANTENNA {i+1}")

            self._worksheet_single.write(self._row_single+2, i*4+self._column_single+1, "RSSI X")
            self._worksheet_single.write(self._row_single+2, i*4+self._column_single+2, "RSSI Y")
            self._worksheet_single.write(self._row_single+2, i*4+self._column_single+3, "RSSI Z")

            for nKey in range(self._KeyAmount):
                self._worksheet_single.write_number(self._row_single+3+nKey, i*4+self._column_single+1, printData[i][nKey][0])
                self._worksheet_single.write_number(self._row_single+3+nKey, i*4+self._column_single+2, printData[i][nKey][1])                 
                self._worksheet_single.write_number(self._row_single+3+nKey, i*4+self._column_single+3, printData[i][nKey][2])

        self._row_single += 9
     

def app_start():
    app = QApplication([])

    window = MainWindow()

    app.exec()

if __name__ == "__main__": 
    app_start() 

# TIME STAMP

# pyinstaller --onefile --hidden-import=can.interfaces.systec -w PKE_Setup.py
# pyinstaller PKE_Setup.py --hidden-import=can.interfaces.systec --noconsole --add-data "pictures;pictures" --name PKE_Setup --noconfirm