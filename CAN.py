from PyQt6.QtCore import QThread, pyqtSignal, QObject
import can

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