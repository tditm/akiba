from typing import List, Any
from chess.pgn import Game
from math import ceil

from src.claims.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class FiftyMovesChecker(BaseChecker):
    """
    Checker for 50-move rule claims.
    
    According to FIDE rules, a player may claim a draw if no capture has been made 
    and no pawn has been moved in the last 50 moves by each player. The comment 
    includes the move number of the last irreversible move.
    """

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def make_game_id(game, game_index: int = None) -> str:
        """Generate stable identifier from PGN headers only."""
        return "|".join([
            game.headers.get("Event", ""),
            game.headers.get("Site", ""),
            game.headers.get("Date", ""),
            game.headers.get("Round", ""),
            game.headers.get("White", ""),
            game.headers.get("Black", ""),
        ])

    def check(self, game: Any, claims_model: Any, **kwargs) -> List[ClaimEntry]:
        """Check a single game for 50-move rule."""
        if not self.enabled:
            return []

        entries = []
        board = game.board()
        game_index = kwargs.get('game_index')
        gid = self.make_game_id(game, None)  # Use header-based ID only
        players = get_players(game)
        board_number = self.get_board_number(game)

        move_counter = 0
        last_irreversible_move = 0

        for move in game.mainline_moves():
            # Detect irreversible moves BEFORE pushing
            if board.is_capture(move) or (board.piece_at(move.from_square) and 
                                          board.piece_at(move.from_square).piece_type == 1):
                last_irreversible_move = move_counter + 1

            san_move = board.san(move)
            board.push(move)
            move_counter += 1

            # Check for 50-move rule (claimable draw, not automatic)
            if board.is_fifty_moves():
                printable_move = self.get_printable_move(move_counter, san_move)
                comment = f"First counting move: {last_irreversible_move}"
                
                entry = ClaimEntry(
                    type=ClaimType.FIFTY_MOVES,
                    board_number=board_number,
                    players=players,
                    move=printable_move,
                    game_index=game_index,
                    move_counter=move_counter,
                    start_move_counter=last_irreversible_move,
                    comment=comment,
                    game_id=gid,
                )
                entries.append(entry)

        return entries

    def check_batch(self, games: List[Any], claims_model: Any, **kwargs) -> tuple:
        """Check multiple games for 50-move rule."""
        if not self.enabled:
            return [], {}

        entries = []

        for idx, game in enumerate(games):
            game_entries = self.check(game, claims_model, game_index=idx)
            # Update game_index to match batch context
            for entry in game_entries:
                entry_dict = entry.__dict__.copy()
                entry_dict['game_index'] = idx
                entries.append(ClaimEntry(**entry_dict))

        return entries, {}

    @staticmethod
    def get_printable_move(move_counter: int, san_move: str) -> str:
        """Formats the move number for display (e.g. '12.Nf3' or '12...Nf6')."""
        move_num = ceil(move_counter / 2)
        return f"{move_num}...{san_move}" if move_counter % 2 == 0 else f"{move_num}.{san_move}"


