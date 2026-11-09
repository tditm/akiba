"""
SPI Analyzer Service

Provides on-demand fair-play analysis using Stockfish engine.
Updated to support split player analysis with Elo-adjusted risk thresholds.
Includes Sigmoidal Precision Index (SPI) score calculation.
"""

import re
import math
import tempfile
import os
import sys
import chess
import chess.engine
from typing import Optional, Tuple, List, Callable

# Windows: Import CREATE_NO_WINDOW for hiding console windows
if sys.platform == "win32":
    from subprocess import CREATE_NO_WINDOW
else:
    CREATE_NO_WINDOW = None

from src.services.stockfish_wrapper import StockfishWrapper
from src.models.spi_results import SPIResults, PlayerAnalysis


class SPIService:
    """
    Service for performing on-demand SPI (Sigmoidal Precision Index / Fair-Play) analysis.
    
    Analyzes chess games using Stockfish engine to detect potential cheating by
    measuring move accuracy and anomaly patterns. Supports split analysis for
    White and Black players with Elo-adjusted risk thresholds.
    """
    
    # Constants for WAR score calculation (simplified, no time factor)
    WAR_SCORE_BEST_MOVE = 0.3  # Fixed score for best engine move
    
    # Base thresholds for Elo = 1500
    BASE_ELO = 1500
    THRESHOLD_ADJUSTMENT_PER_ELO = 0.02  # +0.02% per Elo point
    BASE_HIGH_T1_THRESHOLD = 85.0
    BASE_MEDIUM_T1_THRESHOLD = 75.0
    WAP_HIGH_THRESHOLD = 0.15
    
    def __init__(self, engine_path: str, depth: int = 12):
        """
        Initialize the SPI analyzer service.
        
        Args:
            engine_path: Path to Stockfish executable
            depth: Analysis depth (default: 12)
        """
        self.engine_path = engine_path
        self.depth = depth
        self.progress_callback: Optional[Callable[[str], None]] = None
    
    def _log(self, message: str):
        """Log a progress message via callback if available."""
        if self.progress_callback:
            try:
                self.progress_callback(message)
            except Exception:
                pass  # Ignore callback errors
    
    def analyze_game_from_object(self, game: chess.pgn.Game) -> SPIResults:
        """
        Analyze a game object directly without requiring a file.
        
        Args:
            game: PGN game object
            
        Returns:
            SPIResults with analysis data
        """
        # Save to temp PGN for consistency with analysis logic
        temp_path = self._save_to_temp_pgn(game)
        try:
            return self.analyze_game(temp_path)
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def _save_to_temp_pgn(self, game: chess.pgn.Game) -> str:
        """Save a game object to a temporary PGN file."""
        fd, path = tempfile.mkstemp(suffix='.pgn', text=True)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(str(game))
        except Exception:
            os.close(fd)
            raise
        return path
    
    def analyze_game(self, pgn_path: str) -> SPIResults:
        """
        Analyze a game from a PGN file.
        
        Args:
            pgn_path: Path to PGN file
            
        Returns:
            SPIResults with complete analysis data
        """
        # Read the game
        with open(pgn_path, encoding="utf-8") as f:
            game = chess.pgn.read_game(f)
        
        if game is None:
            raise ValueError("No valid game found in PGN file")
        
        # Extract headers
        white = game.headers.get("White", "Unknown")
        black = game.headers.get("Black", "Unknown")
        event = game.headers.get("Event", "Unknown")
        site = game.headers.get("Site", "Unknown")
        date = game.headers.get("Date", "???? ???? ????")
        round_ = game.headers.get("Round", "?")
        result = game.headers.get("Result", "*")
        
        # Extract Elo ratings (may be missing)
        white_elo = self._extract_elo(game.headers.get("WhiteElo"))
        black_elo = self._extract_elo(game.headers.get("BlackElo"))
        
        # Start engine analysis
        engine = StockfishWrapper(self.engine_path)
        
        try:
            board = game.board()
            
            stats = {
                chess.WHITE: {"moves_analyzed": 0, "top_1_hits": 0,
                              "top_2_hits": 0, "total_br_score": 0.0, "total_cpl": 0},
                chess.BLACK: {"moves_analyzed": 0, "top_1_hits": 0,
                              "top_2_hits": 0, "total_br_score": 0.0, "total_cpl": 0}
            }
            
            node = game
            while node.variations:
                next_node = node.variation(0)
                move = next_node.move
                color = board.turn
                move_number = board.fullmove_number
                
                # Skip deep opening (move < 11) and late endgames (fewer than 6 pieces)
                if move_number >= 11 and bin(board.occupied).count("1") > 6:
                    # Log progress
                    self._log(f"Analyzing move {move_number}...")
                    
                    # Analyze position with multipv=3 to get top 3 moves
                    analysis = self._analyze_position(engine, board, color, move_number)
                    
                    if analysis is None:
                        board.push(move)
                        node = next_node
                        continue
                    
                    evals = analysis["evals"]  # List of (pv, score_cp) tuples
                    
                    # Pad if necessary
                    while len(evals) < 3:
                        evals.append((chess.Move.null(), evals[-1][1] if evals else 0))
                    
                    best_move = evals[0][0]
                    second_best_move = evals[1][0]
                    
                    # Find score of the played move
                    played_move_score = self._get_played_move_score(evals, move)
                    
                    # If not found in top 3, analyze opponent's position to estimate
                    if played_move_score is None:
                        board.push(move)
                        opp_analysis = self._analyze_position(engine, board, board.turn, move_number)
                        if opp_analysis:
                            played_move_score = -opp_analysis["evals"][0][1]
                        else:
                            played_move_score = evals[2][1]  # Use worst of top 3 as fallback
                        board.pop()
                    
                    delta_e = max(0, evals[0][1] - played_move_score)
                    
                    # Check if move matches best/top-2
                    is_top_1 = (move == best_move)
                    is_top_2 = (move == best_move or move == second_best_move)
                    
                    if is_top_1:
                        stats[color]["top_1_hits"] += 1
                    if is_top_2:
                        stats[color]["top_2_hits"] += 1
                    
                    # Calculate BR (Blunder Resistance) score using new formula
                    br = self._calculate_br_score(delta_e, is_top_1)
                    
                    # Track stats for specific player
                    stats[color]["moves_analyzed"] += 1
                    stats[color]["total_cpl"] += delta_e
                    stats[color]["total_br_score"] += br
                    
                board.push(move)
                node = next_node
            
            # Generate independent reports for each player
            white_analysis = self._generate_player_analysis(
                stats[chess.WHITE], white_elo or self.BASE_ELO
            )
            black_analysis = self._generate_player_analysis(
                stats[chess.BLACK], black_elo or self.BASE_ELO
            )
            
            return SPIResults(
                white_player=white,
                black_player=black,
                event=event,
                site=site,
                date=date,
                round_=round_,
                result=result,
                white_elo=white_elo,
                black_elo=black_elo,
                white_analysis=white_analysis,
                black_analysis=black_analysis
            )
            
        finally:
            engine.quit()
    
    def _extract_elo(self, elo_str: Optional[str]) -> Optional[int]:
        """
        Extract Elo rating from PGN header string.
        
        Args:
            elo_str: String like "1500" or None
            
        Returns:
            Integer Elo rating or None if invalid/missing
        """
        if not elo_str:
            return None
        try:
            elo = int(str(elo_str))
            return elo if elo > 0 else None
        except (ValueError, TypeError):
            return None
    
    def _analyze_position(self, engine: StockfishWrapper, board: chess.Board,
                          color: chess.Color, move_number: int = 0) -> Optional[dict]:
        """
        Analyze a position and extract top 3 moves with scores.
        
        Args:
            engine: Stockfish wrapper instance
            board: Current board position
            color: Color to evaluate from
            
        Returns:
            Dict with 'evals' list of (move, score_cp) tuples, or None on error
        """
        # Windows: Use CREATE_NO_WINDOW to hide console popup
        if sys.platform == "win32" and CREATE_NO_WINDOW is not None:
            import subprocess
            temp_engine = chess.engine.SimpleEngine.popen_uci(
                self.engine_path,
                **{"creationflags": subprocess.CREATE_NO_WINDOW}
            )
        else:
            temp_engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        
        try:
            temp_engine.configure({"Threads": 1, "Hash": 16})
            result = temp_engine.analyse(
                board,
                chess.engine.Limit(depth=20, time=2.0),
                multipv=3
            )
            
            evals = []
            for entry in result:
                score = entry["score"].pov(color)
                cp = score.score(mate_score=10000)
                pv = entry.get("pv", [])
                if pv:
                    evals.append((pv[0], cp))
                else:
                    evals.append((chess.Move.null(), cp))
            
            return {"evals": evals}
            
        except Exception as e:
            self._log(f"Analysis error at move {move_number}: {e}")
            return None
            
        finally:
            try:
                temp_engine.quit()
            except Exception:
                pass
    
    def _get_played_move_score(self, evals: list, move: chess.Move) -> Optional[int]:
        """
        Find the score of a specific move in the evaluation list.
        
        Args:
            evals: List of (move, score_cp) tuples
            move: The move to find
            
        Returns:
            Score in centipawns or None if not found
        """
        for mv, cp in evals:
            if mv == move:
                return cp
        return None
    
    def _calculate_br_score(self, delta_e: int, is_best_move: bool) -> float:
        """
        Calculate Blunder Resistance (BR) score for a move.
        
        BR measures resistance to blunders on a scale of 0% to 100%.
        
        - Best move: 100% (move_br_score = 1.0)
        - Not best move: max(0.0, 1.0 - delta_e/40.0)
          - delta_e = 10 cp -> score = 75%
          - delta_e >= 40 cp -> score = 0%
        
        Args:
            delta_e: Error margin (best - played score in centipawns)
            is_best_move: Whether the move matched engine's best choice
            
        Returns:
            BR score (1.0 = perfect, 0.0 = blunder)
        """
        if is_best_move:
            return 1.0  # Perfect move = 100% resistance
        else:
            # Resistance decreases with larger errors
            # delta_e of 40 cp or more = complete blunder (0%)
            return max(0.0, 1.0 - (delta_e / 40.0))
    
    def _calculate_risk_level_with_br(self, t1: float, br: float, elo_rating: int, spi_score: float = 50.0) -> Tuple[str, str]:
        """
        Determine risk level with Elo-adjusted thresholds using Blunder Resistance (BR) and SPI Score.
        
        Risk is triggered by EITHER T1/BR conditions OR SPI conditions.
        
        Base thresholds (for Elo = 1500):
        - HIGH: (T1 > 85% AND BR > 90%) OR SPI > 70
        - MEDIUM: T1 > 75% OR SPI > 60
        - LOW: Neither condition met
        
        Adjustment: +0.02% threshold per Elo point above/below 1500 (for T1 only)
        
        Args:
            t1: Top 1 Match Rate percentage
            br: Blunder Resistance score (0-100%)
            elo_rating: Player's Elo rating
            spi_score: Sigmoidal Precision Index score (50 = human norm)
            
        Returns:
            Tuple of (risk_level, recommendation)
        """
        elo_diff = elo_rating - self.BASE_ELO
        adjustment = elo_diff * self.THRESHOLD_ADJUSTMENT_PER_ELO
        
        adjusted_high_t1 = self.BASE_HIGH_T1_THRESHOLD + adjustment
        adjusted_medium_t1 = self.BASE_MEDIUM_T1_THRESHOLD + adjustment
        
        # Clamp thresholds to reasonable range
        adjusted_high_t1 = max(70.0, min(100.0, adjusted_high_t1))
        adjusted_medium_t1 = max(60.0, min(95.0, adjusted_medium_t1))
        
        # BR threshold for HIGH risk (high match rate + high blunder resistance)
        br_high_threshold = 90.0
        
        # SPI thresholds (independent of Elo)
        spi_high_threshold = 70.0
        spi_medium_threshold = 60.0
        
        # Check SPI conditions first (they can trigger risk independently)
        if spi_score > spi_high_threshold:
            return "HIGH", "Further review recommended"
        elif spi_score > spi_medium_threshold:
            return "MEDIUM", "Routine observation recommended"
        
        # Then check T1/BR conditions
        if t1 > adjusted_high_t1 and br > br_high_threshold:
            return "HIGH", "Further review recommended"
        elif t1 > adjusted_medium_t1:
            return "MEDIUM", "Routine observation recommended"
        else:
            return "LOW", None
    
    def _calculate_sigmoidal_precision_index(self, t1_rate: float, apl_score: float, moves_analyzed: int, player_elo: int = 1500) -> float:
        """
        Calculate Sigmoidal Precision Index (SPI) score based on T1, APL, and player Elo.
        
        Maps T1 (Match Rate) and APL (Average Point Loss) to a sigmoidal precision scale.
        The midpoint shifts based on player Elo, so calculated SPI is normalized
        (50 = norm for EVERY Elo level).
        
        Args:
            t1_rate: Top 1 Match Rate percentage
            apl_score: Average Point Loss
            moves_analyzed: Number of moves analyzed
            player_elo: Player's Elo rating (default: 1500)
            
        Returns:
            SPI score (50 = human norm for this Elo, > 70 = suspicious)
        """
        if moves_analyzed < 5:
            return 50.0  # Too small sample, return pure norm
        
        # 1. Raw performance index in this game
        base_index = t1_rate - (apl_score * 1.5)
        
        # 2. DYNAMIC MIDPOINT (Key change - Elo consideration)
        # Stronger players (e.g., 2200) naturally achieve higher base_index.
        # Weaker players (e.g., 1200) have lower expectations.
        # We shift the curve inflection point by 0.015 per Elo point from base 1500.
        elo_diff = player_elo - 1500
        midpoint = 45.0 + (elo_diff * 0.015)
        
        # 3. Sigmoidal scaling around dynamic reference point
        steepness = 0.12
        roi = 50.0 + (25.0 / (1.0 + math.exp(-steepness * (base_index - midpoint))))
        
        # 4. Safety for inhuman extremes (APL near zero, like 4.4)
        # If result drastically detaches from norm even for a grandmaster:
        if apl_score < 6.0 and t1_rate > 88.0:
            roi = max(roi, 73.0 + (t1_rate - 88.0))
        
        return round(roi, 1)
    
    def _generate_player_analysis(self, player_stats: dict, elo_rating: int) -> PlayerAnalysis:
        """
        Generate PlayerAnalysis object from statistics.
        
        Args:
            player_stats: Dictionary with moves_analyzed, top_1_hits, etc.
            elo_rating: Player's Elo rating for threshold adjustment
            
        Returns:
            PlayerAnalysis object with calculated metrics and risk level
        """
        moves = player_stats["moves_analyzed"]
        
        # Calculate metrics
        t1_rate = (player_stats["top_1_hits"] / moves * 100) if moves > 0 else 0.0
        # BR (Blunder Resistance) as percentage (0-100%)
        br = (player_stats["total_br_score"] / moves * 100) if moves > 0 else 0.0
        # APL in points (not centipawns) - divide by 100
        apl = (player_stats["total_cpl"] / moves / 100) if moves > 0 else 0.0
        
        # Calculate Sigmoidal Precision Index score with Elo normalization
        spi_score = self._calculate_sigmoidal_precision_index(t1_rate, apl, moves, elo_rating)
        
        # Determine risk level with Elo adjustment (using BR and SPI)
        risk_level, recommendation = self._calculate_risk_level_with_br(t1_rate, br, elo_rating, spi_score)
        
        return PlayerAnalysis(
            risk_level=risk_level,
            recommendation=recommendation,
            metrics={
                "t1_rate": round(t1_rate, 1),
                "br_score": round(br, 1),
                "apl": round(apl, 3),
                "moves_analyzed": moves,
                "top_1_hits": player_stats["top_1_hits"],
                "top_2_hits": player_stats["top_2_hits"]
            },
            spi_score=spi_score
        )


# Legacy alias for backward compatibility - use SPIService instead.
ROIService = SPIService
