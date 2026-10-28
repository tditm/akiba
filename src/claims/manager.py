from typing import List, Any, Set

from src.models.events import ClaimEntry
from src.claims.checkers import (
    ThreeFoldChecker,
    FiveFoldChecker,
    FiftyMovesChecker,
    SeventyFiveMovesChecker,
    StalemateChecker,
    CheckmateChecker,
    DeadPositionChecker,
)


class ClaimsManager:
    """Orchestrates all claim checking for chess games."""

    def __init__(self) -> None:
        self.threefold_checker = ThreeFoldChecker()
        self.fivefold_checker = FiveFoldChecker()
        self.fifty_moves_checker = FiftyMovesChecker()
        self.seventyfive_moves_checker = SeventyFiveMovesChecker()
        self.stalemate_checker = StalemateChecker()
        self.checkmate_checker = CheckmateChecker()
        self.dead_position_checker = DeadPositionChecker()

        # Track games that should not be rechecked (after 5-fold or 75-move)
        self.dont_check: Set[str] = set()

    def run_all_claims(self, games: List[Any], claims_model: Any, game_index: int = 0) -> tuple:
        """Run all claim checkers and return collected entries."""
        all_entries: List[ClaimEntry] = []

        # Run stalemate checker (always runs for claims)
        entries_stalemate, _ = self.stalemate_checker.check_batch(games, claims_model, game_index=game_index)
        all_entries.extend(entries_stalemate)

        # Run checkmate checker (always runs for claims)
        entries_checkmate, _ = self.checkmate_checker.check_batch(games, claims_model, game_index=game_index)
        all_entries.extend(entries_checkmate)

        # Run dead position checker (always runs for claims)
        entries_dead_position, _ = self.dead_position_checker.check_batch(games, claims_model, game_index=game_index)
        all_entries.extend(entries_dead_position)

        # Run 5-fold checker (stops game on detection)
        entries_5fold, _ = self.fivefold_checker.check_batch(games, claims_model, game_index=game_index)
        for entry in entries_5fold:
            self.dont_check.add(entry.players)
        all_entries.extend(entries_5fold)

        # Run 75-move checker (stops game on detection)  
        entries_75move, _ = self.seventyfive_moves_checker.check_batch(games, claims_model, game_index=game_index)
        for entry in entries_75move:
            self.dont_check.add(entry.players)
        all_entries.extend(entries_75move)

        # Run 50-move checker (does not stop game)
        entries_50move, _ = self.fifty_moves_checker.check_batch(games, claims_model, game_index=game_index)
        all_entries.extend(entries_50move)

        # Run 3-fold checker (does not stop game)
        entries_3fold, two_fold_shown = self.threefold_checker.check_batch(games, claims_model, game_index=game_index)
        all_entries.extend(entries_3fold)

        return all_entries, self.dont_check, two_fold_shown

    def reset_checkers(self) -> None:
        """Reset all checker states for a fresh scan."""
        self.threefold_checker.reset()
        self.fivefold_checker.seen_positions.clear()
        self.fifty_moves_checker.seen_positions.clear()
        self.seventyfive_moves_checker.seen_positions.clear()
        # Stalemate, checkmate and dead position checkers - reset their seen positions too
        if hasattr(self.stalemate_checker, 'seen_positions'):
            self.stalemate_checker.reset()
        if hasattr(self.checkmate_checker, 'seen_positions'):
            self.checkmate_checker.reset()
        if hasattr(self.dead_position_checker, 'seen_positions'):
            self.dead_position_checker.reset()
        self.dont_check.clear()

    def should_skip_game(self, players: str) -> bool:
        """Check if this game should be skipped (already has terminal claim)."""
        return players in self.dont_check

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


