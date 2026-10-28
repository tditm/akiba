from typing import List, Any, Dict

from src.models.events import ClaimEntry
from src.reminders.checkers import (
    ScoresheetChecker,
    TimeControlChecker,
    TwoFoldChecker,
    PossibleFiftyMoveChecker,
    LowTimeChecker,
    FlagFallChecker,
    SofiaRuleChecker,
    IllegalMoveChecker,
)


class ReminderManager:
    """Orchestrates all reminder checking for chess games."""

    def __init__(self) -> None:
        self.scoresheet_checker = ScoresheetChecker()
        self.time_control_checker = TimeControlChecker()
        self.two_fold_checker = TwoFoldChecker()
        self.fortyfive_moves_checker = PossibleFiftyMoveChecker()
        self.low_time_checker = LowTimeChecker()
        self.flag_fall_checker = FlagFallChecker()
        self.sofia_rule_checker = SofiaRuleChecker()
        self.illegal_move_checker = IllegalMoveChecker()

    def get_enabled_checkers(self) -> Dict[str, Any]:
        return {
            "scoresheet": self.scoresheet_checker,
            "time_control": self.time_control_checker,
            "two_fold": self.two_fold_checker,
            "fortyfive_moves": self.fortyfive_moves_checker,
            "low_time": self.low_time_checker,
            "flag_fall": self.flag_fall_checker,
            "sofia_rule": self.sofia_rule_checker,
            "illegal_move": self.illegal_move_checker,
        }

    def reset_checkers(self) -> None:
        """Reset all checker states (shown_reminders) for a fresh scan."""
        self.two_fold_checker.shown_reminders.clear()
        self.fortyfive_moves_checker.shown_reminders.clear()
        self.illegal_move_checker.shown_reminders.clear()

    def run_all_reminders(
        self,
        games: List[Any],
        claims_model: Any,
        scoresheet_enabled: bool,
        scoresheet_threshold: int,
        scoresheet_fired: Dict[int, bool],
        time_control_enabled: bool,
        time_control_threshold: int,
        time_control_fired: Dict[int, bool],
        two_fold_enabled: bool,
        fiftymove_enabled: bool,
        low_time_enabled: bool,
        low_time_threshold_seconds: int,
        low_time_fired: Dict[int, bool],
        flag_fall_enabled: bool,
        flag_fall_shown: set,
        sofia_rule_enabled: bool,
        sofia_rule_threshold: int,
        sofia_rule_fired: Dict[int, bool],
        illegal_move_enabled: bool,
    ) -> tuple:
        """Run all enabled reminders and return collected entries."""
        all_entries: List[ClaimEntry] = []

        if scoresheet_enabled:
            self.scoresheet_checker.enabled = True
            entries, scoresheet_fired = self.scoresheet_checker.check_batch(
                games, claims_model, threshold=scoresheet_threshold, fired_dict=scoresheet_fired
            )
            all_entries.extend(entries)
        else:
            self.scoresheet_checker.enabled = False

        if time_control_enabled:
            self.time_control_checker.enabled = True
            entries, time_control_fired = self.time_control_checker.check_batch(
                games, claims_model, threshold=time_control_threshold, fired_dict=time_control_fired
            )
            all_entries.extend(entries)
        else:
            self.time_control_checker.enabled = False

        if two_fold_enabled:
            self.two_fold_checker.enabled = True
            entries, two_fold_shown = self.two_fold_checker.check_batch(games, claims_model)
            all_entries.extend(entries)
        else:
            self.two_fold_checker.enabled = False
            two_fold_shown = self.two_fold_checker.shown_reminders

        if fiftymove_enabled:
            self.fortyfive_moves_checker.enabled = True
            entries, fortyfive_moves_shown = self.fortyfive_moves_checker.check_batch(games, claims_model)
            all_entries.extend(entries)
        else:
            self.fortyfive_moves_checker.enabled = False
            fortyfive_moves_shown = self.fortyfive_moves_checker.shown_reminders

        if low_time_enabled:
            self.low_time_checker.enabled = True
            entries, low_time_fired = self.low_time_checker.check_batch(
                games, claims_model, threshold_seconds=low_time_threshold_seconds, fired_dict=low_time_fired
            )
            all_entries.extend(entries)
        else:
            self.low_time_checker.enabled = False

        if flag_fall_enabled:
            self.flag_fall_checker.enabled = True
            entries, flag_fall_shown = self.flag_fall_checker.check_batch(games, claims_model)
            all_entries.extend(entries)
        else:
            self.flag_fall_checker.enabled = False

        if sofia_rule_enabled:
            self.sofia_rule_checker.enabled = True
            entries, sofia_rule_fired = self.sofia_rule_checker.check_batch(
                games, claims_model, threshold=sofia_rule_threshold, fired_dict=sofia_rule_fired
            )
            all_entries.extend(entries)
        else:
            self.sofia_rule_checker.enabled = False

        if illegal_move_enabled:
            self.illegal_move_checker.enabled = True
            entries, illegal_move_shown = self.illegal_move_checker.check_batch(games, claims_model)
            all_entries.extend(entries)
        else:
            self.illegal_move_checker.enabled = False
            illegal_move_shown = self.illegal_move_checker.shown_reminders

        return (
            all_entries, scoresheet_fired, time_control_fired, low_time_fired,
            flag_fall_shown, sofia_rule_fired, two_fold_shown, fortyfive_moves_shown, illegal_move_shown
        )
