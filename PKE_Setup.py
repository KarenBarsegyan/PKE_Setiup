from PyQt5.QtWidgets import (
    QMainWindow, QCheckBox, QVBoxLayout, 
    QApplication, QLabel, QHBoxLayout, 
    QWidget, QPushButton, QLineEdit, 
    QGroupBox, QSpacerItem, QSlider,
    QFrame, QTabWidget, QScrollArea,
    QComboBox, QMenu, QAction, QFileDialog,
    QMessageBox
)
from PyQt5.QtGui import (
    QFont, QIntValidator
)
from PyQt5.QtCore import (
    Qt, QSize, QThread,
    QPropertyAnimation,  QSequentialAnimationGroup, 
    pyqtSlot, pyqtProperty, QTimer, QSettings
)
import numpy as np
import time
import xlsxwriter
import logging
from CAN_bus import CanSendRecv
from points_painter import PointsPainter
import os
import json
from keys_data import KeysData


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self._power_mode = 0
        self._ant_amount = 6
        self._key_amount = 5
        self._store_save_file_path = "store_data/last_opened"
        self._store_data_path_value = ""
        self._logs_path = "app_logs"
        self._pollings_done = 0
        self._auth_status = False
        self._is_polling_in_progress = False
        self._pollings_needed = 1
        self._repeat_polling = False
        self._background_colors = [145, 147, 191]
        self._running_animations = dict()
        self._ants_keys_data = KeysData(self._ant_amount, self._key_amount)

        self._initLogger()
        self._initWorksheet()
        self._setApp()
        self._busInit()
        self._openPreviousFile()

        self.show()
        
    def _openPreviousFile(self):
        try:
            with open(f'{self._store_save_file_path}', 'r') as f:
                to_json = json.load(f)

            self._store_data_path_value = to_json
        except:
            self._logger.info("no such file yet")

        filename = self._store_data_path_value
        if filename != "":
            self._store_data_path = filename

            filename = filename[filename.rfind('/')+1:]
            self.setWindowTitle(f"PKE Setup - {filename[:-len('.pkesetup')]}")
            self._restoreData()
        else:
            self._resetData()

    def closeEvent(self, *args, **kwargs):
        # Say hardware to stop polling
        self._stopPolling()

        # Save window size and pos
        self.settings.setValue( "window_screen_geometry", self.saveGeometry() )

        # Close Exel Log table
        try:
            self._workbook.close()
            self._logger.info("WorkBook Closed")
        except:
            self._logger.info("Error closing WorkBook")

        # Stop CAN bus thread
        try:
            if (self._bus_thread.isRunning()):
                self._bus_thread.quit()
                self._bus_thread.wait()

            self._logger.info("CAN thread terminated")
        except:
            self._logger.info("Error terminating CAN thread")

        # Check if file wasn't created at all or if it hs changed
        self._showSaveWindow()
        self._showSaveNewFileWindow()

        # Save last opened file full path
        to_json = self._store_data_path_value
        with open(f'{self._store_save_file_path}', 'w') as f:
            json.dump(to_json, f)

        # Send close events to other Qt objects
        self._points_painter.closeEvent()

        super(QMainWindow, self).closeEvent(*args, **kwargs)

    def _initLogger(self):
        try:
            os.mkdir(f"{self._logs_path}/")
        except: pass

        self._logger = logging.getLogger(__name__)
        f_handler = logging.FileHandler(f'{self._logs_path}/{__name__}.log')
        f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        f_handler.setFormatter(f_format)
        self._logger.addHandler(f_handler)
        self._logger.setLevel(logging.WARNING)

    def _initWorksheet(self):
        self._row = 0
        self._column = 0
        self._row_single = 0
        self._column_single = 0
    
        time_hms = time.strftime("%Hh_%Mmin", time.localtime())
        time_ymd = time.strftime("%Y-%m-%d", time.localtime())

        try:
            os.mkdir(f"logs/")
        except: pass

        try:
            self._workbook = xlsxwriter.Workbook(f'logs/logs_by_{time_ymd}_{time_hms}.xlsx')
            self._worksheet = self._workbook.add_worksheet(name="All_Data")
            self._worksheet_single = self._workbook.add_worksheet(name="Single Data")
        except:
            self._logger.warning("Error opening XLS")

    def _setApp(self):
        self.setWindowTitle("PKE Setup")

        # Restore window size and pos
        self.settings = QSettings('ITELMA', 'PKE Setup')
        window_screen_geometry = self.settings.value( "window_screen_geometry" )
        if window_screen_geometry:
            self.restoreGeometry(window_screen_geometry)
        else:
            self.resize(QSize(1400, 800))

        # Main layout of GUI
        self._layout_main = QHBoxLayout()

        # Layout for ants keys data
        self._layout_data = QHBoxLayout()
        self._layout_data.setSpacing(0)

        # Layout for widgets on right side of GUI
        self._layout_widgets = QVBoxLayout()
        self._layout_widgets.setSpacing(50)

        # Make widget layout fixed size and scrollable
        v_widget = QWidget()
        v_widget.setLayout(self._layout_widgets)    
        scroll_widget = QScrollArea()
        scroll_widget.setWidget(v_widget)
        scroll_widget.setWidgetResizable(True) 
        scroll_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)     
        scroll_widget.setFixedWidth(400)   

        # Add some spasers to make layout for ants keys data and
        # layout for widgets same height
        layout_widgets_spacer = QVBoxLayout()
        layout_widgets_spacer.addItem(QSpacerItem(0, 25))
        layout_widgets_spacer.addWidget(scroll_widget)
        layout_widgets_spacer.addItem(QSpacerItem(0, 4))
        
        self._layout_main.addLayout(self._layout_data)
        self._layout_main.addLayout(layout_widgets_spacer)

        self._createmenu_bar()
        self._setDataTabs()

        # Order here == order in layout for widgets
        self._setCAN()
        self._setStatuses()
        self._setStartPolling()
        self._setLogs()
        self._setAntCheckBox()
        self._setKeyCheckBox()
        self._setKeyForMeasure()
        self._setAntCurrents()
        self._setStartDiag()
        self._setPowerMode()

        # Init all widgets which doesn't have default text
        self._processData(False)
        
        # Show GUI
        widget = QWidget()
        widget.setLayout(self._layout_main)
        self.setCentralWidget(widget)

    def _createmenu_bar(self):
        # File
        new_action = QAction("&New", self)
        new_action.triggered.connect(self._newFile)

        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._openFile)

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._saveFile)

        save_as_action = QAction("&Save As...", self)
        save_as_action.triggered.connect(self._saveFileAs)

        close_action = QAction("&Close", self)
        close_action.triggered.connect(self._closeFile)

        exit_action = QAction("&Exit", self)
        about_action = QAction("&About", self)       

        # Logging
        new_log_action = QAction("&New", self)
        # new_log_action.triggered.connect(self._newFile)

        open_log_action = QAction("&Open...", self)
        # open_log_action.triggered.connect(self._openFile)

        save_log_action = QAction("&Save", self)
        # save_log_action.triggered.connect(self._saveFile)

        save_as_log_action = QAction("&Save As...", self)

        menu_bar = self.menuBar()
        # File menu
        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addAction(close_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        # Logs Menu 
        logging_menu = QMenu("&Logging", self)
        menu_bar.addMenu(logging_menu)
        logging_menu.addAction(new_log_action)
        logging_menu.addAction(open_log_action)
        logging_menu.addAction(save_log_action)
        logging_menu.addAction(save_as_log_action)
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(about_action)

    def _showSaveWindow(self):
        # You have to save file only if file path
        # is choosen. Othrwise use saveNewFileWindow
        filename = self._store_data_path
        if filename != '':
            try:
                # Check if data was changed or not
                with open(f'{self._store_data_path}', 'r') as f:
                    to_json = json.load(f)

                if (to_json['key_ants'] != self._generateJson() or
                    to_json['points'] != self._points_painter.generateJson()):

                    # if data was changed, ask to save it
                    filename = filename[filename.rfind('/')+1:]
                    filename = filename[:-len('.pkesetup')]
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Information)
                    msg_box.setText(f"Do you want to save changes in \"{filename}\"?")
                    msg_box.setWindowTitle("Message")
                    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

                    return_value = msg_box.exec()
                    if return_value == QMessageBox.Yes:
                        self._saveFile()

            except:
                self._logger.info("no such file yet")
        
    def _showSaveNewFileWindow(self):
        filename = self._store_data_path
        if filename == '':
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText(f"Do you want to create new file ?")
            msg_box.setWindowTitle("Message")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            return_value = msg_box.exec()
            if return_value == QMessageBox.Yes:
                self._newFile()

    def _newFile(self):
        # If user tries to create file with 
        # another file opened and changed, ask to save it
        self._showSaveWindow()

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(self,"Create New File","","Pke Setup (*.pkesetup);;All Files (*)", options=options)
        if filename != '':
            if filename.find('.pkesetup') != len(filename) - len('.pkesetup'):
                filename += '.pkesetup'
            
            self._store_data_path = filename
            
            # We created new file, so lets start from clear data 
            self._resetData()
            self._processData(False)

            self._saveFile()

            filename = filename[filename.rfind('/')+1:]
            self.setWindowTitle(f"PKE Setup - {filename[:-len('.pkesetup')]}")
    
    def _openFile(self):
        self._showSaveWindow()
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(self,"Open File", "","Pke Setup (*.pkesetup);;All Files (*)", options=options)

        if filename != "":
            self._store_data_path = filename
            self._restoreData()

            self._processData(False)

            filename = filename[filename.rfind('/')+1:]
            self.setWindowTitle(f"PKE Setup - {filename[:-len('.pkesetup')]}")

    def _resetData(self):
        for nCnt in range(0, len(self._widget_ant_checkboxes)):
            self._widget_ant_checkboxes[nCnt].setChecked(True)
        
        self._updateAntMask()

        for nCnt in range(0, len(self._widget_key_checkboxes)):
            self._widget_key_checkboxes[nCnt].setChecked(True)
        
        self._updateKeyMask()

        self._widget_auth_checkbox.setChecked(True)
        self._bus_worker.auth_mode = 1

        self._widget_curr_slider.setValue(32)
        self._widget_ant_curr_value_label.setText('Current: %.2f mA' % (15.625*(32)))
        self._bus_worker.poll_current = 32

        self._widget_pwr_mode_label.setText('Normal Mode')
        self._bus_worker.power_mode = 0

        self._widget_polling_amount_lineedit.setText('3')

        for i in range(6):
            self._widget_ant_imps_labels[i].setText(f'Ant {i+1}: {0} Ω')

        self._points_painter.clearData()

    def _restoreData(self):
        try:
            with open(f'{self._store_data_path}') as f:
                all_ants_data = json.load(f)

            keys_ants_data = all_ants_data['key_ants']
            for nCnt in range(0, len(self._widget_ant_checkboxes)):
                if nCnt not in keys_ants_data['ants']:
                    self._widget_ant_checkboxes[nCnt].setChecked(False)
                else:
                    self._widget_ant_checkboxes[nCnt].setChecked(True)

            self._updateAntMask()

            for nCnt in range(0, len(self._widget_key_checkboxes)):
                if nCnt not in keys_ants_data['keys']:
                    self._widget_key_checkboxes[nCnt].setChecked(False)
                else:
                    self._widget_key_checkboxes[nCnt].setChecked(True)

            self._updateKeyMask()

            if keys_ants_data['auth'] == 0:
                self._widget_auth_checkbox.setChecked(False)
                self._bus_worker.auth_mode = 0
            else:
                self._widget_auth_checkbox.setChecked(True)
                self._bus_worker.auth_mode = 1

            self._widget_polling_amount_lineedit.setText(str(keys_ants_data['pollings_amount']))

            val = keys_ants_data['current']
            self._widget_curr_slider.setValue(val)
            self._widget_ant_curr_value_label.setText('Current: %.2f mA' % (15.625*(val)))
            self._bus_worker.poll_current = val

            self._widgetKeyForMeasure.setCurrentIndex(keys_ants_data['key_for_calibration'])

        except:
            self.setWindowTitle(f"PKE Setup - File Was deleted or moved")
            self._store_data_path_value = ""
            self._logger.info("No such file in restore")

    def _saveFile(self):
        if self._store_data_path == "":
            self._saveFileAs()
            return

        to_json = {}
        try:
            with open(f'{self._store_data_path}', 'r') as f:
                to_json = json.load(f)
        except:
            self._logger.info("no such file yet")

        to_json['key_ants'] = self._generateJson()

        with open(f'{self._store_data_path}', 'w') as f:
            json.dump(to_json, f)

        self._points_painter.saveData(self._store_data_path)

    def _generateJson(self):
        to_json = {
            'ants': [],
            'keys': [],
            'auth': 0
        }
        for nCnt in range(0, len(self._widget_ant_checkboxes)):
            if self._widget_ant_checkboxes[nCnt].isChecked():
                to_json['ants'].append(nCnt)

        for nCnt in range(0, len(self._widget_key_checkboxes)):
            if self._widget_key_checkboxes[nCnt].isChecked():
                to_json['keys'].append(nCnt)

        if self._widget_auth_checkbox.isChecked(): 
            to_json['auth'] = 1

        to_json['pollings_amount'] = int(self._widget_polling_amount_lineedit.text())

        to_json['current'] = self._widget_curr_slider.value()

        to_json['key_for_calibration'] = self._widgetKeyForMeasure.currentIndex()

        return to_json

    def _saveFileAs(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(self,"Save As...","","Pke Setup (*.pkesetup);;All Files (*)", options=options)
        if filename != '':
            if filename.find('.pkesetup') != len(filename) - len('.pkesetup'):
                filename += '.pkesetup'
            
            self._store_data_path = filename
            self._saveFile()

            filename = filename[filename.rfind('/')+1:]
            self.setWindowTitle(f"PKE Setup - {filename[:-len('.pkesetup')]}")

    def _closeFile(self):
        # If user tries to close file which was changed, ask to save it
        self._showSaveWindow() 

        self._store_data_path = ''
        self._resetData()
        self.setWindowTitle(f"PKE Setup")

    @property
    def _store_data_path(self):
        return self._store_data_path_value

    @_store_data_path.setter
    def _store_data_path(self, path):
        # Add here setpath functions of all objects
        # which need it
        self._store_data_path_value = path
        self._points_painter.restoreData(path)

    def _setDataTabs(self):
        self._tabs = QTabWidget()
        self._tabs.addTab(self._SetAntsData(), "RSSIs")

        self._points_painter = PointsPainter(askForPollingFunc = self._askStartStopPollingCallback)
        self._tabs.addTab(self._points_painter.SetUpCalibrationDesk(), "Calibration")
        self._tabs.addTab(self._points_painter.SetUpMeasureDesk(), "Measurement")
        
        self._layout_data.addWidget(self._tabs)

    def _SetAntsData(self):
        # We have one big horisontal layout (big_h_layout)
        # with couple of columns storing in
        # small_v_layouts array
        self._ant_frames = []
        self._key_frames = []
        small_v_layout = []
        big_h_layout = QHBoxLayout()
        big_h_layout.setSpacing(0)
        for nAnt in range(self._ant_amount+1):
            small_v_layout.append(QVBoxLayout())
            self._ant_frames.append(QFrame())
            self._ant_frames[nAnt].setLayout(small_v_layout[nAnt])
            # self._ant_frames[nAnt].setStyleSheet("border: 1px solid black")
            small_v_layout[nAnt].setContentsMargins(0,0,0,0)

            big_h_layout.addWidget(self._ant_frames[nAnt])
            if nAnt == 0:
                big_h_layout.setStretch(nAnt, 0)
            else:
                big_h_layout.setStretch(nAnt, 1)


        self._RSSI_widgets = []
        
        w = QLabel(f"")
        font = w.font()
        font.setPointSize(15)
        w.setFont(font)
        small_v_layout[0].addWidget(w)
        small_v_layout[0].setStretch(0, 0)
        small_v_layout[0].setSpacing(0)
        small_v_layout[0].setContentsMargins(0,0,0,0)

        key_frame_local = []
        for nKey in range(self._key_amount):
            key_frame_local.append(QFrame())

            w = QLabel(f"Key {nKey+1}")
            font = w.font()
            font.setPointSize(12)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            l = QVBoxLayout()
            l.addWidget(w)
            l.setSpacing(0)
            key_frame_local[nKey].setLayout(l)
            small_v_layout[0].addWidget(key_frame_local[nKey])
            small_v_layout[0].setStretch(nKey+1, 1)

        self._key_frames.append(key_frame_local)

        for nAnt in range(1, self._ant_amount+1):
            w = QLabel(f"ANT {nAnt}")
            font = w.font()
            font.setPointSize(12)
            w.setFont(font)
            w.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            small_v_layout[nAnt].addWidget(w)
            small_v_layout[nAnt].setSpacing(0)

            templist = []
            key_frame_local = []
            for nKey in range(self._key_amount):
                key_frame_local.append(QFrame())

                k = QLabel()
                k.setFont(QFont('Courier', 14))
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
                key_frame_local[nKey].setLayout(l)

                small_v_layout[nAnt].addWidget(key_frame_local[nKey])
                small_v_layout[nAnt].setStretch(nKey+1, 1)
                
                templist.append(k)

            self._key_frames.append(key_frame_local)

            self._RSSI_widgets.append(templist)

        w = QWidget()
        w.setLayout(big_h_layout)

        scroll = QScrollArea()
        scroll.setWidget(w)
        scroll.setWidgetResizable(True) 

        return scroll

    def _setCAN(self):
        groupbox = QGroupBox("CAN")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        box = QVBoxLayout()
        box.setSpacing(10)
        groupbox.setLayout(box)

        self._widget_usb_state_label = QLabel("Systec Disconnected")
        font = self._widget_usb_state_label.font()
        font.setPointSize(12)
        self._widget_usb_state_label.setFont(font)
        self._widget_usb_state_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        box.addWidget(self._widget_usb_state_label)

        self._widget_usb_connect_button = QPushButton("Connect")
        font = self._widget_usb_connect_button.font()
        font.setPointSize(12)
        self._widget_usb_connect_button.setFont(font)
        self._widget_usb_connect_button.clicked.connect(self._busInitHandler)
        self._widget_usb_connect_button.setFlat(False)
        box.addWidget(self._widget_usb_connect_button)

        widget_usb_dis_connect_button = QPushButton("Disconnect")
        font = widget_usb_dis_connect_button.font()
        font.setPointSize(12)
        widget_usb_dis_connect_button.setFont(font)
        widget_usb_dis_connect_button.clicked.connect(self._busDeInitHandler)
        box.addWidget(widget_usb_dis_connect_button)

        self._widget_msg_period_label = QLabel()
        font = self._widget_msg_period_label.font()
        font.setPointSize(12)
        self._widget_msg_period_label.setFont(font)
        self._widget_msg_period_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        box.addWidget(self._widget_msg_period_label)
     
        self._layout_widgets.addWidget(groupbox)

    def _setStatuses(self):
        groupbox = QGroupBox("Statuses")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        box = QVBoxLayout()
        box.setSpacing(15)
        groupbox.setLayout(box)
    
        h_layout = QHBoxLayout()
        self._widget_last_key_label = QLabel()
        font = self._widget_last_key_label.font()
        font.setPointSize(12)
        self._widget_last_key_label.setFont(font)
        self._widget_last_key_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._widget_last_key_label.setMaximumWidth(280)
        h_layout.addWidget(self._widget_last_key_label)
        box.addLayout(h_layout)

        self._last_key_background = 0
        self._last_key_animation = QSequentialAnimationGroup()
        self._setBackgroundAnimation(self._last_key_animation, b"last_key_background")


        h_layout = QHBoxLayout()
        self._widget_auth_state_label = QLabel() 
        font = self._widget_auth_state_label.font()
        font.setPointSize(12)
        self._widget_auth_state_label.setFont(font)
        self._widget_auth_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._widget_auth_state_label.setMaximumWidth(150)
        h_layout.addWidget(self._widget_auth_state_label)
        box.addLayout(h_layout)
        
        self._auth_background = 0
        self._auth_state_animation = QSequentialAnimationGroup()
        self._setBackgroundAnimation(self._auth_state_animation, b"auth_background")

        h_layout = QHBoxLayout()
        self._widget_auth_checkbox = QCheckBox()
        font = self._widget_auth_checkbox.font()
        font.setPointSize(11)
        self._widget_auth_checkbox.setFont(font)
        self._widget_auth_checkbox.setChecked(True)
        self._widget_auth_checkbox.setText("Perform auth")
        self._widget_auth_checkbox.stateChanged.connect(self._performAuthStateHandler)
        h_layout.addWidget(self._widget_auth_checkbox)

        h_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addLayout(h_layout)

        self._layout_widgets.addWidget(groupbox)

    def _setStartPolling(self):
        groupbox = QGroupBox("Polling State")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        box = QVBoxLayout()
        box.setSpacing(15)
        groupbox.setLayout(box)
    
        widget_pollings_amount_label = QLabel("Pollings Amount: ")
        font = widget_pollings_amount_label.font()
        font.setPointSize(12)
        widget_pollings_amount_label.setFont(font)
        widget_pollings_amount_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        box.addWidget(widget_pollings_amount_label)

        validator = QIntValidator(1, 250)
        self._widget_polling_amount_lineedit = QLineEdit()
        self._widget_polling_amount_lineedit.setValidator(validator)
        font = self._widget_polling_amount_lineedit.font()
        font.setPointSize(12)
        self._widget_polling_amount_lineedit.setFont(font)
        self._widget_polling_amount_lineedit.setMaximumHeight(200)
        self._widget_polling_amount_lineedit.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        box.addWidget(self._widget_polling_amount_lineedit)

        h_layout = QHBoxLayout()
        self._widget_pollings_done_label = QLabel()
        font = self._widget_pollings_done_label.font()
        font.setPointSize(12)
        self._widget_pollings_done_label.setFont(font)
        self._widget_pollings_done_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._widget_pollings_done_label.setMaximumWidth(250)
        h_layout.addWidget(self._widget_pollings_done_label)
        box.addLayout(h_layout)

        self._pollings_done_background = 0
        self._pollings_done_animation = QSequentialAnimationGroup()
        self._setBackgroundAnimation(self._pollings_done_animation, b"pollings_done_background")

        self._widget_start_polling_button = QPushButton("Start Polling")
        font = self._widget_start_polling_button.font()
        font.setPointSize(12)
        self._widget_start_polling_button.setFont(font)
        box.addWidget(self._widget_start_polling_button)
        self._widget_start_polling_button.clicked.connect(self._startPollingHandler)

        self._widget_start_repeat_polling_button = QPushButton("Start Repeat Polling")
        font = self._widget_start_repeat_polling_button.font()
        font.setPointSize(12)
        self._widget_start_repeat_polling_button.setFont(font)
        box.addWidget(self._widget_start_repeat_polling_button)
        self._widget_start_repeat_polling_button.clicked.connect(self._startRepeatPollingHandler)

        self._layout_widgets.addWidget(groupbox)

    def _setStartDiag(self):
        groupbox = QGroupBox("Ant impedances")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        box = QVBoxLayout()
        box.setSpacing(15)
        groupbox.setLayout(box)

        self._widget_ant_imps_labels = []

        inRow = 3
        for nAnt in range(0, int(self._ant_amount/inRow+1)):
            h = QHBoxLayout()
            added = False
            for nCnt in range(inRow):
                idx = nAnt*inRow + nCnt
                if(idx < self._ant_amount):
                    self._widget_ant_imps_labels.append(QLabel())
                    font = self._widget_ant_imps_labels[idx].font()
                    font.setPointSize(11)
                    self._widget_ant_imps_labels[idx].setFont(font)
                    h.addWidget(self._widget_ant_imps_labels[idx])
                    # h.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    added = True
            if added:
                box.addLayout(h)
                added = False

        self._ant_imps_background = 0
        self._antImpsAnimation = QSequentialAnimationGroup()
        self._setBackgroundAnimation(self._antImpsAnimation, b"ant_imps_background")

        self._widget_diag_statuses_combobox = QComboBox()
        box.addWidget(self._widget_diag_statuses_combobox)

        self._widget_ant_diag_button = QPushButton("Get ants impedance and calibrate")
        font = self._widget_ant_diag_button.font()
        font.setPointSize(12)
        self._widget_ant_diag_button.setFont(font)
        box.addWidget(self._widget_ant_diag_button)
        self._widget_ant_diag_button.clicked.connect(self._antDiagHandler)

        self._layout_widgets.addWidget(groupbox)

    def _setPowerMode(self):
        groupbox = QGroupBox("Power Mode")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        box = QVBoxLayout()
        box.setSpacing(15)
        groupbox.setLayout(box)

        # Show Power Mode
        self._widget_pwr_mode_label = QLabel()
        font =  self._widget_pwr_mode_label.font()
        font.setPointSize(12)
        self._widget_pwr_mode_label.setFont(font)
        self._widget_pwr_mode_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        box.addWidget(self._widget_pwr_mode_label)

        # Set Change Power Mode button Label
        widget_change_mode_button = QPushButton("Change Power Mode")
        font = widget_change_mode_button.font()
        font.setPointSize(12)
        widget_change_mode_button.setFont(font)
        box.addWidget(widget_change_mode_button)
        widget_change_mode_button.clicked.connect(self._changeModeHandler)

        self._layout_widgets.addWidget(groupbox)

    def _setLogs(self):
        groupbox = QGroupBox("Logs")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        box = QVBoxLayout()
        box.setSpacing(10)
        groupbox.setLayout(box)
    
        # Get log msg
        self._widget_log_msg_lineedit = QLineEdit()
        font = self._widget_log_msg_lineedit.font()
        font.setPointSize(12)
        self._widget_log_msg_lineedit.setFont(font)
        self._widget_log_msg_lineedit.setMaximumHeight(200)
        box.addWidget(self._widget_log_msg_lineedit)

        # Set button to send log
        widget_add_log_button = QPushButton("Add LOG")
        font = widget_add_log_button.font()
        font.setPointSize(12)
        widget_add_log_button.setFont(font)
        box.addWidget(widget_add_log_button)
        widget_add_log_button.clicked.connect(self._addLogHandler)

        self._layout_widgets.addWidget(groupbox)

    def _setAntCurrents(self):
        groupbox = QGroupBox("Ants currents")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        box = QVBoxLayout()
        box.setSpacing(10)
        groupbox.setLayout(box)
    
        self._widget_curr_slider = QSlider(Qt.Horizontal)
        self._widget_curr_slider.setRange(1, 0x40)
        self._widget_curr_slider.setValue(0x20)
        self._widget_curr_slider.setSingleStep(1)
        self._widget_curr_slider.setPageStep(2)
        self._widget_curr_slider.setTickInterval(0x1F)
        self._widget_curr_slider.setTickPosition(QSlider.TicksBelow)
        self._widget_curr_slider.valueChanged.connect(self._currentChangedHandler)
        box.addWidget(self._widget_curr_slider)

        self._widget_ant_curr_value_label = QLabel()
        font = self._widget_ant_curr_value_label.font()
        font.setPointSize(12)
        self._widget_ant_curr_value_label.setFont(font)
        self._widget_ant_curr_value_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        box.addWidget(self._widget_ant_curr_value_label)     

        self._layout_widgets.addWidget(groupbox)

    def _setAntCheckBox(self):
        groupbox = QGroupBox("Ants for polling")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        box = QVBoxLayout()
        box.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.setSpacing(15)
        groupbox.setLayout(box)
    
        self._widget_ant_checkboxes = []

        inRow = 3
        for nAnt in range(0, int(self._ant_amount/inRow+1)):
            h = QHBoxLayout()
            added = False
            for nCnt in range(inRow):
                idx = nAnt*inRow + nCnt
                if(idx < self._ant_amount):
                    self._widget_ant_checkboxes.append(QCheckBox())
                    font = self._widget_ant_checkboxes[idx].font()
                    font.setPointSize(11)
                    self._widget_ant_checkboxes[idx].setFont(font)
                    self._widget_ant_checkboxes[idx].setChecked(True)
                    self._widget_ant_checkboxes[idx].stateChanged.connect(self._updateAntMaskHandler)
                    self._widget_ant_checkboxes[idx].setText(f"Ant {idx+1}")
                    h.addWidget(self._widget_ant_checkboxes[idx])
                    h.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    added = True

            if added:
                box.addLayout(h)
                added = False

        self._layout_widgets.addWidget(groupbox)

    def _setKeyCheckBox(self):
        groupbox = QGroupBox("Keys for polling")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        box = QVBoxLayout()
        box.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.setSpacing(15)
        groupbox.setLayout(box)
    
        self._widget_key_checkboxes = []

        inRow = 3
        for nKey in range(0, int(self._key_amount/inRow+1)):
            h = QHBoxLayout()
            added = False
            for nCnt in range(inRow):
                idx = nKey*inRow + nCnt
                if(idx < self._key_amount):
                    self._widget_key_checkboxes.append(QCheckBox())
                    font = self._widget_key_checkboxes[idx].font()
                    font.setPointSize(11)
                    self._widget_key_checkboxes[idx].setFont(font)
                    self._widget_key_checkboxes[idx].setChecked(True)
                    self._widget_key_checkboxes[idx].stateChanged.connect(self._updateKeyMaskHandler)
                    self._widget_key_checkboxes[idx].setText(f"Key {idx+1}")
                    h.addWidget(self._widget_key_checkboxes[idx])
                    h.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    added = True
                
            if added:
                box.addLayout(h)
                added = False

        self._layout_widgets.addWidget(groupbox)

    def _setKeyForMeasure(self):
        groupbox = QGroupBox("Key for calibration")
        font = groupbox.font()
        font.setPointSize(10)
        groupbox.setFont(font)
        box = QVBoxLayout()
        box.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        box.setSpacing(15)
        groupbox.setLayout(box)

        self._widgetKeyForMeasure = QComboBox()
        for nKey in range(0, self._key_amount):
            self._widgetKeyForMeasure.addItem(f"Key {nKey+1}")

        box.addWidget(self._widgetKeyForMeasure)

        self._layout_widgets.addWidget(groupbox)

    def _busInit(self):
        # Create a QThread and Worker object
        self._bus_thread = QThread()
        self._bus_worker = CanSendRecv(self._ant_amount, self._key_amount)
        self._bus_worker.moveToThread(self._bus_thread)

        # Connect signals and slots
        self._bus_thread.started.connect(self._bus_worker.start)
        self._bus_worker.canInited.connect(self._busInitedCallback)
        self._bus_worker.canDeInited.connect(self._busDeInitedCallback)
        self._bus_worker.keyNumIdReceived.connect(self._lastKeyUpdateCallback)
        self._bus_worker.keyAuthReceived.connect(self._lastAuthUpdateCallback)
        self._bus_worker.canReceivedAll.connect(self._allDataReceivedCallback)
        self._bus_worker.antImpsReceived.connect(self._antImpsUpdateCallback)
        self._bus_worker.antDiagStateReceived.connect(self._antDiagUpdateCallback)
        
        self._bus_thread.start()

    def _busInitHandler(self):
        self._widget_usb_connect_button.setFlat(True)
        self._bus_worker.BusInit()
        self._widget_usb_connect_button.setFlat(False)

    def _busDeInitHandler(self):
        self._stopPolling()
        self._bus_worker.BusDeInit()

    def _busInitedCallback(self):
        self._widget_usb_state_label.setText("Systec Connected")
        self._widget_usb_state_label.setStyleSheet("color: green;")

    def _busDeInitedCallback(self):
        self._widget_usb_state_label.setText("Systec Disconnected")
        self._widget_usb_state_label.setStyleSheet("color: black;")
        self._processData(False)
        
    def _updateAntMaskHandler(self):
        self._updateAntMask()
        self._bus_worker.sendData()

    def _updateAntMask(self):
        ant_mask = 0
        for nCnt in range(0, len(self._widget_ant_checkboxes)):
            if self._widget_ant_checkboxes[nCnt].isChecked():
                ant_mask |= 1 << nCnt
                self._ant_frames[nCnt+1].show()
            else:
                self._ant_frames[nCnt+1].hide()

        self._bus_worker.ant_mask = ant_mask

    def _updateKeyMaskHandler(self):
        self._updateKeyMask()
        self._bus_worker.sendData()

    def _updateKeyMask(self):
        key_mask = 0
        for nAnt in range(0, len(self._widget_ant_checkboxes)+1):
            for nKey in range(0, len(self._widget_key_checkboxes)):
                if self._widget_key_checkboxes[nKey].isChecked():
                    key_mask |= 1 << nKey
                    self._key_frames[nAnt][nKey].show()
                else:
                    self._key_frames[nAnt][nKey].hide()
        
        self._bus_worker.key_mask = key_mask

    def _lastKeyUpdateCallback(self, lastPressedKey):
        self._widget_last_key_label.setText(f"Last Key Pressed Num: {lastPressedKey}\t\t")
        self._animationStart(self._last_key_animation)

    def _lastAuthUpdateCallback(self, auth_status):
        if self._widget_auth_checkbox.isChecked() and self._is_polling_in_progress:
            if auth_status:
                self._auth_status = True
                self._widget_auth_state_label.setText(f'Auth: OK')
            else:
                self._auth_status = False
                self._widget_auth_state_label.setText(f'Auth: Fail')

            self._animationStart(self._auth_state_animation)

    def _antImpsUpdateCallback(self, imps: list):
        for i in range(len(imps)):
            self._widget_ant_imps_labels[i].setText(f'Ant {i+1}: {imps[i]} Ω')
            
        self._animationStart(self._antImpsAnimation)

    def _antDiagUpdateCallback(self, statuses: list):
        self._widget_diag_statuses_combobox.clear()
        self._widget_diag_statuses_combobox.addItems(statuses)                            

    def _currentChangedHandler(self):
        val = self._widget_curr_slider.value()
        self._widget_ant_curr_value_label.setText('Current: %.2f mA' % (15.625*(val)))
        self._bus_worker.poll_current = val
        self._bus_worker.sendData()

    def _changeModeHandler(self):
        if self._power_mode == 0:
            self._power_mode = 1 #PowerDown
            self._widget_pwr_mode_label.setText("Power Down")
        else:
            self._power_mode = 0 #Normal Mode
            self._widget_pwr_mode_label.setText("Normal Mode")
        
        self._bus_worker.power_mode = self._power_mode

    def _startPollingHandler(self):
        if(self._widget_start_polling_button.text() == "Start Polling"):
            self._updateKeyMask()
            self._startPolling()
        else:
            self._pollings_done = 0
            self._stopPolling()

    def _startRepeatPollingHandler(self):
        if(self._widget_start_repeat_polling_button.text() == "Start Repeat Polling"):
            self._updateKeyMask()
            self._startRepeatPolling()
        else:
            self._pollings_done = 0
            self._stopPolling()

    def _startRepeatPolling(self):
        self._is_polling_in_progress = True
        self._widget_start_polling_button.setText("Start Polling")
        self._widget_start_repeat_polling_button.setText("Stop Repeat Polling")
        self._repeat_polling = True
        self._pollings_done = 0
        self._bus_worker.startPoll()
        self._processData(True)

    def _startPolling(self):
        self._is_polling_in_progress = True
        self._pollings_needed = int(self._widget_polling_amount_lineedit.text())
        self._repeat_polling = False
        self._pollings_done = 0
        
        if(self._pollings_needed <= 0):
            self._pollings_needed = 1
            self._widget_polling_amount_lineedit.setText(str(self._pollings_needed))
        elif(self._pollings_needed >= 250):
            self._pollings_needed = 250
            self._widget_polling_amount_lineedit.setText(str(self._pollings_needed))

        self._widget_start_polling_button.setText("Stop Polling")
        self._widget_start_repeat_polling_button.setText("Start Repeat Polling")
        self._bus_worker.startPoll()
        self._processData(True)

    def _stopPolling(self):
        self._is_polling_in_progress = False
        self._widget_start_polling_button.setText("Start Polling")
        self._widget_start_repeat_polling_button.setText("Start Repeat Polling")
        self._bus_worker.stopPoll()

    def _antDiagHandler(self):
        self._bus_worker.perform_diag()

    def _performAuthStateHandler(self):
        if self._widget_auth_checkbox.isChecked():
            self._bus_worker.auth_mode = 1
        else:
            self._bus_worker.auth_mode = 0
            self._animationStop(self._auth_state_animation)
            self._widget_auth_state_label.setText(f'Auth: None\t')
            self._widget_auth_state_label.setStyleSheet("color: black;")
        
        self._bus_worker.sendData()

    def _askStartStopPollingCallback(self, start: bool = False):
        # We have to start polling anyway, so if it's in process
        # then stop it and start again
        # if(self._widget_start_polling_button.text() == "Stop Polling"):
        self._stopPolling()

        if start:
            key_num = self._widgetKeyForMeasure.currentIndex()
            self._bus_worker.key_mask = (1 << key_num)
            self._startPolling()

    def _allDataReceivedCallback(self):
        if self._is_polling_in_progress:
            self._animationStart(self._pollings_done_animation)

            self._pollings_done += 1
            if self._pollings_done > 250:
                self._pollings_done = 1

            if (self._pollings_done == self._pollings_needed and not self._repeat_polling):
                self._stopPolling()

            self._processData(True)
            # key_num = self._widgetKeyForMeasure.currentIndex()
            # dataForCalibration = self._ants_keys_data.makeOneKeyData(data, key_num)
            # self._points_painter.rememberData(dataForCalibration, key_num, self._auth_status, isPollDone)
            # self._printLogData()

    def _processData(self, res: bool):
        if not res:
            # Just set all widgets to standart state
            self._widget_msg_period_label.setText("Msg Period: 0 ms")
            self._animationStop(self._auth_state_animation)
            self._widget_auth_state_label.setText(f'Auth: None\t')
            self._widget_auth_state_label.setStyleSheet("color: black;")
            self._widget_last_key_label.setText(f"Last Key Pressed Num: None\t")
            data = self._ants_keys_data.getZeroData()
            self._animationStop(self._pollings_done_animation)
            self._widget_pollings_done_label.setText(f"Target: - ; Done: -")
            self._widget_pollings_done_label.setStyleSheet("color: black;")
            self._pollings_done = 0
            
        else:
            # Get data from CAN bus
            data = self._bus_worker.Data
            self._widget_msg_period_label.setText(f"Msg Period: {int(self._bus_worker.TimeBetweenMsgs)} ms")

            # Check if PKE block has done as much polling, as needed
            if (not self._repeat_polling):
                self._widget_pollings_done_label.setText(f"Target: {self._pollings_needed}; Done: {self._pollings_done}")
        
                if (self._pollings_done == self._pollings_needed):
                    self._animationStop(self._pollings_done_animation)
                    self._widget_pollings_done_label.setStyleSheet("color: green;")
                else:
                    self._widget_pollings_done_label.setStyleSheet("color: black;")

            else:  
                self._widget_pollings_done_label.setText(f"Target: ∞ ; Done: - ")

        for nAnt in range(self._ant_amount):
            for nKey in range(self._key_amount):
                self._RSSI_widgets[nAnt][nKey].setText(
                    f"X: {' '*(3-len(str(data[nAnt][nKey][0])))}{data[nAnt][nKey][0]}\n" +
                    f"Y: {' '*(3-len(str(data[nAnt][nKey][1])))}{data[nAnt][nKey][1]}\n" +
                    f"Z: {' '*(3-len(str(data[nAnt][nKey][2])))}{data[nAnt][nKey][2]}"
                )
   
    def _printLogData(self): 
        time_hms = time.strftime("%H:%M:%S", time.localtime())
        time_dmy = time.strftime("%d/%m/%Y", time.localtime())
        
        bold = self._workbook.add_format({'bold': True})

        self._worksheet.write(self._row, self._column,   'Time: ', bold)
        self._worksheet.write(self._row, self._column+1, f'{time_hms}')
        self._worksheet.write(self._row, self._column+2, 'Date: ', bold)
        self._worksheet.write(self._row, self._column+3, f'{time_dmy}')
        
        if self._auth_status:
            self._worksheet.write(self._row, self._column+5, 'Auth OK', bold)
        else:
            self._worksheet.write(self._row, self._column+5, 'Auth Fail', bold)

        for nKey in range(self._key_amount):
            self._worksheet.write(self._row+3+nKey, self._column, f"KEY {nKey+1}")
    
        data = self._bus_worker.Data

        for i in range(self._ant_amount):
            self._worksheet.write(self._row+1, i*4+self._column+2, f"ANTENNA {i+1}")

            self._worksheet.write(self._row+2, i*4+self._column+1, "RSSI X")
            self._worksheet.write(self._row+2, i*4+self._column+2, "RSSI Y")
            self._worksheet.write(self._row+2, i*4+self._column+3, "RSSI Z")

            for nKey in range(self._key_amount):
                self._worksheet.write_number(self._row+3+nKey, i*4+self._column+1, data[i][nKey][0])
                self._worksheet.write_number(self._row+3+nKey, i*4+self._column+2, data[i][nKey][1])                 
                self._worksheet.write_number(self._row+3+nKey, i*4+self._column+3, data[i][nKey][2])

        self._row += 9

    def _addLogHandler(self):
        time_hms = time.strftime("%H:%M:%S", time.localtime())
        time_dmy = time.strftime("%d/%m/%Y", time.localtime())
        
        bold = self._workbook.add_format({'bold': True})

        self._worksheet_single.write(self._row_single, self._column_single,   'Time: ', bold)
        self._worksheet_single.write(self._row_single, self._column_single+1, f'{time_hms}')
        self._worksheet_single.write(self._row_single, self._column_single+2, 'Date: ', bold)
        self._worksheet_single.write(self._row_single, self._column_single+3, f'{time_dmy}')

        if self._auth_status:
            self._worksheet_single.write(self._row_single, self._column_single+5, 'Auth OK', bold)
        else:
            self._worksheet_single.write(self._row_single, self._column_single+5, 'Auth Fail', bold)

        msg = self._widget_log_msg_lineedit.text()
        self._worksheet_single.write(self._row_single, self._column_single+7, 'Message: ', bold)
        self._worksheet_single.write(self._row_single, self._column_single+8, f'{msg}')

        for nKey in range(self._key_amount):
            self._worksheet_single.write(self._row_single+3+nKey, self._column_single, f"KEY {nKey+1}")

        printData = self._bus_worker.Data

        for i in range(6):
            self._worksheet_single.write(self._row_single+1, i*4+self._column_single+2, f"ANTENNA {i+1}")

            self._worksheet_single.write(self._row_single+2, i*4+self._column_single+1, "RSSI X")
            self._worksheet_single.write(self._row_single+2, i*4+self._column_single+2, "RSSI Y")
            self._worksheet_single.write(self._row_single+2, i*4+self._column_single+3, "RSSI Z")

            for nKey in range(self._key_amount):
                self._worksheet_single.write_number(self._row_single+3+nKey, i*4+self._column_single+1, printData[i][nKey][0])
                self._worksheet_single.write_number(self._row_single+3+nKey, i*4+self._column_single+2, printData[i][nKey][1])                 
                self._worksheet_single.write_number(self._row_single+3+nKey, i*4+self._column_single+3, printData[i][nKey][2])

        self._row_single += 9

    def _setBackgroundAnimation(self, animation, func_name):
        animation_1 = QPropertyAnimation(self, func_name, self)
        # animation_1.setEasingCurve(QEasingCurve.OutCubic)
        animation_1.setDuration(200)
        animation_1.setStartValue(0)
        animation_1.setEndValue(0.2)

        animation_2 = QPropertyAnimation(self, func_name, self)
        # animation_2.setEasingCurve(QEasingCurve.InCubic)
        animation_2.setDuration(200)
        animation_2.setStartValue(0.2)
        animation_2.setEndValue(0)

        animation.addAnimation(animation_1)
        animation.addAnimation(animation_2)

    def _animationStart(self, animation):
        animation.start()
        
    def _animationStop(self, animation):
        animation.stop()

    @pyqtProperty(float)
    def auth_background(self):
        return self._auth_background

    @auth_background.setter
    def auth_background(self, pos):
        self._auth_background = pos

        color = ''
        if self._auth_status == True:
            color = 'green'
        else:
            color = 'red'

        self._widget_auth_state_label.setStyleSheet(f"color: {color}; \
                                         background-color: rgba({self._background_colors[0]}, \
                                                                {self._background_colors[1]}, \
                                                                {self._background_colors[2]}, \
                                                                {pos}); \
                                         border-width: 2px; \
                                         border-radius: 10px;")
            
    @pyqtProperty(float)
    def pollings_done_background(self):
        return self._pollings_done_background

    @pollings_done_background.setter
    def pollings_done_background(self, pos):
        self._pollings_done_background = pos
        self._widget_pollings_done_label.setStyleSheet(f"background-color: rgba({self._background_colors[0]}, \
                                                                        {self._background_colors[1]}, \
                                                                        {self._background_colors[2]}, \
                                                                        {pos}); \
                                                 border-width: 2px; \
                                                 border-radius: 10px;")

    @pyqtProperty(float)
    def last_key_background(self):
        return self._last_key_background

    @last_key_background.setter
    def last_key_background(self, pos):
        self._last_key_background = pos
        self._widget_last_key_label.setStyleSheet(f"background-color: rgba({self._background_colors[0]}, \
                                                                      {self._background_colors[1]}, \
                                                                      {self._background_colors[2]}, \
                                                                      {pos}); \
                                               border-width: 2px; \
                                               border-radius: 10px;")

    @pyqtProperty(float)
    def ant_imps_background(self):
        return self._ant_imps_background

    @ant_imps_background.setter
    def ant_imps_background(self, pos):
        self._ant_imps_background = pos
        for i in range(len(self._widget_ant_imps_labels)):
            self._widget_ant_imps_labels[i].setStyleSheet(f"background-color: rgba({self._background_colors[0]}, \
                                                                          {self._background_colors[1]}, \
                                                                          {self._background_colors[2]}, \
                                                                          {pos}); \
                                                   border-width: 2px; \
                                                   border-radius: 10px;")


def app_start():
    app = QApplication([])

    window = MainWindow()

    app.exec()

if __name__ == "__main__": 
    app_start() 

# TIME STAMP

# pyinstaller --onefile --hidden-import=can.interfaces.systec -w PKE_Setup.py
# pyinstaller PKE_Setup.py --hidden-import=can.interfaces.systec --noconsole --add-data "pictures;pictures" --name PKE_Setup --noconfirm