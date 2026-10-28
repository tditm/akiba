from typing import List, Any, Set

from src.reminders.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class TwoFoldChecker(BaseChecker):
    """
    Checker for 2-fold repetition warnings.
    
    This is a WARNING that alerts arbiters when a position has repeated twice,
    so they can monitor if it might become a 3-fold claim soon.
    
    Note: This is NOT an actual claim - just a warning to pay attention.
    """

    def __init__(self) -> None:
        super().__init__()
        self.seen_positions: Set[tuple] = set()
        self.shown_reminders: Set[str] = set()  # Track shown reminders by game_id

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
        """Check a single game for 2-fold repetition."""
        if not self.enabled:
            return []

        entries = []
        board = game.board()
        gid = claims_model.controller.make_game_id(game)
        
        move_counter = 0

        for move in game.mainline_moves():
            san_move = board.san(move)
            board.push(move)
            move_counter += 1
            
            # Use position-only FEN (first 4 fields) for repetition tracking
            # This matches chess library's is_repetition() logic
            fen_parts = board.fen().split()
            position_fen = ' '.join(fen_parts[:4])  # Ignore halfmove and fullmove counters

            # Check for 2-fold repetition using chess library's method
            # is_repetition(count=2) returns True if position has repeated at least twice
            # We only trigger when count == 2 (first time it becomes 2-fold, not 3-fold+)
            if board.is_repetition(count=2):
                # Create a unique key to prevent duplicates (same as threefold_checker)
                key = (ClaimType.TWO_FOLD_WARNING, gid, move_counter, position_fen)

                if key not in self.seen_positions:
                    self.seen_positions.add(key)

                    board_number = claims_model.get_board_number(game)
                    
                    # Format move as SAN with move number (e.g., "34.Nd4")
                    from math import ceil
                    move_num = ceil(move_counter / 2)
                    san_move_formatted = f"{move_num}...{san_move}" if move_counter % 2 == 0 else f"{move_num}.{san_move}"
                    
                    entry = ClaimEntry(
                        type=ClaimType.TWO_FOLD_WARNING,
                        board_number=board_number,
                        players=get_players(game),
                        move=san_move_formatted,
                        game_index=0,
                        move_counter=move_counter,
                        start_move_counter=0,
                        comment=f"Position repeated twice - watch for 3-fold",
                        game_id=gid,
                    )
                    entries.append(entry)

        return entries

    def check_batch(self, games: List[Any], claims_model: Any, **kwargs) -> tuple:
        """
        Check multiple games for 2-fold repetitions.
        
        Args:
            games: List of chess.pgn.Game objects
            claims_model: The Claims model instance
        
        Returns:
            Tuple of (list of ClaimEntry, updated seen_positions set)
        """
        if not self.enabled:
            return [], self.seen_positions

        entries = []

        for idx, game in enumerate(games):
            game_entries = self.check(game, claims_model, game_index=idx)
            # Update game_index to match batch context
            for entry in game_entries:
                entry_dict = entry.__dict__.copy()
                entry_dict['game_index'] = idx
                entries.append(ClaimEntry(**entry_dict))

        return entries, self.seen_positions
    
    def reset(self) -> None:
        """Reset the seen positions set."""
        self.seen_positions.clear()
    
    def run_all_reminders(self, games: List[Any], claims_model: Any, **kwargs):
        """Run all reminders and return entries + shown_reminders."""
        entries, _ = self.check_batch(games, claims_model, **kwargs)
        return entries, self.shown_reminders
