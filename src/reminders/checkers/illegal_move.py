from typing import List, Any, Dict, Set
import chess

from src.reminders.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class IllegalMoveChecker(BaseChecker):
    """
    Checker for illegal move detection in PGN files.
    
    This checker monitors games to detect when an illegal move was made.
    An illegal move is any move that doesn't follow the rules of chess
    (e.g., moving a piece in an invalid way, making an impossible move).
    
    When detected, this serves as a reminder for arbiters to review the game.
    """

    def __init__(self) -> None:
        super().__init__()
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

    def check(self, game: Any, claims_model: Any, **kwargs) -> List[ClaimEntry]:
        """Check a single game for illegal moves."""
        if not self.enabled:
            return []

        entries = []
        board = chess.Board()
        gid = claims_model.controller.make_game_id(game)
        
        move_counter = 0
        first_illegal_move = None
        
        for move in game.mainline_moves():
            try:
                # Try to make the move - will raise exception if illegal
                board.push(move)
                move_counter += 1
            except (ValueError, chess.InvalidMoveError) as e:
                # Illegal move detected
                if first_illegal_move is None:
                    # At this point, move_counter = last VALID move number (was not incremented after failed push)
                    # The illegal move would have been move_counter + 1
                    last_valid_move = move_counter
                    
                    reminder_key = f"{gid}:illegalmove:{last_valid_move}"
                    
                    if reminder_key not in self.shown_reminders:
                        self.shown_reminders.add(reminder_key)
                        
                        board_number = claims_model.get_board_number(game)
                        san_move = board.san(move) if move else "unknown"
                        illegal_move_num = last_valid_move + 1
                        
                        entry = ClaimEntry(
                            type=ClaimType.ILLEGAL_MOVE,
                            board_number=board_number,
                            players=get_players(game),
                            move=f"Move {illegal_move_num}: {san_move}",
                            game_index=0,
                            move_counter=last_valid_move,  # Navigate to last valid position
                            start_move_counter=0,
                            comment=f"Illegal move detected: {str(e)}",
                            game_id=gid,
                        )
                        entries.append(entry)
                break  # Only report first illegal move per game

        return entries

    def check_batch(self, games: List[Any], claims_model: Any, **kwargs) -> tuple:
        """
        Check multiple games for illegal moves.
        
        Args:
            games: List of chess.pgn.Game objects
            claims_model: The Claims model instance
        
        Returns:
            Tuple of (list of ClaimEntry, updated shown_reminders set)
        """
        if not self.enabled:
            return [], self.shown_reminders

        entries = []

        for idx, game in enumerate(games):
            game_entries = self.check(game, claims_model)
            
            # Update game_index to match batch context
            for entry in game_entries:
                entry_dict = entry.__dict__.copy()
                entry_dict['game_index'] = idx
                entries.append(ClaimEntry(**entry_dict))

        return entries, self.shown_reminders