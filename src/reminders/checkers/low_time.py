from typing import List, Any, Dict, Set
import re

from src.reminders.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class LowTimeChecker(BaseChecker):
    """
    Checker for low time reminders.
    
    Triggers when a player has less than a specified amount of time remaining
    on their clock, alerting arbiters to monitor the game closely.
    
    Logic:
    - Finds the FIRST move where a player's clock drops below threshold
    - Does NOT fire again for the same player unless clock increases by 600+ seconds (time control)
    - Displays the remaining time AFTER the indicated move
    
    Uses shown_reminders set to track unique reminders and prevent duplicates.
    Key format: "{game_id}:{player_side}" for first reminder,
                "{game_id}:{player_side}:tc:{move_count}" for time control resets.
    """

    def __init__(self) -> None:
        super().__init__()
        self.default_threshold_seconds = 120  # 2 minutes
        self.time_control_reset_threshold = 600  # 10 minutes - clock increase indicating time control
        self.shown_reminders: Set[str] = set()  # Track unique reminders to prevent duplicates

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

    def find_first_low_time(self, game: Any, threshold: int, gid: str) -> List[tuple]:
        """
        Find the first move where each player's clock drops below threshold.
        
        Logic:
        - Track when each player (White/Black) first goes below threshold using shown_reminders set
        - After firing, only fire again if clock increased by 600+ seconds (time control)
        - Returns list of tuples: (player_side, ply_count, san_move, remaining_seconds)
        
        Args:
            game: The chess game to check
            threshold: Time threshold in seconds
            gid: Game ID for tracking reminders
        
        Returns:
            List of reminders for this game (can be up to 2 - one per player, or more if time controls occur)
        """
        board = game.board()
        results = []
        
        # Track last fired time for each player (for time control detection)
        white_last_fired_time = 0
        black_last_fired_time = 0
        
        for node in game.mainline():
            clock_str = self.extract_clock_from_comment(node)
            
            # Push the move and get its SAN
            if hasattr(node, 'move') and node.move:
                san_move = board.san(node.move)
                board.push(node.move)
                
                if clock_str:
                    seconds = self.parse_clock(clock_str)
                    ply_count = len(list(board.move_stack))
                    
                    # Determine whose clock this is (the player who JUST moved)
                    if ply_count % 2 == 1:
                        # Odd ply count = White just moved, this is White's clock
                        player_side = "White"
                        last_fired_time = white_last_fired_time
                    else:
                        # Even ply count = Black just moved, this is Black's clock
                        player_side = "Black"
                        last_fired_time = black_last_fired_time
                    
                    # Check if we should fire a reminder
                    should_fire = False
                    reminder_key = f"{gid}:{player_side}"
                    
                    if reminder_key not in self.shown_reminders:
                        # First time below threshold for this player
                        if seconds < threshold:
                            should_fire = True
                    else:
                        # Already fired, check if clock reset (time control)
                        # Clock increased by 600+ seconds indicates time control
                        if seconds >= last_fired_time + self.time_control_reset_threshold:
                            # Reset allowed - can fire again if below threshold
                            if seconds < threshold:
                                should_fire = True
                    
                    if should_fire:
                        from math import ceil
                        move_num = ceil(ply_count / 2)
                        san_move_formatted = f"{move_num}...{san_move}" if ply_count % 2 == 0 else f"{move_num}.{san_move}"
                        
                        results.append((player_side, ply_count, san_move_formatted, seconds))
                        self.shown_reminders.add(reminder_key)
                        
                        # Update last fired time for this player
                        if player_side == "White":
                            white_last_fired_time = seconds
                        else:
                            black_last_fired_time = seconds
        
        return results

    def check(self, game: Any, claims_model: Any, threshold_seconds: int = None, **kwargs) -> List[ClaimEntry]:
        """Check a single game for low time reminder."""
        if not self.enabled:
            return []

        entries = []
        threshold = threshold_seconds or self.default_threshold_seconds

        board_number = claims_model.get_board_number(game)
        gid = claims_model.controller.make_game_id(game)

        reminders = self.find_first_low_time(game, threshold, gid)

        for player_side, ply_count, san_move_formatted, remaining_seconds in reminders:
            entry = ClaimEntry(
                type=ClaimType.LOW_TIME_REMINDER,
                board_number=board_number,
                players=get_players(game),
                move=f"{san_move_formatted} ({remaining_seconds}s left)",
                game_index=0,
                move_counter=ply_count,  # Store ply count for correct Board Viewer navigation
                start_move_counter=0,
                comment=f"Low time warning: {player_side} with {remaining_seconds} seconds",
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
            fired_dict: Dict tracking which game indices already fired (not used, kept for compatibility)
        
        Returns:
            Tuple of (list of ClaimEntry, updated shown_reminders set)
        """
        if not self.enabled:
            return [], self.shown_reminders

        entries = []
        threshold = threshold_seconds or self.default_threshold_seconds

        for idx, game in enumerate(games):
            game_entries = self.check(game, claims_model, threshold)
            
            # Update game_index to match batch context
            for entry in game_entries:
                entry_dict = entry.__dict__.copy()
                entry_dict['game_index'] = idx
                entries.append(ClaimEntry(**entry_dict))

        return entries, self.shown_reminders
