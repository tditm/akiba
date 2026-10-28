from abc import ABC, abstractmethod
from typing import List, Any, Dict


class BaseChecker(ABC):
    """
    Abstract base class for all reminder/check claim checkers.
    
    Each checker implements a specific rule (e.g., 3-fold repetition, 50-move rule).
    This abstraction allows for easy extension and testing of individual rules.
    """

    def __init__(self) -> None:
        self.enabled = False

    @abstractmethod
    def check(self, game: Any, claims_model: Any, **kwargs) -> List[Any]:
        """
        Check a single game for the specific rule this checker handles.
        
        Args:
            game: A chess.pgn.Game object
            claims_model: The Claims model instance
            **kwargs: Additional configuration (thresholds, state dicts, etc.)
        
        Returns:
            List of ClaimEntry or ReminderEntry objects
        """
        pass

    @abstractmethod
    def check_batch(self, games: List[Any], claims_model: Any, **kwargs) -> tuple:
        """
        Check multiple games for the specific rule.
        
        Args:
            games: List of chess.pgn.Game objects
            claims_model: The Claims model instance
            **kwargs: Additional configuration
        
        Returns:
            Tuple of (list of entries, updated state dict)
        """
        pass
