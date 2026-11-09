"""
SPI Results Dialog

Modal dialog for displaying Fair-Play SPI analysis results.
Updated to show split player analysis (White and Black separately).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from src.models.spi_results import SPIResults


class SPIDialog(QDialog):
    """
    Dialog displaying SPI (Fair-Play) analysis results.
    
    Shows:
    - Game header information
    - Separate analysis sections for White and Black players
    - Each section has independent metrics and risk level
    """
    
    def __init__(self, results: SPIResults, parent=None):
        """
        Initialize the SPI results dialog.
        
        Args:
            results: SPIResults object with analysis data
            parent: Parent widget
        """
        super().__init__(parent)
        self.results = results
        self.setWindowTitle("Fair-Play Analysis Results")
        self.setMinimumSize(800, 750)
        self._build_ui()
    
    def _build_ui(self):
        """Build the dialog user interface."""
        main_layout = QVBoxLayout(self)
        
        # Create scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        
        # === Game Header Section ===
        header_frame = self._create_header_section()
        layout.addWidget(header_frame)
        
        # === White Player Analysis Section ===
        white_frame = self._create_player_analysis_section(
            "White",
            self.results.white_player,
            self.results.white_elo,
            self.results.white_analysis
        )
        layout.addWidget(white_frame)
        
        # === Black Player Analysis Section ===
        black_frame = self._create_player_analysis_section(
            "Black",
            self.results.black_player,
            self.results.black_elo,
            self.results.black_analysis
        )
        layout.addWidget(black_frame)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # === Close Button ===
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setMinimumWidth(100)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        main_layout.addLayout(button_layout)
    
    def _create_header_section(self) -> QFrame:
        """Create the SPI header information section."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        layout = QVBoxLayout(frame)
        
        # Title
        title_label = QLabel("SPI (Sigmoidal Precision Index) — Beta Version")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #333; padding-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Disclaimer message
        disclaimer = (
            "<b>This tool is intended for arbiters and is currently in its scaling phase. "
            "The data below does not imply any rule violation. Drawing conclusions from a single game "
            "carries high statistical risk; therefore, system outputs, if any, should be treated solely as "
            "suggestions for further routine actions.</b>"
        )
        disclaimer_label = QLabel(disclaimer)
        disclaimer_label.setFont(QFont("Arial", 10))
        disclaimer_label.setStyleSheet("color: #666; line-height: 1.5;")
        disclaimer_label.setWordWrap(True)
        layout.addWidget(disclaimer_label)
        
        return frame
    
    def _create_player_analysis_section(self, color_name: str, player_name: str, 
                                         elo_rating: int | None, analysis) -> QFrame:
        """
        Create a player-specific analysis section.
        
        Args:
            color_name: "White" or "Black"
            player_name: Player's name
            elo_rating: Player's Elo rating (may be None)
            analysis: PlayerAnalysis object with metrics
            
        Returns:
            QFrame containing the player's analysis section
        """
        frame = QFrame()
        
        # Set background and border based on risk level
        risk_color = self._get_risk_color(analysis.risk_level)
        bg_color = self._get_bg_color(risk_color)
        
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
                padding: 10px;
                border: 2px solid {risk_color};
            }}
        """)
        
        layout = QVBoxLayout(frame)
        
        # Title with player name and Elo
        title_parts = [f"{color_name} Player Analysis - <b>{player_name}</b>"]
        if elo_rating is not None:
            title_parts.append(f"(Elo: {elo_rating})")
        title_label = QLabel("".join(title_parts))
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {risk_color}; padding-bottom: 5px;")
        layout.addWidget(title_label)
        
        # SPI badge (Sigmoidal Precision Index)
        spi_badge = QLabel(f"SPI (Sigmoidal Precision Index): {analysis.spi_score}")
        spi_badge.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        spi_badge.setStyleSheet(self._get_spi_stylesheet(analysis.spi_score))
        layout.addWidget(spi_badge)
        
        # Metrics grid with WZS, BR, APL
        metrics_layout = QHBoxLayout()
        
        # T1 column
        t1_layout = QVBoxLayout()
        t1_label = QLabel("Top 1 Match Rate:")
        t1_label.setStyleSheet("color: #555; font-size: 12px;")
        t1_value = QLabel(f"{analysis.t1_rate:.1f}%")
        t1_value.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        t1_value.setStyleSheet("color: #333;")
        t1_layout.addWidget(t1_label)
        t1_layout.addWidget(t1_value)
        metrics_layout.addLayout(t1_layout)
        
        metrics_layout.addSpacing(40)
        
        # BR (Blunder Resistance) column
        br_layout = QVBoxLayout()
        br_label = QLabel("Blunder Resistance (BR):")
        br_label.setStyleSheet("color: #555; font-size: 12px;")
        br_value = QLabel(f"{analysis.metrics.get('br_score', 0.0):.1f}%")
        br_value.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        br_value.setStyleSheet("color: #333;")
        br_layout.addWidget(br_label)
        br_layout.addWidget(br_value)
        metrics_layout.addLayout(br_layout)
        
        metrics_layout.addSpacing(40)
        
        # APL column
        apl_layout = QVBoxLayout()
        apl_label = QLabel("Average Point Loss (APL):")
        apl_label.setStyleSheet("color: #555; font-size: 12px;")
        apl_value = QLabel(f"{analysis.apl:.2f}")
        apl_value.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        apl_value.setStyleSheet("color: #333;")
        apl_layout.addWidget(apl_label)
        apl_layout.addWidget(apl_value)
        metrics_layout.addLayout(apl_layout)
        
        layout.addLayout(metrics_layout)
        
        # Additional stats
        stats_label = QLabel(
            f"Moves Analyzed: {analysis.moves_analyzed} | "
            f"Top 1 Hits: {analysis.top_1_hits} | "
            f"Top 2 Hits: {analysis.top_2_hits}"
        )
        stats_label.setStyleSheet("color: #666; font-size: 11px; padding-top: 8px;")
        layout.addWidget(stats_label)
        
        # Recommendation
        if analysis.recommendation:
            rec_label = QLabel(f"<b>Recommendation:</b> {analysis.recommendation}")
            rec_label.setStyleSheet("color: #333; font-size: 11px; padding-top: 5px;")
            layout.addWidget(rec_label)
        
        return frame
    
    def _get_risk_color(self, risk_level: str) -> str:
        """Get color hex code for risk level."""
        if risk_level == "HIGH":
            return "#f44336"  # Red
        elif risk_level == "MEDIUM":
            return "#ff9800"  # Orange
        else:
            return "#4caf50"  # Green
    
    def _get_bg_color(self, risk_color: str) -> str:
        """Get background color based on risk level (lighter version)."""
        if risk_color == "#f44336":
            return "#ffebee"  # Light red
        elif risk_color == "#ff9800":
            return "#fff3e0"  # Light orange
        else:
            return "#e8f5e9"  # Light green
    
    def _get_spi_stylesheet(self, spi_score: float) -> str:
        """Get stylesheet for SPI score badge."""
        if spi_score > 70:
            return "color: #ffffff; background-color: #f44336; padding: 4px 12px; border-radius: 4px;"
        elif spi_score > 60:
            return "color: #ffffff; background-color: #ff9800; padding: 4px 12px; border-radius: 4px;"
        else:
            return "color: #ffffff; background-color: #4caf50; padding: 4px 12px; border-radius: 4px;"

    def _get_risk_stylesheet(self, risk_level: str) -> str:
        """Get stylesheet for risk level badge."""
        if risk_level == "HIGH":
            return "color: #ffffff; background-color: #f44336; padding: 4px 12px; border-radius: 4px;"
        elif risk_level == "MEDIUM":
            return "color: #ffffff; background-color: #ff9800; padding: 4px 12px; border-radius: 4px;"
        else:
            return "color: #ffffff; background-color: #4caf50; padding: 4px 12px; border-radius: 4px;"


# Legacy alias for backward compatibility - use SPIDialog instead.
ROIDialog = SPIDialog
