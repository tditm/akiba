"""
SPI Progress Dialog

Dialog showing progress and status during SPI analysis.
"""


from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextBrowser
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class SPIProgressDialog(QDialog):
    """
    Dialog displaying progress and status during SPI analysis.
    
    Shows:
    - Progress bar (indeterminate while analyzing)
    - Status messages (starting, analyzing moves, completing)
    - Cancel button (optional)
    """
    
    def __init__(self, parent=None):
        """
        Initialize the progress dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Fair-Play Analysis in Progress...")
        self.setMinimumWidth(400)
        # Non-modal dialog - allows app interaction during analysis
        self.setModal(False)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self._build_ui()
    
    def _build_ui(self):
        """Build the dialog user interface."""
        layout = QVBoxLayout(self)
        
        # Title with icon
        title_label = QLabel("Analyzing Game for Fair-Play Compliance")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Progress bar (indeterminate)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #1496e8;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #1496e8;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Status messages browser
        self.status_browser = QTextBrowser()
        self.status_browser.setFixedHeight(150)
        self.status_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.status_browser)
        
        # Cancel button (optional - analysis may not be cancellable)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setMinimumWidth(80)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def log_message(self, message: str):
        """
        Add a status message to the browser.
        
        Args:
            message: Message to display
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_browser.append(f"[{timestamp}] {message}")
    
    def set_status(self, status: str):
        """
        Update the progress bar status text.
        
        Args:
            status: Status message to show
        """
        self.progress_bar.setFormat(f"{status}...")
    
    def start_analysis(self):
        """Log that analysis has started."""
        self.log_message("Starting Fair-Play Analysis...")
        self.set_status("Initializing engine")
    
    def log_move_analyzed(self, move_num: int, total_moves: int):
        """
        Log progress for a move being analyzed.
        
        Args:
            move_num: Current move number
            total_moves: Total moves to analyze
        """
        self.log_message(f"Analyzing move {move_num}...")
    
    def log_metric(self, metric_name: str, value: str):
        """
        Log a calculated metric.
        
        Args:
            metric_name: Name of the metric
            value: Value to display
        """
        self.log_message(f"{metric_name}: {value}")
    
    def analysis_complete(self):
        """Log that analysis has completed."""
        self.log_message("Analysis complete!")
        self.set_status("Complete")
    
    def log_error(self, error_msg: str):
        """
        Log an error message.
        
        Args:
            error_msg: Error message to display
        """
        self.log_message(f"ERROR: {error_msg}")
