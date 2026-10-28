from typing import List, Any, Dict
import re

from src.reminders.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class LowTimeChecker(BaseChecker):
    """
    Checker for low time reminders.
    
    Triggers when a player has less than a specified amount of time remaining
    on their clock, alerting arbiters to monitor the game closely.
    """

    def __init__(self) -> None:
        super().__init__()
        self.default_threshold_seconds = 120  # 2 minutes

    def extract_clock_from_comment(self, node: Any) -> str | None:
        """Extract clock time from a PGN node comment."""
        if not node or not hasattr(node, 'comment') or not node.comment:
            return None
        
        match = re.search(r"\[%clk\s+(\d{1,2}:\d{2}:\d{2})\]", node.comment)
        if match:
            return match.group(1)
        return None

    def parse_clock(self, clock_str: str) -> int:
        """Convert clock string (HH:MM:SS) to total seconds."""
        parts = clock_str.split(":")
        if len(parts) != 3:
            return 0
        
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            return 0

    def get_lowest_clock(self, game: Any) -> tuple[int, str, int, str]:
        """
        Get the lowest clock time from both players in a game.
        
        Returns:
            Tuple of (lowest_seconds, player_side, move_counter, san_move) 
            where player_side is "White" or "Black"
        """
        board = game.board()
        lowest_time = float('inf')
        lowest_player = None
        lowest_move_counter = 0
        lowest_san_move = ""
        
        for node in game.mainline():
            clock_str = self.extract_clock_from_comment(node)
            
            # Push the move and get its SAN
            if hasattr(node, 'move') and node.move:
                san_move = board.san(node.move)
                board.push(node.move)
                
                if clock_str:
                    seconds = self.parse_clock(clock_str)
                    if seconds < lowest_time:
                        lowest_time = seconds
                        # Determine which player this was (even move counter = white's turn to play, odd = black)
                        move_counter = len(list(board.move_stack)) // 2
                        if len(list(board.move_stack)) % 2 == 0:
                            lowest_player = "White"
                        else:
                            lowest_player = "Black"
                        
                        # Calculate move number for display
                        from math import ceil
                        move_num = ceil(move_counter / 2)
                        san_move_formatted = f"{move_num}...{san_move}" if move_counter % 2 == 0 else f"{move_num}.{san_move}"
                        
                        lowest_move_counter = move_counter
                        lowest_san_move = san_move_formatted
        
        return lowest_time, lowest_player or "", lowest_move_counter, lowest_san_move

    def check(self, game: Any, claims_model: Any, threshold_seconds: int = None, **kwargs) -> List[ClaimEntry]:
        """Check a single game for low time reminder."""
        if not self.enabled:
            return []

        entries = []
        threshold = threshold_seconds or self.default_threshold_seconds

        lowest_time, player_side, move_counter, san_move_formatted = self.get_lowest_clock(game)

        if lowest_time <= threshold and lowest_time > 0:
            board_number = claims_model.get_board_number(game)
            gid = claims_model.controller.make_game_id(game)

            entry = ClaimEntry(
                type=ClaimType.LOW_TIME_REMINDER,
                board_number=board_number,
                players=get_players(game),
                move=f"{san_move_formatted} ({lowest_time}s left)",
                game_index=0,
                move_counter=move_counter,
                start_move_counter=0,
                comment=f"Lowest clock: {player_side} with {lowest_time} seconds",
                game_id=gid,
            )
            entries.append(entry)

        return entries

    def check_batch(self, games: List[Any], claims_model: Any, threshold_seconds: int = None,
                    fired_dict: Dict[int, bool] = None, **kwargs) -> tuple:
        """
        Check multiple games for low time reminders.
        
        Args:
            games: List of chess.pgn.Game objects
            claims_model: The Claims model instance
            threshold_seconds: Time threshold in seconds (default: 120)
            fired_dict: Dict tracking which game indices already fired
        
        Returns:
            Tuple of (list of ClaimEntry, updated fired_dict)
        """
        if not self.enabled:
            return [], fired_dict or {}

        entries = []
        fired_dict = fired_dict or {}
        threshold = threshold_seconds or self.default_threshold_seconds

        for idx, game in enumerate(games):
            already = fired_dict.get(idx, False)
            
            if already:
                continue

            game_entries = self.check(game, claims_model, threshold)
            
            if game_entries:
                fired_dict[idx] = True
                # Update game_index to match batch context
                for entry in game_entries:
                    entry_dict = entry.__dict__.copy()
                    entry_dict['game_index'] = idx
                    entries.append(ClaimEntry(**entry_dict))

        return entries, fired_dict
