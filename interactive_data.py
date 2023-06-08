
from PyQt5.QtWidgets import (
    QVBoxLayout, QApplication, QLabel,
    QHBoxLayout, QWidget, QScrollArea
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QPen, QColor
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
import logging
import os

class InteractiveData(QThread):
    def __init__(self, parent=None):
        QThread.__init__(self, parent)

        self._mesh_step = 25

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

    def _SetPictures(self):
        canvas_width = 700
        canvas_height = 1000
        picture_height = 800

        localLayout = QVBoxLayout()
        localLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel()
        localLayout.addWidget(self._label)

        canvas = QPixmap(canvas_width, canvas_height)
        canvas.fill(Qt.white)
        self._label.setPixmap(canvas)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setMargin(0)
        self._label.mousePressEvent = self.getPos
        # self._label.setFixedHeight(canvas_height)
        # self._label.setFixedWidth(canvas_width)
        self._label.setStyleSheet("border: 1px solid black")

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

        v_widget = QWidget()
        v_widget.setLayout(localLayout)  
        # v_widget.setStyleSheet("border: 1px solid black")

        scrollPicture = QScrollArea()
        scrollPicture.setWidget(v_widget)
        scrollPicture.setWidgetResizable(True) 

        return scrollPicture

    def getPos(self, event):
        if(event.button() == Qt.LeftButton):
            self._drawPoint(event.pos())
        elif(event.button() == Qt.RightButton):
            self._deletePoint(event.pos())

    def _drawPoint(self, pos):
        painter = QPainter(self._label.pixmap())
        pen = QPen()
        radius = 4
        pen.setWidth(radius*2)
        pen.setColor(QColor('green'))
        painter.setPen(pen)

        pos.setX(round(pos.x() / self._mesh_step) * self._mesh_step)
        pos.setY(round(pos.y() / self._mesh_step) * self._mesh_step)

        painter.drawEllipse(pos, radius, radius)
        
        painter.end()
        self._label.update()

    def _deletePoint(self, pos):
        painter = QPainter(self._label.pixmap())
        pen = QPen()
        radius = 4
        pen.setWidth(radius*2)
        pen.setColor(QColor('transperent'))
        painter.setPen(pen)

        pos.setX(round(pos.x() / self._mesh_step) * self._mesh_step)
        pos.setY(round(pos.y() / self._mesh_step) * self._mesh_step)

        painter.drawEllipse(pos, radius, radius)
        painter.end()
        self._label.update()
