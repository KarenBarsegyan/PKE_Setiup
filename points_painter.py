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
from keys_data import KeysData, KeysDataAverage
import math 


class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)

class PointsPainter(QThread):
    class PointType(int):
        Green = 1
        Yellow = 2 
        Red = 3
        Ant = 4
        Gray = 5

    def __init__(self, askForPollingFunc, parent=None):
        QThread.__init__(self, parent)

        ############ Settings ############

        # Mesh size relatively to screen resolution 
        self._mesh_step = 25

        # Calc some real dist and amount mesh steps inside this dist
        amount_of_mesh_steps = 24
        distance_of_this_steps = 1500

        # Picture Settings
        self._vehicle_pic_name = 'pictures/vesta_top_view.png'
        self._canvas_width = 1000
        self._canvas_height = 1500
        self._picture_height = 1200
        self._picture_shift_hor = 18

        # Vehicle size
        self._vehicle_top_left_angle = tuple([225, 200])
        self._vehicle_size = tuple([600, 1000])
        self._zones_step_size_setup = 3
        self._first_ant = 4

        #################################

        # Mesh step to real size
        self._zones_step_size = self._mesh_step * 2 * self._zones_step_size_setup
        self._dist_to_mesh_coeff = distance_of_this_steps/(self._mesh_step * amount_of_mesh_steps)
        self._greenPoints = dict()
        self._grayPoints = dict()
        self._highlitedPoints = dict()
        self._yellowPoints = dict()
        self._redPoints = dict()
        self._purplePoints = dict()
        self._bluePoints = dict()
        self._darkRedPoints = dict()
        self._keyCircles = dict()
        self._zoneCircles = dict()
        self._zoneRssi = dict()
        self._activeZoneCircles = dict()
        self._vehicleEdgeRect = dict()
        self._antPoints = dict()
        self._lastPos = tuple()
        self._lastYellowPos = tuple()
        self._yellowPointInProgress = False
        self._AntAmount = 6
        self._KeyAmount = 5
        self._ants_keys_data = KeysData(self._AntAmount, self._KeyAmount)
        self._askForPollingFunc = askForPollingFunc
        self._amountsOfAverage = 0
        self._picWidth = 0
        self._picHeight = 0
        self._store_data_path = ''
        self._keyChosen = 0
        self._rssiFloatingWindowIsHidden = True
        self._key_inside = 0

        self._yellow_radius = 0
        self._yellowAnimation = QPropertyAnimation(self, b"yellow_radius", self)
        # self._yellowAnimation.setEasingCurve(QEasingCurve.InOutCubic)
        self._yellowAnimation.setDuration(500)
        self._yellowAnimation.setStartValue(5)
        self._yellowAnimation.setEndValue(10)

        self._init_logger()

    def closeEvent(self):
        self._hideFloatingWindow()

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

    def restoreData(self, path):
        # try:
            with open(f'{path}') as f:
                allData = json.load(f)

            pointsData = allData['points']
            self._greenPoints.clear()
            for point in pointsData['pointsGreen']: 
                numpyArray = np.asarray(json.loads(pointsData['pointsGreen'][point][0]))
                pollings = np.asarray(json.loads(pointsData['pointsGreen'][point][1]))
                dataRMS = np.asarray(json.loads(pointsData['pointsGreen'][point][2]))
                auths_ok = pointsData['pointsGreen'][point][3]
                polls_done = pointsData['pointsGreen'][point][4]
                key_num = pointsData['pointsGreen'][point][5]

                data = KeysDataAverage()
                data.setData(numpyArray, auths_ok, pollings, polls_done, key_num, dataRMS)
                self._greenPoints[tuple(json.loads(point))] = data

            self._antPoints.clear()
            for point in pointsData['pointsAnt']: 
                antNum = pointsData['pointsAnt'][point]
                self._antPoints[tuple(json.loads(point))] = antNum

            self._calibrate()
            self._paintCalibrationEvent()
            self._paintMeasureEvent()

        # except Exception as exc:
        #     self._logger.warning(f"No points data yet: {exc}")

    def saveData(self, path):
        to_json = {}
        try:
            with open(f'{path}', 'r') as f:
                to_json = json.load(f)
        except:
            self._logger.info("no such file yet")

        to_json['points'] = self.generateJson()

        with open(f'{path}', 'w') as f:
            json.dump(to_json, f)

        self._paintCalibrationEvent()
        self._paintMeasureEvent()

    def generateJson(self):
        data = dict()

        d = dict()
        for point in self._greenPoints:  
            d[json.dumps(point)] = [json.dumps(self._greenPoints[point].data, cls=NumpyArrayEncoder),
                                    json.dumps(self._greenPoints[point].good_pollings_amount, cls=NumpyArrayEncoder),
                                    json.dumps(self._greenPoints[point].dataRMS, cls=NumpyArrayEncoder),
                                    self._greenPoints[point].auths_ok,
                                    self._greenPoints[point].polls_done,
                                    self._greenPoints[point].key_num]
        data['pointsGreen'] = d

        d = dict()
        for point in self._antPoints:  
            d[json.dumps(point)] = self._antPoints[point]
        data['pointsAnt'] = d

        return data

    def clearData(self):
        self._greenPoints.clear()
        self._yellowPoints.clear()
        self._redPoints.clear()
        self._bluePoints.clear()
        self._darkRedPoints.clear()
        self._keyCircles.clear()
        self._antPoints.clear()
        
    def rememberData(self, Data, authStat, isDone):
        self._ants_keys_data.key_num = Data.key_num
        self._ants_keys_data.one_key_data = Data.makeOneKeyData()
        if self._yellowPointInProgress:
            self._ants_keys_data.addToAverage(self._ants_keys_data.one_key_data, authStat)
            if isDone:
                self._setPoint(type = self.PointType.Green, coords = self._lastYellowPos)
                self._yellowPointInProgress = False
                self._ants_keys_data.clearAverage()
                
        self._calcDistance()
        self._findZone()
        self._updateToolbarData()
    
    def SetUpCalibrationDesk(self):
        localLayout = QVBoxLayout()
        localLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._writeRSSIAction = QAction(self)
        self._writeRSSIAction.setText("Write RSSI")
        self._writeRSSIAction.triggered.connect(partial(self._setPoint, type = self.PointType.Yellow))

        self._deletePointAction = QAction(self)
        self._deletePointAction.setText("Delete Point")
        self._deletePointAction.triggered.connect(self._deletePoint)

        self._setAntAction = QAction(self)
        self._setAntAction.setText("Set Ant Point")
        self._setAntMenu = QMenu()
        self._setAntAction.setMenu(self._setAntMenu)
        self._setAntMenu.aboutToShow.connect(self._populateSetAnts)

        separator = QAction(self)
        separator.setSeparator(True)

        self._ant_num_action = QAction(self)

        self._calibrationLabel = QLabel()
        self._calibrationLabel.mousePressEvent = self._mouseClickCallback
        self._calibrationLabel.keyPressEvent = self.keyPressEvent
        # self._calibrationLabel.focusInEvent = self.focusOutEvent

        self._calibrationLabel.setContextMenuPolicy(Qt.ActionsContextMenu)
        self._calibrationLabel.addAction(self._writeRSSIAction)
        self._calibrationLabel.addAction(self._deletePointAction)
        self._calibrationLabel.addAction(self._setAntAction)
        # self._calibrationLabel.addAction(self._setZoneAction)
        self._calibrationLabel.addAction(separator)
        self._calibrationLabel.addAction(self._ant_num_action)

        localLayout.addWidget(self._calibrationLabel)

        self._paintCalibrationEvent()

        self._rssiFloatingWindow = self._SetAntsData()
        self._rssiFloatingWindow.setWindowFlag(Qt.FramelessWindowHint)
        self._rssiFloatingWindow.keyPressEvent = self.keyPressEvent
        self._rssiFloatingWindow.focusOutEvent = self.focusOutEvent
        # self._rssiFloatingWindow.setFocusPolicy(Qt.StrongFocus)

        v_widget = QWidget()
        v_widget.setLayout(localLayout)  
        # v_widget.setStyleSheet("border: 1px solid black")

        scrollPicture = QScrollArea()
        scrollPicture.setWidget(v_widget)
        scrollPicture.setWidgetResizable(True) 

        return scrollPicture

    def SetUpMeasureDesk(self):
        localLayout = QVBoxLayout()
        localLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._measureLabel = QLabel()

        localLayout.addWidget(self._measureLabel)

        self._paintMeasureEvent()

        v_widget = QWidget()
        v_widget.setLayout(localLayout)  
        # v_widget.setStyleSheet("border: 1px solid black")

        scrollPicture = QScrollArea()
        scrollPicture.setWidget(v_widget)
        scrollPicture.setWidgetResizable(True) 

        return scrollPicture    

    def _calibrate(self): 
        # try:
            pass
        # except Exception as exc:
        #     self._logger.warning(f"No data to _calibrate: {exc}")

    def _paintZones(self):
        self._vehicleEdgeRect[self._vehicle_top_left_angle] = self._vehicle_size
        self._grayPoints.clear()

        aSize = self._vehicle_size[0]/2

        zonePos = tuple()
        for antPos in self._antPoints:
            nAnt = self._antPoints[antPos] 
            if nAnt == self._first_ant-1:
                zonePos = antPos

        if zonePos != tuple():
            self._zoneCircles[zonePos] = []

            topPart = abs(self._vehicle_top_left_angle[1] - zonePos[1])

            for zoneLeftDist in range(0, self._vehicle_size[1] - topPart, self._zones_step_size):
                radius = (zoneLeftDist**2 + aSize**2)**0.5
                if(radius > aSize):
                    self._zoneCircles[zonePos].append(radius)
                    x = self._vehicle_top_left_angle[0]
                    y = zonePos[1] + zoneLeftDist + self._zones_step_size/2
                    pos = tuple([int(x), int(y)])
                    if (y < self._vehicle_top_left_angle[1] + self._vehicle_size[1]):
                        if pos not in self._greenPoints and pos not in self._yellowPoints:
                            self._grayPoints[pos] = 0

    def _convNum(self, num):
        return (num)**(-0.5)

    def _calcDistFromCalibrationData(self, nAnt):
        self._distances = dict()
        self._min_rssi = 0
        self._min_rssi = 0

        # print(nAnt)
        if nAnt == 0 or nAnt == 1:
            # Door ant
            self._distances[self._convNum(6520)] = 200
            self._distances[self._convNum(1135)] = 400
            self._distances[self._convNum(435) ] = 600
            self._distances[self._convNum(231) ] = 800
            self._distances[self._convNum(152) ] = 1000
            self._distances[self._convNum(105) ] = 1200
            self._distances[self._convNum(81)  ] = 1400
            self._distances[self._convNum(68)  ] = 1600
            self._distances[self._convNum(55)  ] = 1800
            self._distances[self._convNum(48)  ] = 2000
            self._distances[self._convNum(35)  ] = 2200
            self._distances[self._convNum(24)  ] = 2400
            self._distances[self._convNum(17)  ] = 2600
            self._distances[self._convNum(14)  ] = 2800
            self._distances[self._convNum(12)  ] = 3000
            self._distances[self._convNum(10.2)] = 3200
            self._distances[self._convNum(6.5) ] = 3400
            self._distances[self._convNum(4.2) ] = 3600
            self._distances[self._convNum(4)   ] = 3800
            self._distances[self._convNum(3.7) ] = 4000

        if nAnt == 2:
            # Bamper ant
            self._distances[self._convNum(3060)] = 200
            self._distances[self._convNum(491) ] = 400
            self._distances[self._convNum(188) ] = 600
            self._distances[self._convNum(110) ] = 800
            self._distances[self._convNum(68)  ] = 1000
            self._distances[self._convNum(48)  ] = 1200
            self._distances[self._convNum(37)  ] = 1400
            self._distances[self._convNum(30)  ] = 1600
            self._distances[self._convNum(25)  ] = 1800
            self._distances[self._convNum(21)  ] = 2000
            self._distances[self._convNum(17)  ] = 2200
            self._distances[self._convNum(12)  ] = 2400
            self._distances[self._convNum(9)   ] = 2600
            self._distances[self._convNum(7)   ] = 2800
            self._distances[self._convNum(6.9) ] = 3000
            self._distances[self._convNum(5.5) ] = 3200
            self._distances[self._convNum(3.4) ] = 3400


        if nAnt == 3:
            # Console ant
            self._distances[self._convNum(3160)] = 200
            self._distances[self._convNum(445) ] = 400
            self._distances[self._convNum(172) ] = 600
            self._distances[self._convNum(100) ] = 800
            self._distances[self._convNum(65)  ] = 1000
            self._distances[self._convNum(45)  ] = 1200
            self._distances[self._convNum(35)  ] = 1400
            self._distances[self._convNum(27)  ] = 1600
            self._distances[self._convNum(23)  ] = 1800
            self._distances[self._convNum(19)  ] = 2000
            self._distances[self._convNum(15)  ] = 2200
            self._distances[self._convNum(10)  ] = 2400
            self._distances[self._convNum(8)   ] = 2600
            self._distances[self._convNum(6.5) ] = 2800
            self._distances[self._convNum(6)   ] = 3000
            self._distances[self._convNum(4.8) ] = 3200
            self._distances[self._convNum(3)   ] = 3400


        try:
            self._min_rssi = min(self._distances.keys())
            self._max_rssi = max(self._distances.keys())
        except: 
            print("loh")

    def _calcDistance(self):
        # try:
            self._keyCircles.clear()

            for antPos in self._antPoints:
                nAnt = self._antPoints[antPos] 
                self._calcDistFromCalibrationData(nAnt)
                sumRSSI = 0
                for i in range(3):
                    sumRSSI += self._ants_keys_data.one_key_data[nAnt][i]**2
                sumRSSI = sumRSSI ** (0.5)

                if sumRSSI > 0:
                    calcDist = sumRSSI ** (-0.5)
                    res = 0
                    if self._max_rssi < calcDist:
                        res = calcDist / self._max_rssi * self._distances[self._max_rssi]
                    elif self._min_rssi > calcDist:
                        res = calcDist / self._min_rssi * self._distances[self._min_rssi]
                    else:
                        min_closest = self._max_rssi
                        max_closest = self._min_rssi
                        for key in self._distances.keys():
                            if key - calcDist > 0 and \
                               key - calcDist < min_closest - calcDist:
                                min_closest = key
                               
                            if calcDist - key > 0 and \
                               calcDist - key < calcDist - max_closest:
                                max_closest = key
                    
                        k = (self._distances[min_closest] - self._distances[max_closest]) / (min_closest-max_closest)

                        b = self._distances[min_closest] - k*min_closest

                        res = k*calcDist + b

                    self._keyCircles[antPos] = res / self._dist_to_mesh_coeff

            points = set()
            self._bluePoints.clear()
            for circ1 in self._keyCircles:
                for circ2 in self._keyCircles:
                    r1 = self._keyCircles[circ1]
                    r2 = self._keyCircles[circ2]
                    res = self._findIntersectionPoint(circ1, r1, circ2, r2)
                    if res:
                        points.add(res)

            pointsList = []
            for p in points:
                pointsList.append(p)
            self._findKeyPoint(pointsList)

    def _findZone(self):
        # try:
            self._key_inside = 0
            
            upperMin = float('inf')
            bottomMin = float('inf')
            for greenPoint in self._greenPoints:
                greenRSSI = self._greenPoints[greenPoint].dataRMS
                
                


            #     minDist = float('inf')
            #     greenPointMin = tuple()
            #     for point in self._greenPoints:
            #         dist = ((point[0] - pos_first_ant[0])**2 + (point[1] - pos_first_ant[1])**2)**0.5

            #         if abs(minDist - dist_from_first_ant) > abs(dist - dist_from_first_ant):
            #             minDist = dist
            #             greenPointMin = point
            #             self._purplePoints.clear()
            #             self._purplePoints[point] = 0

            #     distBetween = minDist - dist_from_first_ant
            #     print(distBetween)

            #     minRadius = float('inf')
            #     for point in self._zoneCircles:
            #         for radius in self._zoneCircles[point]:
            #             if abs(minRadius - minDist) > abs(radius - minDist):
            #                 minRadius = radius
            #                 self._activeZoneCircles.clear()
            #                 self._activeZoneCircles[point] = [radius]

            #     self._key_inside = 1
            #     dataToCompare = self._greenPoints[greenPointMin].dataRMS
 
            #     badAnts = set()
            #     minAntRSSI = float('inf')
            #     for antPos in self._antPoints:
            #         nAnt = self._antPoints[antPos] 

            #         if nAnt != self._first_ant - 1 and dataToCompare[nAnt] != 0:
            #             minAntRSSI = min(minAntRSSI, dataToCompare[nAnt])
            #             print("Ant: ", nAnt+1, "green RSSI: ", dataToCompare[nAnt])
                
            #     print("RSSI to Comp: ", minAntRSSI)

            #     for antPos in self._antPoints:
            #         nAnt = self._antPoints[antPos] 
            #         if nAnt != self._first_ant - 1 and dataToCompare[nAnt] != 0:
            #             sumRSSI = 0
            #             for i in range(3):
            #                 sumRSSI += self._ants_keys_data.one_key_data[nAnt][i]**2
            #             sumRSSI = sumRSSI ** (0.5)
            #             print("Ant: ", nAnt+1, "Real RSSI: ", sumRSSI)
            #             if (minAntRSSI > sumRSSI):
            #                 self._key_inside = 2
            #                 badAnts.add(nAnt+1)

            #     print(badAnts)

            # self._paintMeasureEvent()
        # except Exception as exc:
        #     self._logger.warning(f"Calc Distance Error: {exc}")

    def _findIntersectionPoint(self, circ1pos, r1, circ2pos, r2):
        # try:
            if circ1pos == circ2pos:
                return None

            xdelta = circ1pos[0]
            ydelta = circ1pos[1]

            x2 = circ2pos[0] - xdelta
            y2 = circ2pos[1] - ydelta

            a = -2*x2
            b = -2*y2
            c = x2**2 + y2**2 + r1**2 - r2**2

            r = r1
            eps = self._mesh_step/10
            x0 = -a*c/(a*a+b*b) 
            y0 = -b*c/(a*a+b*b)
            
            dist = (x2**2 + y2**2)**0.5
            if (dist > r1+r2):
                x = (x2 * (((dist-r1-r2)/2) + r1)/dist)
                y = (y2 * (((dist-r1-r2)/2) + r1)/dist)
                pos = tuple([int(x+xdelta), int(y+ydelta)])
                self._bluePoints[pos] = 0 
                return tuple([pos, pos])
            
            elif (dist+eps > r1+r2):
                pos = tuple([int(x0+xdelta), int(y0+ydelta)])
                self._bluePoints[pos] = 0 
                return tuple([pos, pos])
            
            elif (dist-eps < abs(r1-r2)):
                if(r1>r2):
                    x = (x2 * ((r1-dist-r2)/2+dist+r2)/dist)
                    y = (y2 * ((r1-dist-r2)/2+dist+r2)/dist)
                else:
                    x = -(x2 * ((r1-dist-r2)/2+r2)/dist)
                    y = -(y2 * ((r1-dist-r2)/2+r2)/dist)

                pos = tuple([int(x+xdelta), int(y+ydelta)])
                self._bluePoints[pos] = 0 
        
                return tuple([pos, pos])
            else:
                d = r*r - c*c/(a*a+b*b)
                mult = (d / (a*a+b*b))**0.5
                ax = x0 + b * mult + xdelta
                bx = x0 - b * mult + xdelta
                ay = y0 - a * mult + ydelta
                by = y0 + a * mult + ydelta
                pos1 = tuple([int(ax), int(ay)])
                self._bluePoints[pos1] = 0 
                pos2 = tuple([int(bx), int(by)])
                self._bluePoints[pos2] = 0 
                res = [pos1, pos2]
                res.sort()
                return tuple([res[0], res[1]])
        # except Exception as exc:
        #     self._logger.warning(f"Find Intersection Error: {exc}")

    def _findKeyPoint(self, points):
        # try:
            self._darkRedPoints.clear()

            if len(points) < 2:
                return

            iterations = []
            for p in points:
                iterations.append(0)

            min_dist = float("inf")
            cur_dist = 0
            md_points = []
            amountOfPairs = len(points)
            for i in range(1, 2**amountOfPairs+1):
                for j in range(amountOfPairs):
                    for g in range(amountOfPairs):
                        if j < g:
                            cur_dist += ((points[j][iterations[j]][0] - points[g][iterations[g]][0])**2 +
                                        (points[j][iterations[j]][1] - points[g][iterations[g]][1])**2)**0.5

                if (cur_dist < min_dist):
                    min_dist = cur_dist
                    md_points = iterations.copy()
                cur_dist = 0            
                

                for j in range(amountOfPairs):
                    if i % (2**(j)) == 0:
                        if iterations[j] == 0:
                            iterations[j] = 1
                        else:
                            iterations[j] = 0

            sumX = 0
            sumY = 0
            for i in range(amountOfPairs):
                p = points[i][md_points[i]]

                sumX += p[0]
                sumY += p[1]

                if p in self._bluePoints:
                    del self._bluePoints[p]
                self._darkRedPoints[p] = 0 
                if p in self._bluePoints:
                    del self._bluePoints[p]
                self._darkRedPoints[p] = 0

            self._redPoints.clear()
            p = tuple([int(sumX/amountOfPairs), int(sumY/amountOfPairs)])
            self._redPoints[p] = 0 
        # except Exception as exc:
        #     self._logger.warning(f"Find key point Error: {exc}")

    def _populateSetAnts(self):
        self._setAntMenu.clear()

        actions = []
        availableAnts = []
        for i in range(0, self._AntAmount):
            if i not in self._antPoints.values():
                availableAnts.append(i)

        for ant in availableAnts:
            action = QAction(f"Ant {ant+1}", self)
            action.triggered.connect(partial(self._setPoint, type = self.PointType.Ant, antNum = ant))
            actions.append(action)
        # Step 3. Add the actions to the menu
        self._setAntMenu.addActions(actions)

    def _mouseClickCallback(self, event):
        self._lastPos = tuple([(round(event.pos().x() / self._mesh_step) * self._mesh_step),
                               (round(event.pos().y() / self._mesh_step) * self._mesh_step)])

        if event.button() == Qt.LeftButton:
            if self._whichPointPlaced() == self.PointType.Gray and self._rssiFloatingWindowIsHidden:
                if not self._yellowPointInProgress:
                    self._setPoint(type = self.PointType.Yellow)

            if self._whichPointPlaced() == self.PointType.Green:
                self._showFloatingWindow()

            if self._rssiFloatingWindow.isHidden():
                self._rssiFloatingWindowIsHidden = True

        if event.button() == Qt.RightButton:
            self._hideFloatingWindow()
            self._updateToolbarData()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._hideFloatingWindow()
    
    def focusOutEvent(self, e):
        self._hideFloatingWindow()
  
    def _updateToolbarData(self):
        if self._whichPointPlaced() == None:
            self._writeRSSIAction.setVisible(False)
            if (self._yellowPointInProgress):
                self._writeRSSIAction.setText("Polling in progress...")
                self._writeRSSIAction.setDisabled(True)
            else:
                self._writeRSSIAction.setText("Write RSSI")
                self._writeRSSIAction.setEnabled(True)

            self._deletePointAction.setVisible(False)
            if len(self._antPoints) < self._AntAmount:
                self._setAntAction.setVisible(True)
            else:
                self._setAntAction.setVisible(False)

            self._ant_num_action.setVisible(False)

        elif self._whichPointPlaced() == self.PointType.Green:
            self._writeRSSIAction.setVisible(False)
            self._deletePointAction.setVisible(True)
            self._setAntAction.setVisible(False)

            self._ant_num_action.setVisible(False)

        elif self._whichPointPlaced() == self.PointType.Yellow:
            self._writeRSSIAction.setVisible(False)
            self._deletePointAction.setVisible(True)
            self._setAntAction.setVisible(False)

            self._writeRSSIAction.setVisible(True)
            self._writeRSSIAction.setText("Polling in progress...")
            self._writeRSSIAction.setDisabled(True)

            self._ant_num_action.setVisible(False)

        elif self._whichPointPlaced() == self.PointType.Ant:
            antNum = self._antPoints[self._lastPos]
            self._ant_num_action.setVisible(True)
            self._ant_num_action.setText(f"Ant №{antNum+1}")

            self._writeRSSIAction.setVisible(False)
            self._deletePointAction.setVisible(True)
            self._setAntAction.setVisible(False)

        elif self._whichPointPlaced() == self.PointType.Gray:
            self._writeRSSIAction.setVisible(True)
            if (self._yellowPointInProgress):
                self._writeRSSIAction.setText("Polling in progress...")
                self._writeRSSIAction.setDisabled(True)
            else:
                self._writeRSSIAction.setText("Write RSSI")
                self._writeRSSIAction.setEnabled(True)

            self._deletePointAction.setVisible(False)
            if len(self._antPoints) < self._AntAmount:
                self._setAntAction.setVisible(True)
            else:
                self._setAntAction.setVisible(False)

            self._ant_num_action.setVisible(False)

            return
        else:
            return
            
    def _deletePoint(self, coords:tuple() = None) -> PointType:
        type = None
        if not coords:
            pos = self._lastPos
        else:
            pos = coords

        if pos in self._greenPoints.keys():
            del self._greenPoints[pos]
            type = self.PointType.Green

        if pos in self._yellowPoints.keys():
            self._askForPollingFunc(start = False)
            self._yellowPointInProgress = False
            del self._yellowPoints[pos]
            type = self.PointType.Yellow
            self._yellowAnimation.stop()
        
        if pos in self._antPoints.keys():
            del self._antPoints[pos]
            type = self.PointType.Ant

        self._calibrate()
        self._paintCalibrationEvent()
        self._paintMeasureEvent()

        return type
        
    def _setPoint(self, type: PointType, antNum = None, coords:tuple() = None):
        self._deletePoint(coords)
        self._yellowAnimation.stop()

        if not coords:
            pos = self._lastPos
        else:
            pos = coords

        if (pos[0] >= self._mesh_step and pos[0] <= self._picWidth - self._mesh_step and 
            pos[1] >= self._mesh_step and pos[1] <= self._picHeight - self._mesh_step):

            if type == self.PointType.Green:
                self._greenPoints[pos] = KeysDataAverage(self._ants_keys_data)
                self._calibrate()    

            elif type == self.PointType.Yellow: 
                self._yellowPointInProgress = True
                self._lastYellowPos = pos
                self._askForPollingFunc(start = True)
                self._amountsOfAverage = 0
                self._average_data = np.zeros((((self._AntAmount+1, 3))), dtype=int)
                self._authOkAmount = 0
                self._yellowPoints[pos] = 0
                self._yellowAnimation.start()

            elif type == self.PointType.Red: 
                self._redPoints[pos] = 0

            elif type == self.PointType.Ant:  
                self._antPoints[pos] = antNum  
                self._calibrate()              

            self._paintCalibrationEvent()
            self._paintMeasureEvent()

    def _showFloatingWindow(self):
        self._highlitedPoints.clear()
        self._highlitedPoints[self._lastPos] = 0

        cursPos = tuple([(round(QCursor.pos().x() / self._mesh_step) * self._mesh_step),
                         (round(QCursor.pos().y() / self._mesh_step) * self._mesh_step)])
        
        self._rssiFloatingWindow.move(cursPos[0], int(cursPos[1] + self._mesh_step/2))
        self._printAntsData()

        self._highlitedPoints.clear()
        self._highlitedPoints[self._lastPos] = 0
        self._paintCalibrationEvent()

        self._rssiFloatingWindowIsHidden = False
        self._rssiFloatingWindow.setFocus()
        self._rssiFloatingWindow.show()

    def _hideFloatingWindow(self):
        self._rssiFloatingWindow.hide()
        self._highlitedPoints.clear()
        self._paintCalibrationEvent()

    def _whichPointPlaced(self) -> PointType:
        if self._lastPos in self._greenPoints.keys():
            return self.PointType.Green
        
        if self._lastPos in self._grayPoints.keys():
            return self.PointType.Gray
            
        if self._lastPos in self._yellowPoints.keys():
            return self.PointType.Yellow
            
        if self._lastPos in self._redPoints.keys():
            return self.PointType.Red
        
        if self._lastPos in self._antPoints.keys():
            return self.PointType.Ant
            
        return None

    def _paintMainPic(self, label):
        canvas = QPixmap(self._canvas_width, self._canvas_height)
        canvas.fill(Qt.white)
        label.setPixmap(canvas)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMargin(0)
        # self._calibrationLabel.setStyleSheet("border: 1px solid black")

        painter = QPainter(label.pixmap())

        pixmap = QPixmap(self._vehicle_pic_name)
        pixmap = pixmap.scaledToHeight(self._picture_height)
        painter.drawPixmap(self._canvas_width//2 - pixmap.width()//2 + self._picture_shift_hor,
                           self._canvas_height//2 - pixmap.height()//2, 
                           pixmap)
        
        self._picWidth = canvas.width()
        self._picHeight = canvas.height()
        
        x_offset = canvas.width() // 2
        y_offset = canvas.height() // 2
        x_size = canvas.width()
        y_size = canvas.height()
        
        # Draw the coordinate mesh
        pen = QPen(Qt.black, 1, Qt.SolidLine)
        painter.setPen(pen)
        
        # Draw vertical lines
        for x in range(x_offset, x_size, self._mesh_step):
            painter.drawLine(x, 0, x, y_size)
            painter.drawLine(x_size-x, 0, x_size-x, y_size)
        
        # Draw horizontal lines
        for y in range(y_offset, y_size, self._mesh_step):
            painter.drawLine(0, y, x_size, y)
            painter.drawLine(0, y_size-y, x_size, y_size-y)

        painter.end()

    def _paintCalibrationEvent(self, event = None):
        self._calibrationLabel.clear()

        self._paintMainPic(self._calibrationLabel)
        self._paintZones()

        painter = QPainter(self._calibrationLabel.pixmap())

        # Zones full circles dash lines
        painter.setPen(QPen(QColor('gray'), 3, Qt.DotLine))
        painter.setBrush(QColor('transparent'))
        for point in self._zoneCircles:
            for radius in self._zoneCircles[point]:
                radius = int(radius)
                painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)
        
        # Zones purple dash lines
        painter.setPen(QPen(QColor('purple'), 5))
        painter.setBrush(QColor('transparent'))
        for point in self._zoneCircles:
            for radius in self._zoneCircles[point]:
                if (self._vehicle_size[0]/2 <= radius):
                    angle = int(180/3.14*math.acos(self._vehicle_size[0]/(radius*2)))
                    radius = int(radius)
                    painter.drawArc(point[0]-radius, point[1]-radius, 
                                    radius*2, radius*2, 
                                    -angle*16, -(180 - 2*angle) * 16)
                else:
                    painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)
    
        # Edge rect
        painter.setPen(QPen(QColor('purple'), 5))
        painter.setBrush(QColor('transparent'))
        for point in self._vehicleEdgeRect:
            rect = QRect(QPoint(point[0], point[1]), 
                         QSize(self._vehicleEdgeRect[point][0], 
                               self._vehicleEdgeRect[point][1]))
            painter.drawRect(rect)

        # Grat points for calibration places
        radius = 10
        painter.setPen(QPen(QColor('gray'), 1))
        painter.setBrush(QColor('gray'))
        for point in self._grayPoints:
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        # Calibration dots of different collors
        pen = QPen()
        radius = 10
        pen.setWidth(1)
        for point in self._greenPoints:
            k = (self._greenPoints[point].auths_ok /
                 self._greenPoints[point].polls_done)
            color = QColor(max(0, int(150-150*k*2)+1), 
                           min(150, int(75*k*2))+10, 1)
            pen.setColor(color)
            painter.setPen(pen)
            painter.setBrush(color)
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        # Yellow calibration circle with float radius
        radius = self.yellow_radius
        painter.setPen(QPen(QColor('black'), 1))
        painter.setBrush(QColor('yellow'))
        for point in self._yellowPoints:
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        # Ants rectangels
        size = 20
        painter.setPen(QPen(QColor('orange'), 1))
        painter.setBrush(QColor('orange'))
        for point in self._antPoints:
            rect = QRect(QPoint(point[0]-size//2, 
                                point[1]-size//2), 
                         QSize(size, size))
            painter.drawRect(rect)

        # Highligted calibration dots of different collors
        pen = QPen()
        radius = 13
        pen.setWidth(1)
        for point in self._highlitedPoints:
            k = (self._greenPoints[point].auths_ok /
                 self._greenPoints[point].polls_done)

            color = QColor(max(0, int(150-150*k*2)+1), 
                           min(150, int(75*k*2))+60, 1)
            pen.setColor(color)
            painter.setPen(pen)
            painter.setBrush(color)
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        self._calibrationLabel.update()

    def _paintMeasureEvent(self, event = None):
        self._measureLabel.clear()

        self._paintMainPic(self._measureLabel)

        painter = QPainter(self._measureLabel.pixmap())


        # Zones full circles dash lines
        painter.setPen(QPen(QColor('gray'), 3, Qt.DotLine))
        painter.setBrush(QColor('transparent'))
        for point in self._activeZoneCircles:
            for radius in self._activeZoneCircles[point]:
                radius = int(radius)
                painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)
        
        # Zones purple dash lines
        painter.setPen(QPen(QColor('purple'), 5))
        painter.setBrush(QColor('transparent'))
        for point in self._activeZoneCircles:
            for radius in self._activeZoneCircles[point]:
                if (self._vehicle_size[0]/2 <= radius):
                    angle = int(180/3.14*math.acos(self._vehicle_size[0]/(radius*2)))
                    radius = int(radius)
                    painter.drawArc(point[0]-radius, point[1]-radius, 
                                    radius*2, radius*2, 
                                    -angle*16, -(180 - 2*angle) * 16)
                else:
                    painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        # radius = 10
        # painter.setPen(QPen(QColor('red'), 1))
        # painter.setBrush(QColor('red'))
        # for point in self._redPoints:
        #     painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        # radius = 3
        # painter.setPen(QPen(QColor('blue'), 1))
        # painter.setBrush(QColor('blue'))
        # for point in self._bluePoints:
        #     painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        # radius = 4
        # painter.setPen(QPen(QColor('darkRed'), 1))
        # painter.setBrush(QColor('darkRed'))
        # for point in self._darkRedPoints:
        #     painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        size = 20
        painter.setPen(QPen(QColor('orange'), 1))
        painter.setBrush(QColor('orange'))
        for point in self._antPoints:
            rect = QRect(QPoint(point[0]-size//2, 
                                point[1]-size//2), 
                         QSize(size, size))
            painter.drawRect(rect)

        painter.setPen(QPen(QColor('blue'), 1))
        painter.setBrush(QColor('transparent'))
        for point in self._keyCircles:
            radius = self._keyCircles[point]
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        # Edge rect
        painter.setPen(QPen(QColor('purple'), 5))

        if self._key_inside == 0:
            painter.setBrush(QColor('transparent'))
        elif self._key_inside == 1:
            painter.setBrush(QColor(0, 255, 0, 50))
        else:
            painter.setBrush(QColor(255, 0, 0, 50))

        for point in self._vehicleEdgeRect:
            rect = QRect(QPoint(point[0], point[1]), 
                         QSize(self._vehicleEdgeRect[point][0], 
                               self._vehicleEdgeRect[point][1]))
            painter.drawRect(rect)


        radius = 10
        painter.setPen(QPen(QColor('pink'), 1))
        painter.setBrush(QColor('pink'))
        for point in self._purplePoints:
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)


        self._measureLabel.update()

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


        keyFrameLocal=QFrame()

        self._keyLabel = QLabel()
        font = self._keyLabel.font()
        font.setPointSize(10)
        self._keyLabel.setFont(font)
        self._keyLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self._authLabel = QLabel()
        font = self._authLabel.font()
        font.setPointSize(10)
        self._authLabel.setFont(font)
        self._authLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        l = QVBoxLayout()
        l.addWidget(self._keyLabel)
        l.addWidget(self._authLabel)
        l.setSpacing(0)
        keyFrameLocal.setLayout(l)
        smallVLayout[0].addWidget(keyFrameLocal)
        smallVLayout[0].setStretch(1, 1)

        self._keyFrames.append(keyFrameLocal)

        for nAnt in range(1, self._AntAmount+1):
            w = QLabel(f"Ant {nAnt}")
            font = w.font()
            font.setPointSize(10)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            smallVLayout[nAnt].addWidget(w)
            smallVLayout[nAnt].setSpacing(0)

            keyFrameLocal = QFrame()

            k = QLabel()
            k.setFont(QFont('Courier', 10))
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
            keyFrameLocal.setLayout(l)

            smallVLayout[nAnt].addWidget(keyFrameLocal)
            smallVLayout[nAnt].setStretch(1, 1)

            self._keyFrames.append(k)

            self._RSSI_Widgets.append(k)

        w = QWidget()
        w.setLayout(bigHLayout)

        scrollAntsData = QScrollArea()
        scrollAntsData.setWidget(w)
        scrollAntsData.setWidgetResizable(True) 
        scrollAntsData.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scrollAntsData.setFixedHeight(250)
        scrollAntsData.setMinimumWidth(500)
        scrollAntsData.setMaximumWidth(1000)

        return scrollAntsData

    def _printAntsData(self):
        keys_data_average_data = self._greenPoints[self._lastPos]
        self._keyLabel.setText(f"Key {keys_data_average_data.key_num+1}")
        self._authLabel.setText(f"Auths {keys_data_average_data.auths_ok}/{keys_data_average_data.polls_done}")
        data = keys_data_average_data.data
        dataRMS = keys_data_average_data.dataRMS
        polling = keys_data_average_data.good_pollings_amount
        for nAnt in range(self._AntAmount):
            if polling[nAnt] != 0:
                self._antFrames[nAnt+1].show()
                self._RSSI_Widgets[nAnt].setText(f" X : {' '*(6-len(str(int(data[nAnt][0]))))}{int(data[nAnt][0])}\n"
                                                 f" Y : {' '*(6-len(str(int(data[nAnt][1]))))}{int(data[nAnt][1])}\n"
                                                 f" Z : {' '*(6-len(str(int(data[nAnt][2]))))}{int(data[nAnt][2])}\n"
                                                 f"RMS: {' '*(6-len(str(int(dataRMS[nAnt]))))}{int(dataRMS[nAnt])}\n"
                                                 f"Pol: {' '*(6-len(str(    polling[nAnt] )))}{    polling[nAnt] }")
            else:
                self._antFrames[nAnt+1].hide()

    @pyqtProperty(float)
    def yellow_radius(self):
        return self._yellow_radius
    
    @yellow_radius.setter
    def yellow_radius(self, pos):
        self._yellow_radius = pos
        self._paintCalibrationEvent()
        if self._yellowAnimation.endValue() == pos:
            start =  self._yellowAnimation.endValue()
            end =  self._yellowAnimation.startValue()
            self._yellowAnimation.stop()
            self._yellowAnimation.setStartValue(start)
            self._yellowAnimation.setEndValue(end)
            self._yellowAnimation.start()