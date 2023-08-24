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
        Ant = 5

    def __init__(self, askForPollingFunc, parent=None):
        QThread.__init__(self, parent)

        self._mesh_step = 25
        self._greenPoints = dict()
        self._highlitedPoints = dict()
        self._yellowPoints = dict()
        self._redPoints = dict()
        self._bluePoints = dict()
        self._darkRedPoints = dict()
        self._keyCircles = dict()
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
        self._distCoeff = dict()

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
                dataMED = np.asarray(json.loads(pointsData['pointsGreen'][point][3]))
                auths_ok = pointsData['pointsGreen'][point][4]
                polls_done = pointsData['pointsGreen'][point][5]
                key_num = pointsData['pointsGreen'][point][6]

                data = KeysDataAverage()
                data.setData(numpyArray, auths_ok, pollings, polls_done, key_num, dataRMS, dataMED)
                self._greenPoints[tuple(json.loads(point))] = data

            self._antPoints.clear()
            for point in pointsData['pointsAnt']: 
                antNum = pointsData['pointsAnt'][point]
                self._antPoints[tuple(json.loads(point))] = antNum

            self.Calibrate()
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
                                    json.dumps(self._greenPoints[point].dataMED, cls=NumpyArrayEncoder),
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
        self._calibrationLabel.addAction(separator)
        self._calibrationLabel.addAction(self._ant_num_action)

        localLayout.addWidget(self._calibrationLabel)

        self._paintMainPic(self._calibrationLabel)
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

        self._paintMainPic(self._measureLabel)
        self._paintMeasureEvent()

        v_widget = QWidget()
        v_widget.setLayout(localLayout)  
        # v_widget.setStyleSheet("border: 1px solid black")

        scrollPicture = QScrollArea()
        scrollPicture.setWidget(v_widget)
        scrollPicture.setWidgetResizable(True) 

        return scrollPicture    

    def Calibrate(self):
        # try:
            for antPos in self._antPoints:
                coeff = 0
                amountOfCalcs = 0
                nAnt = self._antPoints[antPos]   
                
                # Delete old Coeff if exists
                if nAnt in self._distCoeff:
                    del self._distCoeff[nAnt]

                for gPos in self._greenPoints:
                    sumRSSI = 0
                    for i in range(3):
                        sumRSSI += (self._greenPoints[gPos].data[nAnt][i])**2

                    sumRSSI = sumRSSI ** 0.5

                    if sumRSSI > 0:
                        dist = ((gPos[0] - antPos[0])**2 + (gPos[1] - antPos[1])**2)**0.5
                        coeff += (sumRSSI**(0.4)) * dist
                        amountOfCalcs += 1

                    # print(f"ANT: {nAnt} \t RSSI: {sumRSSI} \t Dist: {int(dist)} \t Coeff: {int(sumRSSI*dist*dist)}")
                    # print(f"Ant: {nAnt}\nnKey: {self._greenPoints[gPos][self._AntAmount][0]+1}\nDist: {dist}\nRSSI: {sumRSSI}")
                if(amountOfCalcs != 0):
                    self._distCoeff[nAnt] = coeff/amountOfCalcs

            # print(f"Mean val: {self._distCoeff}")
            # print("--------------------------------\n")
        # except Exception as exc:
        #     self._logger.warning(f"No data to calibrate: {exc}")

    def _conv(self, num):
        return (num)**(-0.5)

    def _calcDistance(self):
        # try:
            dist_to_mesh_coeff = 8

            distances = dict()
    
            distances[self._conv(9050)] = 200
            distances[self._conv(1250)] = 400
            distances[self._conv(440) ] = 600
            distances[self._conv(227) ] = 800
            distances[self._conv(142) ] = 1000
            distances[self._conv(92)  ] = 1200
            distances[self._conv(64)  ] = 1400
            distances[self._conv(48)  ] = 1600
            distances[self._conv(38)  ] = 1800
            distances[self._conv(30)  ] = 2000
            distances[self._conv(23)  ] = 2200
            distances[self._conv(18)  ] = 2400
            distances[self._conv(14)  ] = 2600
            distances[self._conv(10)  ] = 2800
            distances[self._conv(7.7) ] = 3000
            distances[self._conv(6.2) ] = 3200
            distances[self._conv(5.5) ] = 3400
            distances[self._conv(5)   ] = 3600
            distances[self._conv(4.4) ] = 3800
            distances[self._conv(3.45)] = 4000

            min_rssi = min(distances.keys())
            max_rssi = max(distances.keys())

            self._keyCircles.clear()

            for antPos in self._antPoints:
                nAnt = self._antPoints[antPos]   
                sumRSSI = 0
                for i in range(3):
                    sumRSSI += self._ants_keys_data.one_key_data[nAnt][i]**2
                sumRSSI = sumRSSI ** (0.5)

                if sumRSSI > 0:
                    calcDist = sumRSSI ** (-0.5)
                    res = 0
                    if max_rssi < calcDist:
                        res = calcDist / max_rssi * distances[max_rssi]
                    elif min_rssi > calcDist:
                        res = calcDist / min_rssi * distances[min_rssi]
                    else:
                        min_closest = max_rssi
                        max_closest = min_rssi
                        for key in distances.keys():
                            if key - calcDist > 0 and \
                               key - calcDist < min_closest - calcDist:
                                min_closest = key
                               
                            if calcDist - key > 0 and \
                               calcDist - key < calcDist - max_closest:
                                max_closest = key
                    
                        k = (distances[min_closest] - distances[max_closest]) / (min_closest-max_closest)

                        b = distances[min_closest] - k*min_closest

                        res = k*calcDist + b
                    
                    # print("RSSI   = ", self.testRssi)
                    # print("Dist   = ", res)
                    # print()

                    self._keyCircles[antPos] = res / dist_to_mesh_coeff

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

            self._paintMeasureEvent()
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
            if self._whichPointPlaced() == None and self._rssiFloatingWindowIsHidden:
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

            Data = self._ants_keys_data

            self._ant_num_action.setVisible(False)

        elif self._whichPointPlaced() == self.PointType.Green:
            self._writeRSSIAction.setVisible(False)
            self._deletePointAction.setVisible(True)
            self._setAntAction.setVisible(False)

            Data = self._greenPoints[self._lastPos]

            self._ant_num_action.setVisible(False)

        elif self._whichPointPlaced() == self.PointType.Yellow:
            self._writeRSSIAction.setVisible(False)
            self._deletePointAction.setVisible(True)
            self._setAntAction.setVisible(False)

            self._writeRSSIAction.setVisible(True)
            self._writeRSSIAction.setText("Polling in progress...")
            self._writeRSSIAction.setDisabled(True)

            Data = self._ants_keys_data

            self._ant_num_action.setVisible(False)

        elif self._whichPointPlaced() == self.PointType.Ant:
            antNum = self._antPoints[self._lastPos]
            self._ant_num_action.setVisible(True)
            self._ant_num_action.setText(f"Ant №{antNum+1}")

            self._writeRSSIAction.setVisible(False)
            self._deletePointAction.setVisible(True)
            self._setAntAction.setVisible(False)

            return
        else:
            return

        # self._RSSI_x_action.setText(f"X: {' '*(3-len(str(Data[0][0][0])))}{Data[0][0][0]}")
        # self._RSSI_y_action.setText(f"Y: {' '*(3-len(str(Data[0][0][1])))}{Data[0][0][1]}")
        # self._RSSI_z_action.setText(f"Z: {' '*(3-len(str(Data[0][0][2])))}{Data[0][0][2]}")
            
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

        self.Calibrate()
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
                self.Calibrate()    

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
                self.Calibrate()              

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
            
        if self._lastPos in self._yellowPoints.keys():
            return self.PointType.Yellow
            
        if self._lastPos in self._redPoints.keys():
            return self.PointType.Red
        
        if self._lastPos in self._antPoints.keys():
            return self.PointType.Ant
            
        return None

    def _paintMainPic(self, label):
        canvas_width = 700
        canvas_height = 1000
        picture_height = 800

        canvas = QPixmap(canvas_width, canvas_height)
        canvas.fill(Qt.white)
        label.setPixmap(canvas)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMargin(0)
        # self._calibrationLabel.setStyleSheet("border: 1px solid black")

        painter = QPainter(label.pixmap())

        pixmap = QPixmap('pictures/GAZ_Top_View.png')
        pixmap = pixmap.scaledToHeight(picture_height)
        painter.drawPixmap(canvas_width//2 - pixmap.width()//2,
                           canvas_height//2 - pixmap.height()//2, 
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

        painter = QPainter(self._calibrationLabel.pixmap())
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

        pen = QPen()
        radius = self.yellow_radius
        pen.setWidth(1)
        pen.setColor(QColor('black'))
        painter.setPen(pen)
        painter.setBrush(QColor('yellow'))
        for point in self._yellowPoints:
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        pen = QPen()
        size = 20
        pen.setWidth(1)
        pen.setColor(QColor('orange'))
        painter.setPen(pen)
        painter.setBrush(QColor('orange'))
        for point in self._antPoints:
            rect = QRect(QPoint(point[0]-size//2, 
                                point[1]-size//2), 
                         QSize(size, size))
            painter.drawRect(rect)

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

        pen = QPen()
        radius = 10
        pen.setWidth(1)
        pen.setColor(QColor('red'))
        painter.setPen(pen)
        painter.setBrush(QColor('red'))
        for point in self._redPoints:
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        pen = QPen()
        radius = 3
        pen.setWidth(1)
        pen.setColor(QColor('blue'))
        painter.setPen(pen)
        painter.setBrush(QColor('blue'))
        for point in self._bluePoints:
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        pen = QPen()
        radius = 4
        pen.setWidth(1)
        pen.setColor(QColor('darkRed'))
        painter.setPen(pen)
        painter.setBrush(QColor('darkRed'))
        for point in self._darkRedPoints:
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        pen = QPen()
        size = 20
        pen.setWidth(1)
        pen.setColor(QColor('orange'))
        painter.setPen(pen)
        painter.setBrush(QColor('orange'))
        for point in self._antPoints:
            rect = QRect(QPoint(point[0]-size//2, 
                                point[1]-size//2), 
                         QSize(size, size))
            painter.drawRect(rect)

        pen = QPen()
        pen.setWidth(3)
        pen.setColor(QColor('blue'))
        painter.setPen(pen)
        painter.setBrush(QColor('transparent'))
        for point in self._keyCircles:
            radius = self._keyCircles[point]
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
        dataMED = keys_data_average_data.dataMED
        polling = keys_data_average_data.good_pollings_amount
        for nAnt in range(self._AntAmount):
            if polling[nAnt] != 0:
                self._antFrames[nAnt+1].show()
                self._RSSI_Widgets[nAnt].setText(f" X : {' '*(3-len(str(data[nAnt][0])))}{data[nAnt][0]}\n"
                                                 f" Y : {' '*(3-len(str(data[nAnt][1])))}{data[nAnt][1]}\n"
                                                 f" Z : {' '*(3-len(str(data[nAnt][2])))}{data[nAnt][2]}\n"
                                                 f"RMS: {' '*(3-len(str(dataRMS[nAnt])))}{dataRMS[nAnt]}\n"
                                                 f"MED: {' '*(3-len(str(dataMED[nAnt])))}{dataMED[nAnt]}\n"
                                                 f"Pol: {' '*(3-len(str(polling[nAnt])))}{polling[nAnt]}")
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