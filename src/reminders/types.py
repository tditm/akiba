from dataclasses import dataclass
from enum import Enum


class ReminderType(Enum):
    """Types of reminders that can be triggered."""
    TWO_FOLD_WARNING = "Possible 3-fold reminder (2-fold)"
    SCORESHEET_REMINDER = "Scoresheet reminder"
    TIMECONTROL_REMINDER = "Time control reminder"
    FORTYFIVE_MOVES_WARNING = "Possible 50-move reminder (45 moves)"
    LOW_TIME_REMINDER = "Low time reminder"
    FLAG_FALL_REMINDER = "Flag fall reminder"
    SOFIA_RULE_VIOLATION = "Sofia rule violation"


@dataclass(frozen=True)
class ReminderEntry:
    """
    Represents a single reminder event detected in a game.
    
    This is similar to ClaimEntry but specifically for reminders
    that are not yet actual claims (warnings, notifications).
    """
    type: ReminderType
    board_number: str
    players: str
    description: str          # e.g., "45-move game", "Time control reached"
    game_index: int
    move_counter: int         # current move when reminder triggered
    start_move_counter: int   # starting move for counting rules (e.g. 45-move)
    comment: str = ""         # Additional context (e.g., "First counting move: X")
    game_id: str = ""
