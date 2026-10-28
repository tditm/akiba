from typing import List, Any, Dict

from src.reminders.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class SofiaRuleChecker(BaseChecker):
    """
    Checker for Sofia rule violations.
    
    The Sofia Rule (also known as the "Anti-Grand Draw Agreement") prohibits
    players from agreeing to a draw before move 30 (or another threshold).
    
    This checker monitors for early draw agreements that violate this rule.
    """

    def __init__(self) -> None:
        super().__init__()
        self.default_threshold = 30
        self.shown_reminders: set = set()

    def check(self, game: Any, claims_model: Any, threshold: int = None, **kwargs) -> List[ClaimEntry]:
        """Check a single game for Sofia rule violation."""
        if not self.enabled:
            return []

        entries = []
        threshold = threshold or self.default_threshold
        gid = claims_model.controller.make_game_id(game)

        # Check if game ended in draw before the threshold
        result = game.headers.get("Result", "")
        
        if result not in ("1/2-1/2", "½-½"):
            return entries  # Not a draw, skip
        
        move_count = len(list(game.mainline_moves())) // 2
        
        if move_count >= threshold:
            return entries  # Draw after allowed move count, skip

        # CRITICAL: Check if game ended via legitimate chess rules
        # If so, Sofia rule reminder should NOT appear
        board = game.board()
        
        # Replay the game to check for draw conditions at the end position
        for move in game.mainline_moves():
            board.push(move)
        
        # Check for automatic/legal draw reasons
        if self._is_legitimate_draw_end(board, game):
            return entries  # Game ended legitimately, no Sofia reminder needed

        # Only flag as Sofia violation if it's an early agreed draw
        reminder_key = f"{gid}:sofia:{move_count}"
        
        if reminder_key not in self.shown_reminders:
            self.shown_reminders.add(reminder_key)
            
            board_number = claims_model.controller.claims_manager.get_board_number(game)
            
            entry = ClaimEntry(
                type=ClaimType.SOFIA_RULE,
                board_number=board_number,
                players=get_players(game),
                move=f"Draw at move {move_count}",
                game_index=0,
                move_counter=move_count,
                start_move_counter=0,
                comment=f"Sofia rule violation: draw agreed before move {threshold}",
                game_id=gid,
            )
            entries.append(entry)

        return entries
    
    def _is_legitimate_draw_end(self, board: Any, game: Any) -> bool:
        """
        Check if the game ended via legitimate chess rules (not just agreement).
        
        Returns True if the position could end in draw by:
        - 3-fold repetition
        - 50-move rule  
        - Dead position (insufficient material)
        - Stalemate (pat)
        
        If any of these are true, Sofia rule reminder should NOT be shown.
        """
        # Check for stalemate (pat)
        if board.is_stalemate():
            return True
        
        # Check for insufficient material (dead position)
        if board.is_insufficient_material():
            return True
        
        # Check for 50-move rule
        if board.is_fifty_moves():
            return True
        
        # Check for 3-fold repetition
        if board.is_repetition(count=3):
            return True
        
        # Check PGN comments for explicit draw claim indicators
        for node in game.mainline():
            comment = getattr(node, 'comment', '') or ''
            # Look for FIDE rule claims in comments
            if any(keyword in comment.lower() for keyword in [
                '3-fold', 'threefold', 'repetition',
                '50-move', 'fifty move', 
                'dead position', 'insufficient material'
            ]):
                return True
        
        return False

    def check_batch(self, games: List[Any], claims_model: Any, threshold: int = None,
                    fired_dict: Dict[int, bool] = None, **kwargs) -> tuple:
        """
        Check multiple games for Sofia rule violations.
        
        Args:
            games: List of chess.pgn.Game objects
            claims_model: The Claims model instance
            threshold: Minimum move count before draw is allowed (default: 30)
            fired_dict: Dict tracking which game indices already fired
        
        Returns:
            Tuple of (list of ClaimEntry, updated fired_dict)
        """
        if not self.enabled:
            return [], fired_dict or {}

        entries = []
        fired_dict = fired_dict or {}
        threshold = threshold or self.default_threshold

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
