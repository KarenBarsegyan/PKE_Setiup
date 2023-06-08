import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QMenu, QAction


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Right-click Menu Example")
        self.setGeometry(300, 300, 400, 300)

        self.label = QLabel("Right-click me", self)
        self.label.setGeometry(50, 50, 200, 100)

    def contextMenuEvent(self, event):
        if self.sender() == self.label:
            menu = QMenu(self)

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
