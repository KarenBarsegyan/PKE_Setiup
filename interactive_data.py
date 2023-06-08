
from PyQt5.QtWidgets import (
    QVBoxLayout, QApplication, QLabel,
    QHBoxLayout, QWidget, QScrollArea, QMenu,
    QAction
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QPen, QColor
)
from PyQt5.QtCore import Qt, QThread, QPoint
import logging
import os
import numpy as np

class InteractiveData(QThread):
    class Color(int):
        Green = 1
        Yellow = 2 
        Red = 3 

    def __init__(self, parent=None):
        QThread.__init__(self, parent)

        self._mesh_step = 25
        self._greenPoints = []
        self._yellowPoints = []
        self._redPoints = []
        self._lastPos = QPoint()
        self._data = np.zeros(((6, 5, 3)))

        self._init_logger()

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

    def RememberData(self, Data):
        self._data = Data
        self._updateRSSIData()
        # self._label.update()
    
    def SetUp(self):
        localLayout = QVBoxLayout()
        localLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._writeRSSIAction = QAction(self)
        self._writeRSSIAction.setText("Write RSSI")
        self._writeRSSIAction.triggered.connect(self._setGreenPoint)

        self._deletePointAction = QAction(self)
        self._deletePointAction.setText("Delete Point")
        self._deletePointAction.triggered.connect(self._deletePoint)

        separator = QAction(self)
        separator.setSeparator(True)

        self._RSSI_type_action = QAction(self)
        self._RSSI_type_action.setText(f"Actual Data")

        self._RSSI_x_action = QAction(self)
        self._RSSI_x_action.setText(f"X = 122")

        self._RSSI_y_action = QAction(self)
        self._RSSI_y_action.setText(f"Y = 122")

        self._RSSI_z_action = QAction(self)
        self._RSSI_z_action.setText(f"Z = 122")

        self._label = QLabel()
        self._label.mousePressEvent = self._getPos

        self._label.setContextMenuPolicy(Qt.ActionsContextMenu)
        self._label.addAction(self._writeRSSIAction)
        self._label.addAction(self._deletePointAction)
        self._label.addAction(separator)
        self._label.addAction(self._RSSI_type_action)
        self._label.addAction(self._RSSI_x_action)
        self._label.addAction(self._RSSI_y_action)
        self._label.addAction(self._RSSI_z_action)

        localLayout.addWidget(self._label)

        self._paintMainPic()

        v_widget = QWidget()
        v_widget.setLayout(localLayout)  
        # v_widget.setStyleSheet("border: 1px solid black")

        scrollPicture = QScrollArea()
        scrollPicture.setWidget(v_widget)
        scrollPicture.setWidgetResizable(True) 

        return scrollPicture

    def _getPos(self, event):
        pos = QPoint()
        pos.setX(round(event.pos().x() / self._mesh_step) * self._mesh_step)
        pos.setY(round(event.pos().y() / self._mesh_step) * self._mesh_step)
        # print(f"X: {pos.x()}, Y: {pos.y()}")
        self._lastPos = pos

        if event.button() == Qt.LeftButton:
            if self._whichPointPlaced() == self.Color.Red:
                self._deletePoint()
            elif self._whichPointPlaced() == self.Color.Green:
                self._setYellowPoint()
            elif self._whichPointPlaced() == self.Color.Yellow:
                self._setRedPoint()
            else:
                self._setGreenPoint()

        # print(f"Green: {self._greenPoints}")
        # print(f"Yellow: {self._yellowPoints}")
        # print(f"Red: {self._redPoints}\n")
        elif event.button() == Qt.RightButton:
            self._updateRSSIData()
            if self._whichPointPlaced() == None:
                self._writeRSSIAction.setVisible(True)
                self._deletePointAction.setVisible(False)
            else:
                self._writeRSSIAction.setVisible(False)
                self._deletePointAction.setVisible(True)
  
    def _updateRSSIData(self):
        if self._whichPointPlaced() == None:
            Data = self._data
            self._RSSI_type_action.setText(f"Actual Data")
            self._RSSI_x_action.setText(f"X: {' '*(3-len(str(int(Data[1][0][0]))))}{int(Data[1][0][0])}")
            self._RSSI_y_action.setText(f"Y: {' '*(3-len(str(int(Data[1][0][1]))))}{int(Data[1][0][1])}")
            self._RSSI_z_action.setText(f"Z: {' '*(3-len(str(int(Data[1][0][2]))))}{int(Data[1][0][2])}")

    def _deletePoint(self) -> Color:
        for point in self._greenPoints:
            if point == self._lastPos:
                self._greenPoints.remove(point)
                self._paintEvent()
                return self.Color.Green

        for point in self._yellowPoints:
            if point == self._lastPos:
                self._yellowPoints.remove(point)
                self._paintEvent()
                return self.Color.Yellow

        for point in self._redPoints:
            if point == self._lastPos:
                self._redPoints.remove(point)
                self._paintEvent()
                return self.Color.Red

    def _setGreenPoint(self):
        exists = False
        for point in self._greenPoints:
            if point == self._lastPos:
                exists = True
                break

        if not exists:   
            self._deletePoint()

            self._greenPoints.append(self._lastPos)

            Data = self._data
            self._RSSI_type_action.setText(f"Remembered Data")
            self._RSSI_x_action.setText(f"X: {' '*(3-len(str(int(Data[1][0][0]))))}{int(Data[1][0][0])}")
            self._RSSI_y_action.setText(f"Y: {' '*(3-len(str(int(Data[1][0][1]))))}{int(Data[1][0][1])}")
            self._RSSI_z_action.setText(f"Z: {' '*(3-len(str(int(Data[1][0][2]))))}{int(Data[1][0][2])}")

            self._paintEvent()

    def _setYellowPoint(self):
        exists = False
        for point in self._yellowPoints:
            if point == self._lastPos:
                exists = True
                break

        if not exists:   
            self._deletePoint()
            
            self._yellowPoints.append(self._lastPos)
            self._paintEvent()

    def _setRedPoint(self):
        exists = False
        for point in self._redPoints:
            if point == self._lastPos:
                exists = True
                break

        if not exists:   
            self._deletePoint()
            
            self._redPoints.append(self._lastPos)
            self._paintEvent()

    def _whichPointPlaced(self) -> Color:
        for point in self._greenPoints:
            if point == self._lastPos:
                return self.Color.Green
            
        for point in self._yellowPoints:
            if point == self._lastPos:
                return self.Color.Yellow
            
        for point in self._redPoints:
            if point == self._lastPos:
                return self.Color.Red
            
        return None

    def _paintMainPic(self):
        canvas_width = 700
        canvas_height = 1000
        picture_height = 800

        canvas = QPixmap(canvas_width, canvas_height)
        canvas.fill(Qt.white)
        self._label.setPixmap(canvas)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setMargin(0)
        # self._label.setStyleSheet("border: 1px solid black")

        painter = QPainter(self._label.pixmap())

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

    def _paintEvent(self, event = None):
        self._label.clear()

        self._paintMainPic()

        painter = QPainter(self._label.pixmap())
        pen = QPen()
        radius = 4
        pen.setWidth(radius*2)
        pen.setColor(QColor('green'))
        painter.setPen(pen)
        for point in self._greenPoints:
            painter.drawEllipse(point, radius, radius)

        pen = QPen()
        radius = 4
        pen.setWidth(radius*2)
        pen.setColor(QColor('yellow'))
        painter.setPen(pen)
        for point in self._yellowPoints:
            painter.drawEllipse(point, radius, radius)

        pen = QPen()
        radius = 4
        pen.setWidth(radius*2)
        pen.setColor(QColor('red'))
        painter.setPen(pen)
        for point in self._redPoints:
            painter.drawEllipse(point, radius, radius)

        self._label.update()
        
    def contextMenuEvent(self, event):
        menu = QMenu(self._label.pixmap())

        new_action = QAction("New", self)
        open_action = QAction("Open", self)
        exit_action = QAction("Exit", self)

        menu.addAction(new_action)
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        action = menu.exec_(self.mapToGlobal(event.pos()))

        if action == exit_action:
            QApplication.instance().quit()