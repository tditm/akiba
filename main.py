# Standard library imports
from sys import exit

# Third-party library imports
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

# Local application imports
from src.controllers import ChessClaimController
from src.helpers import resource_path

if __name__ == '__main__':
    # Initialize the main application controller
    app = ChessClaimController()

    # Set a visual theme across all operating systems
    app.setStyle('fusion')

    # Set the application window icon using the resource path helperbo 
    app.setWindowIcon(QIcon(resource_path("logo.png")))

    # Load and apply custom styles from the CSS file
    with open(resource_path('main.css'), 'r') as css_file:
        css = css_file.read().replace('\n', '')
    app.setStyleSheet(css)

    # Start the Qt main event loop and exit the script when the window is closed
    app.do_start()
    exit(app.exec())
