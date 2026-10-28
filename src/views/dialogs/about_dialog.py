from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QSize

from src.helpers import resource_path


class AboutDialog(QDialog):
    """
    About dialog GUI.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Akiba - About")
        # Remove the context help button from title bar
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._layout_built = False   # prevent building the layout more than once

    def set_gui(self) -> None:
        """Build About dialog GUI components."""

        # if layout already exists → do nothing
        if self._layout_built:
            return

        # create layout only once
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 15)  # left, top, right, bottom margins (top=20px)
        layout.setSpacing(7)  # consistent spacing between all elements (except after logo)
        self.setLayout(layout)

        logo = QLabel()
        logo_pixmap = QPixmap(resource_path("logo.png"))
        logo.setPixmap(logo_pixmap.scaled(QSize(128, 128), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        appname = QLabel("<b>Akiba</b> - Monitoring System for Chess Arbiters")
        appname.setObjectName("appname")
        appname.setAlignment(Qt.AlignmentFlag.AlignCenter)
        appname.setTextFormat(Qt.TextFormat.RichText)

        version_and_copyright = QLabel("Version 1.0 by Tomek Delega 2026 ©")
        version_and_copyright.setObjectName("version")
        version_and_copyright.setAlignment(Qt.AlignmentFlag.AlignCenter)

        copyright_info = QLabel("Based on Chess Claim Tool by Athanasios Serntedakis 2019 ©")
        copyright_info.setObjectName("copyright")
        copyright_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(logo)
        # Add 5px spacer after logo (in addition to the default 7px spacing = total 12px)
        layout.addSpacing(12)
        layout.addWidget(appname)
        layout.addWidget(version_and_copyright)
        layout.addWidget(copyright_info)

        self._layout_built = True