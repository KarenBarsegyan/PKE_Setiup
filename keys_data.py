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
            self._good_pollings_amount = data.good_pollings_amount
            self._auths_ok = data.auths_ok
            self._polls_done = data.polls_done
            self._key_num = data.key_num
            self._dataRMS = data.calcAverageRMS(self._data)

    def setData(self, npdata, auths_ok, good_pollings_amoun, polls_done, 
                key_num, dataRMS):
        self._data = npdata
        self._auths_ok = auths_ok
        self._good_pollings_amount = good_pollings_amoun
        self._polls_done = polls_done
        self._key_num = key_num
        self._dataRMS = dataRMS

    @property
    def data(self):
        return self._data

    @property
    def dataRMS(self):
        return self._dataRMS

    @property
    def auths_ok(self):
        return self._auths_ok

    @property
    def polls_done(self):
        return self._polls_done

    @property
    def good_pollings_amount(self):
        return self._good_pollings_amount

    @property
    def key_num(self):
        return self._key_num
    

class KeysData():
    def __init__(self, ant_amount, key_amount):
        self._ant_amount = ant_amount
        self._key_amount = key_amount
        self._data = np.zeros((((self._ant_amount, self._key_amount, 3))))
        self._data_ranges = np.zeros((((self._ant_amount, self._key_amount, 3))))
        self._one_key_data = np.zeros((((self._ant_amount, self._key_amount, 3))))
        self._one_key_average_data = np.zeros((((self._ant_amount, 3))))
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
    def data_ranges(self):
        return self._data_ranges
    
    @data_ranges.setter
    def data_ranges(self, data_ranges):
        self._data_ranges = data_ranges

    @property
    def auths_ok(self):
        return self._auths_ok

    @property
    def polls_done(self):
        return self._polls_done

    @property
    def good_pollings_amount(self):
        return self._one_key_average_data_amount
    
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
        res_data = np.zeros((((self._ant_amount, 3))))
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
        res_data = np.zeros((((self._ant_amount, 3))))
        for nAnt in range(self._ant_amount):
            if(self._one_key_average_data_amount[nAnt] > 0):
                res_data[nAnt] = np.divide(self._one_key_average_data[nAnt], 
                                                 self._one_key_average_data_amount[nAnt])
            else:
                res_data[nAnt] = np.zeros((((3))))

        # print("Data Amount: ", self._one_key_average_data_amount)
        print("Summs: "      , self._one_key_average_data)
        print("Average: "    , res_data)
        return res_data

    def calcAverageRMS(self, averageData):
        res_data = np.zeros(((self._ant_amount)))
        for nAnt in range(self._ant_amount):
            res_data[nAnt] = ((averageData[nAnt][0]**2) + 
                              (averageData[nAnt][1]**2) + 
                              (averageData[nAnt][2]**2))**0.5

        # print("Average: ", averageData)
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
        return np.zeros((((self._ant_amount, self._key_amount, 3))))
    
    