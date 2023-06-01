from PyQt5.QtWidgets import (
    QMainWindow, QCheckBox, QVBoxLayout, 
    QApplication, QLabel, QHBoxLayout, 
    QWidget, QPushButton, QLineEdit
)
from PyQt5.QtCore import Qt, QSize, QThread, QTimer
import numpy as np
import time
import xlsxwriter
import logging
from CAN import CanSendRecv
    
logs_path = "AppLogs"
logger = logging.getLogger(__name__)
f_handler = logging.FileHandler(f'{logs_path}/{__name__}.log')
f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
logger.setLevel(logging.INFO)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self._Initworksheet()
        self._SetApp()
        self._CanInit()

    def __del__(self):
        try:
            self._workbook.close()
            logger.info("WorkBook Closed")
        except:
            logger.info("Error closing WorkBook")

        try:
            if (self._CanThread.isRunning()):
                self._CanThread.quit()

            logger.info("CAN thread terminated")
        except:
            logger.info("Error terminating CAN thread")

    def _Initworksheet(self):
        self._row = 0
        self._row = 0
        self._row_single = 0
        self._row_single = 0
    
        try:
            self._workbook = xlsxwriter.Workbook(f'logs/Data.xlsx')
            self._worksheet = self._workbook.add_worksheet(name="All_Data")
            self._worksheet_single = self._workbook.add_worksheet(name="Single Data")
        except:
            logger.warning("Error opening XLS")

    def _SetApp(self):
        self.setWindowTitle("PKE Setup")
        self.setMinimumSize(QSize(1100, 700))
        self.setMaximumSize(QSize(1500, 1000))

        # Set general Horizontal structure of GUI of 7 self._rows
        self._layoutBig = QHBoxLayout()
        self._layoutLocal = [
            QVBoxLayout(),
            QVBoxLayout(),
            QVBoxLayout(),
            QVBoxLayout(),
            QVBoxLayout(),
            QVBoxLayout(),
            QVBoxLayout()
        ]

        for i in range(7):
            self._layoutBig.addLayout(self._layoutLocal[i])

        # Fill first 6 Horizontal structures of GUI with vertical Ant stuctures
        widgetsAnts = [
            QLabel("ANT 1"),
            QLabel("ANT 2"),
            QLabel("ANT 3"),
            QLabel("ANT 4"),
            QLabel("ANT 5"),
            QLabel("ANT 6")
        ]

        cnt = 0
        for w in widgetsAnts:
            font = w.font()
            font.setPointSize(20)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            self._layoutLocal[cnt].addWidget(w)
            cnt += 1

        self._SetCAN()
        self._SetAdditionalData()
        # self._SetLogs()
        self._SetCheckBox()
        self._SetAntsData()
        
        widget = QWidget()
        widget.setLayout(self._layoutBig)
        self.setCentralWidget(widget)

        self.show()

    def _SetCAN(self):
        # Set USB port state Label
        self._widgetUsbState = QLabel("Systec Disconnected")
        font = self._widgetUsbState.font()
        font.setPointSize(12)
        self._widgetUsbState.setFont(font)
        self._widgetUsbState.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._layoutLocal[6].addWidget(self._widgetUsbState)

        # Set USB port connect button Label
        self._widgetUsbConnect = QPushButton("Connect")
        font = self._widgetUsbConnect.font()
        font.setPointSize(12)
        self._widgetUsbConnect.setFont(font)
        self._layoutLocal[6].addWidget(self._widgetUsbConnect)
        self._widgetUsbConnect.clicked.connect(self._BusInitHandler)
        self._widgetUsbConnect.setFlat(False)

        # Set USB port connect button Label
        widgetUsbDisConnect = QPushButton("Disconnect")
        font = widgetUsbDisConnect.font()
        font.setPointSize(12)
        widgetUsbDisConnect.setFont(font)
        self._layoutLocal[6].addWidget(widgetUsbDisConnect)
        widgetUsbDisConnect.clicked.connect(self._BusDeInitHandler)

        # Set msg receiving Period Label
        self._widgetCanMsgPeriod = QLabel("Msg Period: 0")
        font = self._widgetCanMsgPeriod.font()
        font.setPointSize(12)
        self._widgetCanMsgPeriod.setFont(font)
        self._widgetCanMsgPeriod.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._layoutLocal[6].addWidget(self._widgetCanMsgPeriod)

    def _SetAdditionalData(self):
        # Set last key with pressed button num
        widgetLastKeyNum = QLabel("Last Key Pressed Num: None\t")
        font = widgetLastKeyNum.font()
        font.setPointSize(12)
        widgetLastKeyNum.setFont(font)
        widgetLastKeyNum.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._layoutLocal[6].addWidget(widgetLastKeyNum)

        # Set was auth OK or not
        self._widgetAuth = QLabel("Auth: None\t") 
        font = self._widgetAuth.font()
        font.setPointSize(20)
        self._widgetAuth.setFont(font)
        self._widgetAuth.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._layoutLocal[6].addWidget(self._widgetAuth)

        # # Set Change Power Mode button Label
        # widgetChMode = QPushButton("Change Power Mode")
        # font = widgetChMode.font()
        # font.setPointSize(12)
        # widgetChMode.setFont(font)
        # # layoutLocal[6].addWidget(widgetChMode)
        # # self.widgetChMode.clicked.connect(self.ChangeModeHandler)

        # # Show Power Mode
        # widgetPwrMode = QLabel("Power Mode: Normal")
        # font = widgetPwrMode.font()
        # font.setPointSize(12)
        # widgetPwrMode.setFont(font)
        # widgetPwrMode.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        # self._layoutLocal[6].addWidget(widgetPwrMode)

    def _SetLogs(self):
        # Get log msg
        widgetLogMsg = QLineEdit()
        font = widgetLogMsg.font()
        font.setPointSize(12)
        widgetLogMsg.setFont(font)
        widgetLogMsg.setMaximumHeight(200)
        widgetLogMsg.setMaximumWidth(300)
        self._layoutLocal[6].addWidget(self.widgetLogMsg)

        # Set button to send log
        widgetAddLog = QPushButton("Add LOG")
        font = widgetAddLog.font()
        font.setPointSize(12)
        widgetAddLog.setFont(font)
        self._layoutLocal[6].addWidget(widgetAddLog)
        widgetAddLog.clicked.connect(self.AddLogHandler)

    def _SetCheckBox(self):
        layoutCheckAndLabel = [
            QHBoxLayout(),
            QHBoxLayout(),
            QHBoxLayout(),
            QHBoxLayout(),
            QHBoxLayout(),
            QHBoxLayout()
        ]

        self._widgetCheckBox = [
            QCheckBox(),
            QCheckBox(),
            QCheckBox(),
            QCheckBox(),
            QCheckBox(),
            QCheckBox()
        ]

        widgetAntNumCheckBox = [
            QLabel("ANT 1\t"),
            QLabel("ANT 2\t"),
            QLabel("ANT 3\t"),
            QLabel("ANT 4\t"),
            QLabel("ANT 5\t"),
            QLabel("ANT 6\t")
        ]

        for nCnt in range(0, len(layoutCheckAndLabel)):
            font = widgetAntNumCheckBox[nCnt].font()
            font.setPointSize(11)
            widgetAntNumCheckBox[nCnt].setFont(font)
            widgetAntNumCheckBox[nCnt].setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self._widgetCheckBox[nCnt].setChecked(True)
            self._widgetCheckBox[nCnt].stateChanged.connect(self._updateAntMask)

            layoutCheckAndLabel[nCnt].addWidget(self._widgetCheckBox[nCnt])
            layoutCheckAndLabel[nCnt].addWidget(widgetAntNumCheckBox[nCnt])

        for l in layoutCheckAndLabel:
            self._layoutLocal[6].addLayout(l)

    def _SetAntsData(self):  
        self._widgetsAnt1 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self._widgetsAnt1:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._layoutLocal[0].addWidget(w)

        self._widgetsAnt2 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self._widgetsAnt2:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._layoutLocal[1].addWidget(w)

        self._widgetsAnt3 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self._widgetsAnt3:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._layoutLocal[2].addWidget(w)

        self._widgetsAnt4 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self._widgetsAnt4:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._layoutLocal[3].addWidget(w)

        self._widgetsAnt5 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self._widgetsAnt5:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._layoutLocal[4].addWidget(w)

        self._widgetsAnt6 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self._widgetsAnt6:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._layoutLocal[5].addWidget(w)

    def _CanInit(self):
        # Create a QThread and Worker object
        self._CanThread = QThread()
        self._CanWorker = CanSendRecv()
        self._CanWorker.moveToThread(self._CanThread)

        # Connect signals and slots
        self._CanThread.started.connect(self._CanWorker.Start)
        self._CanWorker.canInited.connect(self._BusInitedCallback)
        self._CanWorker.canDeInited.connect(self._BusDeInitedCallback)
        self._CanWorker.canReceivedAll.connect(self._PrintData)
        # self._CanWorker.finished.connect(self._CanThread.quit)
        # self._CanWorker.finished.connect(self._CanWorker.deleteLater)
        # self._CanThread.finished.connect(self._CanThread.deleteLater)
        
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
        self._widgetCanMsgPeriod.setText("Msg Period: %d ms" % int(0))
        self._PrintData(False) 
        
    def _updateAntMask(self):
        AntMask = 0
        for nCnt in range(0, len(self._widgetCheckBox)):
            if self._widgetCheckBox[nCnt].isChecked():
                AntMask |= 1 << nCnt

        self._CanWorker.SetAntMask(AntMask)

    # def _BusSend(self):

    # def _BusReceive(self):


    # def _LastKeyIdUpdate(self):
    #     self.widgetLastKeyNum.setText("Last Key Pressed Num: %d\t\t" % lastPressedKey)

    # def _AddLogHandler(self):
    #     self.AddLog(self.CanWorker.Data)

    # def _ChangeModeHandler(self):
    #     global PowerMode

    #     if PowerMode == 0:
    #         PowerMode = 1 #PowerDown
    #         self.widgetPwrMode.setText("Power Mode: Power Down")
    #     else:
    #         PowerMode = 0 #Normal Mode
    #         self.widgetPwrMode.setText("Power Mode: Normal")
        
    #     self.CanSendHandler()


    def _PrintData(self, res: bool):
        onlyGUI = False
        if not res:
            Data = np.zeros(((6, 5, 3)))
            onlyGUI = True
        else:
            Data = self._CanWorker.Data

        self._PrintScreenData(Data)

        # if not onlyGUI:
        #     self._PrintLogData(Data)

    def _PrintScreenData(self, printData):
        self._widgetCanMsgPeriod.setText("Msg Period: %d ms" % int(self._CanWorker.TimeBetweenMsgs))

        if self._CanWorker.AuthStatus:
            self._widgetAuth.setText(f'Auth: OK')
        else:
            self._widgetAuth.setText(f'Auth: Fail')

        self._widgetsAnt1[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[0][0][0], printData[0][0][1], printData[0][0][2]))
        self._widgetsAnt1[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[0][1][0], printData[0][1][1], printData[0][1][2]))
        self._widgetsAnt1[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[0][2][0], printData[0][2][1], printData[0][2][2]))
        self._widgetsAnt1[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[0][3][0], printData[0][3][1], printData[0][3][2]))
        self._widgetsAnt1[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[0][4][0], printData[0][4][1], printData[0][4][2]))

        self._widgetsAnt2[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[1][0][0], printData[1][0][1], printData[1][0][2]))
        self._widgetsAnt2[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[1][1][0], printData[1][1][1], printData[1][1][2]))
        self._widgetsAnt2[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[1][2][0], printData[1][2][1], printData[1][2][2]))
        self._widgetsAnt2[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[1][3][0], printData[1][3][1], printData[1][3][2]))
        self._widgetsAnt2[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[1][4][0], printData[1][4][1], printData[1][4][2]))

        self._widgetsAnt4[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[2][0][0], printData[2][0][1], printData[2][0][2]))
        self._widgetsAnt4[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[2][1][0], printData[2][1][1], printData[2][1][2]))
        self._widgetsAnt4[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[2][2][0], printData[2][2][1], printData[2][2][2]))
        self._widgetsAnt4[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[2][3][0], printData[2][3][1], printData[2][3][2]))
        self._widgetsAnt4[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[2][4][0], printData[2][4][1], printData[2][4][2]))

        self._widgetsAnt4[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[3][0][0], printData[3][0][1], printData[3][0][2]))
        self._widgetsAnt4[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[3][1][0], printData[3][1][1], printData[3][1][2]))
        self._widgetsAnt4[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[3][2][0], printData[3][2][1], printData[3][2][2]))
        self._widgetsAnt4[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[3][3][0], printData[3][3][1], printData[3][3][2]))
        self._widgetsAnt4[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[3][4][0], printData[3][4][1], printData[3][4][2]))

        self._widgetsAnt5[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[4][0][0], printData[4][0][1], printData[4][0][2]))
        self._widgetsAnt5[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[4][1][0], printData[4][1][1], printData[4][1][2]))
        self._widgetsAnt5[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[4][2][0], printData[4][2][1], printData[4][2][2]))
        self._widgetsAnt5[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[4][3][0], printData[4][3][1], printData[4][3][2]))
        self._widgetsAnt5[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[4][4][0], printData[4][4][1], printData[4][4][2]))

        self._widgetsAnt6[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[5][0][0], printData[5][0][1], printData[5][0][2]))
        self._widgetsAnt6[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[5][1][0], printData[5][1][1], printData[5][1][2]))
        self._widgetsAnt6[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[5][2][0], printData[5][2][1], printData[5][2][2]))
        self._widgetsAnt6[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[5][3][0], printData[5][3][1], printData[5][3][2]))
        self._widgetsAnt6[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[5][4][0], printData[5][4][1], printData[5][4][2]))
    
    def _PrintLogData(self, printData): 
        time_hms = time.strftime("%H:%M:%S", time.localtime())
        time_dmy = time.strftime("%d/%m/%Y", time.localtime())
        
        bold = self._workbook.add_format({'bold': True})

        self._worksheet.write(self._row, self._row,   'Time: ', bold)
        self._worksheet.write(self._row, self._row+1, f'{time_hms}')
        self._worksheet.write(self._row, self._row+2, 'Date: ', bold)
        self._worksheet.write(self._row, self._row+3, f'{time_dmy}')
        
        if self.CanWorker.AuthStatus:
            self._worksheet.write(self._row, self._row+5, 'Auth OK', bold)
        else:
            self._worksheet.write(self._row, self._row+5, 'Auth Fail', bold)


        self._worksheet.write(self._row+3, self._row, "KEY 1")
        self._worksheet.write(self._row+4, self._row, "KEY 2")
        self._worksheet.write(self._row+5, self._row, "KEY 3")
        self._worksheet.write(self._row+6, self._row, "KEY 4")
        self._worksheet.write(self._row+7, self._row, "KEY 5")

        for i in range(5):
            self._worksheet.write(self._row+1, i*4+self._row+2, f"ANTENNA {i+1}")

            self._worksheet.write(self._row+2, i*4+self._row+1, "RSSI X")
            self._worksheet.write(self._row+2, i*4+self._row+2, "RSSI Y")
            self._worksheet.write(self._row+2, i*4+self._row+3, "RSSI Z")

            self._worksheet.write_number(self._row+3, i*4+self._row+1, printData[i][0][0])
            self._worksheet.write_number(self._row+3, i*4+self._row+2, printData[i][0][1])                 
            self._worksheet.write_number(self._row+3, i*4+self._row+3, printData[i][0][2])

            self._worksheet.write_number(self._row+4, i*4+self._row+1, printData[i][1][0])
            self._worksheet.write_number(self._row+4, i*4+self._row+2, printData[i][1][1])                 
            self._worksheet.write_number(self._row+4, i*4+self._row+3, printData[i][1][2])

            self._worksheet.write_number(self._row+5, i*4+self._row+1, printData[i][2][0])
            self._worksheet.write_number(self._row+5, i*4+self._row+2, printData[i][2][1])                 
            self._worksheet.write_number(self._row+5, i*4+self._row+3, printData[i][2][2])

            self._worksheet.write_number(self._row+6, i*4+self._row+1, printData[i][3][0])
            self._worksheet.write_number(self._row+6, i*4+self._row+2, printData[i][3][1])                 
            self._worksheet.write_number(self._row+6, i*4+self._row+3, printData[i][3][2])

            self._worksheet.write_number(self._row+7, i*4+self._row+1, printData[i][4][0])
            self._worksheet.write_number(self._row+7, i*4+self._row+2, printData[i][4][1])                 
            self._worksheet.write_number(self._row+7, i*4+self._row+3, printData[i][4][2])

        self._row += 9

    def _PrintSigleLog(self, printData):
        time_hms = time.strftime("%H:%M:%S", time.localtime())
        time_dmy = time.strftime("%d/%m/%Y", time.localtime())
        
        bold = self._workbook.add_format({'bold': True})

        self._worksheet_single.write(self._row_single, self._row_single,   'Time: ', bold)
        self._worksheet_single.write(self._row_single, self._row_single+1, f'{time_hms}')
        self._worksheet_single.write(self._row_single, self._row_single+2, 'Date: ', bold)
        self._worksheet_single.write(self._row_single, self._row_single+3, f'{time_dmy}')

        if self.CanWorker.AuthStatus:
            self._worksheet_single.write(self._row_single, self._row_single+5, 'Auth OK', bold)
        else:
            self._worksheet_single.write(self._row_single, self._row_single+5, 'Auth Fail', bold)

        msg = self.widgetLogMsg.text()
        self._worksheet_single.write(self._row_single, self._row_single+7, 'Message: ', bold)
        self._worksheet_single.write(self._row_single, self._row_single+8, f'{msg}')

        self._worksheet_single.write(self._row_single+3, self._row_single, "KEY 1")
        self._worksheet_single.write(self._row_single+4, self._row_single, "KEY 2")
        self._worksheet_single.write(self._row_single+5, self._row_single, "KEY 3")
        self._worksheet_single.write(self._row_single+6, self._row_single, "KEY 4")
        self._worksheet_single.write(self._row_single+7, self._row_single, "KEY 5")

        for i in range(5):
            self._worksheet_single.write(self._row_single+1, i*4+self._row_single+2, f"ANTENNA {i+1}")

            self._worksheet_single.write(self._row_single+2, i*4+self._row_single+1, "RSSI X")
            self._worksheet_single.write(self._row_single+2, i*4+self._row_single+2, "RSSI Y")
            self._worksheet_single.write(self._row_single+2, i*4+self._row_single+3, "RSSI Z")

            self._worksheet_single.write_number(self._row_single+3, i*4+self._row_single+1, printData[i][0][0])
            self._worksheet_single.write_number(self._row_single+3, i*4+self._row_single+2, printData[i][0][1])                 
            self._worksheet_single.write_number(self._row_single+3, i*4+self._row_single+3, printData[i][0][2])

            self._worksheet_single.write_number(self._row_single+4, i*4+self._row_single+1, printData[i][1][0])
            self._worksheet_single.write_number(self._row_single+4, i*4+self._row_single+2, printData[i][1][1])                 
            self._worksheet_single.write_number(self._row_single+4, i*4+self._row_single+3, printData[i][1][2])

            self._worksheet_single.write_number(self._row_single+5, i*4+self._row_single+1, printData[i][2][0])
            self._worksheet_single.write_number(self._row_single+5, i*4+self._row_single+2, printData[i][2][1])                 
            self._worksheet_single.write_number(self._row_single+5, i*4+self._row_single+3, printData[i][2][2])

            self._worksheet_single.write_number(self._row_single+6, i*4+self._row_single+1, printData[i][3][0])
            self._worksheet_single.write_number(self._row_single+6, i*4+self._row_single+2, printData[i][3][1])                 
            self._worksheet_single.write_number(self._row_single+6, i*4+self._row_single+3, printData[i][3][2])

            self._worksheet_single.write_number(self._row_single+7, i*4+self._row_single+1, printData[i][4][0])
            self._worksheet_single.write_number(self._row_single+7, i*4+self._row_single+2, printData[i][4][1])                 
            self._worksheet_single.write_number(self._row_single+7, i*4+self._row_single+3, printData[i][4][2])

        self._row_single += 9
     

def app_start():
    app = QApplication([])

    window = MainWindow()

    app.exec()



if __name__ == "__main__": 

    # time_hms = time.strftime("%H:%M:%S", time.localtime())
    # time_dmy = time.strftime("%d/%m/%Y", time.localtime())

    # try:
    #     os.mkdir(f"logs/")
    # except: pass

    app_start() 


# TIME STAMP

# pyinstaller --onefile --hidden-import=can.interfaces.systec -w PKE_Setup.py