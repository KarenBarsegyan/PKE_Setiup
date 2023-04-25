import sys

from PyQt6.QtWidgets import (
    QMainWindow, QCheckBox, QVBoxLayout, 
    QApplication, QLabel, QHBoxLayout, 
    QWidget, QPushButton, QLineEdit
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QObject
from PyQt6 import QtCore

import can
import numpy as np

import time

import xlsxwriter

import os

RKE_KEY_NUM_ID        = 0x0111

PKE_ANT1_KEY_1_2_3_ID = 0x0112
PKE_ANT1_KEY_3_4_5_ID = 0x0113

PKE_ANT2_KEY_1_2_3_ID = 0x0114
PKE_ANT2_KEY_3_4_5_ID = 0x0115

PKE_ANT3_KEY_1_2_3_ID = 0x0116
PKE_ANT3_KEY_3_4_5_ID = 0x0117

PKE_ANT4_KEY_1_2_3_ID = 0x0118
PKE_ANT4_KEY_3_4_5_ID = 0x0119

PKE_ANT5_KEY_1_2_3_ID = 0x011A
PKE_ANT5_KEY_3_4_5_ID = 0x011B

PKE_ANT6_KEY_1_2_3_ID = 0x011C
PKE_ANT6_KEY_3_4_5_ID = 0x011D

PKE_AUTH_OK_ID        = 0x011E

busInitialized = False
data = np.zeros(((6, 5, 3)))
lastPressedKey = 0
lastAuth = 0
isAllReceived = [False]*13
timeBetweenMsgs = 0
lastMsgTime = 0
firstMsgTime = 0
firstReceivedMsg = True
AntMask = 0
PowerMode = 0

row = 0
column = 0
row_single = 0
column_single = 0

class WorkThread(QObject):
    finished = pyqtSignal()
    canReceivedAll = pyqtSignal()
    keyNumIdReceived = pyqtSignal()

    def __init__(self, parent=None):
        QThread.__init__(self, parent)

    def CanSend(self):
        global AntMask
        global PowerMode

        msg_to_send = can.Message(
            arbitration_id=0x0211,
            data=[AntMask, PowerMode, 0, 0, 0, 0, 0, 0],
            is_extended_id = False
        )
        
        global bus
        try:
            bus.send(msg_to_send)
        except Exception as exc:
            print("CAN didn't send: ", exc)
            BusDeInit()

        self.finished.emit()
        
    def CanReceive(self):
        while True:
            try:
                msg = bus.recv(0.01)
            except Exception as exc:
                print("Can did't receive: ", exc)
                BusDeInit()
                break

            if msg == None:
                break

            global lastMsgTime
            lastMsgTime = msg.timestamp

            if   msg.arbitration_id == RKE_KEY_NUM_ID:
                global lastPressedKey
                lastPressedKey = int(msg.data[0] + 1)
                self.keyNumIdReceived.emit()

            elif msg.arbitration_id == PKE_AUTH_OK_ID:
                isAllReceived[12] = True
                global lastAuth
                lastAuth = int(msg.data[1])

            elif msg.arbitration_id == PKE_ANT1_KEY_1_2_3_ID:
                isAllReceived[0] = True

                data[0][0][0] = int(msg.data[0])
                data[0][0][1] = int(msg.data[1])
                data[0][0][2] = int(msg.data[2])

                data[0][1][0] = int(msg.data[3])
                data[0][1][1] = int(msg.data[4])
                data[0][1][2] = int(msg.data[5])

                data[0][2][0] = int(msg.data[6])
                data[0][2][1] = int(msg.data[7])

            elif msg.arbitration_id == PKE_ANT1_KEY_3_4_5_ID:
                isAllReceived[1] = True

                data[0][2][2] = int(msg.data[0])

                data[0][3][0] = int(msg.data[1])
                data[0][3][1] = int(msg.data[2])
                data[0][3][2] = int(msg.data[3])

                data[0][4][0] = int(msg.data[4])
                data[0][4][1] = int(msg.data[5])
                data[0][4][2] = int(msg.data[6])

            elif msg.arbitration_id == PKE_ANT2_KEY_1_2_3_ID:
                isAllReceived[2] = True

                data[1][0][0] = int(msg.data[0])
                data[1][0][1] = int(msg.data[1])
                data[1][0][2] = int(msg.data[2])

                data[1][1][0] = int(msg.data[3])
                data[1][1][1] = int(msg.data[4])
                data[1][1][2] = int(msg.data[5])

                data[1][2][0] = int(msg.data[6])
                data[1][2][1] = int(msg.data[7])

            elif msg.arbitration_id == PKE_ANT2_KEY_3_4_5_ID:
                isAllReceived[3] = True

                data[1][2][2] = int(msg.data[0])

                data[1][3][0] = int(msg.data[1])
                data[1][3][1] = int(msg.data[2])
                data[1][3][2] = int(msg.data[3])

                data[1][4][0] = int(msg.data[4])
                data[1][4][1] = int(msg.data[5])
                data[1][4][2] = int(msg.data[6])

            elif msg.arbitration_id == PKE_ANT3_KEY_1_2_3_ID:
                isAllReceived[4] = True

                data[2][0][0] = int(msg.data[0])
                data[2][0][1] = int(msg.data[1])
                data[2][0][2] = int(msg.data[2])

                data[2][1][0] = int(msg.data[3])
                data[2][1][1] = int(msg.data[4])
                data[2][1][2] = int(msg.data[5])

                data[2][2][0] = int(msg.data[6])
                data[2][2][1] = int(msg.data[7])

            elif msg.arbitration_id == PKE_ANT3_KEY_3_4_5_ID:
                isAllReceived[5] = True

                data[2][2][2] = int(msg.data[0])

                data[2][3][0] = int(msg.data[1])
                data[2][3][1] = int(msg.data[2])
                data[2][3][2] = int(msg.data[3])

                data[2][4][0] = int(msg.data[4])
                data[2][4][1] = int(msg.data[5])
                data[2][4][2] = int(msg.data[6])

            elif msg.arbitration_id == PKE_ANT4_KEY_1_2_3_ID:
                isAllReceived[6] = True

                data[3][0][0] = int(msg.data[0])
                data[3][0][1] = int(msg.data[1])
                data[3][0][2] = int(msg.data[2])

                data[3][1][0] = int(msg.data[3])
                data[3][1][1] = int(msg.data[4])
                data[3][1][2] = int(msg.data[5])

                data[3][2][0] = int(msg.data[6])
                data[3][2][1] = int(msg.data[7])

            elif msg.arbitration_id == PKE_ANT4_KEY_3_4_5_ID:
                isAllReceived[7] = True

                data[3][2][2] = int(msg.data[0])

                data[3][3][0] = int(msg.data[1])
                data[3][3][1] = int(msg.data[2])
                data[3][3][2] = int(msg.data[3])

                data[3][4][0] = int(msg.data[4])
                data[3][4][1] = int(msg.data[5])
                data[3][4][2] = int(msg.data[6])

            elif msg.arbitration_id == PKE_ANT5_KEY_1_2_3_ID:
                isAllReceived[8] = True

                data[4][0][0] = int(msg.data[0])
                data[4][0][1] = int(msg.data[1])
                data[4][0][2] = int(msg.data[2])

                data[4][1][0] = int(msg.data[3])
                data[4][1][1] = int(msg.data[4])
                data[4][1][2] = int(msg.data[5])

                data[4][2][0] = int(msg.data[6])
                data[4][2][1] = int(msg.data[7])

            elif msg.arbitration_id == PKE_ANT5_KEY_3_4_5_ID:
                isAllReceived[9] = True

                data[4][2][2] = int(msg.data[0])

                data[4][3][0] = int(msg.data[1])
                data[4][3][1] = int(msg.data[2])
                data[4][3][2] = int(msg.data[3])

                data[4][4][0] = int(msg.data[4])
                data[4][4][1] = int(msg.data[5])
                data[4][4][2] = int(msg.data[6])

            elif msg.arbitration_id == PKE_ANT6_KEY_1_2_3_ID:
                isAllReceived[10] = True

                data[5][0][0] = int(msg.data[0])
                data[5][0][1] = int(msg.data[1])
                data[5][0][2] = int(msg.data[2])

                data[5][1][0] = int(msg.data[3])
                data[5][1][1] = int(msg.data[4])
                data[5][1][2] = int(msg.data[5])

                data[5][2][0] = int(msg.data[6])
                data[5][2][1] = int(msg.data[7])

            elif msg.arbitration_id == PKE_ANT6_KEY_3_4_5_ID:
                isAllReceived[11] = True

                data[5][2][2] = int(msg.data[0])

                data[5][3][0] = int(msg.data[1])
                data[5][3][1] = int(msg.data[2])
                data[5][3][2] = int(msg.data[3])

                data[5][4][0] = int(msg.data[4])
                data[5][4][1] = int(msg.data[5])
                data[5][4][2] = int(msg.data[6])
                

        isAllDone = True
        for cnt in isAllReceived:
            if not cnt:
                isAllDone = False
                break
        
        if isAllDone:
            global timeBetweenMsgs
            global firstMsgTime
            global firstReceivedMsg

            if (firstReceivedMsg == False):
                timeBetweenMsgs = (lastMsgTime - firstMsgTime)*1000
            else:
                timeBetweenMsgs = 0
                firstReceivedMsg = False

            firstMsgTime = lastMsgTime

            for idx in range(0, len(isAllReceived)):
                isAllReceived[idx] = False 

            self.canReceivedAll.emit()

        self.finished.emit()
        

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.SetApp()
        BusInitQuick()
        self.CanReceiveInit()
        self.CanSendInit()
    
    def SetApp(self):
        self.setWindowTitle("PKE Setup")
        self.setMinimumSize(QSize(1100, 700))
        self.setMaximumSize(QSize(1500, 1000))

        # Set general Horizontal structure of GUI of 7 columns
        layoutBig = QHBoxLayout()
        layoutLocal = [
            QVBoxLayout(),
            QVBoxLayout(),
            QVBoxLayout(),
            QVBoxLayout(),
            QVBoxLayout(),
            QVBoxLayout(),
            QVBoxLayout()
        ]

        layoutBig.addLayout(layoutLocal[0])
        layoutBig.addLayout(layoutLocal[1])
        layoutBig.addLayout(layoutLocal[2])
        layoutBig.addLayout(layoutLocal[3])
        layoutBig.addLayout(layoutLocal[4])
        layoutBig.addLayout(layoutLocal[5])
        layoutBig.addLayout(layoutLocal[6])

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

            layoutLocal[cnt].addWidget(w)
            cnt += 1

        # Fill the last Horizontal structure of GUI with vertical stuctures of different widgets

        # Set USB port state Label
        self.widgetUsbState = QLabel("Systec Disconnected")
        font = self.widgetUsbState.font()
        font.setPointSize(12)
        self.widgetUsbState.setFont(font)
        self.widgetUsbState.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        layoutLocal[6].addWidget(self.widgetUsbState)

        # Set USB port connect button Label
        self.widgetUsbConnect = QPushButton("Connect")
        font = self.widgetUsbConnect.font()
        font.setPointSize(12)
        self.widgetUsbConnect.setFont(font)
        layoutLocal[6].addWidget(self.widgetUsbConnect)
        self.widgetUsbConnect.clicked.connect(self.BusInitHandler)

        # Set USB port connect button Label
        self.widgetUsbDisConnect = QPushButton("Disconnect")
        font = self.widgetUsbDisConnect.font()
        font.setPointSize(12)
        self.widgetUsbDisConnect.setFont(font)
        layoutLocal[6].addWidget(self.widgetUsbDisConnect)
        self.widgetUsbDisConnect.clicked.connect(self.BusDeInitHandler)

        # Set msg receiving Period Label
        self.widgetCanMsgPeriod = QLabel("Msg Period: 0")
        font = self.widgetCanMsgPeriod.font()
        font.setPointSize(12)
        self.widgetCanMsgPeriod.setFont(font)
        self.widgetCanMsgPeriod.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        layoutLocal[6].addWidget(self.widgetCanMsgPeriod)

        # Set last key with pressed button num
        self.widgetLastKeyNum = QLabel("Last Key Pressed Num: None\t")
        font = self.widgetLastKeyNum.font()
        font.setPointSize(12)
        self.widgetLastKeyNum.setFont(font)
        self.widgetLastKeyNum.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        layoutLocal[6].addWidget(self.widgetLastKeyNum)

        # Set was auth OK or not
        self.widgetAuth = QLabel("Auth: None\t") 
        font = self.widgetAuth.font()
        font.setPointSize(20)
        self.widgetAuth.setFont(font)
        self.widgetAuth.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        layoutLocal[6].addWidget(self.widgetAuth)

        # # Set Change Power Mode button Label
        # self.widgetChMode = QPushButton("Change Power Mode")
        # font = self.widgetChMode.font()
        # font.setPointSize(12)
        # self.widgetChMode.setFont(font)
        # # layoutLocal[6].addWidget(self.widgetChMode)
        # # self.widgetChMode.clicked.connect(self.ChangeModeHandler)

        # # Show Power Mode
        # self.widgetPwrMode = QLabel("Power Mode: Normal")
        # font = self.widgetPwrMode.font()
        # font.setPointSize(12)
        # self.widgetPwrMode.setFont(font)
        # self.widgetPwrMode.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        # layoutLocal[6].addWidget(self.widgetPwrMode)

        # Get log msg
        self.widgetLogMsg = QLineEdit()
        font = self.widgetLogMsg.font()
        font.setPointSize(12)
        self.widgetLogMsg.setFont(font)
        self.widgetLogMsg.setMaximumHeight(200)
        self.widgetLogMsg.setMaximumWidth(300)
        layoutLocal[6].addWidget(self.widgetLogMsg)

        # Set button to send log
        self.widgetAddLog = QPushButton("Add LOG")
        font = self.widgetAddLog.font()
        font.setPointSize(12)
        self.widgetAddLog.setFont(font)
        layoutLocal[6].addWidget(self.widgetAddLog)
        self.widgetAddLog.clicked.connect(self.AddLogHandler)


        self.layoutCheckAndLabel = [
            QHBoxLayout(),
            QHBoxLayout(),
            QHBoxLayout(),
            QHBoxLayout(),
            QHBoxLayout(),
            QHBoxLayout()
        ]

        self.widgetCheckBox = [
            QCheckBox(),
            QCheckBox(),
            QCheckBox(),
            QCheckBox(),
            QCheckBox(),
            QCheckBox()
        ]

        self.widgetAntNumCheckBox = [
            QLabel("ANT 1\t"),
            QLabel("ANT 2\t"),
            QLabel("ANT 3\t"),
            QLabel("ANT 4\t"),
            QLabel("ANT 5\t"),
            QLabel("ANT 6\t")
        ]

        for nCnt in range(0, len(self.layoutCheckAndLabel)):
            font = self.widgetAntNumCheckBox[nCnt].font()
            font.setPointSize(11)
            self.widgetAntNumCheckBox[nCnt].setFont(font)
            self.widgetAntNumCheckBox[nCnt].setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.widgetCheckBox[nCnt].setChecked(True)
            self.widgetCheckBox[nCnt].stateChanged.connect(self.CanSendHandler)

            self.layoutCheckAndLabel[nCnt].addWidget(self.widgetCheckBox[nCnt])
            self.layoutCheckAndLabel[nCnt].addWidget(self.widgetAntNumCheckBox[nCnt])

        for l in self.layoutCheckAndLabel:
            layoutLocal[6].addLayout(l)

        self.widgetsAnt1 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self.widgetsAnt1:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layoutLocal[0].addWidget(w)

        self.widgetsAnt2 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self.widgetsAnt2:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layoutLocal[1].addWidget(w)

        self.widgetsAnt3 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self.widgetsAnt3:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layoutLocal[2].addWidget(w)

        self.widgetsAnt4 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self.widgetsAnt4:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layoutLocal[3].addWidget(w)

        self.widgetsAnt5 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self.widgetsAnt5:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layoutLocal[4].addWidget(w)

        self.widgetsAnt6 = [
            QLabel("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0)),
            QLabel("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(0, 0, 0))
        ]

        for w in self.widgetsAnt6:
            font = w.font()
            font.setPointSize(14)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layoutLocal[5].addWidget(w)


        widget = QWidget()
        widget.setLayout(layoutBig)
        self.setCentralWidget(widget)

        self.show()

    def CanSendInit(self):
        # Create a QThread and Worker object
        self.sendThread = QThread()
        self.sendWorker = WorkThread()
        self.sendWorker.moveToThread(self.sendThread)

        # Connect signals and slots
        self.sendThread.started.connect (self.sendWorker.CanSend)
        # self.sendWorker.finished.connect(self.sendWorker.deleteLater)
        # self.sendThread.finished.connect(self.sendThread.deleteLater)
        self.sendWorker.finished.connect(self.sendThread.quit)

    def CanReceiveInit(self):
        # Create a QThread and Worker object
        self.receiveThread = QThread()
        self.receiveWorker = WorkThread()
        self.receiveWorker.moveToThread(self.receiveThread)

        # Connect signals and slots
        self.receiveThread.started.connect (self.receiveWorker.CanReceive)
        self.receiveWorker.canReceivedAll.connect(self.PrintAllDataHandler)
        self.receiveWorker.keyNumIdReceived.connect(self.LastKeyIdUpdate)
        # self.receiveWorker.finished.connect(self.receiveWorker.deleteLater)
        # self.receiveThread.finished.connect(self.receiveThread.deleteLater)
        self.receiveWorker.finished.connect(self.receiveThread.quit)

    def CanSendHandler(self):
        # Check if Systec is connected
        if busInitialized and not self.sendThread.isRunning():
            global AntMask
            AntMask = 0
            for nCnt in range(0, len(self.widgetCheckBox)):
                if self.widgetCheckBox[nCnt].isChecked():
                    AntMask |= 1 << nCnt
            
            # Start the thread
            self.sendThread.start()

    def CanReceiveHandler(self):
        # Check if Systec is connected
        if busInitialized and not self.receiveThread.isRunning():
            self.widgetUsbState.setText("Systec Connected")
            # Start the thread
            self.receiveThread.start()
        else:
            self.widgetUsbState.setText("Systec Disconnected")
            self.widgetCanMsgPeriod.setText("Msg Period: %d" % int(0))
            global firstReceivedMsg
            firstReceivedMsg = True
            global data
            data = np.zeros(((6, 5, 3)))
            self.PrintAllData(0) 

    def LastKeyIdUpdate(self):
        self.widgetLastKeyNum.setText("Last Key Pressed Num: %d\t\t" % lastPressedKey)

    def BusInitHandler(self):
        BusInit()

    def BusDeInitHandler(self):
        BusDeInit()

    def AddLogHandler(self):
        self.AddLog(data)

    def AddLog(self, printData):
        global row_single
        global column_single

        time_hms = time.strftime("%H:%M:%S", time.localtime())
        time_dmy = time.strftime("%d/%m/%Y", time.localtime())
        
        bold = workbook.add_format({'bold': True})

        worksheet_single.write(row_single, column_single,   'Time: ', bold)
        worksheet_single.write(row_single, column_single+1, f'{time_hms}')
        worksheet_single.write(row_single, column_single+2, 'Date: ', bold)
        worksheet_single.write(row_single, column_single+3, f'{time_dmy}')

        global lastAuth
        if lastAuth:
            worksheet_single.write(row_single, column_single+5, 'Auth OK', bold)
        else:
            worksheet_single.write(row_single, column_single+5, 'Auth Fail', bold)

        msg = self.widgetLogMsg.text()
        worksheet_single.write(row_single, column_single+7, 'Message: ', bold)
        worksheet_single.write(row_single, column_single+8, f'{msg}')

        worksheet_single.write(row_single+3, column_single, "KEY 1")
        worksheet_single.write(row_single+4, column_single, "KEY 2")
        worksheet_single.write(row_single+5, column_single, "KEY 3")
        worksheet_single.write(row_single+6, column_single, "KEY 4")
        worksheet_single.write(row_single+7, column_single, "KEY 5")

        for i in range(5):
            worksheet_single.write(row_single+1, i*4+column_single+2, f"ANTENNA {i+1}")

            worksheet_single.write(row_single+2, i*4+column_single+1, "RSSI X")
            worksheet_single.write(row_single+2, i*4+column_single+2, "RSSI Y")
            worksheet_single.write(row_single+2, i*4+column_single+3, "RSSI Z")

            worksheet_single.write_number(row_single+3, i*4+column_single+1, printData[i][0][0])
            worksheet_single.write_number(row_single+3, i*4+column_single+2, printData[i][0][1])                 
            worksheet_single.write_number(row_single+3, i*4+column_single+3, printData[i][0][2])

            worksheet_single.write_number(row_single+4, i*4+column_single+1, printData[i][1][0])
            worksheet_single.write_number(row_single+4, i*4+column_single+2, printData[i][1][1])                 
            worksheet_single.write_number(row_single+4, i*4+column_single+3, printData[i][1][2])

            worksheet_single.write_number(row_single+5, i*4+column_single+1, printData[i][2][0])
            worksheet_single.write_number(row_single+5, i*4+column_single+2, printData[i][2][1])                 
            worksheet_single.write_number(row_single+5, i*4+column_single+3, printData[i][2][2])

            worksheet_single.write_number(row_single+6, i*4+column_single+1, printData[i][3][0])
            worksheet_single.write_number(row_single+6, i*4+column_single+2, printData[i][3][1])                 
            worksheet_single.write_number(row_single+6, i*4+column_single+3, printData[i][3][2])

            worksheet_single.write_number(row_single+7, i*4+column_single+1, printData[i][4][0])
            worksheet_single.write_number(row_single+7, i*4+column_single+2, printData[i][4][1])                 
            worksheet_single.write_number(row_single+7, i*4+column_single+3, printData[i][4][2])

        row_single += 9

    def ChangeModeHandler(self):
        global PowerMode

        if PowerMode == 0:
            PowerMode = 1 #PowerDown
            self.widgetPwrMode.setText("Power Mode: Power Down")
        else:
            PowerMode = 0 #Normal Mode
            self.widgetPwrMode.setText("Power Mode: Normal")
        
        self.CanSendHandler()

    def PrintAllDataHandler(self):
        self.widgetCanMsgPeriod.setText("Msg Period: %d ms" % int(timeBetweenMsgs))
        global lastAuth
        if lastAuth:
            self.widgetAuth.setText(f'Auth: OK')
        else:
            self.widgetAuth.setText(f'Auth: Fail')

        self.PrintAllData(data)

    def PrintAllData(self, printData):

        onlyGUI = False

        try:
            if printData == 0:
                printData = np.zeros(((6, 5, 3)))
                onlyGUI = True
        except: pass

        self.widgetsAnt1[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[0][0][0], printData[0][0][1], printData[0][0][2]))
        self.widgetsAnt1[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[0][1][0], printData[0][1][1], printData[0][1][2]))
        self.widgetsAnt1[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[0][2][0], printData[0][2][1], printData[0][2][2]))
        self.widgetsAnt1[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[0][3][0], printData[0][3][1], printData[0][3][2]))
        self.widgetsAnt1[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[0][4][0], printData[0][4][1], printData[0][4][2]))

        self.widgetsAnt2[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[1][0][0], printData[1][0][1], printData[1][0][2]))
        self.widgetsAnt2[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[1][1][0], printData[1][1][1], printData[1][1][2]))
        self.widgetsAnt2[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[1][2][0], printData[1][2][1], printData[1][2][2]))
        self.widgetsAnt2[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[1][3][0], printData[1][3][1], printData[1][3][2]))
        self.widgetsAnt2[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[1][4][0], printData[1][4][1], printData[1][4][2]))

        self.widgetsAnt3[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[2][0][0], printData[2][0][1], printData[2][0][2]))
        self.widgetsAnt3[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[2][1][0], printData[2][1][1], printData[2][1][2]))
        self.widgetsAnt3[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[2][2][0], printData[2][2][1], printData[2][2][2]))
        self.widgetsAnt3[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[2][3][0], printData[2][3][1], printData[2][3][2]))
        self.widgetsAnt3[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[2][4][0], printData[2][4][1], printData[2][4][2]))

        self.widgetsAnt4[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[3][0][0], printData[3][0][1], printData[3][0][2]))
        self.widgetsAnt4[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[3][1][0], printData[3][1][1], printData[3][1][2]))
        self.widgetsAnt4[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[3][2][0], printData[3][2][1], printData[3][2][2]))
        self.widgetsAnt4[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[3][3][0], printData[3][3][1], printData[3][3][2]))
        self.widgetsAnt4[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[3][4][0], printData[3][4][1], printData[3][4][2]))

        self.widgetsAnt5[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[4][0][0], printData[4][0][1], printData[4][0][2]))
        self.widgetsAnt5[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[4][1][0], printData[4][1][1], printData[4][1][2]))
        self.widgetsAnt5[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[4][2][0], printData[4][2][1], printData[4][2][2]))
        self.widgetsAnt5[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[4][3][0], printData[4][3][1], printData[4][3][2]))
        self.widgetsAnt5[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[4][4][0], printData[4][4][1], printData[4][4][2]))

        self.widgetsAnt6[0].setText("  KEY 1\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[5][0][0], printData[5][0][1], printData[5][0][2]))
        self.widgetsAnt6[1].setText("  KEY 2\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[5][1][0], printData[5][1][1], printData[5][1][2]))
        self.widgetsAnt6[2].setText("  KEY 3\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[5][2][0], printData[5][2][1], printData[5][2][2]))
        self.widgetsAnt6[3].setText("  KEY 4\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[5][3][0], printData[5][3][1], printData[5][3][2]))
        self.widgetsAnt6[4].setText("  KEY 5\nRSSI_X: %d\nRSSI_Y: %d\nRSSI_Z: %d\n" %(printData[5][4][0], printData[5][4][1], printData[5][4][2]))


        if onlyGUI:
            return

        # Start from the first cell.
        # Rows and columns are zero indexed.
        global row
        global column
        
        time_hms = time.strftime("%H:%M:%S", time.localtime())
        time_dmy = time.strftime("%d/%m/%Y", time.localtime())
        
        bold = workbook.add_format({'bold': True})

        worksheet.write(row, column,   'Time: ', bold)
        worksheet.write(row, column+1, f'{time_hms}')
        worksheet.write(row, column+2, 'Date: ', bold)
        worksheet.write(row, column+3, f'{time_dmy}')
        
        global lastAuth
        if lastAuth:
            worksheet.write(row, column+5, 'Auth OK', bold)
        else:
            worksheet.write(row, column+5, 'Auth Fail', bold)


        worksheet.write(row+3, column, "KEY 1")
        worksheet.write(row+4, column, "KEY 2")
        worksheet.write(row+5, column, "KEY 3")
        worksheet.write(row+6, column, "KEY 4")
        worksheet.write(row+7, column, "KEY 5")

        for i in range(5):
            worksheet.write(row+1, i*4+column+2, f"ANTENNA {i+1}")

            worksheet.write(row+2, i*4+column+1, "RSSI X")
            worksheet.write(row+2, i*4+column+2, "RSSI Y")
            worksheet.write(row+2, i*4+column+3, "RSSI Z")

            worksheet.write_number(row+3, i*4+column+1, printData[i][0][0])
            worksheet.write_number(row+3, i*4+column+2, printData[i][0][1])                 
            worksheet.write_number(row+3, i*4+column+3, printData[i][0][2])

            worksheet.write_number(row+4, i*4+column+1, printData[i][1][0])
            worksheet.write_number(row+4, i*4+column+2, printData[i][1][1])                 
            worksheet.write_number(row+4, i*4+column+3, printData[i][1][2])

            worksheet.write_number(row+5, i*4+column+1, printData[i][2][0])
            worksheet.write_number(row+5, i*4+column+2, printData[i][2][1])                 
            worksheet.write_number(row+5, i*4+column+3, printData[i][2][2])

            worksheet.write_number(row+6, i*4+column+1, printData[i][3][0])
            worksheet.write_number(row+6, i*4+column+2, printData[i][3][1])                 
            worksheet.write_number(row+6, i*4+column+3, printData[i][3][2])

            worksheet.write_number(row+7, i*4+column+1, printData[i][4][0])
            worksheet.write_number(row+7, i*4+column+2, printData[i][4][1])                 
            worksheet.write_number(row+7, i*4+column+3, printData[i][4][2])

        row += 9


def BusInitQuick():
    global bus
    global busInitialized
    try:
        bus = can.Bus(interface='systec', channel='0', bitrate=500000)
        busInitialized = True
        print("CAN was inited!")
        return True
    except Exception as exc:
        print("CAN was not inited: ", exc)
        return False

def BusInit():
    if busInitialized == False:
        for cnt in range(0, 3):
            if BusInitQuick():
                break
            time.sleep(0.1)

def BusDeInit():
    global bus
    global busInitialized
    if busInitialized == True:
        busInitialized = False
        try:
            bus.shutdown()
            # del self.bus
            # self.widgetUsbState.setText("Systec Disconnected")
            print("CAN was deinited!")
        except Exception as exc:
            print("CAN was not deinited: ", exc)
     
def app_start():
    app = QApplication([])

    window = MainWindow()

    timerCanSend = QtCore.QTimer()
    timerCanSend.timeout.connect(window.CanSendHandler)
    timerCanSend.start(1000)

    timerCanReceive = QtCore.QTimer()
    timerCanReceive.timeout.connect(window.CanReceiveHandler)
    timerCanReceive.start(100)
    try:
        app.exec()
    except: pass

    workbook.close()

    try:
        if busInitialized:
            bus.shutdown()
    except: pass


if __name__ == "__main__": 

    time_hms = time.strftime("%H:%M:%S", time.localtime())
    time_dmy = time.strftime("%d/%m/%Y", time.localtime())

    try:
        os.mkdir(f"logs/")
    except: pass

    try:
        workbook = xlsxwriter.Workbook(f'logs/Data.xlsx')
        worksheet = workbook.add_worksheet(name="All_Data")
        worksheet_single = workbook.add_worksheet(name="Single Data")
    except:
        print("Error opening XLS")

    app_start() 


# TIME STAMP

# pyinstaller --onefile --hidden-import=can.interfaces.systec -w PKE_Setup.py