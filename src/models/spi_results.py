"""
SPI Results Data Models

Data classes for storing and transmitting SPI (Sigmoidal Precision Index / Fair-Play) analysis results.
Updated to support split player analysis with Elo-adjusted risk thresholds.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlayerAnalysis:
    """Independent analysis results for a single player."""
    
    risk_level: str  # "LOW", "MEDIUM", or "HIGH"
    recommendation: str
    metrics: dict
    spi_score: float = 50.0  # Sigmoidal Precision Index score (default: human norm)
    
    # Convenience properties for direct access
    @property
    def t1_rate(self) -> float:
        """Top 1 Match Rate percentage."""
        return self.metrics.get("t1_rate", 0.0)
    
    @property
    def apl(self) -> float:
        """Average Point Loss (APL)."""
        return self.metrics.get("apl", 0.0)
    
    @property
    def moves_analyzed(self) -> int:
        """Number of moves analyzed for this player."""
        return self.metrics.get("moves_analyzed", 0)
    
    @property
    def top_1_hits(self) -> int:
        """Number of Top 1 engine match hits."""
        return self.metrics.get("top_1_hits", 0)
    
    @property
    def top_2_hits(self) -> int:
        """Number of Top 2 engine match hits."""
        return self.metrics.get("top_2_hits", 0)


@dataclass
class SPIResults:
    """Complete SPI analysis results for a chess game with split player analysis."""
    
    # Game headers
    white_player: str
    black_player: str
    event: str
    site: str
    date: str
    round_: str
    result: str
    
    # Elo ratings (may be None if not in PGN)
    white_elo: Optional[int] = None
    black_elo: Optional[int] = None
    
    # NEW: Independent analysis for each player
    white_analysis: PlayerAnalysis = None  # type: ignore
    black_analysis: PlayerAnalysis = None  # type: ignore
    
    # REMOVED: anomaly_moves field completely removed


# Legacy alias for backward compatibility - use SPIResults instead.
ROIResults = SPIResults
