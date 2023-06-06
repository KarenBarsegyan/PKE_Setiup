from PyQt5.QtWidgets import (
    QMainWindow, QCheckBox, QVBoxLayout, 
    QApplication, QLabel, QHBoxLayout, 
    QWidget, QPushButton, QLineEdit, 
    QGroupBox, QGridLayout, QStackedLayout,
    QFrame
)
from PyQt5.QtCore import Qt, QSize, QThread
import numpy as np
import time
import xlsxwriter
import logging
from CAN import CanSendRecv
import os
    

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self._PowerMode = 0
        self._AntAmount = 6
        self._KeyAmount = 5

        self._InitLogger()
        self._Initworksheet()
        self._SetApp()
        self._CanInit()

    def __del__(self):
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

    def _InitLogger(self):
        logs_path = "app_logs"
        try:
            os.mkdir(f"{logs_path}/")
        except: pass

        self._logger = logging.getLogger(__name__)
        f_handler = logging.FileHandler(f'{logs_path}/{__name__}.log')
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
        # self.resize(QSize(1700, 1000))
        # self.setStyleSheet("background-color: white;")

        self._layoutBig = QHBoxLayout()
        self._layoutAnts = QHBoxLayout()
        self._layoutAnts.setSpacing(0)

        self._layoutWidgets = QVBoxLayout()
        self._layoutWidgets.setSpacing(30)
        v_widget = QWidget()
        v_widget.setLayout(self._layoutWidgets)
        v_widget.setFixedWidth(350)            

        self._layoutBig.addLayout(self._layoutAnts)
        self._layoutBig.addWidget(v_widget)

        self._SetAntsData()
        self._SetCAN()
        self._SetStatuses()
        self._SetPowerMode()
        self._SetLogs()
        self._SetCheckBox()

        self._PrintData(False)
        
        widget = QWidget()
        widget.setLayout(self._layoutBig)
        self.setCentralWidget(widget)

        self.show()

    def _SetAntsData(self): 
        self._antFrames = []
        gridAntsLayout = []
        for nAnt in range(self._AntAmount+1):
            gridAntsLayout.append(QGridLayout())
            self._antFrames.append(QFrame())
            self._antFrames[nAnt].setLayout(gridAntsLayout[nAnt])
            # self._antFrames[nAnt].setStyleSheet("border: 1px solid black")
            gridAntsLayout[nAnt].setSpacing(5)

            if nAnt == 0:
                gridAntsLayout[nAnt].setColumnMinimumWidth(0, 80)

            gridAntsLayout[nAnt].setRowMinimumHeight(0, 50)
            for i in range(self._KeyAmount): gridAntsLayout[nAnt].setRowMinimumHeight(i+1, 150)

            gridAntsLayout[nAnt].setRowStretch(0, 0)
            for i in range(self._KeyAmount): gridAntsLayout[nAnt].setRowStretch(i+1, 1)

            self._layoutAnts.addWidget(self._antFrames[nAnt])
            if nAnt == 0:
                self._layoutAnts.setStretch(nAnt, 0)
            else:
                self._layoutAnts.setStretch(nAnt, 1)


        self._RSSI_Widgets = []

        for nKey in range(self._KeyAmount):
            w = QLabel(f"Key {nKey+1}")
            font = w.font()
            font.setPointSize(15)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            gridAntsLayout[0].addWidget(w, nKey+1, 0)

        for nAnt in range(1, self._AntAmount+1):
            w = QLabel(f"ANT {nAnt}")
            font = w.font()
            font.setPointSize(15)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            # w.setStyleSheet("border: 1px solid black")
            gridAntsLayout[nAnt].addWidget(w, 0, nAnt)

            templist = []
            for nKey in range(self._KeyAmount):
                k = QLabel()
                font = k.font()
                font.setPointSize(14)
                k.setFont(font)
                k.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                # k.setStyleSheet("border: 1px solid black")
                
                groupbox = QGroupBox()
                font = groupbox.font()
                font.setPointSize(10)
                groupbox.setFont(font)
                Box = QVBoxLayout()
                Box.setSpacing(20)
                groupbox.setLayout(Box)
                Box.addWidget(k)

                gridAntsLayout[nAnt].addWidget(groupbox, nKey+1, nAnt)
                
                templist.append(k)

            self._RSSI_Widgets.append(templist)

    def _SetCAN(self):
        CANgroupbox = QGroupBox("CAN")
        font = CANgroupbox.font()
        font.setPointSize(10)
        CANgroupbox.setFont(font)
        CANbox = QVBoxLayout()
        CANbox.setSpacing(20)
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
        StatusesBox.setSpacing(20)
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

        self._layoutWidgets.addWidget(StatusGroupbox)

    def _SetPowerMode(self):
        PowerModeGroupbox = QGroupBox("Power Mode")
        font = PowerModeGroupbox.font()
        font.setPointSize(10)
        PowerModeGroupbox.setFont(font)
        StatusesBox = QVBoxLayout()
        StatusesBox.setSpacing(20)
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
        Logbox.setSpacing(20)
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

    def _SetCheckBox(self):
        groupbox = QGroupBox("Ants for polling")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        Choosebox = QVBoxLayout()
        Choosebox.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        Choosebox.setSpacing(20)
        groupbox.setLayout(Choosebox)
    

        self._widgetCheckBox = []

        for nCnt in range(0, int(self._AntAmount/2+1)):
            if(nCnt*2 < self._AntAmount):
                self._widgetCheckBox.append(QCheckBox())
                h = QHBoxLayout()
                font = self._widgetCheckBox[nCnt*2].font()
                font.setPointSize(11)
                self._widgetCheckBox[nCnt*2].setFont(font)
                self._widgetCheckBox[nCnt*2].setChecked(True)
                self._widgetCheckBox[nCnt*2].stateChanged.connect(self._updateAntMask)
                self._widgetCheckBox[nCnt*2].setText(f"Ant {nCnt*2+1}")
                h.addWidget(self._widgetCheckBox[nCnt*2])

            if(nCnt*2+1 < self._AntAmount):
                self._widgetCheckBox.append(QCheckBox())
                font = self._widgetCheckBox[nCnt*2+1].font()
                font.setPointSize(11)
                self._widgetCheckBox[nCnt*2+1].setFont(font)
                self._widgetCheckBox[nCnt*2+1].setChecked(True)
                self._widgetCheckBox[nCnt*2+1].stateChanged.connect(self._updateAntMask)
                self._widgetCheckBox[nCnt*2+1].setText(f"Ant {nCnt*2+2}")
                h.addWidget(self._widgetCheckBox[nCnt*2+1])

            if(nCnt*2 < self._AntAmount):
                Choosebox.addLayout(h)

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
        self._CanWorker.canReceivedAll.connect(self._PrintData)
        
        self._CanThread.start()

    def _BusInitHandler(self):
        self._widgetUsbConnect.setFlat(True)
        self._CanWorker.BusInit()
        self._widgetUsbConnect.setFlat(False)

    def _BusDeInitHandler(self):
        self._CanWorker.BusDeInit()

    def _BusInitedCallback(self):
        self._widgetUsbState.setText("Systec Connected")

    def _BusDeInitedCallback(self):
        self._widgetUsbState.setText("Systec Disconnected")
        self._PrintData(False)
        
    def _updateAntMask(self):
        AntMask = 0
        for nCnt in range(0, len(self._widgetCheckBox)):
            if self._widgetCheckBox[nCnt].isChecked():
                AntMask |= 1 << nCnt
                self._antFrames[nCnt+1].show()
            else:
                self._antFrames[nCnt+1].hide()

        self._layoutAnts.activate

        self._CanWorker.SetAntMask(AntMask)

    def _LastKeyIdUpdate(self, lastPressedKey):
        self._widgetLastKeyNum.setText(f"Last Key Pressed Num: {lastPressedKey}\t\t")

    def _ChangeModeHandler(self):
        if self._PowerMode == 0:
            self._PowerMode = 1 #PowerDown
            self._widgetPwrMode.setText("Power Down")
        else:
            self._PowerMode = 0 #Normal Mode
            self._widgetPwrMode.setText("Normal Mode")
        
        self._CanWorker.SetPowerMode(self._PowerMode)

    def _PrintData(self, res: bool):
        if not res:
            self._widgetCanMsgPeriod.setText("Msg Period: 0 ms")
            self._widgetAuth.setText(f'Auth: None\t')
            self._widgetLastKeyNum.setText(f"Last Key Pressed Num: None\t")
            Data = np.zeros(((self._AntAmount, self._KeyAmount, 3)))

        else:
            Data = self._CanWorker.Data
            self._widgetCanMsgPeriod.setText(f"Msg Period: {int(self._CanWorker.TimeBetweenMsgs)} ms")
            if self._CanWorker.AuthStatus:
                self._widgetAuth.setText(f'Auth: OK')
            else:
                self._widgetAuth.setText(f'Auth: Fail')

            self._PrintLogData()

        for nAnt in range(self._AntAmount):
            for nKey in range(self._KeyAmount):
                self._RSSI_Widgets[nAnt][nKey].setText(f"RSSI_X: {' '*(3-len(str(int(Data[nAnt][nKey][0]))))}{int(Data[nAnt][nKey][0])}\n" +
                                                       f"RSSI_Y: {' '*(3-len(str(int(Data[nAnt][nKey][1]))))}{int(Data[nAnt][nKey][1])}\n" +
                                                       f"RSSI_Z: {' '*(3-len(str(int(Data[nAnt][nKey][2]))))}{int(Data[nAnt][nKey][2])}")
   
    def _PrintLogData(self): 
        time_hms = time.strftime("%H:%M:%S", time.localtime())
        time_dmy = time.strftime("%d/%m/%Y", time.localtime())
        
        bold = self._workbook.add_format({'bold': True})

        self._worksheet.write(self._row, self._column,   'Time: ', bold)
        self._worksheet.write(self._row, self._column+1, f'{time_hms}')
        self._worksheet.write(self._row, self._column+2, 'Date: ', bold)
        self._worksheet.write(self._row, self._column+3, f'{time_dmy}')
        
        if self._CanWorker.AuthStatus:
            self._worksheet.write(self._row, self._column+5, 'Auth OK', bold)
        else:
            self._worksheet.write(self._row, self._column+5, 'Auth Fail', bold)

        for nKey in range(self._KeyAmount):
            self._worksheet.write(self._row+3+nKey, self._column, f"KEY {nKey+1}")
    
        printData = self._CanWorker.Data

        for i in range(6):
            self._worksheet.write(self._row+1, i*4+self._column+2, f"ANTENNA {i+1}")

            self._worksheet.write(self._row+2, i*4+self._column+1, "RSSI X")
            self._worksheet.write(self._row+2, i*4+self._column+2, "RSSI Y")
            self._worksheet.write(self._row+2, i*4+self._column+3, "RSSI Z")

            for nKey in range(self._KeyAmount):
                self._worksheet.write_number(self._row+3+nKey, i*4+self._column+1, printData[i][nKey][0])
                self._worksheet.write_number(self._row+3+nKey, i*4+self._column+2, printData[i][nKey][1])                 
                self._worksheet.write_number(self._row+3+nKey, i*4+self._column+3, printData[i][nKey][2])

        self._row += 9

    def _PrintSigleLog(self):
        time_hms = time.strftime("%H:%M:%S", time.localtime())
        time_dmy = time.strftime("%d/%m/%Y", time.localtime())
        
        bold = self._workbook.add_format({'bold': True})

        self._worksheet_single.write(self._row_single, self._column_single,   'Time: ', bold)
        self._worksheet_single.write(self._row_single, self._column_single+1, f'{time_hms}')
        self._worksheet_single.write(self._row_single, self._column_single+2, 'Date: ', bold)
        self._worksheet_single.write(self._row_single, self._column_single+3, f'{time_dmy}')

        if self._CanWorker.AuthStatus:
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