"""
Mismatched Result Checker Module

Detects discrepancies between declared game results and Stockfish engine evaluation.
Flags games where the recorded result doesn't match the final position evaluation.
Uses background workers to prevent UI freeze during analysis.
"""

from typing import List, Any, Set, Optional
import chess
import chess.pgn

from src.reminders.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class MismatchedResultChecker(BaseChecker):
    """
    Checker for mismatched game results.
    
    This checker compares the declared game result (1-0, 0-1, 1/2-1/2) with
    the Stockfish engine evaluation of the final position. If there's a significant
    discrepancy (e.g., +3.0 for white but result is 0-1), it flags the game as
    having a possible incorrect result.
    
    Uses background EngineWorker threads to prevent UI freeze during analysis.
    
    Attributes:
        threshold: Evaluation threshold for flagging mismatches (default: 3.0 pawns)
        engine_path: Path to Stockfish executable
        shown_reminders: Set of already shown reminder keys
    """

    def __init__(self, engine_path: str = "engine/stockfish.exe", threshold: float = 3.0) -> None:
        """
        Initialize the mismatched result checker.
        
        Args:
            engine_path: Path to stockfish.exe
            threshold: Evaluation difference threshold in pawn units (default: 3.0)
                       Games where evaluation differs from result by more than this
                       will be flagged.
        """
        super().__init__()
        self.threshold = threshold
        self.engine_path = engine_path
        self.shown_reminders: Set[str] = set()
        self._workers: List[Any] = []  # Track running workers

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

    def _parse_result(self, result: str) -> int:
        """
        Parse PGN result string to numeric value.
        
        Args:
            result: Result string ("1-0", "0-1", "1/2-1/2", "*")
        
        Returns:
            int: 1 for white win, -1 for black win, 0 for draw, None for unknown
        """
        result_map = {
            "1-0": 1,      # White wins
            "0-1": -1,     # Black wins
            "1/2-1/2": 0,  # Draw
            "*": None      # Unknown/incomplete
        }
        return result_map.get(result)

    def _evaluate_result_match(self, engine_score: float, declared_result: int) -> bool:
        """
        Check if engine evaluation matches the declared result.
        
        Args:
            engine_score: Evaluation score from Stockfish (positive = white advantage)
            declared_result: Parsed result (1=white wins, -1=black wins, 0=draw)
        
        Returns:
            bool: True if result is consistent with evaluation, False otherwise
        """
        if declared_result is None:
            return True  # Unknown result, can't verify
        
        # White won but engine favors black significantly
        if declared_result == 1 and engine_score < -self.threshold:
            return False
        
        # Black won but engine favors white significantly
        if declared_result == -1 and engine_score > self.threshold:
            return False
        
        # Draw but one side has significant advantage
        if declared_result == 0 and abs(engine_score) > self.threshold:
            return False
        
        return True

    def _create_entry_from_score(
        self,
        game: Any,
        claims_model: Any,
        engine_score: float,
        parsed_result: int,
        result: str,
        board: chess.Board
    ) -> Optional[ClaimEntry]:
        """Create a ClaimEntry if the score indicates a mismatch."""
        if not self._evaluate_result_match(engine_score, parsed_result):
            gid = self.make_game_id(game)
            reminder_key = f"{gid}:mismatchedresult"
            
            if reminder_key not in self.shown_reminders:
                self.shown_reminders.add(reminder_key)
                
                board_number = claims_model.get_board_number(game)
                
                # Get last move in SAN format (same as Sofia rule checker)
                moves_list = list(board.move_stack)
                if moves_list:
                    ply_count = len(moves_list)
                    full_move_count = ply_count // 2
                    
                    # Replay board to get position before last move
                    temp_board = chess.Board()
                    for move in moves_list[:-1]:
                        temp_board.push(move)
                    
                    last_san = temp_board.san(moves_list[-1])
                    
                    # Format move number with ellipsis for black's move
                    if ply_count % 2 == 0:
                        move_num_str = f"{full_move_count}...{last_san}"
                    else:
                        move_num_str = f"{full_move_count}.{last_san}"
                else:
                    move_num_str = ""
                
                # Determine mismatch type and message
                if parsed_result == 1 and engine_score < -self.threshold:
                    mismatch_type = "White won but position favors Black"
                elif parsed_result == -1 and engine_score > self.threshold:
                    mismatch_type = "Black won but position favors White"
                else:  # Draw with significant advantage
                    if engine_score > self.threshold:
                        mismatch_type = "Draw declared but position favors White"
                    else:
                        mismatch_type = "Draw declared but position favors Black"
                
                return ClaimEntry(
                    type=ClaimType.MISMATCHED_RESULT,
                    board_number=board_number,
                    players=get_players(game),
                    move=f"{move_num_str} ({result})" if move_num_str else f"Result: {result}",
                    game_index=0,
                    move_counter=len(moves_list) if moves_list else 0,
                    start_move_counter=0,
                    comment=(
                        f"{mismatch_type}. "
                        f"Engine evaluation: {engine_score:+.2f}"
                    ),
                    game_id=gid,
                    extra_data={
                        "declared_result": result,
                        "engine_evaluation": engine_score,
                        "threshold": self.threshold,
                    }
                )
        return None

    def check(self, game: Any, claims_model: Any, **kwargs) -> List[ClaimEntry]:
        """
        Check a single game for result mismatch (synchronous version).
        
        Note: For async checking, use check_batch() with EngineWorker.
        
        Args:
            game: A chess.pgn.Game object
            claims_model: The Claims model instance
            **kwargs: Additional configuration including 'engine_score'
        
        Returns:
            List of ClaimEntry objects for mismatches found
        """
        if not self.enabled:
            return []

        entries = []
        
        # Get declared result from game headers
        result = game.headers.get("Result", "*")
        parsed_result = self._parse_result(result)
        
        # Skip if result is unknown
        if parsed_result is None:
            return []
        
        # Get final position FEN
        board = chess.Board()
        for move in game.mainline_moves():
            try:
                board.push(move)
            except (ValueError, chess.InvalidMoveError):
                break  # Stop at illegal move
        
        # Check if engine score was provided (from async worker)
        engine_score = kwargs.get('engine_score')
        
        if engine_score is not None:
            # Use provided score from async worker
            entry = self._create_entry_from_score(game, claims_model, engine_score, parsed_result, result, board)
            if entry:
                entries.append(entry)
        else:
            # Synchronous evaluation (fallback - use with caution as it blocks UI)
            try:
                from src.models.workers import EngineWorker
                # For sync mode, we still need to evaluate
                from src.services.stockfish_wrapper import StockfishWrapper
                final_fen = board.fen()
                
                with StockfishWrapper(self.engine_path) as engine:
                    engine_score = engine.get_position_evaluation(final_fen, time_limit=0.2)
                    
                entry = self._create_entry_from_score(game, claims_model, engine_score, parsed_result, result, board)
                if entry:
                    entries.append(entry)
            except Exception as e:
                # Log error but don't crash
                pass
        
        return entries

    def check_batch(self, games: List[Any], claims_model: Any, **kwargs) -> tuple:
        """
        Check multiple games for result mismatches.
        
        Note: This checker now uses async EngineWorker via Scan worker instead of batch processing.
        Returns empty list to avoid duplicate analysis.
        
        Args:
            games: List of chess.pgn.Game objects
            claims_model: The Claims model instance
        
        Returns:
            Tuple of (empty list, unchanged shown_reminders set)
        """
        if not self.enabled:
            return [], self.shown_reminders

        # Async analysis is handled by Scan worker - no batch processing here
        return [], self.shown_reminders

    def set_threshold(self, threshold: float) -> None:
        """
        Set the evaluation threshold for flagging mismatches.
        
        Args:
            threshold: New threshold in pawn units (e.g., 3.0 means flag if 
                      evaluation differs by more than 3 pawns from result)
        """
        if threshold > 0:
            self.threshold = threshold

    def close(self) -> None:
        """Release engine resources."""
        if self._engine is not None:
            self._engine.quit()
            self._engine = None
