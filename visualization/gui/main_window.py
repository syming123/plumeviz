from PyQt6.QtWidgets import QMainWindow, QWidget
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout

from visualization.gui.vtk_widget import VTKWidget
from visualization.gui.feature_widget import FeatureWidget
from visualization.gui.control_widget import ControlWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(380, 200, 1400, 800)
        self.setWindowTitle("PlumeViz")
        self.setStyleSheet("background:#1f1f1f")
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(3, 3, 3, 3)
        main_widget.setLayout(main_layout)

        center_widget = QWidget()
        right_widget = QWidget()
        right_widget.setStyleSheet("background:#454545")
        main_layout.addWidget(center_widget)
        main_layout.addWidget(right_widget)
        main_layout.setSpacing(3)

        # center widget:
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_widget.setLayout(center_layout)
        center_layout.setSpacing(3)

        # center : declare widget
        vtk_widget = VTKWidget()
        control_widget = ControlWidget()

        # center : add widget
        center_layout.addWidget(vtk_widget)
        center_layout.addWidget(control_widget)

        # right_widget:
        right_widget.setFixedWidth(350)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_widget.setLayout(right_layout)

        # right : declare children widget
        feature_widget = FeatureWidget()

        # right : add children widget
        right_layout.addWidget(feature_widget)
