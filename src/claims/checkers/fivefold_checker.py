from typing import List, Any
from chess.pgn import Game

from src.claims.checkers.base import BaseChecker
from src.models.events import ClaimEntry, ClaimType, get_players


class FiveFoldChecker(BaseChecker):
    """
    Checker for 5-fold repetition claims (automatic draw).
    
    According to FIDE rules, the game is automatically drawn if the same position 
    has appeared five times consecutively. This is an actual claim that stops the game.
    """

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def make_game_id(game: Game) -> str:
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
        """Check a single game for 5-fold repetition."""
        if not self.enabled:
            return []

        entries = []
        board = game.board()
        game_index = kwargs.get('game_index')
        gid = self.make_game_id(game)  # Use header-based ID only
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

            # Check for 5-fold repetition (automatic draw)
            if board.is_fivefold_repetition():
                printable_move = self.get_printable_move(move_counter, san_move)
                
                entry = ClaimEntry(
                    type=ClaimType.FIVEFOLD,
                    board_number=board_number,
                    players=players,
                    move=printable_move,
                    game_index=game_index,
                    move_counter=move_counter,
                    start_move_counter=last_irreversible_move,
                    comment="",
                    game_id=gid,
                )
                entries.append(entry)
                
                # Stop checking after 5-fold (automatic draw)
                break

        return entries

    def check_batch(self, games: List[Any], claims_model: Any, **kwargs) -> tuple:
        """Check multiple games for 5-fold repetition."""
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


