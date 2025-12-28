import sys
from PySide6.QtWidgets import QApplication
from gui import MainWindow


#TODO: semiauto updater/release bundle/.exe/qss style sheet/splash screen> WTFS>
#error handling, pass cookies to youtube automatically/manually?

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())