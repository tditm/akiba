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

    def get_ply_count(self, game: Any) -> int:
        """Get the number of plies (half-moves) in a game."""
        return len(list(game.mainline_moves()))

    def check(self, game: Any, claims_model: Any, threshold: int = None, **kwargs) -> List[ClaimEntry]:
        """Check a single game for time control reminder."""
        if not self.enabled:
            return []

        threshold = threshold or self.default_threshold
        entries = []

        moves_list = list(game.mainline_moves())
        ply_count = len(moves_list)  # Total plies in the game
        full_move_count = ply_count // 2  # Full moves for display/comparison

        if full_move_count >= threshold:
            # Check if game ended at exactly the threshold move with a legitimate result
            # If so, no need to remind arbiter about time control (game is over)
            result = game.headers.get("Result", "")
            if result in ("1-0", "0-1", "1/2-1/2", "½-½") and full_move_count == threshold:
                return entries  # Game ended at threshold, skip reminder

            board_number = claims_model.get_board_number(game)
            gid = claims_model.controller.make_game_id(game)

            # Get the move at threshold position (e.g., move 40) for display and navigation
            threshold_ply_index = threshold * 2 - 1
            
            if threshold_ply_index < len(moves_list):
                board = game.board()
                for i in range(threshold_ply_index):
                    board.push(moves_list[i])
                threshold_san = board.san(moves_list[threshold_ply_index])
                from math import ceil
                move_num = ceil((threshold_ply_index + 1) / 2)
                if (threshold_ply_index + 1) % 2 == 0:
                    printable_move = f"{move_num}...{threshold_san}"
                else:
                    printable_move = f"{move_num}.{threshold_san}"
            else:
                printable_move = ""

            entry = ClaimEntry(
                type=ClaimType.TIMECONTROL_REMINDER,
                board_number=board_number,
                players=get_players(game),
                move=f"{printable_move} ({threshold} moves)" if printable_move else f"{threshold} moves",
                game_index=0,
                move_counter=threshold_ply_index + 1,  # Store ply index + 1 for correct Board Viewer navigation
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
            moves_list = list(game.mainline_moves())
            ply_count = len(moves_list)  # Total plies in the game
            full_move_count = ply_count // 2  # Full moves for display/comparison
            already = fired_dict.get(idx, False)

            if not already and full_move_count >= threshold:
                # Check if game ended at exactly the threshold move with a legitimate result
                result = game.headers.get("Result", "")
                if result in ("1-0", "0-1", "1/2-1/2", "½-½") and full_move_count == threshold:
                    continue  # Game ended at threshold, skip reminder

                fired_dict[idx] = True

                board_number = claims_model.get_board_number(game)
                gid = claims_model.controller.make_game_id(game)

                # Get the move at threshold position (e.g., move 40) for display and navigation
                threshold_ply_index = threshold * 2 - 1
                
                if threshold_ply_index < len(moves_list):
                    board = game.board()
                    for i in range(threshold_ply_index):
                        board.push(moves_list[i])
                    threshold_san = board.san(moves_list[threshold_ply_index])
                    from math import ceil
                    move_num = ceil((threshold_ply_index + 1) / 2)
                    if (threshold_ply_index + 1) % 2 == 0:
                        printable_move = f"{move_num}...{threshold_san}"
                    else:
                        printable_move = f"{move_num}.{threshold_san}"
                else:
                    printable_move = ""

                entry = ClaimEntry(
                    type=ClaimType.TIMECONTROL_REMINDER,
                    board_number=board_number,
                    players=get_players(game),
                    move=f"{printable_move} ({threshold} moves)" if printable_move else f"{threshold} moves",
                    game_index=idx - 1,
                    move_counter=threshold_ply_index + 1,  # Store ply index + 1 for correct Board Viewer navigation
                    start_move_counter=0,
                    game_id=gid,
                )
                entries.append(entry)

        return entries, fired_dict
