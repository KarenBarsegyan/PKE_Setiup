
from PyQt5.QtWidgets import (
    QVBoxLayout, QLabel,
    QWidget, QScrollArea, QMenu,
    QAction
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QPen, QColor
)
from PyQt5.QtCore import Qt, QThread, QPoint, QSize, QRect, pyqtSignal
import logging
import os
import numpy as np
from functools import partial
import json
from json import JSONEncoder

class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)

class InteractiveData(QThread):
    class PointType(int):
        Green = 1
        Yellow = 2 
        Red = 3 
        Blue = 4
        Ant = 5

    def __init__(self, askForPollingFunc, parent=None):
        QThread.__init__(self, parent)

        self._mesh_step = 25
        self._greenPoints = dict()
        self._yellowPoints = dict()
        self._redPoints = dict()
        self._bluePoints = dict()
        self._keyCircles = dict()
        self._antPoints = dict()
        self._lastPos = tuple()
        self._lastYellowPos = tuple()
        self._yellowPointInProgress = False
        self._AntAmount = 6
        self._KeyAmount = 5
        self._data = np.zeros((((self._AntAmount, self._KeyAmount, 3))), dtype=int)
        self._average_data = self._data
        self._askForPollingFunc = askForPollingFunc
        self._amountsOfAverage = 0
        self._picWidth = 0
        self._picHeight = 0
        self._distCoeff = 0

        self._store_data_path = 'store_data'

        self._init_logger()
        self._restoreData()
        self.Calibrate()

    def __del__(self):
        pass

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

    def _restoreData(self):
        try:
            os.mkdir(f"{self._store_data_path}/")
        except: pass

        try:
            with open(f'{self._store_data_path}/points') as f:
                pointsData = json.load(f)

            for point in pointsData['pointsGreen']: 
                numpyArray = np.asarray(pointsData['pointsGreen'][point])
                self._greenPoints[tuple(json.loads(point))] = numpyArray

            # for point in pointsData['pointsYellow']: 
            #     self._yellowPoints[tuple(json.loads(point))] = 0

            # for point in pointsData['pointsRed']: 
            #     self._redPoints[tuple(json.loads(point))] = 0

            for point in pointsData['pointsAnt']: 
                antNum = pointsData['pointsAnt'][point]
                self._antPoints[tuple(json.loads(point))] = antNum

        except:
            self._logger.info("No points data yet")

    def _saveData(self):
        data = dict()

        d = dict()
        for point in self._greenPoints:  
            d[json.dumps(point)] = self._greenPoints[point]
        data['pointsGreen'] = d

        # d = dict()
        # for point in self._yellowPoints:  
        #     d[json.dumps(point)] = self._yellowPoints[point]
        # data['pointsYellow'] = d

        # d = dict()
        # for point in self._redPoints:  
        #     d[json.dumps(point)] = self._redPoints[point]
        # data['pointsRed'] = d

        d = dict()
        for point in self._antPoints:  
            d[json.dumps(point)] = self._antPoints[point]
        data['pointsAnt'] = d
        
        with open(f'{self._store_data_path}/points', 'w') as f:
            json.dump(data, f, cls=NumpyArrayEncoder)

    def RememberData(self, Data, isDone):
        self._data = Data
        self._average_data += self._data
        self._amountsOfAverage += 1
    
        if isDone and self._yellowPointInProgress:
           self._data = np.floor_divide(self._average_data, self._amountsOfAverage)
           self._setPoint(type = self.PointType.Green, coords = self._lastYellowPos)
           self._average_data = np.zeros((((self._AntAmount, self._KeyAmount, 3))), dtype=int)
           self._amountsOfAverage = 0
           self._yellowPointInProgress = False

        self._updateToolbarData()
        self._calcDistance()
    
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

        self._calibrationLabel.setContextMenuPolicy(Qt.ActionsContextMenu)
        self._calibrationLabel.addAction(self._writeRSSIAction)
        self._calibrationLabel.addAction(self._deletePointAction)
        self._calibrationLabel.addAction(self._setAntAction)
        self._calibrationLabel.addAction(separator)
        self._calibrationLabel.addAction(self._ant_num_action)

        localLayout.addWidget(self._calibrationLabel)

        self._paintMainPic(self._calibrationLabel)
        self._paintCalibrationEvent()

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
        # self._calibration_data = np.zeros((((self._AntAmount, self._KeyAmount, 1))), dtype=int)
        coeff = 0
        amountOfCalcs = 0
        for antPos in self._antPoints:
            nAnt = self._antPoints[antPos]   
            for gPos in self._greenPoints:
                for nKey in range(1):
                    sumRSSI = 0
                    for i in range(3):
                        sumRSSI += (self._greenPoints[gPos][nAnt][nKey][i])**2

                    sumRSSI = int(round(sumRSSI ** 0.5))
                    dist = ((gPos[0] - antPos[0])**2 + (gPos[1] - antPos[1])**2)**0.5

                    coeff += sumRSSI*dist*dist
                    amountOfCalcs += 1

                print(f"RSSI: {sumRSSI} - Dist: {dist} - Coeff: {sumRSSI*dist*dist}")
                # print(f"Ant: {nAnt}\nnKey: {nKey}\nDist: {dist}\nRSSI: {sumRSSI}")
        if(amountOfCalcs != 0):
            self._distCoeff = coeff/amountOfCalcs

            print(f"Mean val: {coeff/amountOfCalcs}")
        print("--------------------------------\n")

    def _calcDistance(self):
        self._keyCircles.clear()
        self._bluePoints.clear()

        for antPos in self._antPoints:
            nAnt = self._antPoints[antPos]   
            sumRSSI = 0
            for i in range(3):
                sumRSSI += (self._data[nAnt][0][i])**2
            sumRSSI = int(round(sumRSSI ** 0.5))

            if sumRSSI > 0:
                radius = int((self._distCoeff/sumRSSI)**0.5)
                self._keyCircles[antPos] = radius
        

        for circ1 in self._keyCircles:
            for circ2 in self._keyCircles:
                r1 = self._keyCircles[circ1]
                r2 = self._keyCircles[circ2]
                self._findIntersectionPoint(circ1, r1, circ2, r2)

        self._paintMeasureEvent()

    def _findIntersectionPoint(self, circ1pos, r1, circ2pos, r2):
        if circ1pos == circ2pos:
            return

        xdelta = circ1pos[0]
        ydelta = circ1pos[1]

        x2 = circ2pos[0] - xdelta
        y2 = circ2pos[1] - ydelta

        a = -2*x2
        b = -2*y2
        c = x2**2 + y2**2 + r1**2 - r2**2

        r = r1
        eps = 0 #self._mesh_step/10
        x0 = -a*c/(a*a+b*b) 
        y0 = -b*c/(a*a+b*b)

        if (c*c > r*r*(a*a+b*b)+eps):
            return None
        elif (abs(c*c - r*r*(a*a+b*b)) < eps):
            pos = tuple([int(x0+xdelta), int(y0+ydelta)])
            self._setPoint(type = self.PointType.Blue, coords=pos) 
        else:
            d = r*r - c*c/(a*a+b*b)
            mult = (d / (a*a+b*b))**0.5
            ax = x0 + b * mult + xdelta
            bx = x0 - b * mult + xdelta
            ay = y0 - a * mult + ydelta
            by = y0 + a * mult + ydelta
            pos = tuple([int(ax), int(ay)])
            self._setPoint(type = self.PointType.Blue, coords=pos) 
            pos = tuple([int(bx), int(by)])
            self._setPoint(type = self.PointType.Blue, coords=pos) 

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
            if self._whichPointPlaced() == None:
                if not self._yellowPointInProgress:
                    self._setPoint(type = self.PointType.Yellow)
            elif self._whichPointPlaced() == self.PointType.Green:
                pass
        
        if event.button() == Qt.RightButton:
            self._updateToolbarData()
  
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

            Data = self._data

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

            Data = self._data

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

        # if pos in self._redPoints.keys():
        #     del self._redPoints[pos]

            type = self.PointType.Red
        
        if pos in self._antPoints.keys():
            del self._antPoints[pos]
            type = self.PointType.Ant

        self._paintCalibrationEvent()
        self._paintMeasureEvent()
        self._saveData()

        return type
        
    def _setPoint(self, type: PointType, antNum = None, coords:tuple() = None):
        self._deletePoint(coords)

        if not coords:
            pos = self._lastPos
        else:
            pos = coords

        if (pos[0] >= self._mesh_step and pos[0] <= self._picWidth - self._mesh_step and 
            pos[1] >= self._mesh_step and pos[1] <= self._picHeight - self._mesh_step):

            if type == self.PointType.Green:
                self._greenPoints[pos] = self._data.copy()
                self.Calibrate()

            elif type == self.PointType.Yellow: 
                self._yellowPointInProgress = True
                self._lastYellowPos = pos
                self._askForPollingFunc(start = True)
                self._yellowPoints[pos] = 0

            elif type == self.PointType.Red: 
                self._redPoints[pos] = 0

            elif type == self.PointType.Blue: 
                self._bluePoints[pos] = 0

            elif type == self.PointType.Ant:  
                self._antPoints[pos] = antNum

            self._paintCalibrationEvent()
            self._paintMeasureEvent()
            self._saveData()

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
        pen.setColor(QColor('green'))
        painter.setPen(pen)
        painter.setBrush(QColor('green'))
        for point in self._greenPoints:
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)

        pen = QPen()
        radius = 10
        pen.setWidth(1)
        pen.setColor(QColor('yellow'))
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
        pen.setWidth(1)
        pen.setColor(QColor('blue'))
        painter.setPen(pen)
        painter.setBrush(QColor('transparent'))
        for point in self._keyCircles:
            radius = self._keyCircles[point]
            painter.drawEllipse(QPoint(point[0], point[1]), radius, radius)


        self._measureLabel.update()
        