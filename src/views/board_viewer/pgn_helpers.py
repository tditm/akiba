"""PGN helper functions - extracted from BoardViewerWindow."""

import chess
import chess.pgn
import chess.svg
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QPixmap, QPainter


def load_games_from_file(pgn_path: str):
    """Load all games from a PGN file. Returns list of (index, game) tuples."""
    games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        index = 0
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            if not game.headers.get("White") or not game.headers.get("Black"):
                continue
            
            games.append((index, game))
            index += 1
    return games


def apply_filter(games, search_text: str, active_only: bool):
    """Filter games based on search text and active status. Returns filtered list."""
    filtered = []
    text = search_text.lower().strip()

    for index, game in games:
        white = game.headers.get("White", "").lower()
        black = game.headers.get("Black", "").lower()
        result = game.headers.get("Result", "").strip()

        if active_only and result in ("1-0", "0-1", "1/2-1/2", "½-½"):
            continue

        if not text:
            filtered.append((index, game))
            continue

        is_number = text.isdigit()
        if is_number and index == int(text):
            filtered.append((index, game))
            continue

        if text in white or text in black:
            filtered.append((index, game))

    return filtered


def format_game_item(index: int, game) -> str:
    """Format a game for display in the list widget."""
    white = game.headers.get("White", "White")
    black = game.headers.get("Black", "Black")
    result = game.headers.get("Result", "")

    if result == "1-0":
        result_text = "1-0"
    elif result == "0-1":
        result_text = "0-1"
    elif result in ("1/2-1/2", "½-½"):
        result_text = "½-½"
    else:
        result_text = ""

    if result_text:
        return f"{index + 1}. {white} – {black} ({result_text})"
    else:
        return f"{index + 1}. {white} – {black}"


def render_board_svg(game, move_list, move_index: int, size: int = 400) -> bytes:
    """Generate SVG board for current position."""
    if not game:
        return b""

    board = game.board()
    for i, move in enumerate(move_list):
        if i < move_index:
            board.push(move)

    svg_board = chess.svg.board(board=board, arrows=None, size=size)
    return svg_board.encode('utf-8')


def create_pixmap_from_svg(svg_bytes: bytes) -> QPixmap:
    """Convert SVG bytes to QPixmap for display."""
    renderer = QSvgRenderer(svg_bytes)
    size = renderer.defaultSize()
    pixmap = QPixmap(size.width(), size.height())
    pixmap.fill()
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def extract_clock(comment: str):
    """Extract [%clk HH:MM:SS] from a PGN comment."""
    if "[%clk" not in comment:
        return None
    try:
        start = comment.index("[%clk") + 6
        end = comment.index("]", start)
        return comment[start:end].strip()
    except Exception:
        return None


def extract_emt(comment: str):
    """Extract [%emt HH:MM:SS] from a PGN comment."""
    if "[%emt" not in comment:
        return None
    try:
        start = comment.index("[%emt") + 6
        end = comment.index("]", start)
        return comment[start:end].strip()
    except Exception:
        return None


def compute_repetition_snapshots(move_list) -> set:
    """Compute positions that appear for the third time (for threefold repetition)."""
    if not move_list:
        return set()

    board = chess.Board()
    key_map = {}

    for idx, move in enumerate(move_list):
        board.push(move)
        key = board._transposition_key()
        key_map.setdefault(key, []).append(idx)

    chosen_indices = []
    max_reps = 0
    latest_ply = -1

    for key, indices in key_map.items():
        reps_count = len(indices)
        if reps_count >= 3:
            last_idx_in_group = indices[-1]
            if reps_count > max_reps or (reps_count == max_reps and last_idx_in_group > latest_ply):
                max_reps = reps_count
                chosen_indices = indices
                latest_ply = last_idx_in_group

    return set(chosen_indices) if chosen_indices else set()


def build_pgn_html(game, highlight_index=None):
    """Generate HTML for the PGN view with clickable moves."""
    if not game:
        return "<p>No game loaded</p>"

    moves = list(game.mainline_moves())
    html_parts = ["<html><body style='font-family: Arial;'>"]

    white = game.headers.get("White", "Unknown")
    black = game.headers.get("Black", "Unknown")
    result = game.headers.get("Result", "*")
    date = game.headers.get("Date", "????.??.??")
    event = game.headers.get("Event", "?")
    
    # Check for errors in the game
    has_errors = hasattr(game, 'errors') and game.errors
    
    html_parts.append(f"<h3>{white} - {black}</h3>")
    html_parts.append(f"<p><b>Event:</b> {event}<br>")
    html_parts.append(f"<b>Date:</b> {date}<br>")
    html_parts.append(f"<b>Result:</b> {result}</p>")
    
    html_parts.append("<hr>")

    board = game.board()
    move_counter = 1

    for i, move in enumerate(moves):
        san = board.san(move)
        is_white = (i % 2 == 0)

        if is_white:
            if highlight_index is not None and i == highlight_index:
                html_parts.append(f"{move_counter}. <a href='move_{i}' style='background:#ffff99'>{san}</a> ")
            else:
                html_parts.append(f"{move_counter}. <a href='move_{i}'>{san}</a> ")

            if i + 1 < len(moves):
                next_node = moves[i + 1]
                comment = getattr(next_node, 'comment', '') or ''
                clk = extract_clock(comment)
                emt = extract_emt(comment)
                if clk != "--:--:--" or emt:
                    emt_str = f" ({emt})" if emt else ""
                    html_parts.append(f"<span style='color:#666;font-size:10px'>[{clk}{emt_str}]</span> ")

            move_counter += 1
        else:
            if highlight_index is not None and i == highlight_index:
                html_parts.append(f"<a href='move_{i}' style='background:#ffff99'>{san}</a><br>")
            else:
                html_parts.append(f"<a href='move_{i}'>{san}</a><br>")

            if i + 1 < len(moves):
                next_node = moves[i + 1]
                comment = getattr(next_node, 'comment', '') or ''
                clk = extract_clock(comment)
                emt = extract_emt(comment)
                if clk != "--:--:--" or emt:
                    emt_str = f" ({emt})" if emt else ""
                    html_parts.append(f"<span style='color:#666;font-size:10px'>[{clk}{emt_str}]</span><br>")

        board.push(move)

    # Show illegal move info at the end of PGN notation (before Total moves section)
    if has_errors:
        import re
        html_parts.append("<hr>")  # Separator before illegal move info
        
        for i, error in enumerate(game.errors):
            san_match = re.search(r"illegal san: '([^']+)'", str(error))
            fullmove_match = re.search(r"w - - (\d+) (\d+)", str(error))
            
            if san_match and fullmove_match:
                illegal_san = san_match.group(1)
                fullmove_num = int(fullmove_match.group(2))
                html_parts.append(f"<p style='color:red; font-weight:bold;'>⚠ {fullmove_num}. {illegal_san} - illegal move!</p>")
            elif san_match:
                illegal_san = san_match.group(1)
                html_parts.append(f"<p style='color:red; font-weight:bold;'>⚠ {illegal_san} - illegal move!</p>")
            else:
                html_parts.append(f"<p style='color:red; font-weight:bold;'>⚠ Illegal move detected!</p>")

    html_parts.append("<hr>")  # Separator before stats section
    html_parts.append(f"<p><b>Total moves:</b> {len(moves)}<br>")
    html_parts.append(f"<b>Final FEN:</b> <code style='font-size:9px'>{board.fen()}</code></p>")

    html_parts.append("</body></html>")
    return "".join(html_parts)