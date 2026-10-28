from dataclasses import dataclass, field
from enum import Enum
from math import ceil
from chess.pgn import Game
from typing import List, Dict, Optional


def get_players(game: Game) -> str:
    """
    Returns a short 'White - Black' string for display.
    Names are trimmed to keep UI compact.
    """
    white = game.headers.get("White", "")[:22]
    black = game.headers.get("Black", "")[:22]
    return f"{white} - {black}"


class ClaimType(Enum):
    THREEFOLD = "3-fold repetition"
    FIVEFOLD = "5-fold repetition"
    FIFTY_MOVES = "50-move rule"
    SEVENTYFIVE_MOVES = "75-move rule"
    STALEMATE_CLAIM = "Stalemate"
    CHECKMATE_CLAIM = "Checkmate"
    DEAD_POSITION_CLAIM = "Dead position"
    SCORESHEET_REMINDER = "Scoresheet change"
    TWO_FOLD_WARNING = "2-fold repetition"
    FORTYFIVE_MOVES_WARNING = "45-move reminder"
    TIMECONTROL_REMINDER = "Time control"
    LOW_TIME_REMINDER = "Low on time"
    FLAG_FALL_REMINDER = "Flag fall reminder"
    SOFIA_RULE = "Sofia rule violation"
    ILLEGAL_MOVE = "First illegal move"
    
@dataclass(frozen=True)
class ClaimEntry:
    """
    Represents a single claim event detected in a game.
    start_move_counter is used for rules that require
    tracking the beginning of a counting sequence (e.g. 50-move rule).
    """
    type: ClaimType
    board_number: str
    players: str
    move: str
    game_index: int
    move_counter: int          # final move index (claim moment)
    start_move_counter: int    # starting move index
    comment: str = ""          # NEW — PGN comment (e.g. "First counting move: X")
    game_id: str = ""
    cleared: bool = False       # NEW - if True, this claim was cleared via Clear Resolved button and should not reappear after restart


@dataclass
class ClaimsStore:
    """
    Central store for all claims - SINGLE SOURCE OF TRUTH.
    
    This replaces the scattered state in:
    - ClaimEntry.game_index
    - userData() in QStandardItem  
    - self.current_entry_game_index in view
    
    All claims operations go through this store.
    """
    claims: List[ClaimEntry] = field(default_factory=list)
    game_ids: set = field(default_factory=set)  # Track all unique game_ids
    
    def add_claim(self, entry: ClaimEntry) -> None:
        """Add a new claim to the store."""
        self.claims.append(entry)
        if entry.game_id:
            self.game_ids.add(entry.game_id)
    
    def get_claim_by_row(self, row_index: int) -> Optional[ClaimEntry]:
        """Get claim by its row index in the table."""
        if 0 <= row_index < len(self.claims):
            return self.claims[row_index]
        return None
    
    def get_claims_for_game(self, game_index: int) -> List[ClaimEntry]:
        """Get all claims for a specific game."""
        return [c for c in self.claims if c.game_index == game_index]
    
    def get_claim_by_game_index(self, game_index: int) -> Optional[ClaimEntry]:
        """Get first claim for a specific game (or None)."""
        for c in self.claims:
            if c.game_index == game_index:
                return c
        return None
    
    def clear(self) -> None:
        """Clear all claims from the store."""
        self.claims.clear()
        self.game_ids.clear()

    def remove_claim_by_game_index(self, game_index: int) -> None:
        """Remove all claims for a specific game index."""
        # Get game_ids to remove BEFORE filtering
        games_to_remove = {c.game_id for c in self.claims if c.game_index == game_index}
        self.claims = [c for c in self.claims if c.game_index != game_index]
        # Also remove associated game_ids
        self.game_ids -= games_to_remove

    def mark_cleared(self, game_index: int) -> None:
        """Mark all claims for a specific game index as cleared (cleared=True)."""
        for claim in self.claims:
            if claim.game_index == game_index:
                # Create new ClaimEntry with cleared=True (dataclass is frozen, so need to replace)
                updated_claim = ClaimEntry(
                    type=claim.type,
                    board_number=claim.board_number,
                    players=claim.players,
                    move=claim.move,
                    game_index=claim.game_index,
                    move_counter=claim.move_counter,
                    start_move_counter=claim.start_move_counter,
                    comment=claim.comment,
                    game_id=claim.game_id,
                    cleared=True
                )
                # Replace in list
                idx = self.claims.index(claim)
                self.claims[idx] = updated_claim
    
    @property
    def count(self) -> int:
        """Total number of claims."""
        return len(self.claims)
