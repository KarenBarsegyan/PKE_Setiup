from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication
import numpy as np
import time
import can
import logging

###### CAN MSG IDs ######
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


logs_path = "AppLogs"
logger = logging.getLogger(__name__)
f_handler = logging.FileHandler(f'{logs_path}/{__name__}.log')
f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
logger.setLevel(logging.INFO)


class CanSendRecv(QThread):
    finished = pyqtSignal()
    canInited = pyqtSignal()
    canDeInited = pyqtSignal()
    canReceivedAll = pyqtSignal()
    keyNumIdReceived = pyqtSignal()

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self._busInitialized = False
        self._data = np.zeros(((6, 5, 3)))
        self._lastPressedKey = 0
        self._lastAuth = 0
        self._isAllReceived = [False]*13
        self._timeBetweenMsgs = 0
        self._lastMsgTime = 0
        self._firstMsgTime = 0
        self._firstReceivedMsg = True
        self._AntMask = 0
        self._PowerMode = 0

    def _CanSend(self):
        if self._busInitialized:
            print("Send")
            print("A")
            self._AntMask
            msg_to_send = can.Message(
                arbitration_id=0x0211,
                data=[self._AntMask, self._PowerMode, 0, 0, 0, 0, 0, 0],
                is_extended_id = False
            )
            
            try:
                self._bus.send(msg_to_send)
            except Exception as exc:
                logger.warning("CAN didn't send: ", exc)
                self.BusDeInit()

        
    def _CanReceive(self):
        if self._busInitialized:
            while True:
                try:
                    msg = self._bus.recv(0.01)
                except Exception as exc:
                    logger.warning("Can did't receive: ", exc)
                    self._BusDeInit()
                    break

                if msg == None:
                    break

                self._lastMsgTime = msg.timestamp

                self._ParseData(msg)

            isAllDone = True
            for cnt in self._isAllReceived:
                if not cnt:
                    isAllDone = False
                    break
            
            if isAllDone:
                if (self._firstReceivedMsg == False):
                    self._timeBetweenMsgs = (self._lastMsgTime - self._firstMsgTime)*1000
                else:
                    self._timeBetweenMsgs = 0
                    self._firstReceivedMsg = False

                self._firstMsgTime = self._lastMsgTime

                for idx in range(0, len(self._isAllReceived)):
                    self._isAllReceived[idx] = False 

                self.canReceivedAll.emit()


    @property
    def Data(self):
        return self._data

    @property
    def TimeBetweenMsgs(self):
        return self._timeBetweenMsgs
    
    @property
    def AuthStatus(self):
        return self._lastAuth
    
    def SetAntMask(self, mask):
        self._AntMask = mask
        self._CanSend()

    def _ParseData(self, msg):
        if   msg.arbitration_id == RKE_KEY_NUM_ID:
            self._lastPressedKey = int(msg.data[0] + 1)
            self.keyNumIdReceived.emit()

        elif msg.arbitration_id == PKE_AUTH_OK_ID:
            self._isAllReceived[12] = True
            self._lastAuth = int(msg.data[1])

        elif msg.arbitration_id == PKE_ANT1_KEY_1_2_3_ID:
            self._isAllReceived[0] = True

            self._data[0][0][0] = int(msg.data[0])
            self._data[0][0][1] = int(msg.data[1])
            self._data[0][0][2] = int(msg.data[2])

            self._data[0][1][0] = int(msg.data[3])
            self._data[0][1][1] = int(msg.data[4])
            self._data[0][1][2] = int(msg.data[5])

            self._data[0][2][0] = int(msg.data[6])
            self._data[0][2][1] = int(msg.data[7])

        elif msg.arbitration_id == PKE_ANT1_KEY_3_4_5_ID:
            self._isAllReceived[1] = True

            self._data[0][2][2] = int(msg.data[0])

            self._data[0][3][0] = int(msg.data[1])
            self._data[0][3][1] = int(msg.data[2])
            self._data[0][3][2] = int(msg.data[3])

            self._data[0][4][0] = int(msg.data[4])
            self._data[0][4][1] = int(msg.data[5])
            self._data[0][4][2] = int(msg.data[6])

        elif msg.arbitration_id == PKE_ANT2_KEY_1_2_3_ID:
            self._isAllReceived[2] = True

            self._data[1][0][0] = int(msg.data[0])
            self._data[1][0][1] = int(msg.data[1])
            self._data[1][0][2] = int(msg.data[2])

            self._data[1][1][0] = int(msg.data[3])
            self._data[1][1][1] = int(msg.data[4])
            self._data[1][1][2] = int(msg.data[5])

            self._data[1][2][0] = int(msg.data[6])
            self._data[1][2][1] = int(msg.data[7])

        elif msg.arbitration_id == PKE_ANT2_KEY_3_4_5_ID:
            self._isAllReceived[3] = True

            self._data[1][2][2] = int(msg.data[0])

            self._data[1][3][0] = int(msg.data[1])
            self._data[1][3][1] = int(msg.data[2])
            self._data[1][3][2] = int(msg.data[3])

            self._data[1][4][0] = int(msg.data[4])
            self._data[1][4][1] = int(msg.data[5])
            self._data[1][4][2] = int(msg.data[6])

        elif msg.arbitration_id == PKE_ANT3_KEY_1_2_3_ID:
            self._isAllReceived[4] = True

            self._data[2][0][0] = int(msg.data[0])
            self._data[2][0][1] = int(msg.data[1])
            self._data[2][0][2] = int(msg.data[2])

            self._data[2][1][0] = int(msg.data[3])
            self._data[2][1][1] = int(msg.data[4])
            self._data[2][1][2] = int(msg.data[5])

            self._data[2][2][0] = int(msg.data[6])
            self._data[2][2][1] = int(msg.data[7])

        elif msg.arbitration_id == PKE_ANT3_KEY_3_4_5_ID:
            self._isAllReceived[5] = True

            self._data[2][2][2] = int(msg.data[0])

            self._data[2][3][0] = int(msg.data[1])
            self._data[2][3][1] = int(msg.data[2])
            self._data[2][3][2] = int(msg.data[3])

            self._data[2][4][0] = int(msg.data[4])
            self._data[2][4][1] = int(msg.data[5])
            self._data[2][4][2] = int(msg.data[6])

        elif msg.arbitration_id == PKE_ANT4_KEY_1_2_3_ID:
            self._isAllReceived[6] = True

            self._data[3][0][0] = int(msg.data[0])
            self._data[3][0][1] = int(msg.data[1])
            self._data[3][0][2] = int(msg.data[2])

            self._data[3][1][0] = int(msg.data[3])
            self._data[3][1][1] = int(msg.data[4])
            self._data[3][1][2] = int(msg.data[5])

            self._data[3][2][0] = int(msg.data[6])
            self._data[3][2][1] = int(msg.data[7])

        elif msg.arbitration_id == PKE_ANT4_KEY_3_4_5_ID:
            self._isAllReceived[7] = True

            self._data[3][2][2] = int(msg.data[0])

            self._data[3][3][0] = int(msg.data[1])
            self._data[3][3][1] = int(msg.data[2])
            self._data[3][3][2] = int(msg.data[3])

            self._data[3][4][0] = int(msg.data[4])
            self._data[3][4][1] = int(msg.data[5])
            self._data[3][4][2] = int(msg.data[6])

        elif msg.arbitration_id == PKE_ANT5_KEY_1_2_3_ID:
            self._isAllReceived[8] = True

            self._data[4][0][0] = int(msg.data[0])
            self._data[4][0][1] = int(msg.data[1])
            self._data[4][0][2] = int(msg.data[2])

            self._data[4][1][0] = int(msg.data[3])
            self._data[4][1][1] = int(msg.data[4])
            self._data[4][1][2] = int(msg.data[5])

            self._data[4][2][0] = int(msg.data[6])
            self._data[4][2][1] = int(msg.data[7])

        elif msg.arbitration_id == PKE_ANT5_KEY_3_4_5_ID:
            self._isAllReceived[9] = True

            self._data[4][2][2] = int(msg.data[0])

            self._data[4][3][0] = int(msg.data[1])
            self._data[4][3][1] = int(msg.data[2])
            self._data[4][3][2] = int(msg.data[3])

            self._data[4][4][0] = int(msg.data[4])
            self._data[4][4][1] = int(msg.data[5])
            self._data[4][4][2] = int(msg.data[6])

        elif msg.arbitration_id == PKE_ANT6_KEY_1_2_3_ID:
            self._isAllReceived[10] = True

            self._data[5][0][0] = int(msg.data[0])
            self._data[5][0][1] = int(msg.data[1])
            self._data[5][0][2] = int(msg.data[2])

            self._data[5][1][0] = int(msg.data[3])
            self._data[5][1][1] = int(msg.data[4])
            self._data[5][1][2] = int(msg.data[5])

            self._data[5][2][0] = int(msg.data[6])
            self._data[5][2][1] = int(msg.data[7])

        elif msg.arbitration_id == PKE_ANT6_KEY_3_4_5_ID:
            self._isAllReceived[11] = True

            self._data[5][2][2] = int(msg.data[0])

            self._data[5][3][0] = int(msg.data[1])
            self._data[5][3][1] = int(msg.data[2])
            self._data[5][3][2] = int(msg.data[3])

            self._data[5][4][0] = int(msg.data[4])
            self._data[5][4][1] = int(msg.data[5])
            self._data[5][4][2] = int(msg.data[6])
                
    def _BusInitQuick(self):
        try:
            self._bus = can.Bus(interface='systec', channel='0', bitrate=500000)
            self._busInitialized = True
            logger.info("CAN was inited!")
            self.canInited.emit()
            self._CanSend()
            return True
        except Exception as exc:
            logger.warning(f"CAN was not inited: {exc}")
            return False

    def BusInit(self):
        if self._busInitialized == False:
            for cnt in range(0, 10):
                if self._BusInitQuick():
                    break
                QApplication.processEvents()
                time.sleep(0.1)
        else:
            logger.info("CAN is already inited!")

    def BusDeInit(self):
        if self._busInitialized == True:
            self._busInitialized = False
            self.canDeInited.emit()
            try:
                self._bus.shutdown()
                logger.info("CAN was deinited!")
            except Exception as exc:
                logger.warning(f"CAN was not deinited: {exc}")
        else:
            logger.info("CAN is already not inited!")

    

    def Start(self):
        try:
            self.BusInit()
            self._CanSend()
            self._CanReceive()

            while not self.isInterruptionRequested(): 
                QApplication.processEvents()

        except:
            logger.info("CAN Task Cancelled")
        finally:
            logger.info("CAN Task finished")


