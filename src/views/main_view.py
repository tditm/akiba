from __future__ import annotations

import platform
from datetime import datetime
from typing import Optional, Callable, List

from PyQt6.QtCore import Qt, QSize, QEvent
from PyQt6.QtGui import QPixmap, QMovie, QColor, QAction
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QStatusBar,
    QMessageBox,
    QMenu,
    QWidgetAction,
    QCheckBox,
    QSpinBox,
    QSizePolicy,
)

from src.helpers import resource_path, Status
from src.models.events import ClaimType, ClaimsStore

# Import new component classes
from src.views.components.button_box import ButtonBox
from src.views.components.claims_table import ClaimsTable
from src.views.components.menu_builder import MenuBarBuilder
from src.views.dialogs.about_dialog import AboutDialog


def sources_warning() -> None:
    """Display a warning dialog when no valid PGN sources are found."""
    from PyQt6.QtWidgets import QMessageBox
    
    warning_dialog = QMessageBox()
    warning_dialog.setIcon(QMessageBox.Icon.Warning)
    warning_dialog.setWindowTitle("Warning")
    warning_dialog.setText("PGN File(s) Not Found")
    warning_dialog.setInformativeText("Please enter at least one valid PGN source.")
    warning_dialog.exec()

class ChessClaimView(QMainWindow):
    """
    Main application window.

    Displays:
    - claims table (via ClaimsTable component)
    - control buttons (via ButtonBox component)
    - status bar with sources / download / scan status
    """
    ICON_SIZE = 16
    
    __slots__ = [
        "controller",
        "button_box",
        "claims_table_widget",
        "ok_pixmap",
        "error_pixmap",
        "source_label",
        "source_image",
        "download_label",
        "download_image",
        "scan_label",
        "scan_image",
        "spinner",
        "status_bar",
        "about_dialog",
        "notification",
        "notifications_enabled_action",
        "scoresheet_action",
        "scoresheet_spin",
        "possible_threefold_action",
        "possible_fiftymove_action",
        "timecontrol_action",
        "timecontrol_spin",
        "low_time_action",
        "low_time_spin",
        "flag_fall_action",
        "sofia_action",
        "sofia_spin",
        "claims_store",
        "clear_resolved_button",
    ]

    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        
        # Use same ClaimsStore as controller - SINGLE SOURCE OF TRUTH
        self.claims_store = controller.claims_store

        # Basic window setup
        self.resize(720, 275)
        self.setWindowTitle("Akiba")
        self.center()

        # Status icons and labels (shared by status bar components)
        self.ok_pixmap = QPixmap(resource_path("check_icon.png"))
        self.error_pixmap = QPixmap(resource_path("error_icon.png"))

        # Initialize notification system
        if platform.system() == "Darwin":
            from src.notifications.mac import Notification
            self.notification = Notification()
        elif platform.system() == "Windows":
            from windows_toasts import WindowsToaster, ToastImageAndText2, ToastDisplayImage, ToastDuration
            self.notification = WindowsToaster("Akiba")
        else:
            self.notification = None

        # Main widgets - using new components
        self.claims_table_widget = ClaimsTable(controller)
        self.button_box = ButtonBox()
        
        # Alias for backward compatibility with controller
        self.claims_table = self.claims_table_widget

        # Status bar labels and images
        self.source_label = QLabel()
        self.source_image = QLabel()
        self.download_label = QLabel()
        self.download_image = QLabel()
        self.scan_label = QLabel()
        self.scan_image = QLabel()

        # Spinner for scan status
        self.spinner = QMovie(resource_path("spinner.gif"))

        # Clear Resolved button (for status bar)
        self.clear_resolved_button = QPushButton("Clear Resolved")
        self.clear_resolved_button.setObjectName("clearResolved")

        # Status bar
        self.status_bar = QStatusBar()

        # About dialog
        self.about_dialog = AboutDialog()

        # Menu widgets (settings) - kept in main view as they control controller state
        self._setup_menu_widgets()

        # Build the UI
        self._build_ui()
        
        # Connect buttons to controller callbacks
        self.button_box.set_scan_button_callback(self.controller.on_scan_button_clicked)
        self.button_box.set_stop_button_callback(self.controller.on_stop_button_clicked)
        self.button_box.set_board_button_callback(self.controller.on_board_viewer_clicked)
        
        self.create_status_bar()
        self.create_menu()

    def _setup_menu_widgets(self) -> None:
        """Setup menu widgets for settings."""
        
        # Notification system toggle
        self.notifications_enabled_action = QCheckBox("Enable Windows/Mac notifications")
        self.notifications_enabled_action.setChecked(True)
        
        # Scoresheet reminder
        self.scoresheet_action = QCheckBox("Scoresheet change reminder after move")
        self.scoresheet_action.setChecked(False)
        self.scoresheet_spin = QSpinBox()
        self.scoresheet_spin.setRange(1, 200)
        self.scoresheet_spin.setValue(55)
        self.scoresheet_spin.setEnabled(False)

        # Time control reminder
        self.timecontrol_action = QCheckBox("Time control reminder after move")
        self.timecontrol_action.setChecked(False)
        self.timecontrol_spin = QSpinBox()
        self.timecontrol_spin.setRange(1, 200)
        self.timecontrol_spin.setValue(38)
        self.timecontrol_spin.setEnabled(False)

        # Possible Threefold Reminder
        self.possible_threefold_action = QCheckBox("Possible threefold reminder (2 fold)")
        self.possible_threefold_action.setChecked(False)

        # Possible 50-move Reminder
        self.possible_fiftymove_action = QCheckBox("Possible 50-move reminder (45 moves)")
        self.possible_fiftymove_action.setChecked(False)

        # Low Time Reminder
        self.low_time_action = QCheckBox("Low time reminder if less seconds than")
        self.low_time_action.setChecked(False)
        self.low_time_spin = QSpinBox()
        self.low_time_spin.setRange(1, 600)
        self.low_time_spin.setValue(120)
        self.low_time_spin.setEnabled(False)

        # Flag Fall Reminder
        self.flag_fall_action = QCheckBox("Flag fall reminder (00:00:00)")
        self.flag_fall_action.setChecked(False)

        # Illegal Move Reminder
        self.illegal_move_action = QCheckBox("First illegal move")
        self.illegal_move_action.setChecked(False)

        # Sofia Rule Reminder
        self.sofia_action = QCheckBox("Sofia rule - draw before move completed")
        self.sofia_action.setChecked(False)
        self.sofia_spin = QSpinBox()
        self.sofia_spin.setRange(1, 200)
        self.sofia_spin.setValue(30)
        self.sofia_spin.setEnabled(False)

    def _build_ui(self) -> None:
        """Build the main UI layout."""
        # Main layout - use claims_table_widget.table from component
        container_layout = QVBoxLayout()
        container_layout.setSpacing(0)
        container_layout.addWidget(self.claims_table_widget.table)
        container_layout.addWidget(self.button_box)

        container_widget = QWidget()
        container_widget.setLayout(container_layout)

        self.setCentralWidget(container_widget)
        self.setStatusBar(self.status_bar)
        
        # Adjust window width to fit table properly (from backup: create_claims_table does this)
        self.resize(860, self.height())

    def center(self) -> None:
        """Center the window on the screen."""
        from PyQt6.QtGui import QGuiApplication
        
        # Get primary screen geometry (PyQt6 replacement for QDesktopWidget)
        screen = QGuiApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            int((screen.width() - size.width()) / 2),
            int((screen.height() - size.height()) / 2),
        )

    def set_gui(self) -> None:
        """Initialize all GUI components (wrapper for backward compatibility)."""
        # All initialization is already done in __init__
        pass

    def create_menu(self) -> None:
        """Create the main menu bar using MenuBarBuilder."""
        builder = MenuBarBuilder(self)
        builder.build_menu()

        # Connect signals to update settings in controller
        self.notifications_enabled_action.stateChanged.connect(
            lambda state: (setattr(self.controller, "notifications_enabled", bool(state)), self.controller.save_options())
        )
        
        self.scoresheet_action.stateChanged.connect(self._update_scoresheet_settings)
        self.scoresheet_spin.valueChanged.connect(self._update_scoresheet_settings)
        
        self.timecontrol_action.stateChanged.connect(self._update_timecontrol_settings)
        self.timecontrol_spin.valueChanged.connect(self._update_timecontrol_settings)
        
        self.possible_threefold_action.stateChanged.connect(
            lambda state: (setattr(self.controller, "possible_threefold_enabled", bool(state)), self.controller.save_options())
        )

        self.possible_fiftymove_action.stateChanged.connect(
            lambda state: (setattr(self.controller, "possible_fiftymove_enabled", bool(state)), self.controller.save_options())
        )

        self.low_time_action.stateChanged.connect(self._update_low_time_settings)
        self.low_time_spin.valueChanged.connect(self._update_low_time_settings)

        self.flag_fall_action.stateChanged.connect(
            lambda state: (setattr(self.controller, "flag_fall_reminder_enabled", bool(state)), self.controller.save_options())
        )

        # Illegal move reminder connection
        self.illegal_move_action.stateChanged.connect(
            lambda state: (setattr(self.controller, "illegal_move_reminder_enabled", bool(state)), self.controller.save_options())
        )

        # Sofia rule reminder connection
        self.sofia_action.stateChanged.connect(self._update_sofia_settings)
        self.sofia_spin.valueChanged.connect(self._update_sofia_settings)

    def _update_scoresheet_settings(self) -> None:
        """Update controller settings from menu widgets."""
        enabled = self.scoresheet_action.isChecked()
        self.scoresheet_spin.setEnabled(enabled)

        self.controller.scoresheet_reminder_enabled = enabled
        self.controller.scoresheet_threshold = self.scoresheet_spin.value()
        
        # Save options to persist settings
        self.controller.save_options()
        
    def _update_timecontrol_settings(self) -> None:
        enabled = self.timecontrol_action.isChecked()
        self.timecontrol_spin.setEnabled(enabled)
        self.controller.timecontrol_reminder_enabled = enabled
        self.controller.timecontrol_threshold = self.timecontrol_spin.value()
        
        # Save options to persist settings
        self.controller.save_options()

    def _update_low_time_settings(self):
        enabled = self.low_time_action.isChecked()
        self.low_time_spin.setEnabled(enabled)
        self.controller.low_time_reminder_enabled = enabled
        self.controller.low_time_threshold_seconds = self.low_time_spin.value()
        
        # Save options to persist settings
        self.controller.save_options()
    
    def _update_sofia_settings(self) -> None:
        """Update controller settings from Sofia rule menu widgets."""
        enabled = self.sofia_action.isChecked()
        self.sofia_spin.setEnabled(enabled)

        self.controller.sofia_rule_enabled = enabled
        self.controller.sofia_rule_threshold = self.sofia_spin.value()
        
        # Save options to persist settings
        self.controller.save_options()

    def create_status_bar(self) -> None:
        """Create and configure the status bar."""
        sources_button = QPushButton("Add Sources")
        sources_button.setObjectName("sources")
        sources_button.clicked.connect(self.controller.on_sources_button_clicked)
        
        # Set fixed width for Add Sources button (based on Clear Resolved text length)
        sources_button.setMinimumWidth(125)

        self.source_image.setObjectName("source-image")
        self.download_image.setObjectName("download-image")
        self.scan_image.setObjectName("scan-image")

        self.spinner.setScaledSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
        self.spinner.start()

        self.status_bar.setSizeGripEnabled(False)
        
        # Create a layout for the entire status bar content
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)
        
        # Add sources button on the far left side (fixed width)
        sources_button.setMinimumWidth(125)
        status_layout.addWidget(sources_button)
        
        # Create center container for Source and Scan labels with spacing from sources
        center_container = QWidget()
        center_layout = QHBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(30)  # spacing from Add Sources button
        
        center_layout.addWidget(self.source_label)
        center_layout.addWidget(self.source_image)
        center_layout.addWidget(self.download_label)
        center_layout.addWidget(self.download_image)
        center_layout.addWidget(self.scan_label)
        center_layout.addWidget(self.scan_image)
        
        center_container.setLayout(center_layout)
        status_layout.addWidget(center_container)
        
        # Add stretchable space to push everything left
        status_layout.addStretch()
        
        # Add clear resolved button on the right side (same width as Add Sources)
        self.clear_resolved_button.setMinimumWidth(125)
        self.clear_resolved_button.clicked.connect(self.controller.on_clear_resolved_clicked)
        status_layout.addWidget(self.clear_resolved_button)
        
        # Create a widget to hold the layout and set it as the status bar
        status_widget = QWidget()
        status_widget.setLayout(status_layout)
        self.status_bar.addPermanentWidget(status_widget, stretch=1)
        
        self.status_bar.setContentsMargins(10, 5, 9, 5)

    def add_item_to_table(self, entry) -> None:
        """Add a claim to the table using ClaimsTable component."""
        self.claims_table_widget.add_claim(entry)

    def clear_claims_table(self) -> None:
        """Clear all rows from the claims table using component method."""
        self.claims_table_widget.clear()

    def clear_ack_rows(self) -> None:
        """Clear only acknowledged (✅) rows from the claims table."""
        self.claims_table_widget.clear_ack_rows()

    # Alias for backward compatibility with controller
    clear_table = clear_claims_table
    
    def refresh_table(self) -> None:
        """Refresh the claims table (alias for resize_columns)."""
        self.claims_table_widget.refresh_table()

    def set_sources_status(self, status: Status, valid_sources: Optional[List] = None) -> None:
        """
        Update the sources status in the status bar.

        Shows a tooltip listing all valid sources.
        """
        if valid_sources is None:
            valid_sources = []

        count = len(valid_sources)
        self.source_label.setText(f"Sources ({count})")

        try:
            text = ""
            for idx, source in enumerate(valid_sources):
                text += f"{idx + 1}) {source.get_value()}"
                if idx != len(valid_sources) - 1:
                    text += "\n"
            self.source_label.setToolTip(text)
        except TypeError:
            # In case valid_sources is not iterable or contains unexpected types
            pass

        self.set_pixmap(self.source_image, status)

    def set_download_status(self, status: Status) -> None:
        """Update the download status in the status bar."""
        timestamp = str(datetime.now().strftime("%H:%M:%S"))
        self.download_label.setText(f"{timestamp} Download:")

        self.set_pixmap(self.download_image, status)

        if status == Status.STOP:
            self.download_image.clear()
            self.download_label.clear()

    def set_scan_status(self, status: Status) -> None:
        """Update the scan status in the status bar."""
        timestamp = str(datetime.now().strftime("%H:%M:%S"))
        self.scan_label.setText(f"Scan ({timestamp}):")
        self.set_pixmap(self.scan_image, status)

        if status == Status.ACTIVE:
            self.scan_image.clear()
            self.scan_image.setMovie(self.spinner)
        elif status == Status.STOP:
            self.scan_label.clear()
            self.scan_image.clear()

    def change_scan_button_text(self, status: Status) -> None:
        """Change the scan button text depending on the scan status."""
        if status == Status.ACTIVE:
            self.button_box.scan_button.setText("Scanning PGN...")
        elif status == Status.STOP:
            self.button_box.scan_button.setText("Start Scan")
        elif status == Status.WAIT:
            self.button_box.scan_button.setText("Please Wait")

    def set_pixmap(self, image: QLabel, status: Status) -> None:
        """Set the appropriate status icon."""
        if status in (Status.OK, Status.WAIT):
            image.setPixmap(
                self.ok_pixmap.scaled(
                    self.ICON_SIZE,
                    self.ICON_SIZE,
                    transformMode=Qt.TransformationMode.SmoothTransformation,
                )
            )
        elif status == Status.ERROR:
            image.setPixmap(
                self.error_pixmap.scaled(
                    self.ICON_SIZE,
                    self.ICON_SIZE,
                    transformMode=Qt.TransformationMode.SmoothTransformation,
                )
            )

    def enable_buttons(self) -> None:
        """Enable main control buttons."""
        self.button_box.scan_button.setEnabled(True)
        self.button_box.stop_button.setEnabled(True)

    def disable_buttons(self) -> None:
        """Disable main control buttons."""
        self.button_box.scan_button.setEnabled(False)
        self.button_box.stop_button.setEnabled(False)

    def enable_status_bar(self) -> None:
        """Show download and scan status messages in the status bar."""
        self.download_label.setVisible(True)
        self.scan_label.setVisible(True)
        self.download_image.setVisible(True)
        self.scan_image.setVisible(True)

    def disable_status_bar(self) -> None:
        """Hide download and scan status messages from the status bar."""
        self.download_label.setVisible(False)
        self.download_image.setVisible(False)
        self.scan_label.setVisible(False)
        self.scan_image.setVisible(False)

    def closeEvent(self, event: QEvent) -> None:
        """
        Reimplement the close event to warn if scanning is in progress.
        """
        try:
            if self.controller.scan_worker and self.controller.scan_worker.isRunning():
                exit_dialog = QMessageBox()
                exit_dialog.setWindowTitle("Warning")
                exit_dialog.setText("Scanning in Progress")
                exit_dialog.setInformativeText("Do you want to quit?")
                exit_dialog.setIcon(exit_dialog.Warning)
                exit_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                exit_dialog.setDefaultButton(QMessageBox.Cancel)

                # --- button width adjustment ---
                yes_button = exit_dialog.button(QMessageBox.Yes)
                cancel_button = exit_dialog.button(QMessageBox.Cancel)
                yes_button.setMinimumWidth(100)
                cancel_button.setMinimumWidth(100)
                # --------------------------------

                replay = exit_dialog.exec()

                if replay == QMessageBox.Yes:
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()
        except Exception:
            event.accept()

    def load_about_dialog(self) -> None:
        """Display the About dialog."""
        self.about_dialog.set_gui()
        self.about_dialog.show()
    def open_user_manual(self) -> None:
        """Open the user documentation file in an internal browser window."""
        import os
        from src.helpers import resource_path
        
        # Get the path to USER_DOCUMENTATION.md using resource_path (works for both dev and frozen mode)
        manual_path = resource_path("USER_DOCUMENTATION.md")
        
        if not os.path.exists(manual_path):
            QMessageBox.warning(
                self,
                "User Manual Not Found",
                "The user documentation file could not be found."
            )
            return
        
        # Read the markdown file
        try:
            with open(manual_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error Reading Manual",
                f"Could not read the user documentation:\n\n{str(e)}"
            )
            return
        
        # Create a new window for the manual
        from PyQt6.QtWidgets import QMainWindow, QTextBrowser, QVBoxLayout, QWidget
        from PyQt6.QtCore import Qt
        
        self.manual_window = QMainWindow()
        self.manual_window.setWindowTitle("Akiba - User Manual")
        self.manual_window.setMinimumSize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.manual_window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create QTextBrowser with markdown support
        self.manual_browser = QTextBrowser()
        # Convert markdown to rich text (QTextBrowser has limited markdown support, but basic formatting works)
        self.manual_browser.setMarkdown(markdown_content)
        self.manual_browser.setFontFamily("Segoe UI")
        self.manual_browser.setFontPointSize(10)
        layout.addWidget(self.manual_browser)
        
        # Show the window
        self.manual_window.show()
    def notify(self, claim_type: ClaimType, players: str, move: str) -> None:
        """Send a desktop notification depending on the OS."""
        # Check if notifications are enabled in controller settings
        if not getattr(self.controller, 'notifications_enabled', True):
            return

        if self.notification is None:
            return

        if platform.system() == "Darwin":
            from src.notifications.mac import Notification
            if isinstance(self.notification, Notification):
                self.notification.clearNotifications()
                self.notification.notify(claim_type.value, players, move)

        elif platform.system() == "Windows":
            try:
                newToast = ToastImageAndText2()
                newToast.SetHeadline(str(claim_type))
                newToast.SetBody(f"{players}\n{move}")
                newToast.AddImage(ToastDisplayImage.fromPath(resource_path("notification_icon.png")))
                newToast.SetDuration(ToastDuration("short"))
                if hasattr(self.notification, 'show_toast'):
                    self.notification.show_toast(newToast)
            except Exception:
                # Fallback to simple text notification
                try:
                    from windows_toasts import ToastText1
                    toast = ToastText1()
                    toast.SetHeadline(str(claim_type))
                    toast.SetText1(f"{players}\n{move}")
                    if hasattr(self.notification, 'show_toast'):
                        self.notification.show_toast(toast)
                except Exception:
                    pass

