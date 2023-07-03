from PyQt5.QtWidgets import (
    QVBoxLayout, QLabel, QHBoxLayout, 
    QWidget, QGroupBox, QFrame, 
    QScrollArea, QMenu, QAction
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QPen, QColor,
    QFont, QCursor
)
from PyQt5.QtCore import (
    Qt, QThread, QPoint, QSize, QRect,
    QEasingCurve, QPropertyAnimation, 
    QSequentialAnimationGroup, pyqtSlot, 
    pyqtProperty
)
import logging
import os
import numpy as np
from functools import partial
import json
from json import JSONEncoder

class KeysDataAverage():
    def __init__(self, data = None):
        if (data != None):
            self._data = data.calcAverage()
            self._auths_ok = data.auths_ok
            self._polls_done = data.polls_done
            self._key_num = data.key_num

    def setData(self, npdata, auths_ok, polls_done, key_num):
        self._data = npdata
        self._auths_ok = auths_ok
        self._polls_done = polls_done
        self._key_num = key_num

    @property
    def data(self):
        return self._data

    @property
    def auths_ok(self):
        return self._auths_ok

    @property
    def polls_done(self):
        return self._polls_done

    @property
    def key_num(self):
        return self._key_num
    

class KeysData():
    def __init__(self, ant_amount, key_amount):
        self._ant_amount = ant_amount
        self._key_amount = key_amount
        self._data = np.zeros((((self._ant_amount, self._key_amount, 3))), dtype=int)
        self._one_key_data = np.zeros((((self._ant_amount, self._key_amount, 3))), dtype=int)
        self._one_key_average_data = np.zeros((((self._ant_amount, 3))), dtype=int)
        self._one_key_average_data_amount = []
        self.clearAverage()

        self._auths_ok = 0
        self._polls_done = 0
        self._key_num = 0

    @property
    def data(self):
        return self._data
    
    @data.setter
    def data(self, data):
        self._data = data

    @property
    def auths_ok(self):
        return self._auths_ok

    @property
    def polls_done(self):
        return self._polls_done
    
    @property
    def key_num(self):
        return self._key_num

    @property
    def one_key_data(self):
        return self._one_key_data
    
    @one_key_data.setter
    def one_key_data(self, data):
        self._one_key_data = data

    @property
    def key_num(self):
        return self._key_num
    
    @key_num.setter
    def key_num(self, num):
        self._key_num = num

    def makeOneKeyData(self):
        res_data = np.zeros((((self._ant_amount, 3))), dtype=int)
        for nAnt in range(0, self._ant_amount):
            res_data[nAnt][0] = self._data[nAnt][self._key_num][0]
            res_data[nAnt][1] = self._data[nAnt][self._key_num][1]
            res_data[nAnt][2] = self._data[nAnt][self._key_num][2]
        
        return res_data
    
    def addToAverage(self, data, auth_stat):
        self._polls_done += 1
        for nAnt in range(self._ant_amount):
            if not(data[nAnt][0] == 0 and data[nAnt][1] == 0 and data[nAnt][2] == 0):
                self._one_key_average_data[nAnt] += data[nAnt]
                self._one_key_average_data_amount[nAnt] += 1

        if auth_stat:
            self._auths_ok += 1

    def calcAverage(self):
        res_data = np.zeros((((self._ant_amount, 3))), dtype=int)
        for nAnt in range(self._ant_amount):
            if(self._one_key_average_data_amount[nAnt] > 0):
                res_data[nAnt] = np.floor_divide(self._one_key_average_data[nAnt], 
                                                 self._one_key_average_data_amount[nAnt])
            else:
                res_data[nAnt] = np.zeros((((3))), dtype=int)

        print("Summs: ", self._one_key_average_data_amount)
        # print("Data: ", res_data)
        return res_data

    def clearAverage(self):
        self._one_key_average_data_amount = []
        self._distCoeff = []

        for nAnt in range(self._ant_amount): 
            self._one_key_average_data_amount.append(0)
            self._distCoeff.append(0)
            self._one_key_average_data[nAnt][0] = 0
            self._one_key_average_data[nAnt][1] = 0
            self._one_key_average_data[nAnt][2] = 0

        self._auths_ok = 0
        self._polls_done = 0

    def getZeroData(self):
        return np.zeros((((self._ant_amount, self._key_amount, 3))), dtype=int)
    
    