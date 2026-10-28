from typing import List, Any, Dict
import re

from src.reminders.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class FlagFallChecker(BaseChecker):
    """
    Checker for flag fall reminders.
    
    Monitors games to detect when a player's flag has fallen (time expired).
    This is typically indicated in PGN comments or by clock time reaching 0.
    """

    def __init__(self) -> None:
        super().__init__()
        self.shown_reminders: set = set()

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

    def extract_clock_from_node(self, node: Any) -> str | None:
        """Extract clock time from a PGN node comment."""
        if not node or not hasattr(node, 'comment') or not node.comment:
            return None

        match = re.search(r"\[%clk\s+(\d{1,2}:\d{2}:\d{2})\]", node.comment)
        if match:
            return match.group(1)
        return None

    def check(self, game: Any, claims_model: Any, **kwargs) -> List[ClaimEntry]:
        """Check a single game for flag fall."""
        if not self.enabled:
            return []

        entries = []
        gid = claims_model.controller.make_game_id(game)
        
        # Check for flag fall indicators in PGN comments
        for node in game.mainline():
            if hasattr(node, 'comment') and node.comment:
                comment = node.comment.lower()
                
                # Look for flag fall indicators
                if any(indicator in comment for indicator in ['flag', 'time expired', 'out of time']):
                    reminder_key = f"{gid}:flagfall"
                    
                    if reminder_key not in self.shown_reminders:
                        self.shown_reminders.add(reminder_key)
                        
                        board_number = claims_model.get_board_number(game)
                        
                        entry = ClaimEntry(
                            type=ClaimType.FLAG_FALL_REMINDER,
                            board_number=board_number,
                            players=get_players(game),
                            move="Flag fall detected",
                            game_index=0,
                            move_counter=len(list(game.mainline_moves())) // 2,
                            start_move_counter=0,
                            comment=f"Flag fall indicated in PGN: {node.comment}",
                            game_id=gid,
                        )
                        entries.append(entry)
                        break

        return entries

    def check_batch(self, games: List[Any], claims_model: Any, **kwargs) -> tuple:
        """
        Check multiple games for flag falls.
        
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
