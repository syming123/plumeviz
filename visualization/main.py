import sys
import vtk
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow


if __name__ == '__main__':
    # close vtk warning
    #vtk.vtkOutputWindow.SetGlobalWarningDisplay(0)

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
