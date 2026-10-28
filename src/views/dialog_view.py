from functools import partial
from typing import List, Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QWidget, QComboBox, QLineEdit, QPushButton,
    QLabel, QHBoxLayout, QVBoxLayout, QFileDialog, QSpinBox
)

from src.helpers import resource_path, Status


class AddSourceDialog(QDialog):
    """
    Dialog window for managing PGN sources.

    Allows the user to add, remove, and validate multiple PGN sources,
    either from a web URL or a local file.
    """

    ICON_SIZE = 20
    __slots__ = ['controller', 'layout', 'bottomBox', 'sources', 'sources_cnt']

    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller

        # Basic dialog configuration
        self.setModal(True)
        self.setMinimumWidth(620)
        self.resize(620, 100)
        self.setWindowTitle("PGN Sources")

        # Remove the "?" help button from the title bar
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowType.WindowContextHelpButtonHint)

        self.layout = None
        self.bottomBox = None
        self.sources: List[SourceHBox] = []
        self.sources_cnt = 0

    def set_gui(self) -> None:
        """Initialize all GUI components for the dialog."""

        # Bottom button box (Apply + OK)
        self.bottomBox = BottomBox(self.controller)

        # Button for adding new source rows
        add_source_button = QPushButton("")
        add_source_button.setIcon(QIcon(resource_path("add_icon.png")))
        add_source_button.setIconSize(QSize(self.ICON_SIZE + 4, self.ICON_SIZE + 4))
        add_source_button.setObjectName('AddSource')
        add_source_button.clicked.connect(self.on_add_source_button_clicked)

        # Main layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(add_source_button, 1, Qt.AlignmentFlag.AlignRight)
        self.layout.addWidget(self.bottomBox)

        self.setLayout(self.layout)
        self.adjustSize()

    def on_add_source_button_clicked(self) -> None:
        """Triggered when the user clicks the '+' button."""
        self.add_default_source()

    def add_source(self, option: int, value: str, round_num: int = 1) -> None:
        """
        Add a new source row to the dialog.

        Args:
            option (int): 0 = Web URL, 1 = Local file, 2 = LiveChessCloud Live
            value (str): URL or file path
            round_num (int): Round number for LiveChessCloud (default: 1)
        """
        self.sources_cnt += 1
        source_hbox = SourceHBox(self)
        source_hbox.set_source(option)
        source_hbox.set_value(value)
        
        # Set round number if this is a LiveChessCloud source and value was provided
        if option == 2 and value:
            source_hbox.set_round_num(round_num)

        self.sources.append(source_hbox)
        self.layout.insertWidget(self.sources_cnt - 1, source_hbox)

    def add_default_source(self) -> None:
        """Add a new empty Web URL source row."""
        self.add_source(0, "")

    def enable_ok_button(self) -> None:
        """Enable the OK button."""
        self.bottomBox.change_ok_status(True)

    def disable_ok_button(self) -> None:
        """Disable the OK button."""
        self.bottomBox.change_ok_status(False)

    def remove_hbox(self, hbox) -> None:
        """
        Remove a source row from the dialog.

        Args:
            hbox (SourceHBox): The row to remove.
        """
        self.layout.removeWidget(hbox)
        self.sources.remove(hbox)
        self.sources_cnt -= 1

        hbox.deleteLater()
        self.adjustSize()


class SourceHBox(QWidget):
    """
    A single row representing one PGN source.

    Contains:
    - ComboBox (Web URL / Local file)
    - LineEdit for URL or file path
    - Optional "Choose File" button
    - Status icon (OK / Error)
    - Delete button
    """

    __slots__ = [
        'dialog', 'select_source', 'source_value', 'choose_button',
        'status_image', 'ok_pixmap', 'error_pixmap', 'round_spinbox'
    ]

    def __init__(self, dialog: AddSourceDialog) -> None:
        super().__init__()
        self.dialog = dialog

        # Source type selector
        self.select_source = QComboBox()
        self.select_source.addItems(["Web(url)", "Local", "LiveChessCloud"])
        self.select_source.currentIndexChanged.connect(self.select_change)

        # Input field for URL or file path
        self.source_value = QLineEdit()
        self.source_value.textChanged.connect(self.line_edit_changed)
        self.source_value.setPlaceholderText("https://example.com/pgn/games.pgn")
        self.source_value.setMinimumWidth(200)

        # File chooser button (only visible for local file option)
        self.choose_button = QPushButton("Choose File")
        self.choose_button.clicked.connect(self.on_choose_button_clicked)
        self.choose_button.setHidden(True)

        # Round number spinbox (for LiveChessCloud)
        self.round_spinbox = QSpinBox()
        self.round_spinbox.setMinimum(1)  # Minimum round is 1
        self.round_spinbox.setMaximum(9999)
        self.round_spinbox.setValue(1)  # Default to round 1
        self.round_spinbox.setHidden(True)
        round_label = QLabel("Round:")
        round_label.setHidden(True)
        self.round_label = round_label

        # Status icon (OK / Error)
        self.status_image = QLabel()
        self.ok_pixmap = QPixmap(resource_path("check_icon.png"))
        self.error_pixmap = QPixmap(resource_path("error_icon.png"))

        # Delete button
        delete_button = QPushButton("")
        delete_button.setIcon(QIcon(resource_path("delete_icon.png")))
        delete_button.setIconSize(QSize(self.dialog.ICON_SIZE, self.dialog.ICON_SIZE))
        delete_button.setObjectName('DeleteSource')
        delete_button.clicked.connect(
            partial(self.dialog.controller.on_delete_button_clicked, self)
        )

        # Layout for the row
        layout = QHBoxLayout()
        layout.addWidget(self.select_source)
        layout.addWidget(self.source_value)
        layout.addWidget(self.choose_button)
        layout.addWidget(round_label)
        layout.addWidget(self.round_spinbox)
        layout.addWidget(self.status_image)
        layout.addWidget(delete_button)

        self.setLayout(layout)
        self.adjustSize()

    def set_value(self, text: str) -> None:
        """Set the text of the input field."""
        self.source_value.setText(text)

    def set_source(self, index: int) -> None:
        """Set the source type (0 = URL, 1 = Local)."""
        self.select_source.setCurrentIndex(index)

    def get_value(self) -> str:
        """Return the current text in the input field."""
        return self.source_value.text()

    def get_source_index(self) -> int:
        """Return the selected source type index."""
        return self.select_source.currentIndex()

    def has_url(self) -> bool:
        """Return True if the source type is Web URL."""
        return self.select_source.currentIndex() == 0

    def has_local(self) -> bool:
        """Return True if the source type is Local file."""
        return self.select_source.currentIndex() == 1
    
    def has_livechess(self) -> bool:
        """Return True if the source type is LiveChessCloud Live."""
        return self.select_source.currentIndex() == 2
    
    def get_round_num(self) -> Optional[int]:
        """Get round number."""
        if not self.has_livechess():
            return None
        value = self.round_spinbox.value()
        return value
    
    def set_round_num(self, round_num: int) -> None:
        """Set the round number for LiveChessCloud source.
        
        Args:
            round_num (int): Round number to set (default: 1)
        """
        # Always set the value - it will be used when source type is changed to LiveChessCloud
        self.round_spinbox.setValue(round_num if round_num is not None else 1)

    def line_edit_changed(self) -> None:
        """Reset status when the user edits the input field."""
        self.dialog.disable_ok_button()
        self.status_image.clear()

    def select_change(self, index: int) -> None:
        """
        Handle switching between Web URL, Local file, and LiveChessCloud.

        Args:
            index (int): 0 = Web URL, 1 = Local file, 2 = LiveChessCloud Live
        """
        self.line_edit_changed()

        if index == 0:
            # Web URL mode
            self.choose_button.setHidden(True)
            self.round_label.setHidden(True)
            self.round_spinbox.setHidden(True)
            self.source_value.setText("")
            self.source_value.setPlaceholderText("https://example.com/pgn/games.pgn")

        elif index == 1:
            # Local file mode
            self.choose_button.setHidden(False)
            self.round_label.setHidden(True)
            self.round_spinbox.setHidden(True)
            self.source_value.setText("")
            self.source_value.setPlaceholderText("")

        elif index == 2:
            # LiveChessCloud mode
            self.choose_button.setHidden(True)
            self.round_label.setHidden(False)
            self.round_spinbox.setHidden(False)
            self.source_value.setText("")
            self.source_value.setPlaceholderText("https://view.livechesscloud.com/#uuid")

    def set_status(self, status: Status) -> None:
        """
        Display the status icon (OK or Error).

        Args:
            status (Status): Validation result
        """
        if status == Status.OK:
            self.status_image.setPixmap(
                self.ok_pixmap.scaled(
                    self.dialog.ICON_SIZE,
                    self.dialog.ICON_SIZE,
                    transformMode=Qt.TransformationMode.SmoothTransformation
                )
            )

        elif status == Status.ERROR:
            self.status_image.setPixmap(
                self.error_pixmap.scaled(
                    self.dialog.ICON_SIZE,
                    self.dialog.ICON_SIZE,
                    transformMode=Qt.TransformationMode.SmoothTransformation
                )
            )

    def on_choose_button_clicked(self) -> None:
        """Open a file dialog for selecting a local PGN file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", "PGN Files (*.pgn)"
        )
        if filename:
            self.source_value.setText(filename)


class BottomBox(QWidget):
    """
    Bottom section of the dialog containing:
    - Apply button
    - OK button
    """

    __slots__ = ['controller', 'ok_button']

    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller

        # Buttons
        apply_button = QPushButton("Apply")
        self.ok_button = QPushButton("OK")

        apply_button.setObjectName("apply")
        self.ok_button.setObjectName("ok")

        apply_button.clicked.connect(self.controller.on_apply_button_clicked)
        self.ok_button.clicked.connect(self.controller.on_ok_button_clicked)

        # OK button is disabled until validation succeeds
        self.ok_button.setEnabled(False)

        # Layout
        layout = QHBoxLayout()
        layout.setSpacing(30)
        layout.addWidget(apply_button)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def change_ok_status(self, status: bool) -> None:
        """Enable or disable the OK button."""
        self.ok_button.setEnabled(status)
