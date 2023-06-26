from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from animated import AnimatedToggle

app = QApplication([])

window = QWidget()

mainToggle = AnimatedToggle()
mainToggle.setFixedSize(mainToggle.sizeHint())

window.setLayout(QVBoxLayout())
window.layout().addWidget(QLabel("Main Toggle"))
window.layout().addWidget(mainToggle)

window.show()
app.exec_()