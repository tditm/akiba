import json
import os
import sys
from threading import Event, Thread, Lock
from typing import List, Dict

from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtWidgets import QApplication

from src.helpers import get_appdata_path, Status
from src.claims.manager import ClaimsManager
from src.models.workers import CheckDownload, DownloadGames, MakePgn, Scan, Stop, DownloadLiveChessGames
from src.models.events import ClaimEntry, ClaimType, ClaimsStore
from src.views.dialog_view import AddSourceDialog, SourceHBox
from src.views.main_view import ChessClaimView, sources_warning
from src.views.board_viewer import BoardViewerWindow
from src.models.events import get_players
from src.reminders.manager import ReminderManager
from src.models.livechesscloud import LiveChessCloudSource


class ChessClaimController(QApplication):

    __slots__ = [
        'view', 'claims_manager', 'sources_dialog',
        'make_pgn_worker', 'stop_worker', 'download_worker', 'scan_worker',
        'stop_event', 'board_viewer', 'reminder_manager',
        'scoresheet_reminder_enabled', 'scoresheet_threshold',
        'scoresheet_reminder_fired',
        'timecontrol_reminder_enabled', 'timecontrol_threshold',
        'timecontrol_reminder_fired',
        'possible_threefold_enabled', 'possible_fiftymove_enabled',
        'threefold_fired', 'fiftymove_fired',
        'games',
        'claims',
        'low_time_reminder_enabled',
        'low_time_threshold_seconds',
        'low_time_reminder_fired',
        'flag_fall_reminder_enabled',
        'flag_fall_reminder_fired',
        'illegal_move_reminder_enabled',
        'filepaths',
        'downloads',
        'notifications_enabled',
        'livechess_sources',
        'livechess_worker',
    ]

    def __init__(self) -> None:
        super().__init__(sys.argv)

        # NEW: Central claims store - SINGLE SOURCE OF TRUTH (must be before view!)
        self.claims_store = ClaimsStore()
        
        self.view = ChessClaimView(self)
        self.claims_manager = ClaimsManager()
        self.claims_manager.controller = self
        self.sources_dialog = None
        self.current_viewed_gid = None
        self.reminder_manager = ReminderManager()

        self.make_pgn_worker = None
        self.download_worker = None
        self.scan_worker = None
        self.stop_worker = None
        self.livechess_worker = None

        self.stop_event = Event()
        self.board_viewer = None
        
        # LiveChessCloud sources
        self.livechess_sources: List[LiveChessCloudSource] = []

        # Scoresheet reminder
        self.scoresheet_reminder_enabled = False
        self.scoresheet_threshold = 55
        self.scoresheet_reminder_fired: Dict[int, bool] = {}

        # Timecontrol reminder
        self.timecontrol_reminder_enabled = False
        self.timecontrol_threshold = 40
        self.timecontrol_reminder_fired: Dict[int, bool] = {}

        # Low time reminder
        self.low_time_reminder_enabled = False
        self.low_time_threshold_seconds = 120
        self.low_time_reminder_fired: Dict[int, bool] = {}

        # Flag fall reminder (uses set for tracking shown reminders)
        self.flag_fall_reminder_enabled = False
        self.flag_fall_reminder_fired: set = set()

        # Illegal move reminder (uses set for tracking shown reminders to prevent duplicates)
        self.illegal_move_reminder_enabled = False
        self.illegal_move_reminder_fired: set = set()

        # Sofia rule reminder
        self.sofia_rule_enabled = False
        self.sofia_rule_threshold = 30
        self.sofia_rule_fired: Dict[int, bool] = {}

        # Possible reminders (2-fold and 45-move warnings)
        self.possible_threefold_enabled = False  # Two-fold warning
        self.possible_fiftymove_enabled = False  # 45-move warning

        # Notification system enabled by default
        self.notifications_enabled = True

        # Game list and mapping
        self.games: List = []
        self.game_id_to_index: Dict[str, int] = {}

    def make_game_id(self, game) -> str:
        """
        Generates a stable identifier for a game based on PGN headers.
        This ID does NOT change even if the PGN file is rebuilt or reordered.
        """
        return "|".join([
            game.headers.get("Event", ""),
            game.headers.get("Site", ""),
            game.headers.get("Date", ""),
            game.headers.get("Round", ""),
            game.headers.get("White", ""),
            game.headers.get("Black", ""),
        ])

    # -------------------------------------------------------------------------
    # START
    # -------------------------------------------------------------------------

    def do_start(self) -> None:
        app_path = get_appdata_path()
        os.makedirs(app_path, exist_ok=True)

        self.view.set_gui()
        self.load_options()  # Load saved reminder settings
        self.apply_options_to_view()  # Apply loaded settings to view checkboxes
        self.view.show()

    # -------------------------------------------------------------------------
    # OPTIONS (Settings Persistence)
    # -------------------------------------------------------------------------

    def load_options(self) -> None:
        """Load saved reminder settings from options.json."""
        try:
            options_path = os.path.join(get_appdata_path(), "options.json")
            if not os.path.exists(options_path):
                return

            with open(options_path, "r") as file:
                data = json.load(file)

            # Notification system
            self.notifications_enabled = data.get("enable_notifications", True)

            # Scoresheet reminder
            self.scoresheet_reminder_enabled = data.get("scoresheet_enabled", False)
            self.scoresheet_threshold = data.get("scoresheet_move", 55)

            # Timecontrol reminder
            self.timecontrol_reminder_enabled = data.get("timecontrol_enabled", False)
            self.timecontrol_threshold = data.get("timecontrol_move", 40)

            # Possible reminders (2-fold and 50-move warnings)
            self.possible_threefold_enabled = data.get("possible_threefold", False)
            self.possible_fiftymove_enabled = data.get("possible_50_move", False)

            # Low time reminder
            self.low_time_reminder_enabled = data.get("low_time_enabled", False)
            self.low_time_threshold_seconds = data.get("low_time_seconds", 120)

            # Flag fall reminder
            self.flag_fall_reminder_enabled = data.get("flag_fall_reminder", False)

            # Illegal move reminder
            self.illegal_move_reminder_enabled = data.get("illegal_move_reminder", False)

            # Sofia rule reminder
            self.sofia_rule_enabled = data.get("sofia_enabled", False)
            self.sofia_rule_threshold = data.get("sofia_move", 30)

        except Exception:
            # If loading fails, keep default values
            pass

    def save_options(self) -> None:
        """Save current reminder settings to options.json."""
        data = {
            "enable_notifications": self.notifications_enabled,
            "scoresheet_enabled": self.scoresheet_reminder_enabled,
            "scoresheet_move": self.scoresheet_threshold,
            "timecontrol_enabled": self.timecontrol_reminder_enabled,
            "timecontrol_move": self.timecontrol_threshold,
            "possible_threefold": self.possible_threefold_enabled,
            "possible_50_move": self.possible_fiftymove_enabled,
            "low_time_enabled": self.low_time_reminder_enabled,
            "low_time_seconds": self.low_time_threshold_seconds,
            "flag_fall_reminder": self.flag_fall_reminder_enabled,
            "illegal_move_reminder": self.illegal_move_reminder_enabled,
            "sofia_enabled": self.sofia_rule_enabled,
            "sofia_move": self.sofia_rule_threshold,
        }

        with open(os.path.join(get_appdata_path(), 'options.json'), 'w') as file:
            json.dump(data, file, indent=4)

    def apply_options_to_view(self) -> None:
        """Apply loaded settings to view checkboxes and spinboxes."""
        # Notification system
        self.view.notifications_enabled_action.setChecked(self.notifications_enabled)
        
        # Scoresheet reminder
        self.view.scoresheet_action.setChecked(self.scoresheet_reminder_enabled)
        self.view.scoresheet_spin.setValue(self.scoresheet_threshold)
        self.view.scoresheet_spin.setEnabled(self.scoresheet_reminder_enabled)
        
        # Timecontrol reminder
        self.view.timecontrol_action.setChecked(self.timecontrol_reminder_enabled)
        self.view.timecontrol_spin.setValue(self.timecontrol_threshold)
        self.view.timecontrol_spin.setEnabled(self.timecontrol_reminder_enabled)
        
        # Possible reminders
        self.view.possible_threefold_action.setChecked(self.possible_threefold_enabled)
        self.view.possible_fiftymove_action.setChecked(self.possible_fiftymove_enabled)
        
        # Low time reminder
        self.view.low_time_action.setChecked(self.low_time_reminder_enabled)
        self.view.low_time_spin.setValue(self.low_time_threshold_seconds)
        self.view.low_time_spin.setEnabled(self.low_time_reminder_enabled)
        
        # Flag fall reminder
        self.view.flag_fall_action.setChecked(self.flag_fall_reminder_enabled)

        # Illegal move reminder
        self.view.illegal_move_action.setChecked(self.illegal_move_reminder_enabled)

        # Sofia rule reminder
        self.view.sofia_action.setChecked(self.sofia_rule_enabled)
        self.view.sofia_spin.setValue(self.sofia_rule_threshold)
        self.view.sofia_spin.setEnabled(self.sofia_rule_enabled)


    def extract_clock_from_node(self, node):
        import re

        if not node or not node.comment:
            return None

        match = re.search(r"\[%clk\s+(\d{1,2}:\d{2}:\d{2})\]", node.comment)
        if match:
            return match.group(1)
        return None

    # -------------------------------------------------------------------------
    # ABOUT
    # -------------------------------------------------------------------------
    # HELP MENU
    # -------------------------------------------------------------------------

    def on_user_manual_clicked(self) -> None:
        """Open the user documentation file."""
        self.view.open_user_manual()

    def on_about_clicked(self) -> None:
        self.view.load_about_dialog()

    # -------------------------------------------------------------------------
    # BOARD VIEWER
    # -------------------------------------------------------------------------

    def on_board_viewer_clicked(self):
        """
        Opens the Board Viewer and jumps to the correct game
        based on the selected claim entry.
        
        FIX: Always get data from column 0 of the clicked row,
        because userData is only stored in column 0 items.
        """
        app_path = get_appdata_path()
        pgn_path = os.path.join(app_path, "games.pgn")

        if self.board_viewer is None:
            self.board_viewer = BoardViewerWindow(pgn_path)

        # Get the current index
        index = self.view.claims_table.currentIndex()
        
        # FIX: Always use column 0 for data lookup (userData is only in column 0)
        if index.isValid():
            # Get index from column 0 of the same row
            col0_index = index.model().index(index.row(), 0, index.parent())
            data = col0_index.data(Qt.ItemDataRole.UserRole)
            
            if data:
                gid = data.get("game_id", "")
                game_index = data.get("game_index", 0)

                if gid and gid == self.current_viewed_gid:
                    self.board_viewer.show()
                    return

                idx = self.game_id_to_index.get(gid, game_index)
                self.current_viewed_gid = gid
                self.board_viewer.load_game_at_index(idx)

        self.board_viewer.show()

    def open_viewer_for_claim(self, game_index: int, move_index: int, game_id: str = None):
        """
        Opens the Board Viewer and jumps to a specific move
        (used when clicking on a table row).
        
        BUG FIX #3: Uses game_id lookup instead of direct index access because 
        the games list may have been reordered after PGN updates.
        
        Args:
            game_index: Original stored index (may be stale)
            move_index: Move position within the game
            game_id: Stable game identifier for accurate lookup (preferred method)
        """
        app_path = get_appdata_path()
        pgn_path = os.path.join(app_path, "games.pgn")

        if self.board_viewer is None:
            self.board_viewer = BoardViewerWindow(pgn_path)
        else:
            self.on_pgn_updated()

        # BUG FIX #3: Use game_id to find the current correct index
        # This ensures we open the right game even after PGN reloads reorder the list
        try:
            actual_index = game_index  # Default fallback
            
            if game_id and game_id in self.game_id_to_index:
                # Primary method: Look up by stable game_id
                actual_index = self.game_id_to_index[game_id]
            elif len(self.games) > game_index:
                # Secondary method: Verify index is still valid
                current_game = self.games[game_index]
                gid = self.make_game_id(current_game)
                actual_index = self.game_id_to_index.get(gid, game_index)

            self.board_viewer.load_game_at_index(actual_index)
            self.board_viewer.jump_to_move(move_index)
        except Exception:
            return

        self.board_viewer.show()
        self.board_viewer.raise_()

    # -------------------------------------------------------------------------
    # PGN UPDATE
    # -------------------------------------------------------------------------

    def on_pgn_updated(self):
        app_path = get_appdata_path()
        pgn_path = os.path.join(app_path, "games.pgn")

        if not os.path.exists(pgn_path):
            return

        import chess.pgn
        self.games = []
        
        # Track illegal moves detected during parsing - stores full game and error info
        illegal_move_games = []  # List of (game_index, san_move)
        
        # Log file for tracking illegal moves
        log_path = os.path.join(app_path, "illegal_moves_log.txt")
        
        with open(pgn_path, "r", encoding="utf-8") as f:
            game_index = 0
            
            while True:
                try:
                    g = chess.pgn.read_game(f)
                    if not g:
                        break
                    
                    # Check for errors in the loaded game
                    if g.errors:
                        for error in g.errors:
                            illegal_move_games.append((game_index, str(error)))
                            
                            # Log detailed info to file
                            with open(log_path, 'a', encoding='utf-8') as log_file:
                                log_file.write(f"\n{'='*60}\n")
                                log_file.write(f"Game #{game_index + 1}\n")
                                log_file.write(f"Error: {error}\n\n")
                                
                                # Log game headers
                                for header in ['Event', 'Site', 'Date', 'Round', 'White', 'Black']:
                                    value = g.headers.get(header, '')
                                    log_file.write(f"{header}: {value}\n")
                                log_file.write("\n")
                                
                                # Log moves before the error
                                board = chess.Board()
                                move_num = 1
                                for node in g.mainline():
                                    try:
                                        move = node.move
                                        san = board.san(move)
                                        board.push(move)
                                        log_file.write(f"{move_num}. {san} ")
                                        if move_num % 2 == 0:
                                            log_file.write("\n")
                                        move_num += 1
                                    except Exception as e:
                                        # This is where the error occurred
                                        log_file.write(f"\n>>> ERROR HERE: {node.move} - {e}\n<<<\n")
                                        break
                                log_file.write("\n\n")
                    
                    self.games.append(g)
                    game_index += 1
                    
                except (chess.InvalidMoveError, chess.IllegalMoveError) as e:
                    # Fallback for direct exceptions
                    illegal_move_games.append((game_index, str(e)))
                    
                    with open(log_path, 'a', encoding='utf-8') as log_file:
                        log_file.write(f"\n{'='*60}\n")
                        log_file.write(f"Game #{game_index + 1} (direct exception)\n")
                        log_file.write(f"Error: {e}\n\n")
                    
                    game_index += 1
                    
                except Exception as e:
                    # Other parsing errors
                    break
        
        # Close the log file explicitly
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f"\n{'='*60}\n")
            log_file.write(f"Total games processed: {game_index}\n")
            log_file.write(f"Illegal moves detected: {len(illegal_move_games)}\n")

        # Rebuild stable mapping game_id -> current index
        self.game_id_to_index = {}
        for idx, game in enumerate(self.games):
            gid = self.make_game_id(game)  # Use header-based ID only
            self.game_id_to_index[gid] = idx

        # Reload viewer if open
        if self.board_viewer is not None:
            self.board_viewer.reload_pgn(pgn_path)

        # Process illegal moves detected during parsing and add to claims
        for game_idx, error_msg in illegal_move_games:
            self._add_illegal_move_claim(game_idx, error_msg)

        # Run all reminders through the manager
        self.run_all_reminders()

        # Refresh table
        self.view.refresh_table()

    def _add_illegal_move_claim(self, game_idx: int, error_msg: str) -> None:
        """Add an illegal move claim entry for a game that failed to parse."""
        if game_idx >= len(self.games):
            return
        
        game = self.games[game_idx]
        
        # Check if this game already has an illegal move claim
        game_id = self.make_game_id(game)
        if game_id in self.illegal_move_reminder_fired:
            return
        
        # Extract players from the game (use consistent "White - Black" format)
        white = game.headers.get("White", "Player1")
        black = game.headers.get("Black", "Player2")
        players = f"{white} - {black}"
        
        board_number = ClaimsManager.get_board_number(game)
        
        # Extract SAN move and fullmove number from error message
        import re
        match = re.search(r"illegal san: '([^']+)'", error_msg)
        san_move = match.group(1) if match else "Unknown"
        
        # Get the ACTUAL number of valid moves in this game (before the illegal move)
        try:
            actual_move_count = len(list(game.mainline_moves()))
        except Exception:
            actual_move_count = 0
        
        # For navigation: last valid move is the actual count
        last_valid_move = actual_move_count
        
        # Extract fullmove number from FEN for display (illegal move would be this number)
        fen_match = re.search(r"w - - \d+ (\d+)", error_msg)
        illegal_move_num = fen_match.group(1) if fen_match else str(actual_move_count + 1)
        
        move_display = f"{illegal_move_num}.{san_move}"
        
        entry = ClaimEntry(
            type=ClaimType.ILLEGAL_MOVE,
            board_number=board_number,
            players=players,
            move=move_display,
            game_index=game_idx,
            move_counter=last_valid_move,  # Navigate to last valid position
            start_move_counter=0,
            comment=f"Parsing failed: {error_msg}",
            game_id=self.make_game_id(game),
        )
        
        # Add to claims_store AND update GUI table
        self.claims_store.add_claim(entry)
        self.view.add_item_to_table(entry)
        
        # Mark this game as processed to prevent duplicates
        self.illegal_move_reminder_fired.add(self.make_game_id(game))

    # -------------------------------------------------------------------------
    # NEW MOVE
    # -------------------------------------------------------------------------

    def on_new_move(self):
        if not self.sources_dialog:
            return

        filepaths = self.sources_dialog.get_filepath_list()
        if not filepaths:
            return

        lock = Lock()
        make_pgn = MakePgn(filepaths, self.stop_event, lock)
        make_pgn.make_pgn()

        self.on_pgn_updated()

    # -------------------------------------------------------------------------
    # CENTRAL REMINDER ORCHESTRATION
    # -------------------------------------------------------------------------

    def run_all_reminders(self):
        """
        Central method that runs all enabled reminders via ReminderManager
        and updates the GUI table with returned results.
        """
        if not self.games:
            return

        (
            entries,
            scoresheet_fired,
            time_control_fired,
            low_time_fired,
            flag_fall_shown,
            sofia_rule_fired,
            two_fold_shown,
            fortyfive_moves_shown,
            illegal_move_shown
        ) = self.reminder_manager.run_all_reminders(
            games=self.games,
            claims_model=self.claims_manager,
            scoresheet_enabled=self.scoresheet_reminder_enabled,
            scoresheet_threshold=self.scoresheet_threshold,
            scoresheet_fired=self.scoresheet_reminder_fired,
            time_control_enabled=self.timecontrol_reminder_enabled,
            time_control_threshold=self.timecontrol_threshold,
            time_control_fired=self.timecontrol_reminder_fired,
            two_fold_enabled=self.possible_threefold_enabled,
            fiftymove_enabled=self.possible_fiftymove_enabled,
            low_time_enabled=self.low_time_reminder_enabled,
            low_time_threshold_seconds=self.low_time_threshold_seconds,
            low_time_fired=self.low_time_reminder_fired,
            flag_fall_enabled=self.flag_fall_reminder_enabled,
            flag_fall_shown=self.flag_fall_reminder_fired,
            sofia_rule_enabled=self.sofia_rule_enabled,
            sofia_rule_threshold=self.sofia_rule_threshold,
            sofia_rule_fired=self.sofia_rule_fired,
            illegal_move_enabled=self.illegal_move_reminder_enabled,
        )

        # Update state dictionaries from manager results
        self.scoresheet_reminder_fired = scoresheet_fired
        self.timecontrol_reminder_fired = time_control_fired
        self.low_time_reminder_fired = low_time_fired
        self.flag_fall_reminder_fired = flag_fall_shown
        self.sofia_rule_fired = sofia_rule_fired

        # NEW: Store all claims in central store AND update GUI table
        for entry in entries:
            self.claims_store.add_claim(entry)  # Store in ClaimsStore
            self.view.add_item_to_table(entry)


    # -------------------------------------------------------------------------
    # SCAN / DOWNLOAD / STOP
    # -------------------------------------------------------------------------

    def on_clear_resolved_clicked(self) -> None:
        """
        Clear selected rows from the claims table.
        Called when user clicks "Clear Resolved" button (referee has responded).
        """
        self.view.claims_table_widget.clear_selected_rows()

    def on_sources_button_clicked(self) -> None:
        if not self.sources_dialog:
            self.sources_dialog = SourceDialogController()
            self.sources_dialog.view.accepted.connect(self.update_status_bar_sources)
            self.sources_dialog.do_start()
            return

        if self.scan_worker and self.scan_worker.isRunning():
            self.on_stop_button_clicked()

        self.sources_dialog.do_resume()

    def on_scan_button_clicked(self) -> None:
        if not self.sources_dialog or not self.sources_dialog.has_valid_sources():
            sources_warning()
            return

        if self.scan_worker and self.scan_worker.isRunning():
            return

        # DON'T clear acknowledged rows - they should reappear after restart
        # unless they were explicitly cleared via Clear Resolved button
        # self.view.clear_ack_rows()  <-- REMOVE THIS!
        self.view.change_scan_button_text(Status.ACTIVE)

        # Send beacon (anonymous report after clicking Start Scan)
        try:
            import threading
            from src.beacon import send_beacon_async
            threading.Thread(target=send_beacon_async, daemon=True).start()
        except Exception:
            pass  # Ignore errors - app must work without beacon

        download_list = self.sources_dialog.get_download_list()
        if download_list:
            self.start_download_worker(download_list)

        games_pgn_mutex = Lock()
        self.start_make_png_worker(games_pgn_mutex)
        self.start_scan_worker(games_pgn_mutex)

    def on_stop_button_clicked(self) -> None:
        if not self.scan_worker or not self.scan_worker.isRunning():
            return

        self.stop_worker = Stop(
            self.stop_event,
            self.make_pgn_worker,
            self.scan_worker,
            self.download_worker,
            self.livechess_worker
        )

        self.stop_worker.enable_signal.connect(self.on_stop_enable_status)
        self.stop_worker.disable_signal.connect(self.on_stop_disable_status)
        self.stop_worker.start()
        self.stop_worker.wait()
        self.view.change_scan_button_text(Status.STOP)

        # DON'T reset checkers - preserve seen_positions for continuity
        # self.reminder_manager.reset_checkers()
        self.stop_event.clear()
        
        # Clear livechess sources on stop
        self.livechess_sources = []

    def on_stop_enable_status(self) -> None:
        self.view.set_scan_status(Status.ACTIVE)

    def on_stop_disable_status(self) -> None:
        self.view.set_scan_status(Status.INACTIVE)
        self.view.change_scan_button_text(Status.INACTIVE)

    def update_status_bar_sources(self) -> None:
        valid_sources = self.sources_dialog.get_valid_sources()
        if valid_sources:
            self.view.set_sources_status(Status.OK, valid_sources)
        else:
            self.view.set_sources_status(Status.ERROR)

    def update_claims_table(self, entry) -> None:
        # Skip adding to table if already cleared (was marked via Clear Resolved)
        if entry.cleared:
            return
        
        self.claims_store.add_claim(entry)  # Store in ClaimsStore
        self.view.add_item_to_table(entry)

    def update_download_status(self, status: Status) -> None:
        self.view.set_download_status(status)

    def update_bar_scan_status(self, status: Status) -> None:
        self.view.set_scan_status(status)

    # -------------------------------------------------------------------------
    # WORKERS
    # -------------------------------------------------------------------------

    def start_download_worker(self, downloads: Dict[str, str]) -> None:
        if not downloads:
            return

        self.download_worker = DownloadGames(downloads, self.stop_event)
        self.download_worker.status_signal.connect(self.update_download_status)
        self.download_worker.start()

    def start_make_png_worker(self, lock: Lock) -> None:
        filepaths = self.sources_dialog.get_filepath_list()
        
        # FIX: Run make_pgn SYNCHRONOUSLY first to ensure games.pgn exists
        # This ensures on_pgn_updated() has a valid file to load
        make_pgn_sync = MakePgn(filepaths, None, lock)
        make_pgn_sync.make_pgn()  # Synchronous call
        
        # Then start the background worker for periodic updates
        self.make_pgn_worker = MakePgn(filepaths, self.stop_event, lock)
        self.make_pgn_worker.start()

    def start_scan_worker(self, lock: Lock) -> None:
        app_path = get_appdata_path()
        filename = os.path.join(app_path, "games.pgn")

        self.scan_worker = Scan(
            self.claims_manager,
            filename,
            lock,
            None,
            self.stop_event
        )

        self.scan_worker.add_entry_signal.connect(self.update_claims_table)
        self.scan_worker.status_signal.connect(self.update_bar_scan_status)

        if hasattr(self.scan_worker, "new_move_signal"):
            self.scan_worker.new_move_signal.connect(self.on_new_move)

        # FIX: Load games BEFORE starting scan so game_id_to_index is populated
        # Only if games.pgn already exists (created by make_pgn_worker)
        app_path = get_appdata_path()
        pgn_path = os.path.join(app_path, "games.pgn")
        if os.path.exists(pgn_path):
            self.on_pgn_updated()

        self.scan_worker.finished.connect(self.on_new_move)

        self.scan_worker.start()


# -------------------------------------------------------------------------
# SOURCE DIALOG CONTROLLER
# -------------------------------------------------------------------------

class SourceDialogController:

    def __init__(self) -> None:
        self.view = AddSourceDialog(self)
        self.app_path = get_appdata_path()
        self.threadPool = QThreadPool()
        self.filepaths: List[str] = []
        self.downloads: Dict[str, str] = dict()
        self.livechess_sources: List[LiveChessCloudSource] = []
        self.livechess_worker = None
        self.stop_event = Event()  # Add stop event for polling workers
        self.apply_lock = Lock()
        self.shown_reminders = set()

    def do_start(self) -> None:
        self.view.set_gui()
        self.restore()
        self.view.show()

    def do_resume(self) -> None:
        self.view.show()

    def get_filepath_list(self) -> List[str]:
        return self.filepaths

    def get_valid_sources(self) -> List[SourceHBox]:
        return self.view.sources

    def get_download_list(self) -> Dict[str, str]:
        return self.downloads

    def has_valid_sources(self) -> bool:
        return len(self.filepaths) > 0

    def restore(self) -> None:
        try:
            with open(os.path.join(self.app_path, "sources.json"), "r") as file:
                data = json.load(file)
                
                if not data:
                    self.view.add_default_source()
                    return
                
                for entry in data:
                    option = entry["option"]
                    value = entry["value"]
                    # For LiveChessCloud sources, restore round number too (default to 1 if not specified)
                    if option == 2 and "round" in entry:
                        round_num = entry["round"] if entry.get("round", 1) > 0 else 1
                        self.view.add_source(option, value, round_num)
                    else:
                        self.view.add_source(option, value)
        except Exception as e:
            self.view.add_default_source()

    def on_delete_button_clicked(self, source_hbox) -> None:
        with self.apply_lock:
            self.remove_hbox_refs(source_hbox)
            self.view.remove_hbox(source_hbox)

    def remove_hbox_refs(self, hbox: SourceHBox) -> None:
        value = hbox.get_value()
        if hbox.has_url() and value in self.downloads:
            filepath = self.downloads[value]
            if filepath in self.filepaths:
                self.filepaths.remove(filepath)
            del self.downloads[value]
        elif hbox.has_local() and value in self.filepaths:
            self.filepaths.remove(value)

    def on_apply_button_clicked(self) -> None:
        Thread(target=self._apply_thread, daemon=True).start()

    def _apply_thread(self) -> None:
        with self.apply_lock:
            self.filepaths = []
            self.downloads = {}
            self.livechess_sources = []

            download_id = 0
            for source_hbox in self.view.sources:
                option = source_hbox.get_source_index()
                value = source_hbox.get_value()
                
                if source_hbox.has_url():
                    self.threadPool.start(CheckDownload(self, source_hbox, download_id))
                    download_id += 1
                elif source_hbox.has_local():
                    filepath = source_hbox.get_value()
                    if os.path.exists(filepath):
                        source_hbox.set_status(Status.OK)
                        if filepath not in self.filepaths:
                            self.filepaths.append(filepath)
                    else:
                        source_hbox.set_status(Status.ERROR)
                elif source_hbox.has_livechess():
                    # Validate LiveChessCloud URL
                    from src.models.download import check_livechess_download
                    url = source_hbox.get_value()
                    round_num = source_hbox.get_round_num()
                    
                    if check_livechess_download(url):
                        source_hbox.set_status(Status.OK)
                        livechess_source = LiveChessCloudSource(url, round_num)
                        self.livechess_sources.append(livechess_source)
                        # Add the generated PGN file path
                        filepath = os.path.join(self.app_path, livechess_source.get_filename())
                        if filepath not in self.filepaths:
                            self.filepaths.append(filepath)
                    else:
                        source_hbox.set_status(Status.ERROR)
                else:
                    pass  # Unknown option, ignore

            self.threadPool.waitForDone()

            if self.filepaths:
                self.view.enable_ok_button()

    def on_ok_button_clicked(self) -> None:
        # Save sources IMMEDIATELY before closing dialog
        self.save_sources()
        
        # Now start background workers (they will run after app main loop starts)
        if self.livechess_sources:
            from src.models.workers import DownloadLiveChessGames
            import time
            
            def background_work():
                time.sleep(1)  # Small delay to let dialog close
                
                self.livechess_worker = DownloadLiveChessGames(
                    self.livechess_sources, 
                    self.stop_event
                )
                self.livechess_worker.start()
            
            Thread(target=background_work, daemon=True).start()

        self.view.accept()
        self.view.close()

    def _exit_thread(self) -> None:
        # Download regular web PGNs
        if self.downloads:
            worker = DownloadGames(self.downloads)
            worker.start()
            worker.wait()

        # Download/update LiveChessCloud live games (with polling)
        if self.livechess_sources:
            self.livechess_worker = DownloadLiveChessGames(
                self.livechess_sources, 
                self.stop_event
            )
            self.livechess_worker.start()
            
            # Wait for FIRST full poll cycle before creating combined PGN
            # This ensures livechess PGN files are created BEFORE MakePgn runs
            if not self.stop_event.is_set():
                import time
                time.sleep(5)  # Wait longer to ensure games are fetched
                self.livechess_worker.wait()  # Wait for initial run to complete

        make_pgn = MakePgn(self.filepaths)
        make_pgn.start()
        make_pgn.join()

        # Save sources using SourceDialogController's method
        if self.sources_dialog:
            self.sources_dialog.save_sources()

        # AUTOMATICALLY start Scan worker so user can see games immediately
        from threading import Thread
        Thread(target=self._auto_start_scan, daemon=True).start()

    def _auto_start_scan(self) -> None:
        """Automatically start scan after PGN is created."""
        import time
        
        # Wait for MakePgn to finish and file system to sync
        time.sleep(2)  # Increased from 0.5 to 2 seconds
        
        if not self.sources_dialog or not self.sources_dialog.has_valid_sources():
            return
            
        if self.scan_worker and self.scan_worker.isRunning():
            return

        # Set status to ACTIVE
        self.view.change_scan_button_text(Status.ACTIVE)

        games_pgn_mutex = Lock()
        self.start_make_png_worker(games_pgn_mutex)
        self.start_scan_worker(games_pgn_mutex)

    def save_sources(self) -> None:
        data = []
        
        for i, source in enumerate(self.view.sources):
            option = source.get_source_index()
            value = source.get_value()
            
            entry = {
                "option": option,
                "value": value
            }
            
            # Add round number for LiveChessCloud sources
            if source.has_livechess():
                round_num = source.get_round_num()
                entry["round"] = round_num if round_num is not None else 1
            
            data.append(entry)

        # Ensure directory exists
        sources_file = os.path.join(self.app_path, 'sources.json')
        
        try:
            os.makedirs(self.app_path, exist_ok=True)
            
            with open(sources_file, 'w') as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            pass  # Silent failure for now

    def add_valid_url(self, url: str, download_id: int) -> None:
        filepath = os.path.join(self.app_path, f"games{download_id}.pgn")
        self.downloads[url] = filepath
        if filepath not in self.filepaths:
            self.filepaths.append(filepath)
