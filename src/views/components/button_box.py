from __future__ import annotations

from typing import Callable

from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout


class ButtonBox(QWidget):
    """
    Provides a horizontal box with three buttons:
    - Scan
    - Stop
    - Board Viewer
    """

    __slots__ = ["scan_button", "stop_button", "board_button"]

    def __init__(self) -> None:
        super().__init__()

        self.scan_button = QPushButton("Start Scan")
        self.scan_button.setObjectName("Scan")

        self.stop_button = QPushButton("Stop Scan")
        self.stop_button.setObjectName("Stop")

        self.board_button = QPushButton("Board Viewer")
        self.board_button.setObjectName("BoardViewer")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(self.scan_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.board_button)

        self.setLayout(layout)

    def set_scan_button_callback(self, on_clicked: Callable) -> None:
        """Set callback for the scan button."""
        self.scan_button.clicked.connect(on_clicked)

    def set_stop_button_callback(self, on_clicked: Callable) -> None:
        """Set callback for the stop button."""
        self.stop_button.clicked.connect(on_clicked)

    def set_board_button_callback(self, on_clicked: Callable) -> None:
        """Set callback for the board viewer button."""
        self.board_button.clicked.connect(on_clicked)