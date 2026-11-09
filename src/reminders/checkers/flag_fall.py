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
    
    def normalize_clock_time(self, clock_time: str | None) -> str | None:
        """
        Normalize clock time to HH:MM:SS format with leading zeros.
        Handles formats like '0:00:00', '00:00:00', '1:23:45', etc.
        """
        if not clock_time:
            return None
        
        try:
            parts = clock_time.split(':')
            if len(parts) != 3:
                return None
            
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            
            # Return normalized format with leading zeros
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except (ValueError, IndexError):
            return None

    def check(self, game: Any, claims_model: Any, **kwargs) -> List[ClaimEntry]:
        """Check a single game for flag fall."""
        if not self.enabled:
            return []

        entries = []
        gid = claims_model.controller.make_game_id(game)
        
        # Check for flag fall indicators in PGN comments
        moves_list = list(game.mainline_moves())
        
        for idx, node in enumerate(game.mainline()):
            clock_time = self.extract_clock_from_node(node)
            
            # Flag fall triggered when clock reaches 0:00:00 (normalized format)
            normalized_time = self.normalize_clock_time(clock_time)
            if normalized_time == "00:00:00":
                reminder_key = f"{gid}:flagfall"
                
                if reminder_key not in self.shown_reminders:
                    self.shown_reminders.add(reminder_key)
                    
                    board_number = claims_model.get_board_number(game)
                    
                    # Get the move that led to flag fall (current node's move)
                    move_counter = (idx + 1)  # 1-based ply index
                    from math import ceil
                    move_num = ceil((idx + 1) / 2)
                    
                    if idx < len(moves_list):
                        board = game.board()
                        for i in range(idx):
                            board.push(moves_list[i])
                        san_move = board.san(moves_list[idx])
                        
                        # Format move with number (e.g., "40. e5" or "40...e5")
                        if (idx + 1) % 2 == 0:
                            printable_move = f"{move_num}...{san_move} ({clock_time})"
                        else:
                            printable_move = f"{move_num}.{san_move} ({clock_time})"
                    else:
                        printable_move = f"{move_num} ({clock_time})"
                    
                    entry = ClaimEntry(
                        type=ClaimType.FLAG_FALL_REMINDER,
                        board_number=board_number,
                        players=get_players(game),
                        move=printable_move,
                        game_index=0,
                        move_counter=move_counter,
                        start_move_counter=0,
                        comment=f"Flag fall: clock reached {clock_time}",
                        game_id=gid,
                    )
                    entries.append(entry)
                    break
            
            # Also check for text-based flag fall indicators (backward compatibility)
            if hasattr(node, 'comment') and node.comment:
                comment = node.comment.lower()
                
                # Look for flag fall indicators
                if any(indicator in comment for indicator in ['flag', 'time expired', 'out of time']):
                    reminder_key = f"{gid}:flagfall"
                    
                    if reminder_key not in self.shown_reminders:
                        self.shown_reminders.add(reminder_key)
                        
                        board_number = claims_model.get_board_number(game)
                        
                        # Get the move that led to flag fall (current node's move)
                        move_counter = (idx + 1)  # 1-based ply index
                        from math import ceil
                        move_num = ceil((idx + 1) / 2)
                        
                        if idx < len(moves_list):
                            board = game.board()
                            for i in range(idx):
                                board.push(moves_list[i])
                            san_move = board.san(moves_list[idx])
                            
                            # Format move with number (e.g., "40. e5" or "40...e5")
                            if (idx + 1) % 2 == 0:
                                printable_move = f"{move_num}...{san_move}"
                            else:
                                printable_move = f"{move_num}.{san_move}"
                        else:
                            printable_move = str(move_num)
                        
                        entry = ClaimEntry(
                            type=ClaimType.FLAG_FALL_REMINDER,
                            board_number=board_number,
                            players=get_players(game),
                            move=printable_move,
                            game_index=0,
                            move_counter=move_counter,
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
