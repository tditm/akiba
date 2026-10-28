from typing import List, Any, Set
from math import ceil

from src.claims.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class DeadPositionChecker(BaseChecker):
    """
    Checker for dead position claims.
    
    Detects when a game reaches a dead position (neither side has sufficient 
    winning material). This is an automatic draw under FIDE rules.
    """

    def __init__(self) -> None:
        super().__init__()
        self.enabled = True  # Always enabled for claims
        self.seen_positions: Set[tuple] = set()  # Track seen dead position positions

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

    @staticmethod
    def get_printable_move(move_counter: int, san_move: str) -> str:
        """Formats the move number for display (e.g. '4.Qxf7#' or '12...Nf6')."""
        move_num = ceil(move_counter / 2)
        return f"{move_num}...{san_move}" if move_counter % 2 == 0 else f"{move_num}.{san_move}"

    def check(self, game: Any, claims_model: Any, **kwargs) -> List[ClaimEntry]:
        """Check a single game for dead position."""
        if not self.enabled:
            return []

        entries = []
        
        board = game.board()
        game_index = kwargs.get('game_index', 0)
        gid = self.make_game_id(game)
        players = get_players(game)
        board_number = self.get_board_number(game)
        
        move_counter = 0
        
        for move in game.mainline_moves():
            san_move = board.san(move)
            board.push(move)
            move_counter += 1
            
            # Check for dead position after each move
            if board.is_insufficient_material():
                # Use FEN to track unique dead position positions and avoid duplicates
                fen = board.fen()
                key = (ClaimType.DEAD_POSITION_CLAIM, gid, move_counter, fen)
                
                if key not in self.seen_positions:
                    self.seen_positions.add(key)
                    
                    printable_move = self.get_printable_move(move_counter, san_move)
                    
                    entry = ClaimEntry(
                        type=ClaimType.DEAD_POSITION_CLAIM,
                        board_number=board_number,
                        players=players,
                        move=printable_move,
                        game_index=game_index,
                        move_counter=move_counter,  # Use full move counter (plies), not divided by 2
                        start_move_counter=0,
                        comment=f"Dead position detected",
                        game_id=gid,
                    )
                    entries.append(entry)
                break  # Stop at first dead position (game is over)

        return entries

    def check_batch(self, games: List[Any], claims_model: Any, **kwargs) -> tuple:
        """
        Check multiple games for dead positions.
        
        Args:
            games: List of chess.pgn.Game objects
            claims_model: The Claims model instance
        
        Returns:
            Tuple of (list of ClaimEntry, empty dict)
        """
        if not self.enabled:
            return [], {}

        entries = []

        for idx, game in enumerate(games):
            # Pass game_index to check() so make_game_id can use it for uniqueness
            # Remove game_index from kwargs to avoid duplicate argument error
            check_kwargs = {k: v for k, v in kwargs.items() if k != 'game_index'}
            game_entries = self.check(game, claims_model, game_index=idx, **check_kwargs)
            
            # Update game_index to match batch context if needed
            for entry in game_entries:
                entry_dict = entry.__dict__.copy()
                entry_dict['game_index'] = idx
                entries.append(ClaimEntry(**entry_dict))

        return entries, {}

    def reset(self) -> None:
        """Reset the seen positions set."""
        self.seen_positions.clear()