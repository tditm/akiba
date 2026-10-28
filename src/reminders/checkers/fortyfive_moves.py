from typing import List, Any, Dict, Set

from src.reminders.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class PossibleFiftyMoveChecker(BaseChecker):
    """
    Checker for possible 50-move rule alerts (45-move warning).
    
    This checker monitors games that have reached 45 moves without a capture
    or pawn move, alerting arbiters that a 50-move claim may be imminent.
    
    This is a PROACTIVE alert at move 45, not the actual 50-move rule trigger.
    """

    def __init__(self) -> None:
        super().__init__()
        self.default_threshold = 45
        self.shown_reminders: Set[str] = set()

    def make_game_id(self, game: Any) -> str:
        """Generate stable game identifier from PGN headers."""
        return "|".join([
            game.headers.get("Event", ""),
            game.headers.get("Site", ""),
            game.headers.get("Date", ""),
            game.headers.get("Round", ""),
            game.headers.get("White", ""),
            game.headers.get("Black", ""),
        ])

    def check(self, game: Any, claims_model: Any, threshold: int = None, **kwargs) -> List[ClaimEntry]:
        """Check a single game for possible 50-move rule (45-move warning)."""
        if not self.enabled:
            return []

        entries = []
        board = game.board()
        gid = claims_model.controller.make_game_id(game)
        threshold = threshold or self.default_threshold

        last_irreversible_move = 0
        move_counter = 0

        for move in game.mainline_moves():
            # Check if this is an irreversible move (capture or pawn move)
            if board.is_capture(move) or board.piece_at(move.from_square).piece_type == 1:
                last_irreversible_move = move_counter + 1

            board.push(move)
            move_counter += 1

            # Alert when we reach threshold moves without irreversible move
            if (move_counter - last_irreversible_move) >= threshold and last_irreversible_move > 0:
                reminder_key = f"{gid}:45move:{last_irreversible_move}"
                if reminder_key not in self.shown_reminders:
                    self.shown_reminders.add(reminder_key)

                    board_number = claims_model.get_board_number(game)
                    
                    entry = ClaimEntry(
                        type=ClaimType.FIFTY_MOVES,  # Using FIFTY_MOVES type but as warning
                        board_number=board_number,
                        players=get_players(game),
                        move=f"45 moves without capture/pawn",
                        game_index=0,
                        move_counter=move_counter,
                        start_move_counter=last_irreversible_move,
                        comment=f"First counting move: {last_irreversible_move}",
                        game_id=gid,
                    )
                    entries.append(entry)
                    break  # Only alert once per game

        return entries

    def check_batch(self, games: List[Any], claims_model: Any, threshold: int = None, **kwargs) -> tuple:
        """
        Check multiple games for possible 50-move rule.
        
        Args:
            games: List of chess.pgn.Game objects
            claims_model: The Claims model instance
            threshold: Move threshold (default: 45)
        
        Returns:
            Tuple of (list of ClaimEntry, updated shown_reminders set)
        """
        if not self.enabled:
            return [], self.shown_reminders

        entries = []
        threshold = threshold or self.default_threshold

        for idx, game in enumerate(games):
            game_entries = self.check(game, claims_model, threshold)
            # Update game_index to match batch context
            for entry in game_entries:
                entry_dict = entry.__dict__.copy()
                entry_dict['game_index'] = idx
                entries.append(ClaimEntry(**entry_dict))

        return entries, self.shown_reminders
