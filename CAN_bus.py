from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow
import numpy as np
import time
import can
import logging
import os

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
PKE_DIAG_STATE_ID     = 0x011F
PKE_ANT_IMPS_ID       = 0x0120


class CanSendRecv(QThread):
    finished = pyqtSignal()
    canInited = pyqtSignal()
    canDeInited = pyqtSignal()
    canReceivedAll = pyqtSignal()
    keyNumIdReceived = pyqtSignal(int)
    keyAuthReceived = pyqtSignal(int)
    antImpsReceived = pyqtSignal(list)
    antDiagStateReceived = pyqtSignal(list)

    def __init__(self, ANT_AMOUNT, KEY_AMOUNT, parent=None):
        QThread.__init__(self, parent)
        self._busInitialized = False
        self._data = np.zeros((((ANT_AMOUNT, KEY_AMOUNT, 3))), dtype=int)
        self._isAllReceived = [False]*12
        self._timeBetweenMsgs = 0
        self._lastMsgTime = 0
        self._firstMsgTime = 0
        self._firstReceivedMsg = True
        self._ant_mask = 0
        self._key_mask = 0
        self._power_mode = 0
        self._auth_mode = 0
        self._perform_diag = 0
        self._poll_current = 0
        self._AntAmount = ANT_AMOUNT
        self._KeyAmount = KEY_AMOUNT
        self._performPollings = 0

        self._init_logger()

    def __del__(self):
        self.BusDeInit()

    def _init_logger(self):
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

    def sendData(self):
        try:
            if self._busInitialized:
                msg_to_send = can.Message(
                    arbitration_id=0x0211,
                    data=[self._ant_mask, 
                          self._key_mask,
                          self._performPollings, 
                          self._auth_mode, 
                          self._perform_diag,
                          self._poll_current,
                          self._power_mode,
                          0],
                    is_extended_id = False
                )
                self._perform_diag = 0
                try:
                    self._bus.send(msg_to_send)
                except Exception as exc:
                    self._logger.warning(f"CAN didn't send: {exc}")
                    self.BusDeInit()
        except Exception as exc:
            self._logger.warning(f"CanSend error: {exc}")
        
    def _receiveData(self):
        try:
            if self._busInitialized:
                while True:
                    try:
                        msg = self._bus.recv(0.01)
                    except Exception as exc:
                        self._logger.warning(f"Can did't receive: {exc}")
                        self.BusDeInit()
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
                        self._timeBetweenMsgs = round((self._lastMsgTime - self._firstMsgTime)*100)*10
                    else:
                        self._timeBetweenMsgs = 0
                        self._firstReceivedMsg = False

                    self._firstMsgTime = self._lastMsgTime

                    for idx in range(0, len(self._isAllReceived)):
                        self._isAllReceived[idx] = False 

                    self.canReceivedAll.emit()
        except Exception as exc:
            self._logger.warning(f"CanReceive error: {exc}")

    @property
    def Data(self):
        return self._data

    @property
    def TimeBetweenMsgs(self):
        return self._timeBetweenMsgs
    
    @property
    def ant_mask(self):
        return self._ant_mask
    @ant_mask.setter
    def ant_mask(self, mask):
        # print("AntMask: ", mask)
        self._ant_mask = mask

    @property
    def key_mask(self):
        return self._key_mask
    @key_mask.setter
    def key_mask(self, mask):
        # print("KeyMask: ", mask)
        self._key_mask = mask

    @property
    def power_mode(self):
        return self._power_mode
    @power_mode.setter
    def power_mode(self, mode):
        # print("PowerMode: ", mode)
        self._power_mode = mode

    @property
    def auth_mode(self):
        return self._auth_mode
    @auth_mode.setter
    def auth_mode(self, mode):
        # print("AuthMode: ", mode)
        self._auth_mode = mode

    @property
    def poll_current(self):
        return self._poll_current
    @poll_current.setter
    def poll_current(self, curr):
        # print("Current: ", curr)
        self._poll_current = curr
    
    def perform_diag(self):
        self._perform_diag = 1
        self.sendData()

    def startPoll(self):
        self._performPollings = 1
        self._firstReceivedMsg = True
        self.sendData()

    def stopPoll(self):
        self._performPollings = 0
        self.sendData()

    def _ParseData(self, msg):
        if   msg.arbitration_id == RKE_KEY_NUM_ID:
            lastPressedKey = int(msg.data[0] + 1)
            self.keyNumIdReceived.emit(lastPressedKey)

        elif msg.arbitration_id == PKE_AUTH_OK_ID:
            lastAuth = int(msg.data[1])
            self.keyAuthReceived.emit(lastAuth)

        elif msg.arbitration_id == PKE_DIAG_STATE_ID:
            state = self._parseDiagState(list(msg.data))
            self.antDiagStateReceived.emit(state)

        elif msg.arbitration_id == PKE_ANT_IMPS_ID:
            antImps = list(msg.data[:6])
            self.antImpsReceived.emit(antImps)

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

    def _parseDiagState(self, state: list):
        res = []
        errorList = [
            "INTERNAL_TIMEOUT_ERROR"      ,
            "BS_EXCHANGE_ERROR"           ,
            "BS_RESET_ERROR"              ,    
            "BS_OPERATION_ERROR"          ,    
            "BS_TEMP_ERROR"               ,    
            "BS_VOLTAGE_ERROR"            ,    
            "BS_PROTECTION_ERROR"         ,    
            "BS_DRIVER_PROTECTION_ERROR"  ,    
            "ANT_1_TX_SHORT_TO_GND_ERROR" ,    
            "ANT_1_TX_SHORT_TO_BAT_ERROR" ,    
            "ANT_1_TX_OPEN_ERROR"         ,
            "ANT_1_TX_INTER_SHORT_ERROR"  ,
            "ANT_2_TX_SHORT_TO_GND_ERROR" ,
            "ANT_2_TX_SHORT_TO_BAT_ERROR" ,
            "ANT_2_TX_OPEN_ERROR"         ,
            "ANT_2_TX_INTER_SHORT_ERROR"  ,
            "ANT_3_TX_SHORT_TO_GND_ERROR" ,
            "ANT_3_TX_SHORT_TO_BAT_ERROR" ,
            "ANT_3_TX_OPEN_ERROR"         ,
            "ANT_3_TX_INTER_SHORT_ERROR"  ,
            "ANT_4_TX_SHORT_TO_GND_ERROR" ,
            "ANT_4_TX_SHORT_TO_BAT_ERROR" ,
            "ANT_4_TX_OPEN_ERROR"         ,
            "ANT_4_TX_INTER_SHORT_ERROR"  ,
            "ANT_5_TX_SHORT_TO_GND_ERROR" ,
            "ANT_5_TX_SHORT_TO_BAT_ERROR" ,
            "ANT_5_TX_OPEN_ERROR"         ,
            "ANT_5_TX_INTER_SHORT_ERROR"  ,
            "ANT_6_TX_SHORT_TO_GND_ERROR" ,
            "ANT_6_TX_SHORT_TO_BAT_ERROR" ,
            "ANT_6_TX_OPEN_ERROR"         ,
            "ANT_6_TX_INTER_SHORT_ERROR"  
        ]
        for i in range(len(errorList)):
            if (state[int(i/8)] & (1 << (i - 8*int(i/8)))):
                res.append(errorList[i])

        return res

    def _BusInitQuick(self):
        try:
            self._bus = can.Bus(interface='systec', channel='0', bitrate=500000)
            self._busInitialized = True
            self._logger.info("CAN was inited!")
            try:
                self.canInited.emit()
            except Exception as exc: 
                self._logger.warning(f"Can Inited emit fail: {exc}")
            self.sendData()
            return True
        except Exception as exc:
            self._logger.warning(f"CAN was not inited: {exc}")
            return False

    def BusInit(self):
        try:
            if self._busInitialized == False:
                for cnt in range(0, 5):
                    if self._BusInitQuick():
                        break

                    for cnt in range(0, 5):
                        QApplication.processEvents()
                        time.sleep(0.1)
            else:
                self._logger.info("CAN is already inited!")
        except Exception as exc:
            self._logger.warning(f"BusInit error: {exc}")

    def BusDeInit(self):
        try:
            if self._busInitialized == True:
                self._busInitialized = False
                try:
                    self._bus.shutdown()
                    del self._bus
                    try:
                        self.canDeInited.emit()
                    except Exception as exc: 
                        self._logger.warning(f"Error in CAN De Init emit: {exc}") 
                    self._logger.info("CAN was deinited!")
                except Exception as exc:
                    self._logger.warning(f"CAN was not deinited: {exc}")
            else:
                self._logger.info("CAN is already not inited!")
        except Exception as exc:
            self._logger.warning(f"BusDeInit error: {exc}")

    def MainTask(self):
        if self._Counter > 5:
            self._Counter = 0
            self.sendData()

        self._Counter += 1

        self._receiveData()

        QTimer.singleShot(100, self.MainTask)

    def start(self):
        self._logger.info("CAN Task Run")
        try:
            self.BusInit()

            self._Counter = 0
            self.MainTask()
        except Exception as exc:
            self._logger.warning(f"Start error: {exc}")