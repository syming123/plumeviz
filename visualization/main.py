import sys
import os
import vtk
from PyQt6.QtWidgets import QApplication

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from gui.main_window import MainWindow


if __name__ == '__main__':
    # close vtk warning
    vtk.vtkOutputWindow.SetGlobalWarningDisplay(0)

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
