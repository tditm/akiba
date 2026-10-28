from abc import ABC, abstractmethod
from typing import List, Any


class BaseChecker(ABC):
    """Abstract base class for all claim checkers."""

    def __init__(self) -> None:
        self.enabled = True

    @staticmethod
    def get_board_number(game: Any) -> str:
        """Get board number from game headers."""
        board = game.headers.get("Board")
        if board and board != "None":
            return board

        rnd = game.headers.get("Round")
        if rnd and rnd != "None":
            return rnd

        return "-"

    @abstractmethod
    def check(self, game: Any, claims_model: Any, **kwargs) -> List[Any]:
        """Check a single game for claims. Must be implemented by subclasses."""
        pass

    def check_batch(self, games: List[Any], claims_model: Any, **kwargs) -> tuple:
        """Check multiple games. Returns (entries, state_dict)."""
        if not self.enabled:
            return [], {}

        entries = []
        for idx, game in enumerate(games):
            # Pass game_index to check() so make_game_id can use it for uniqueness
            game_entries = self.check(game, claims_model, game_index=idx, **kwargs)
            entries.extend(game_entries)

        return entries, {}

