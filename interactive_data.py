
from PyQt5.QtWidgets import (
    QVBoxLayout, QLabel,
    QWidget, QScrollArea, QMenu,
    QAction
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QPen, QColor
)
from PyQt5.QtCore import Qt, QThread, QPoint, QSize, QRect
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
        Ant = 4

    def __init__(self, parent=None):
        QThread.__init__(self, parent)

        self._mesh_step = 25
        self._greenPoints = dict()
        self._yellowPoints = dict()
        self._redPoints = dict()
        self._antPoints = dict()
        self._lastPos = tuple()
        self._data = np.zeros(((6, 5, 3)))
        self._AntAmount = 6
        self._KeyAmount = 5

        self._store_data_path = 'store_data'

        self._init_logger()
        self._restoreData()

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

            for point in pointsData['pointsYellow']: 
                self._yellowPoints[tuple(json.loads(point))] = 0

            for point in pointsData['pointsRed']: 
                self._redPoints[tuple(json.loads(point))] = 0

            for point in pointsData['pointsAnt']: 
                self._antPoints[tuple(json.loads(point))] = 0

        except:
            print("No points data yet")
            self._logger.info("No points data yet")

    def _saveData(self):
        print("Seved")
        data = {
            'pointsGreen': {json.dumps(tuple([100, 100])): np.zeros(((6, 5, 3)))},
            'pointsYellow': {json.dumps(tuple([100, 100])): np.zeros(((6, 5, 3)))},
            'pointsRed': {json.dumps(tuple([150, 150])): np.zeros(((6, 5, 3)))},
            'pointsAnt': {json.dumps(tuple([200, 200])): np.zeros(((6, 5, 3)))},
        }
        for point in self._greenPoints():
            

        with open(f'{self._store_data_path}/points', 'w') as f:
            json.dump(data, f, cls=NumpyArrayEncoder)

    def RememberData(self, Data):
        self._data = Data
        self._updateToolbarData()
    
    def SetUpCalibrationDesk(self):
        localLayout = QVBoxLayout()
        localLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._writeRSSIAction = QAction(self)
        self._writeRSSIAction.setText("Write RSSI")
        self._writeRSSIAction.triggered.connect(partial(self._setPoint, self.PointType.Green))

        self._deletePointAction = QAction(self)
        self._deletePointAction.setText("Delete Point")
        self._deletePointAction.triggered.connect(self._deletePoint)

        self._setAntAction = QAction(self)
        self._setAntAction.setText("Set Ant Point")
        self._setAntMenu = QMenu("Open Recent")
        self._setAntAction.setMenu(self._setAntMenu)
        self._setAntMenu.aboutToShow.connect(self._populateSetAnts)
        # self._setAntAction.triggered.connect(self._setAntPoint)

        separator = QAction(self)
        separator.setSeparator(True)

        self._RSSI_type_action = QAction(self)

        self._RSSI_x_action = QAction(self)
        self._RSSI_x_action.setText(f"X = 122")
        self._RSSI_y_action = QAction(self)
        self._RSSI_y_action.setText(f"Y = 122")
        self._RSSI_z_action = QAction(self)
        self._RSSI_z_action.setText(f"Z = 122")

        self._calibrationLabel = QLabel()
        self._calibrationLabel.mousePressEvent = self._mouseClickCallback

        self._calibrationLabel.setContextMenuPolicy(Qt.ActionsContextMenu)
        self._calibrationLabel.addAction(self._writeRSSIAction)
        self._calibrationLabel.addAction(self._deletePointAction)
        self._calibrationLabel.addAction(self._setAntAction)
        self._calibrationLabel.addAction(separator)
        self._calibrationLabel.addAction(self._RSSI_type_action)
        self._calibrationLabel.addAction(self._RSSI_x_action)
        self._calibrationLabel.addAction(self._RSSI_y_action)
        self._calibrationLabel.addAction(self._RSSI_z_action)

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

    def _populateSetAnts(self):
        self._setAntMenu.clear()

        actions = []
        availableAnts = []
        for i in range(1, self._AntAmount + 1):
            if i not in self._antPoints.values():
                availableAnts.append(i)

        for ant in availableAnts:
            action = QAction(f"Ant {ant}", self)
            action.triggered.connect(partial(self._setPoint, self.PointType.Ant, ant))
            actions.append(action)
        # Step 3. Add the actions to the menu
        self._setAntMenu.addActions(actions)

    def _mouseClickCallback(self, event):
        self._lastPos = tuple( [(round(event.pos().x() / self._mesh_step) * self._mesh_step),
                                (round(event.pos().y() / self._mesh_step) * self._mesh_step)])

        if event.button() == Qt.LeftButton:
            if self._whichPointPlaced() == None:
                self._setPoint(self.PointType.Green)

            # print(f"Green: {len(self._greenPoints)}")
            # print(f"Yellow: {len(self._yellowPoints)}")
            # print(f"Red: {len(self._redPoints)}\n")
        elif event.button() == Qt.RightButton:
            self._updateToolbarData()
  
    def _updateToolbarData(self):
        if self._whichPointPlaced() == None:
            self._RSSI_x_action.setVisible(True)
            self._RSSI_y_action.setVisible(True)
            self._RSSI_z_action.setVisible(True)

            self._writeRSSIAction.setVisible(True)
            self._deletePointAction.setVisible(False)
            if len(self._antPoints) < self._AntAmount:
                self._setAntAction.setVisible(True)
            else:
                self._setAntAction.setVisible(False)

            Data = self._data

            self._RSSI_type_action.setText(f"Actual Data")

        elif self._whichPointPlaced() == self.PointType.Green:
            self._RSSI_x_action.setVisible(True)
            self._RSSI_y_action.setVisible(True)
            self._RSSI_z_action.setVisible(True)

            self._writeRSSIAction.setVisible(False)
            self._deletePointAction.setVisible(True)
            self._setAntAction.setVisible(False)

            Data = self._greenPoints[self._lastPos]

            self._RSSI_type_action.setText(f"Remebered Data")

        elif self._whichPointPlaced() == self.PointType.Ant:
            antNum = self._antPoints[self._lastPos]
            self._RSSI_type_action.setText(f"Ant №{antNum}")
            self._RSSI_x_action.setVisible(False)
            self._RSSI_y_action.setVisible(False)
            self._RSSI_z_action.setVisible(False)

            self._writeRSSIAction.setVisible(False)
            self._deletePointAction.setVisible(True)
            self._setAntAction.setVisible(False)

            return
        else:
            return

        self._RSSI_x_action.setText(f"X: {' '*(3-len(str(int(Data[0][0][0]))))}{int(Data[0][0][0])}")
        self._RSSI_y_action.setText(f"Y: {' '*(3-len(str(int(Data[0][0][1]))))}{int(Data[0][0][1])}")
        self._RSSI_z_action.setText(f"Z: {' '*(3-len(str(int(Data[0][0][2]))))}{int(Data[0][0][2])}")
            
    def _deletePoint(self) -> PointType:
        if self._lastPos in self._greenPoints.keys():
            del self._greenPoints[self._lastPos]
            self._paintCalibrationEvent()
            return self.PointType.Green

        if self._lastPos in self._yellowPoints.keys():
            del self._yellowPoints[self._lastPos]
            self._paintCalibrationEvent()
            return self.PointType.Yellow

        if self._lastPos in self._redPoints.keys():
            del self._redPoints[self._lastPos]
            self._paintCalibrationEvent()
            return self.PointType.Red
        
        if self._lastPos in self._antPoints.keys():
            del self._antPoints[self._lastPos]
            self._paintCalibrationEvent()
            self._paintMeasureEvent()
            return self.PointType.Ant

    def _setPoint(self, type: PointType, antNum = None):
        self._deletePoint()
        if type == self.PointType.Green:
            self._greenPoints[self._lastPos] = self._data.copy()

        elif type == self.PointType.Yellow:  
            self._yellowPoints[self._lastPos] = 0

        elif type == self.PointType.Red:  
            self._redPoints[self._lastPos] = 0

        elif type == self.PointType.Ant:  
            self._antPoints[self._lastPos] = antNum

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

        self._measureLabel.update()
        