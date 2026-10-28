"""LiveChessCloud API client for fetching live tournament data and generating PGN."""

import re
import urllib.request
from typing import Dict, List, Optional, Any
from urllib.error import HTTPError, URLError

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "X-Client": "ChessClaimTool/LiveChess"
}

LIVECHESS_BASE = "https://1.pool.livechesscloud.com/get"


def get_ssl_cert_path() -> str:
    """Get path to SSL certificate for HTTPS requests."""
    from src.helpers import resource_path
    return resource_path("cert/cacert.pem")


def extract_tournament_id(url: str) -> Optional[str]:
    """Extract tournament ID (UUID) from a view.livechesscloud.com URL."""
    try:
        match = re.search(r'[view.livechesscloud\.com/#]([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', url)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def _fetch_json(url: str, timeout: int = 30) -> Optional[Any]:
    """Fetch JSON data from a URL with error handling."""
    try:
        req = urllib.request.Request(url, headers=BROWSER_HEADERS)
        cert_path = get_ssl_cert_path()
        response = urllib.request.urlopen(req, timeout=timeout, cafile=cert_path)
        return response.read()
    except (HTTPError, URLError, TimeoutError, Exception):
        return None


def get_tournament_url(tournament_id: str) -> str:
    return f"{LIVECHESS_BASE}/{tournament_id}/tournament.json"


def get_index_url(tournament_id: str, round_num: int) -> str:
    return f"{LIVECHESS_BASE}/{tournament_id}/round-{round_num}/index.json"


def get_game_url(tournament_id: str, round_num: int, game_num: int) -> str:
    return f"{LIVECHESS_BASE}/{tournament_id}/round-{round_num}/game-{game_num}.json?poll"


class TournamentData:
    def __init__(self):
        self.id = ""
        self.name = "?"
        self.location = "?"
        self.timecontrol = ""  # Add time control field
        self.rounds = []


class RoundData:
    def __init__(self):
        self.date = ""
        self.pairings = []


class GameData:
    def __init__(self):
        self.live = False
        self.serialnr = ""
        self.result = "*"
        self.moves = []
        self.clock = None  # Add clock data (if available)


def fetch_tournament(tournament_id: str) -> Optional[TournamentData]:
    """Fetch tournament metadata."""
    url = get_tournament_url(tournament_id)
    data = _fetch_json(url)
    
    if not data:
        return None
    
    try:
        import json
        parsed = json.loads(data)
        
        t = TournamentData()
        t.id = parsed.get("id", "")
        t.name = parsed.get("name", "?")
        t.location = parsed.get("location", "?")
        # Add time control if available (e.g., "90 + 30")
        t.timecontrol = parsed.get("timecontrol", "")
        for r in parsed.get("rounds", []):
            t.rounds.append({"count": r.get("count", 0), "live": r.get("live", 0)})
        return t
    except Exception:
        return None


def fetch_index(tournament_id: str, round_num: int) -> Optional[RoundData]:
    """Fetch index (round pairing and date) data."""
    url = get_index_url(tournament_id, round_num)
    data = _fetch_json(url)
    
    if not data:
        return None
    
    try:
        import json
        parsed = json.loads(data)
        
        rd = RoundData()
        rd.date = parsed.get("date", "")
        rd.pairings = parsed.get("pairings", [])
        return rd
    except Exception:
        return None


def fetch_game(tournament_id: str, round_num: int, game_num: int) -> Optional[GameData]:
    """Fetch game moves (with polling)."""
    url = get_game_url(tournament_id, round_num, game_num)
    
    for attempt in range(3):
        data = _fetch_json(url, timeout=10)
        if not data:
            continue
        
        try:
            import json
            parsed = json.loads(data)
            
            g = GameData()
            g.live = parsed.get("live", False)
            g.serialnr = str(parsed.get("serialNr", ""))
            g.result = _map_game_result(parsed.get("result", "*"))
            # moves now includes time data: "move whiteTime+blackTime"
            g.moves = parsed.get("moves", [])
            # clock field might contain current game state
            g.clock = parsed.get("clock")  # Could be null or contain timing info
            return g
        except Exception:
            pass
    
    return None


def _map_game_result(result_code: str) -> str:
    result_map = {"WHITEWIN": "1-0", "BLACKWIN": "0-1", "DRAW": "1/2-1/2", "NO_RESULT": "*", "*": "*"}
    return result_map.get(result_code, "*")


def _format_moves(moves: List[str]) -> str:
    """Format moves into PGN notation with clock and EMT annotations.
    
    API returns moves in format: "move whiteClock+whiteEMT" or "move blackClock+blackEMT"
    Each move contains the time data for the player who made that move.
    """
    if not moves:
        return ""
    
    result = []
    
    def sec_to_clock(total_sec: int) -> str:
        hours = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        seconds = total_sec % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    for i, move in enumerate(moves):
        if not move:
            continue
        
        parts = move.split()
        move_san = parts[0] if parts else ""
        
        if not move_san:
            continue
        
        # Parse clock and EMT from move data (e.g., "d4 5456+4")
        # First value = clock time, Second value (+) = EMT for this move
        if len(parts) > 1 and "+" in parts[1]:
            try:
                time_parts = parts[1].split("+")
                clock_sec = int(time_parts[0])
                emt_sec = int(time_parts[1]) if len(time_parts) > 1 else 0
                
                clock_str = sec_to_clock(clock_sec)
                emt_str = sec_to_clock(emt_sec)
                
                move_number = i // 2 + 1
                
                # ePGN format: after each move, show [%clk] and [%emt] for the player who moved
                if i % 2 == 0:
                    result.append(f"{move_number}. {move_san} {{[%clk {clock_str}]}} {{[%emt {emt_str}]}}")
                else:
                    result.append(f"{move_san} {{[%clk {clock_str}]}} {{[%emt {emt_str}]}}")
            except (ValueError, IndexError):
                # Fallback if parsing fails
                move_number = i // 2 + 1
                if i % 2 == 0:
                    result.append(f"{move_number}. {move_san}")
                else:
                    result.append(move_san)
        else:
            # No time data available - fallback to simple format
            move_number = i // 2 + 1
            if i % 2 == 0:
                result.append(f"{move_number}. {move_san}")
            else:
                result.append(move_san)
    
    return " ".join(result)


def _get_player_name(player: Dict[str, Any]) -> str:
    """Get full player name from pairing data."""
    if not player:
        return "?"
    fname = player.get("fname", "") or ""
    lname = player.get("lname", "") or ""
    mname = player.get("mname", "") or ""
    if not fname and not lname:
        return "?"
    full_name = f"{lname}, {fname}"
    if mname:
        full_name += f" {mname}"
    return full_name.strip().strip(",") or "?"


def generate_pgn_for_round(tournament: TournamentData, round_data: RoundData, 
                           games: Dict[int, GameData], round_num: int) -> str:
    """Generate PGN string for games in a specific round."""
    
    def _format_date(date_str: str) -> str:
        if not date_str or len(date_str) < 10:
            return "?"
        parts = date_str.split(".")
        if len(parts) == 3:
            return f"{parts[0]}.{parts[1]}.{parts[2]}"
        return date_str if date_str else "?"
    
    pgn_games = []
    
    for game_num, pairing in enumerate(round_data.pairings, start=1):
        game = games.get(game_num)
        if not game or not game.moves:
            continue
        
        white = _get_player_name(pairing.get("white"))
        black = _get_player_name(pairing.get("black"))
        result = game.result if game.result else pairing.get("result", "*")
        ply_count = len(game.moves) * 2
        
        # Generate round number with board: "round.board" format (e.g., "5.1", "5.2")
        # This matches the standard format used by chess servers
        round_with_board = f"{round_num}.{game_num}"
        
        headers = [
            f'[Event "{tournament.name}"]',
            f'[Site "{tournament.location}"]',
            f'[Date "{_format_date(round_data.date)}"]',
            f'[Round "{round_with_board}"]',  # Round + board number (e.g., "5.1")
            f'[White "{white}"]',
            f'[Black "{black}"]',
            f'[Result "{result}"]',
            f'[PlyCount "{ply_count}"]',
        ]
        
        # Add ePGN header if time data is available (indicates extended PGN support)
        if tournament.timecontrol:
            headers.insert(1, '[ePGN "0.1;DGT LiveChess/2.2.11"]')
            headers.append(f'[TimeControl "{tournament.timecontrol}"]')
        
        moves_str = _format_moves(game.moves)
        pgn_game = "\n".join(headers) + "\n\n" + moves_str + f" {result}"
        pgn_games.append(pgn_game)
    
    return "\n\n".join(pgn_games)


def get_rounds_with_games(rounds: List[Dict[str, int]]) -> List[int]:
    """Get list of round numbers that have games."""
    return [idx + 1 for idx, r in enumerate(rounds) if r.get("count", 0) > 0]


class LiveChessCloudSource:
    def __init__(self, url: str, round_num: Optional[int] = None):
        self.url = url
        self.tournament_id = extract_tournament_id(url) or ""
        self.round_num = round_num
    
    @property
    def is_valid(self) -> bool:
        return bool(self.tournament_id)
    
    def get_filename(self) -> str:
        """Generate filename including round number for separate PGN files per round."""
        if self.round_num and self.round_num > 0:
            return f"livechess_{self.tournament_id[:8]}_r{self.round_num}.pgn"
        else:
            return f"livechess_{self.tournament_id[:8]}.pgn"
