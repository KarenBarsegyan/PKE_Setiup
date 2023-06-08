import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtCore import Qt, QPointF


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Draw Points")
        self.setGeometry(100, 100, 800, 600)

        self.label = QLabel(self)
        self.label.setGeometry(100, 100, 600, 400)
        
        self.points = []
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.points.append(event.pos() - self.label.pos())
            self.update_label()
        elif event.button() == Qt.RightButton:
            for point in self.points:
                if self.is_point_selected(point, event.pos() - self.label.pos()):
                    self.points.remove(point)
                    self.update_label()
                    break

    def paintEvent(self, event):
        painter = QPainter(self.label.pixmap())
        
        # Draw the points
        pen = QPen(Qt.black, 8, Qt.SolidLine)
        painter.setPen(pen)
        for point in self.points:
            painter.drawPoint(point)
        
    def update_label(self):
        pixmap = self.label.pixmap()
        if pixmap is None:
            pixmap = self.label.grab()
        else:
            pixmap.fill(Qt.transparent)
        
        self.label.setPixmap(pixmap)
        
    def is_point_selected(self, point, mouse_pos):
        distance = (point - mouse_pos).manhattanLength()
        return distance < 10


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())