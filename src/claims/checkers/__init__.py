from src.claims.checkers.base import BaseChecker
from src.models.events import ClaimType


# Import all checkers for easy access
try:
    from src.claims.checkers.threefold_checker import ThreeFoldChecker
except ImportError:
    ThreeFoldChecker = None

try:
    from src.claims.checkers.fivefold_checker import FiveFoldChecker
except ImportError:
    FiveFoldChecker = None

try:
    from src.claims.checkers.fifty_moves_checker import FiftyMovesChecker
except ImportError:
    FiftyMovesChecker = None

try:
    from src.claims.checkers.seventyfive_moves_checker import SeventyFiveMovesChecker
except ImportError:
    SeventyFiveMovesChecker = None

try:
    from src.claims.checkers.stalemate_checker import StalemateChecker
except ImportError:
    StalemateChecker = None

try:
    from src.claims.checkers.checkmate_checker import CheckmateChecker
except ImportError:
    CheckmateChecker = None

try:
    from src.claims.checkers.dead_position_checker import DeadPositionChecker
except ImportError:
    DeadPositionChecker = None


__all__ = [
    'BaseChecker',
    'ClaimType',
    'ThreeFoldChecker',
    'FiveFoldChecker', 
    'FiftyMovesChecker',
    'SeventyFiveMovesChecker',
    'StalemateChecker',
    'CheckmateChecker',
    'DeadPositionChecker',
]

