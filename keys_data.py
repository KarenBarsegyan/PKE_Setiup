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

class KeysData():
    def __init__(self, ant_amount, key_amount):
        self._ant_amount = ant_amount
        self._key_amount = key_amount
        self._data = np.zeros((((self._ant_amount, 3))), dtype=int)

    @property
    def data(self):
        return self._data
    
    @data.setter
    def data(self, data):
        print(type(np.zeros((((self._ant_amount, self._key_amount, 3))), dtype=int)))
        self._data = data

    def makeOneKeyData(self, data, keyNum):
        res_data = np.zeros((((self._ant_amount, 3))), dtype=int)
        for nAnt in range(0, self._ant_amount):
            res_data[nAnt][0] = data[nAnt][keyNum][0]
            res_data[nAnt][1] = data[nAnt][keyNum][1]
            res_data[nAnt][2] = data[nAnt][keyNum][2]
        
        return res_data

    def getZeroData(self):
        return np.zeros((((self._ant_amount, self._key_amount, 3))), dtype=int)