"""
SPI Worker Thread

Background worker for on-demand SPI analysis to prevent UI freeze.
"""

import os
from PyQt6.QtCore import QThread, pyqtSignal
import chess.pgn

from src.services.spi_analyzer import SPIService
from src.models.spi_results import SPIResults


class SPIWorker(QThread):
    """
    Worker thread for on-demand SPI (Fair-Play) analysis.
    
    Runs analysis in background to prevent UI freeze during engine evaluation.
    Emits signals when analysis completes or an error occurs.
    
    Signals:
        analysis_complete: Emitted with SPIResults when analysis finishes
        error_occurred: Emitted with error message on failure
        progress_update: Emitted with status string during analysis
    """
    
    # Signal emits SPIResults object when analysis is complete
    analysis_complete = pyqtSignal(object)
    
    # Signal emits error message string when analysis fails
    error_occurred = pyqtSignal(str)
    
    # Signal emits progress/status messages during analysis
    progress_update = pyqtSignal(str)
    
    def __init__(self, engine_path: str, game: chess.pgn.Game):
        """
        Initialize the SPI worker.
        
        Args:
            engine_path: Path to Stockfish executable
            game: PGN game object to analyze
        """
        super().__init__()
        self.engine_path = engine_path
        self.game = game
        self.daemon = True
    
    def run(self):
        """
        Run analysis in background thread.
        Creates SPIService, analyzes the game, and emits results or error.
        """
        
        try:
            # Emit start message
            self.progress_update.emit("Starting Fair-Play Analysis...")
            
            # Create service with default depth of 12
            service = SPIService(self.engine_path, depth=12)
            service.progress_callback = self.progress_update.emit
            
            # Perform analysis - this may take several seconds for long games
            self.progress_update.emit("Loading game data...")
            results = service.analyze_game_from_object(self.game)
            
            # Emit success signal with results
            self.progress_update.emit("Analysis complete!")
            self.analysis_complete.emit(results)
            
        except Exception as e:
            # Emit error signal with exception message
            import traceback
            error_detail = f"{str(e)}\n\n{traceback.format_exc()}"
            self.error_occurred.emit(error_detail)


# Legacy alias for backward compatibility - use SPIWorker instead.
ROIWorker = SPIWorker
