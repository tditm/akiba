from typing import List, Any, Dict
import re

from src.reminders.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class TimeControlChecker(BaseChecker):
    """
    Checker for time control reminders.
    
    Triggers when a game reaches a certain number of moves, reminding arbiters
    to check if players have completed their time control requirements.
    """

    def __init__(self) -> None:
        super().__init__()
        self.default_threshold = 40

    def get_move_count(self, game: Any) -> int:
        """Get the number of full moves in a game."""
        return len(list(game.mainline_moves())) // 2

    def check(self, game: Any, claims_model: Any, threshold: int = None, **kwargs) -> List[ClaimEntry]:
        """Check a single game for time control reminder."""
        if not self.enabled:
            return []

        threshold = threshold or self.default_threshold
        entries = []

        move_count = self.get_move_count(game)

        if move_count >= threshold:
            board_number = claims_model.get_board_number(game)
            gid = claims_model.controller.make_game_id(game)

            entry = ClaimEntry(
                type=ClaimType.TIMECONTROL_REMINDER,
                board_number=board_number,
                players=get_players(game),
                move=f"{threshold} move",
                game_index=0,
                move_counter=move_count,
                start_move_counter=0,
                game_id=gid,
            )
            entries.append(entry)

        return entries

    def check_batch(self, games: List[Any], claims_model: Any, threshold: int = None,
                    fired_dict: Dict[int, bool] = None, **kwargs) -> tuple:
        """
        Check multiple games for time control reminders.
        
        Args:
            games: List of chess.pgn.Game objects
            claims_model: The Claims model instance
            threshold: Move count threshold (default: 40)
            fired_dict: Dict tracking which game indices already fired
        
        Returns:
            Tuple of (list of ClaimEntry, updated fired_dict)
        """
        if not self.enabled:
            return [], fired_dict or {}

        threshold = threshold or self.default_threshold
        entries = []
        fired_dict = fired_dict or {}

        for idx, game in enumerate(games, start=1):
            move_count = self.get_move_count(game)
            already = fired_dict.get(idx, False)

            if not already and move_count >= threshold:
                fired_dict[idx] = True

                board_number = claims_model.get_board_number(game)
                gid = claims_model.controller.make_game_id(game)

                entry = ClaimEntry(
                    type=ClaimType.TIMECONTROL_REMINDER,
                    board_number=board_number,
                    players=get_players(game),
                    move=f"{threshold} move",
                    game_index=idx - 1,
                    move_counter=move_count,
                    start_move_counter=0,
                    game_id=gid,
                )
                entries.append(entry)

        return entries, fired_dict
