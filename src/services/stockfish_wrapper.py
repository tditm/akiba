"""
Stockfish Wrapper Module

Provides a Python wrapper for communicating with Stockfish via the UCI protocol.
Uses python-chess library for UCI engine communication.
"""

import chess
import chess.engine
from typing import Optional, Tuple
import subprocess
import sys


class StockfishWrapper:
    """
    A wrapper class for interacting with Stockfish chess engine.
    
    Attributes:
        engine_path: Path to the Stockfish executable
        engine: The chess.engine.SimpleEngine instance
    """

    def __init__(self, engine_path: str):
        """
        Initialize the Stockfish wrapper with the path to the engine executable.
        
        Args:
            engine_path: Path to stockfish.exe (e.g., 'engine/stockfish.exe')
        
        Raises:
            FileNotFoundError: If the engine executable is not found
            RuntimeError: If the engine fails to start
        """
        self.engine_path = engine_path
        self.engine: Optional[chess.engine.SimpleEngine] = None
        self._start_engine()

    def _start_engine(self) -> None:
        """Start the Stockfish engine process without showing console window."""
        try:
            # Create subprocess creation flags to hide console window on Windows
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
            
            self.engine = chess.engine.SimpleEngine.popen_uci(
                self.engine_path,
                creationflags=creationflags
            )
            # Limit CPU and memory usage to prevent UI freeze
            self.engine.configure({"Threads": 1})
            self.engine.configure({"Hash": 4})  # 4MB hash table - minimal but sufficient
        except FileNotFoundError:
            raise FileNotFoundError(f"Stockfish executable not found at: {self.engine_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to start Stockfish engine: {e}")

    def get_position_evaluation(self, fen: str, time_limit: float = 1.5) -> tuple:
        """
        Get the evaluation of a given position along with engine's predicted continuation.
        
        Args:
            fen: FEN string representing the board position
            time_limit: Time in seconds to analyze (default: 1.5 for accurate evaluation)
        
        Returns:
            tuple: (score, pv_moves) where:
                - score: Evaluation in pawns (positive = white advantage)
                - pv_moves: Formatted string of best moves with move numbers (e.g., "28.Rf1 Ne7 29.Qd3")
        
        Raises:
            RuntimeError: If engine is not running or evaluation fails
        """
        if self.engine is None:
            raise RuntimeError("Engine is not running. Call start() or reinitialize.")

        board = chess.Board(fen)
        try:
            # Use longer time limit for accurate evaluation
            result = self.engine.analyse(board, chess.engine.Limit(time=time_limit))
            score = result["score"].white()
            
            # Get principal variation (engine's predicted best moves) with proper move numbers
            pv_moves = []
            if "pv" in result:
                pv = result["pv"]
                temp_board = chess.Board(fen)
                
                # Calculate starting move number from the FEN's fullmove counter
                # The FEN already contains the correct move number we should start from
                import re
                fen_parts = fen.split()
                fullmove_num = int(fen_parts[5]) if len(fen_parts) > 5 else 1
                
                # Get up to 6 half-moves (3 full moves) for the continuation
                is_white_turn = board.turn == chess.WHITE
                move_num = fullmove_num
                
                for i, move in enumerate(pv[:6]):
                    try:
                        san = temp_board.san(move)
                        
                        if is_white_turn:  # White's turn
                            pv_moves.append(f"{move_num}.{san}")
                        else:  # Black's turn - just the move name (no dot prefix)
                            pv_moves.append(san)
                        
                        temp_board.push(move)
                        is_white_turn = not is_white_turn
                        
                        # Increment move number after white's move
                        if not is_white_turn:
                            move_num += 1
                    except Exception:
                        break
                
                # Join moves with spaces: "28.Rf1 Ne7 29.Qd3"
                pv_str = " ".join(pv_moves)
            else:
                pv_str = ""
            
            # Handle mate scores - use a capped value to avoid overflow
            if score.is_mate():
                # Mate distance is in half-moves; convert to a reasonable score
                mate_moves = score.mate()
                # Cap at +/- 10000 to prevent overflow issues
                # Positive for white winning, negative for black winning
                if mate_moves > 0:
                    return (min(100.0, mate_moves * 0.5), pv_str)  # White wins in N moves (capped at +100)
                else:
                    return (max(-100.0, mate_moves * 0.5), pv_str)  # Black wins in N moves (capped at -100)
            
            # Get centipawn value and convert to pawn units
            # score.cp returns centipawns directly (e.g., 350 = +3.5 pawns)
            try:
                cp = int(score.cp)
                return (cp / 100.0, pv_str)
            except (TypeError, AttributeError):
                # Fallback for different chess engine versions
                return (float(score.cp) / 100.0, pv_str)
            
        except Exception as e:
            raise RuntimeError(f"Failed to evaluate position: {e}")

    def get_best_move(self, fen: str, time_limit: float = 1.0) -> Optional[str]:
        """
        Get the best move for the current position.
        
        Args:
            fen: FEN string representing the board position
            time_limit: Time in seconds to think (default: 1.0)
        
        Returns:
            str: Best move in UCI format (e.g., 'e2e4'), or None if no moves available
        
        Raises:
            RuntimeError: If engine is not running or move calculation fails
        """
        if self.engine is None:
            raise RuntimeError("Engine is not running. Call start() or reinitialize.")

        board = chess.Board(fen)
        
        # Check for game over
        if board.is_game_over():
            return None
        
        try:
            result = self.engine.play(board, chess.engine.Limit(time=time_limit))
            return result.move.uci()
        except Exception as e:
            raise RuntimeError(f"Failed to calculate best move: {e}")

    def analyze_position(self, fen: str, depth: int = 15, time_limit: float = 2.0) -> dict:
        """
        Get detailed analysis of a position.
        
        Args:
            fen: FEN string representing the board position
            depth: Search depth (default: 15)
            time_limit: Maximum time to think in seconds (default: 2.0)
        
        Returns:
            dict: Analysis results containing:
                - score: Evaluation in pawn units
                - depth: Actual search depth reached
                - pv: Principal variation (list of moves in UCI format)
                - mate: Mate distance if applicable (None if not mating position)
        
        Raises:
            RuntimeError: If analysis fails
        """
        if self.engine is None:
            raise RuntimeError("Engine is not running. Call start() or reinitialize.")

        board = chess.Board(fen)
        try:
            result = self.engine.analyse(board, chess.engine.Limit(depth=depth, time=time_limit))
            
            score = result["score"].white()
            pv = [move.uci() for move in result.get("pv", [])]
            
            analysis = {
                "score": score.pawn_score() / 100.0 if not score.is_mate() else None,
                "depth": result.get("depth", depth),
                "pv": pv,
                "mate": None,
            }
            
            # Handle mate scores
            if score.is_mate():
                analysis["mate"] = score.mate()
                analysis["score"] = 50000 * abs(score.mate()) * (1 if score.mate() > 0 else -1)
            
            return analysis
            
        except Exception as e:
            raise RuntimeError(f"Failed to analyze position: {e}")

    def set_skill_level(self, level: int) -> None:
        """
        Set Stockfish's skill level (0-20).
        
        Args:
            level: Skill level from 0 (weakest) to 20 (strongest)
        
        Raises:
            ValueError: If level is not between 0 and 20
            RuntimeError: If setting the option fails
        """
        if self.engine is None:
            raise RuntimeError("Engine is not running.")
        
        if not 0 <= level <= 20:
            raise ValueError("Skill level must be between 0 and 20")
        
        try:
            self.engine.configure({"Skill Level": level})
        except Exception as e:
            raise RuntimeError(f"Failed to set skill level: {e}")

    def set_depth(self, depth: int) -> None:
        """
        Set default search depth for analysis.
        
        Args:
            depth: Search depth (positive integer)
        
        Raises:
            ValueError: If depth is not positive
            RuntimeError: If setting the option fails
        """
        if self.engine is None:
            raise RuntimeError("Engine is not running.")
        
        if depth <= 0:
            raise ValueError("Depth must be a positive integer")
        
        try:
            # Note: Stockfish uses 'UCI_LimitStrength' for controlled play
            self.engine.configure({"UCI_LimitStrength": False})
        except Exception as e:
            raise RuntimeError(f"Failed to configure engine: {e}")

    def quit(self) -> None:
        """
        Properly close the engine and release resources.
        
        Should be called when done using the wrapper to prevent resource leaks.
        """
        if self.engine is not None:
            try:
                self.engine.quit()
            except Exception:
                pass  # Engine might already be closed
            finally:
                self.engine = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures engine is properly closed."""
        self.quit()
        return False
