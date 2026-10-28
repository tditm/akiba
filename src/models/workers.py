from __future__ import annotations

import os.path
from threading import Thread
from typing import List, TYPE_CHECKING, Dict, Optional

from PyQt6.QtCore import QRunnable, QThread, pyqtSignal
from chess.pgn import read_game

from src.helpers import get_appdata_path, Status
from src.claims.manager import ClaimsManager
from src.models.events import get_players, ClaimType, ClaimEntry
from src.models.download import check_download, download_pgn
from src.models.livechesscloud import (
    extract_tournament_id, fetch_tournament, 
    TournamentData, LiveChessCloudSource, get_rounds_with_games,
    fetch_index, fetch_game, generate_pgn_for_round
)

if TYPE_CHECKING:
    from src.controllers import SourceDialogController
    from src.views.dialog_view import SourceHBox
    from threading import Event, Lock
    from PyQt6.QtWidgets import QAction


# ---------------------------------------------------------
# CHECK DOWNLOAD
# ---------------------------------------------------------

class CheckDownload(QRunnable):
    """Checks if a web source is valid."""

    __slots__ = ["controller", "source", "download_id"]

    def __init__(self, controller: SourceDialogController, source: SourceHBox, download_id: int):
        super().__init__()
        self.controller = controller
        self.source = source
        self.download_id = download_id

    def run(self):
        url = self.source.get_value()
        if check_download(url):
            self.source.set_status(Status.OK)
            if url not in self.controller.downloads:
                self.controller.add_valid_url(url, self.download_id)
        else:
            self.source.set_status(Status.ERROR)


# ---------------------------------------------------------
# DOWNLOAD GAMES
# ---------------------------------------------------------

class DownloadGames(QThread):
    """Downloads PGN files from the web."""

    status_signal = pyqtSignal(Status)
    INTERVAL = 4
    __slots__ = ["downloads", "stop_event", "app_path"]

    def __init__(self, downloads: Dict[str, str], stop_event: Event = None):
        super().__init__()
        self.downloads = downloads
        self.stop_event = stop_event
        self.app_path = get_appdata_path()

    def run(self) -> None:
        if not self.stop_event:
            return self.download_pgns()

        while not self.stop_event.is_set():
            self.download_pgns()
            self.stop_event.wait(self.INTERVAL)

    def download_pgns(self):
        for url in self.downloads:
            status = Status.OK

            data = download_pgn(url)
            if not data:
                status = Status.ERROR
            self.status_signal.emit(status)

            filename = self.downloads[url]
            try:
                with open(filename, "wb") as file:
                    file.write(data)
            except (FileNotFoundError, TypeError):
                self.status_signal.emit(Status.ERROR)
                continue


# ---------------------------------------------------------
# DOWNLOAD LIVECHESS GAMES
# ---------------------------------------------------------

class DownloadLiveChessGames(QThread):
    """Downloads and updates PGN from LiveChessCloud live tournaments."""
    
    status_signal = pyqtSignal(Status)
    INTERVAL = 4  # Same as DownloadGames for consistency
    
    __slots__ = ["sources", "stop_event", "app_path"]
    
    def __init__(self, sources: List[LiveChessCloudSource], stop_event: Event = None):
        super().__init__()
        self.sources = sources
        self.stop_event = stop_event
        self.app_path = get_appdata_path()
    
    def run(self) -> None:
        if not self.stop_event:
            return self.download_pgns()
        
        while not self.stop_event.is_set():
            self.download_pgns()
            self.stop_event.wait(self.INTERVAL)
    
    def download_pgns(self):
        """Fetch live games and update PGN files."""
        from src.models.livechesscloud import (
            fetch_tournament, fetch_index, fetch_game,
            generate_pgn_for_round
        )
        
        for source in self.sources:
            status = Status.OK
            
            if not source.is_valid:
                continue
            
            tournament = fetch_tournament(source.tournament_id)
            if not tournament:
                self.status_signal.emit(Status.ERROR)
                status = Status.ERROR
                continue
            
            # Process only the specified round (default: 1)
            round_num = source.round_num if source.round_num is not None else 1
            round_data = fetch_index(source.tournament_id, round_num)
            
            if not round_data:
                self.status_signal.emit(Status.ERROR)
                status = Status.ERROR
                continue
            
            # Fetch all games in this round
            games = {}
            for game_num in range(1, len(round_data.pairings) + 1):
                game = fetch_game(source.tournament_id, round_num, game_num)
                if game and game.moves:
                    games[game_num] = game
            
            # Generate PGN for this round
            if not games:
                self.status_signal.emit(Status.ERROR)
                status = Status.ERROR
                continue
            
            pgn_content = generate_pgn_for_round(
                tournament, round_data, games, round_num
            )
            # Write PGN to file
            filename = source.get_filename()
            filepath = os.path.join(self.app_path, filename)
            
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(pgn_content)
            except Exception:
                self.status_signal.emit(Status.ERROR)
                status = Status.ERROR
    
    def get_filepaths(self) -> List[str]:
        """Get list of PGN file paths for this source type."""
        return [os.path.join(self.app_path, source.get_filename()) 
                for source in self.sources if source.is_valid]


# ---------------------------------------------------------
# SCAN PGN
# ---------------------------------------------------------

class Scan(QThread):
    """
    Continuously scans the combined PGN file for new games.
    Emits ClaimEntry objects to update the GUI.
    """

    __slots__ = ["filename", "claims_manager", "lock", "live_pgn_option", "stop_event"]

    add_entry_signal = pyqtSignal(object)   # emits ClaimEntry
    status_signal = pyqtSignal(Status)
    new_move_signal = pyqtSignal()

    INTERVAL = 4

    def __init__(self, claims_manager: ClaimsManager, filename: str, lock: Lock,
                 live_pgn_option: QAction, stop_event: Event):
        super().__init__()
        self.filename = filename
        self.claims_manager = claims_manager
        self.lock = lock
        self.live_pgn_option = live_pgn_option   # can be None
        self.stop_event = stop_event

    def run(self):
        last_size = 0

        while not self.stop_event.is_set():
            try:
                size_of_pgn = os.path.getsize(self.filename)
            except FileNotFoundError:
                size_of_pgn = 0

###            if self.is_file_updated(last_size, size_of_pgn):
            if size_of_pgn != 0:       
                self.status_signal.emit(Status.ACTIVE)
                self.new_move_signal.emit()
                self.check_pgn()

            self.status_signal.emit(Status.WAIT)
            last_size = size_of_pgn

            self.stop_event.wait(self.INTERVAL)

    def check_pgn(self):
        """
        Reads the PGN file and emits new ClaimEntry objects.
        """

        self.lock.acquire()
        try:
            with open(self.filename, "r", encoding="utf-8") as pgn:
                game_index = 0

                while not self.stop_event.is_set():
                    game = read_game(pgn)
                    if not game:
                        break

                    # ---------------------------------------------
                    # FIX: Live PGN optional
                    # ---------------------------------------------
                    if (
                        self.live_pgn_option
                        and self.live_pgn_option.isChecked()
                        and game.headers.get("Result") != "*"
                    ):
                        continue

                    if self.stop_event.is_set():
                        break
                    
                    # Use ClaimsManager for checking instead of old Claims class
                    entries, dont_check, _ = self.claims_manager.run_all_claims([game], None, game_index=game_index)

                    for entry in entries:
                        self.add_entry_signal.emit(entry)

                    game_index += 1

        finally:
            self.lock.release()

    @staticmethod
    def is_file_updated(last_size: int, current_size: int):
        return current_size != 0 and last_size != current_size


# ---------------------------------------------------------
# STOP WORKERS
# ---------------------------------------------------------

class Stop(QThread):
    """Stops all running threads and resets the model."""

    enable_signal = pyqtSignal()
    disable_signal = pyqtSignal()

    __slots__ = ["stop_event", "make_pgn_worker", "scan_worker", "download_worker", "livechess_worker"]

    def __init__(self, stop_event: Event, make_pgn_worker: Thread,
                 scan_worker: QThread, download_worker: QThread = None, livechess_worker: QThread = None):
        super().__init__()
        self.stop_event = stop_event
        self.download_worker = download_worker
        self.livechess_worker = livechess_worker
        self.make_pgn_worker = make_pgn_worker
        self.scan_worker = scan_worker

    def run(self):
        self.disable_signal.emit()
        self.stop_event.set()

        if self.download_worker:
            self.download_worker.wait()
        
        if self.livechess_worker:
            self.livechess_worker.wait()

        self.scan_worker.wait()
        self.make_pgn_worker.join()

        self.enable_signal.emit()


# ---------------------------------------------------------
# MAKE PGN
# ---------------------------------------------------------

class MakePgn(Thread):
    """
    Creates a combined PGN file from all available sources.
    This worker does NOT emit Qt signals (it is a plain Thread).
    """

    INTERVAL = 4
    __slots__ = ["filepaths", "stop_event", "is_running", "lock", "daemon"]

    def __init__(self, filepaths: List[str], stop_event: Event = None, lock: Lock = None):
        super().__init__()
        self.filepaths = filepaths
        self.lock = lock
        self.stop_event = stop_event
        self.daemon = True

        app_path = get_appdata_path()
        self.filename = os.path.join(app_path, "games.pgn")

    def run(self) -> None:
        if not self.stop_event:
            return self.make_pgn()

        while not self.stop_event.is_set():
            self.make_pgn()
            self.stop_event.wait(self.INTERVAL)

    def make_pgn(self):
        """
        Merges all PGN files into a single combined PGN.
        Ensures proper separation between games.
        """

        data = b""
        for filepath in self.filepaths:
            try:
                with open(filepath, "rb") as in_file:
                    content = in_file.read().strip()
                    if not content:
                        continue
                    data += b"\n\n" + content + b"\n\n"
            except FileNotFoundError:
                continue

        self.lock_file()
        try:
            with open(self.filename, "wb") as file:
                file.write(data)
        finally:
            self.release_file()

    def lock_file(self):
        if self.lock:
            self.lock.acquire()

    def release_file(self):
        if self.lock:
            self.lock.release()

