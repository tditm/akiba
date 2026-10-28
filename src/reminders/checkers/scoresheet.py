from typing import List, Any, Dict

from src.reminders.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class ScoresheetChecker(BaseChecker):
    """
    Checker for scoresheet reminders.
    
    Triggers when a game exceeds a certain number of moves without a result.
    Used to remind arbiters to check if players are recording moves properly.
    """

    def __init__(self) -> None:
        super().__init__()
        self.default_threshold = 55

    def get_move_count(self, game: Any) -> int:
        """Get the number of full moves in a game."""
        return len(list(game.mainline_moves())) // 2

    def check(self, game: Any, claims_model: Any, threshold: int = None, **kwargs) -> List[ClaimEntry]:
        """Check a single game for scoresheet reminder."""
        if not self.enabled:
            return []

        threshold = threshold or self.default_threshold
        entries = []

        move_count = self.get_move_count(game)

        if move_count >= threshold:
            board_number = claims_model.get_board_number(game)
            gid = claims_model.controller.make_game_id(game)

            entry = ClaimEntry(
                type=ClaimType.SCORESHEET_REMINDER,
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
        Check multiple games for scoresheet reminders.
        
        Args:
            games: List of chess.pgn.Game objects
            claims_model: The Claims model instance
            threshold: Move count threshold (default: 55)
            fired_dict: Dict tracking which game indices already fired a reminder
        
        Returns:
            Tuple of (list of ClaimEntry, updated fired_dict)
        """
        if not self.enabled:
            return [], fired_dict or {}

        threshold = threshold or self.default_threshold
        entries = []
        fired_dict = fired_dict or {}

        for idx, game in enumerate(games):
            move_count = self.get_move_count(game)
            already = fired_dict.get(idx, False)

            if already:
                continue

            if move_count >= threshold:
                fired_dict[idx] = True

                board_number = claims_model.get_board_number(game)
                gid = claims_model.controller.make_game_id(game)

                entry = ClaimEntry(
                    type=ClaimType.SCORESHEET_REMINDER,
                    board_number=board_number,
                    players=get_players(game),
                    move=f"{threshold} move",
                    game_index=idx,
                    move_counter=move_count,
                    start_move_counter=0,
                    game_id=gid,
                )
                entries.append(entry)

        return entries, fired_dict
