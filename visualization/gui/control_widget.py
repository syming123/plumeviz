import threading
import time

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QPushButton, QProgressBar
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout

from common.entity import DataFrame
from visualization.gui.signal_group import signals


class ControlWidget(QWidget):
    thread = None
    playing = False

    group_index = 0
    frame_index = 0
    group_size = 0

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background-color:#454545")
        box_widget = QWidget()
        box_layout = QVBoxLayout()
        box_widget.setLayout(box_layout)
        box_widget.setObjectName("boxWidget")
        box_widget.setStyleSheet('QWidget#boxWidget{background-color:#454545}')
        box_widget.setFixedHeight(100)

        # 创建一个进度条
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("color:#bbbbbb")

        # 创建一个水平布局来放置按钮
        operator_widget = QWidget()
        operator_layout = QHBoxLayout()
        operator_widget.setLayout(operator_layout)
        operator_widget.setContentsMargins(80, 0, 80, 0)

        # 添加按钮到布局中
        self.first_frame_button = QPushButton()
        self.first_frame_button.setIcon(QIcon('../res/icons/first-frame.png'))  # 设置图标
        self.first_frame_button.setStyleSheet("background-color:#454545;border:0px")
        self.first_frame_button.setIconSize(QSize(40, 40))
        self.first_frame_button.setFixedSize(40, 40)
        operator_layout.addWidget(self.first_frame_button)
        self.first_frame_button.clicked.connect(self.first_click)

        self.prev_frame_button = QPushButton()
        self.prev_frame_button.setIcon(QIcon('../res/icons/previous.png'))  # 设置图标
        self.prev_frame_button.setStyleSheet("background-color:#454545;border:0px")
        self.prev_frame_button.setIconSize(QSize(40, 40))
        self.prev_frame_button.setFixedSize(40, 40)
        operator_layout.addWidget(self.prev_frame_button)
        self.prev_frame_button.clicked.connect(self.front_click)

        self.play_button = QPushButton()
        self.play_button.setIcon(QIcon('../res/icons/play.png'))  # 设置图标
        self.play_button.setStyleSheet("background-color:#454545;border:0px")
        self.play_button.setIconSize(QSize(40, 40))
        self.play_button.setFixedSize(40, 40)
        operator_layout.addWidget(self.play_button)
        self.play_button.clicked.connect(self.play_click)

        self.next_frame_button = QPushButton()
        self.next_frame_button.setIcon(QIcon('../res/icons/next.png'))  # 设置图标
        self.next_frame_button.setStyleSheet("background-color:#454545;border:0px")
        self.next_frame_button.setIconSize(QSize(40, 40))
        self.next_frame_button.setFixedSize(40, 40)
        operator_layout.addWidget(self.next_frame_button)
        self.next_frame_button.clicked.connect(self.next_click)

        self.last_frame_button = QPushButton()
        self.last_frame_button.setIcon(QIcon('../res/icons/last-frame.png'))  # 设置图标
        self.last_frame_button.setStyleSheet("background-color:#454545;border:0px")
        self.last_frame_button.setIconSize(QSize(40, 40))
        self.last_frame_button.setFixedSize(40, 40)
        operator_layout.addWidget(self.last_frame_button)
        self.last_frame_button.clicked.connect(self.last_click)

        box_layout.addWidget(self.progress_bar)
        box_layout.addWidget(operator_widget)

        layout.addWidget(box_widget)

        # ==============================
        # global slots
        # ==============================
        signals.load_frame.connect(self.on_frame_load)


    def on_frame_load(self, frame: DataFrame, group_index: int, frame_index: int, group_size: int):
        self.group_index = group_index
        self.frame_index = frame_index
        self.group_size = group_size

        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(group_size - 1)
        self.progress_bar.setValue(frame_index)


    def front_click(self):
        new_index = (self.frame_index - 1 + self.group_size) % self.group_size
        signals.pick_changed.emit(self.group_index, new_index)

    def next_click(self):
        new_index = (self.frame_index + 1) % self.group_size
        signals.pick_changed.emit(self.group_index, new_index)

    def first_click(self):
        signals.pick_changed.emit(self.group_index, 0)

    def last_click(self):
        signals.pick_changed.emit(self.group_index, self.group_size - 1)

    def play_click(self):
        def run():
            while self.playing:
                self.next_click()
                time.sleep(0.1)

        if self.playing:
            self.playing = False
            self.play_button.setIcon(QIcon('../res/icons/play.png'))
        else:
            self.playing = True
            self.play_button.setIcon(QIcon('../res/icons/pause.png'))
            self.thread = threading.Thread(target=run)
            self.thread.start()
