import chess
import chess.pgn
import chess.svg
import io

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLabel, QTextBrowser, QPushButton, QLineEdit,
    QSizePolicy, QCheckBox
)
from PyQt6.QtGui import QPixmap, QPainter, QPen
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtSvg import QSvgRenderer

from .pgn_helpers import (
    load_games_from_file,
    apply_filter,
    format_game_item,
    render_board_svg,
    create_pixmap_from_svg,
    build_pgn_html,
    extract_clock,
    extract_emt,
    compute_repetition_snapshots,
)

class BoardViewerWindow(QMainWindow):
    """
    PGN viewer window with LIVE PGN support and threefold snapshots.
    """

    def showEvent(self, event):
        super().showEvent(event)
        self.update_board()

    def __init__(self, pgn_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Akiba - Board Viewer")
        self.resize(1100, 580)

        self.pgn_path = pgn_path
        self.games = []              # [(index (1-based), game)]
        self.filtered_games = []     # subset of self.games
        self.current_game = None
        self.current_board = None
        self.move_list = []
        self.move_index = 0
        self.current_game_index = 0  # row index in filtered_games (0-based)

        self.repetition_snapshots = set()

        self._build_ui()
        self._load_games()
        self._refresh_game_list()

        if self.filtered_games:
            self.load_game_at_index(0)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.centralWidget().setFocus()

        self.pgn_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.game_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.search_box.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def _last_clk_for_color(self, nodes, upto_idx: int, is_white: bool):
        """
        Returns the last [%clk] for a given side (is_white)
        from nodes[0..upto_idx].
        """
        for i in range(upto_idx, -1, -1):
            if (i % 2 == 0) == is_white:
                comment = getattr(nodes[i], "comment", "") or ""
                clk = self.extract_clock(comment)
                if clk:
                    return clk
        return "--:--:--"

    def _last_emt_for_color(self, nodes, upto_idx: int, is_white: bool):
        """
        Returns the last [%emt] for a given side (is_white)
        from nodes[0..upto_idx].
        """
        for i in range(upto_idx, -1, -1):
            if (i % 2 == 0) == is_white:
                comment = getattr(nodes[i], "comment", "") or ""
                emt = self.extract_emt(comment)
                if emt is not None:
                    return emt
        return None

    # ---------------------------------------------------------
    # LOAD GAME / SELECTION
    # ---------------------------------------------------------
    def load_game_at_index(self, row: int):
        """
        Load a specific game by row index in self.filtered_games.
        
        Args:
            row: Row index (0-based) in filtered_games list
        """
        if not self.filtered_games:
            return
        if row < 0 or row >= len(self.filtered_games):
            return

        # Set current game
        self.current_game_index = row
        
        # Block automatic switching during programmatic load
        self._loading_game = True
        try:
            index, game = self.filtered_games[row]  # index = 0-based PGN position
            
            self.current_game = game
            self.current_board = game.board()
            self.move_list = list(game.mainline_moves())
            self.move_index = len(self.move_list)

            self._compute_repetition_snapshots()

            if hasattr(self, "game_list"):
                self.game_list.setCurrentRow(row)
        finally:
            self._loading_game = False

        self._refresh_pgn_with_highlight()
        self.update_board()

    def on_game_selected(self, arg) -> None:
        """Handle game list selection change - only if triggered by user."""
        # Prevent recursive calls during programmatic loading
        if self._loading_game:
            return
        
        if isinstance(arg, int):
            row = arg
        else:
            row = self.game_list.row(arg)

        self.load_game_at_index(row)

    # ---------------------------------------------------------
    # UI SETUP
    # ---------------------------------------------------------
    def _build_ui(self) -> None:
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # LEFT SIDE
        left_layout = QVBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by player name or by board number ...")
        self.search_box.textChanged.connect(self._apply_filter)
        left_layout.addWidget(self.search_box)

        # Checkbox: show only active games
        self.chk_active_only = QCheckBox("Show only active games")
        self.chk_active_only.stateChanged.connect(self._apply_filter)
        left_layout.addWidget(self.chk_active_only)

        self.game_list = QListWidget()
        self.game_list.setMinimumWidth(350)
        
        # NEW: Block automatic switching when viewing a claim
        self._loading_game = False  # Flag to prevent recursive calls
        
        self.game_list.currentRowChanged.connect(self.on_game_selected)
        left_layout.addWidget(self.game_list)

        # --- Game navigation buttons (FIRST / PREV / NEXT / LAST GAME) ---
        game_nav_layout = QHBoxLayout()

        self.btn_game_first = QPushButton("⏮")
        self.btn_game_prev = QPushButton("◀")
        self.btn_game_next = QPushButton("▶")
        self.btn_game_last = QPushButton("⏭")

        for btn in [self.btn_game_first, self.btn_game_prev, self.btn_game_next, self.btn_game_last]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.btn_game_first.clicked.connect(self.go_first_game)
        self.btn_game_prev.clicked.connect(self.go_prev_game)
        self.btn_game_next.clicked.connect(self.go_next_game)
        self.btn_game_last.clicked.connect(self.go_last_game)

        game_nav_layout.addWidget(self.btn_game_first)
        game_nav_layout.addWidget(self.btn_game_prev)
        game_nav_layout.addWidget(self.btn_game_next)
        game_nav_layout.addWidget(self.btn_game_last)

        left_layout.addLayout(game_nav_layout)

        main_layout.addLayout(left_layout, 40)

        # RIGHT SIDE
        right_layout = QVBoxLayout()

        self.board_label = QLabel()
        self.board_label.setMinimumSize(350, 350)
        self.board_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.board_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # PLAYER NAME LABELS (medium size)
        self.black_name_label = QLabel("Black: --:--:--")
        self.black_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.black_name_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.black_name_label.setFixedHeight(24)

        self.white_name_label = QLabel("White: --:--:--")
        self.white_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.white_name_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.white_name_label.setFixedHeight(24)

        right_layout.addWidget(self.black_name_label)
        right_layout.addWidget(self.board_label, stretch=60)
        right_layout.addWidget(self.white_name_label)

        self.pgn_view = QTextBrowser()
        self.pgn_view.setOpenLinks(False)
        self.pgn_view.anchorClicked.connect(self.on_move_clicked)
        self._apply_no_underline_style()

        font = self.game_list.font()
        font.setPointSize(10)
        self.pgn_view.setFont(font)
        right_layout.addWidget(self.pgn_view, 40)

        # Navigation buttons (moves)
        buttons_layout = QHBoxLayout()
        self.btn_start = QPushButton("⏮")
        self.btn_prev = QPushButton("◀")
        self.btn_next = QPushButton("▶")
        self.btn_end = QPushButton("⏭")

        for btn in [self.btn_start, self.btn_prev, self.btn_next, self.btn_end]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.btn_start.clicked.connect(self.go_start)
        self.btn_prev.clicked.connect(self.go_prev)
        self.btn_next.clicked.connect(self.go_next)
        self.btn_end.clicked.connect(self.go_end)

        buttons_layout.addWidget(self.btn_start)
        buttons_layout.addWidget(self.btn_prev)
        buttons_layout.addWidget(self.btn_next)
        buttons_layout.addWidget(self.btn_end)

        right_layout.addLayout(buttons_layout)
        main_layout.addLayout(right_layout, 60)

    def _apply_no_underline_style(self):
        self.pgn_view.document().setDefaultStyleSheet("""
            a { text-decoration: none; color: black; }
            a:link { text-decoration: none; color: black; }
            a:visited { text-decoration: none; color: black; }
            a:hover { text-decoration: none; color: black; }
            a:active { text-decoration: none; color: black; }
        """)

    # ---------------------------------------------------------
    # LOAD GAMES / FILTER
    # ---------------------------------------------------------
    def _load_games(self) -> None:
        """Load all games from PGN file with 0-based indexing."""
        self.games.clear()
        
        try:
            self.games = load_games_from_file(self.pgn_path)
        except Exception as e:
            self.game_list.addItem(f"Error loading PGN: {e}")

        self.filtered_games = list(self.games)

    def _apply_filter(self) -> None:
        # Remember currently selected game by its "index" (1-based from PGN)
        selected_index = None
        if 0 <= self.current_game_index < len(self.filtered_games):
            selected_index = self.filtered_games[self.current_game_index][0]

        text = self.search_box.text().lower().strip()
        active_only = self.chk_active_only.isChecked()

        # Use helper function from pgn_helpers.py
        self.filtered_games = apply_filter(self.games, text, active_only)

        self._refresh_game_list()

        if not self.filtered_games:
            return

        # Try to return to the same game (by index), if it's still in the filter
        if selected_index is not None:
            for row, (idx, game) in enumerate(self.filtered_games):
                if idx == selected_index:
                    self.load_game_at_index(row)
                    break
            else:
                # If game not found in new filter – select the first one
                self.load_game_at_index(0)
        else:
            self.load_game_at_index(0)

    def _refresh_game_list(self) -> None:
        # Hide list during rebuild to avoid flickering
        self.game_list.setVisible(False)
        self.game_list.clear()

        for index, game in self.filtered_games:
            item_text = format_game_item(index, game)
            self.game_list.addItem(item_text)

        # Show ready list
        self.game_list.setVisible(True)

    # ---------------------------------------------------------
    # PGN HTML (Arbiter version with numbered related positions)
    # ---------------------------------------------------------
    def build_pgn_html(self, game, highlight_index=None) -> str:
        board = game.board()
        moves = list(game.mainline_moves())

        white = game.headers.get("White", "White")
        black = game.headers.get("Black", "Black")

        # Generate current repetition map based on the logic selected above
        # Sort indices chronologically to properly number repetitions (1, 2, 3...)
        sorted_rep_indices = sorted(list(self.repetition_snapshots))
        total_reps = len(sorted_rep_indices)
        
        # Determine the correct main label (3-fold or 5-fold) based on actual number of repetitions
        if total_reps >= 5:
            base_label = "5-fold"
        elif total_reps >= 3:
            base_label = "3-fold"
        else:
            base_label = None

        html_parts = []
        # Player surnames are already above the board, so we skip them in game notation
        # html_parts.append(
        #     f'<div style="font-size:14pt; font-weight:bold; margin-bottom:10px;">'
        #     f'{white} – {black}'
        #     f'</div>'
        # )
        html_parts.append('<div style="height:8px;"></div>')

        ply_index = 0
        move_number = 1
        i = 0

        while i < len(moves):
            html_parts.append(
                f'<span style="font-weight:bold; color:#333;">[{move_number}]</span> '
            )

            # --- White Move ---
            white_move = moves[i]
            white_san = board.san(white_move)
            board.push(white_move)

            flags = []
            # 1. Handle position repetitions (Always as first flag)
            if base_label and ply_index in sorted_rep_indices:
                rep_number = sorted_rep_indices.index(ply_index) + 1
                flags.append(f"{base_label} {rep_number}/{total_reps} WHITE")
            
            # 2. Handle move counters (Fixed indentation - independent of repetitions!)
            if board.halfmove_clock >= 150:
                flags.append("75-move rule")
            elif board.halfmove_clock >= 100:
                flags.append("50-move rule")

            flag_text = ""
            if flags:
                flag_text = (
                    ' <span style="color:#008000; font-weight:bold;">('
                    + ", ".join(flags)
                    + ')</span>'
                )

            if highlight_index == ply_index:
                html_parts.append(
                    f'<span style="color:red; font-weight:bold;"><a href="move_{ply_index}">{white_san}</a></span>{flag_text} '
                )
            else:
                html_parts.append(
                    f'<a href="move_{ply_index}">{white_san}</a>{flag_text} '
                )

            ply_index += 1
            i += 1

            # --- Black's Move (Black Move) ---
            if i < len(moves):
                black_move = moves[i]
                black_san = board.san(black_move)
                board.push(black_move)

                flags = []
                # 1. Handle position repetitions
                if base_label and ply_index in sorted_rep_indices:
                    rep_number = sorted_rep_indices.index(ply_index) + 1
                    flags.append(f"{base_label} {rep_number}/{total_reps} BLACK")
                
                # 2. Handle move counters (Independent of repetitions)
                if board.halfmove_clock >= 150:
                    flags.append("75-move rule")
                elif board.halfmove_clock >= 100:
                    flags.append("50-move rule")

                flag_text = ""
                if flags:
                    flag_text = (
                        ' <span style="color:#008000; font-weight:bold;">('
                        + ", ".join(flags)
                        + ')</span>'
                    )

                if highlight_index == ply_index:
                    html_parts.append(
                        f'<span style="color:red; font-weight:bold;"><a href="move_{ply_index}">{black_san}</a></span>{flag_text} '
                    )
                else:
                    html_parts.append(
                        f'<a href="move_{ply_index}">{black_san}</a>{flag_text} '
                    )

                ply_index += 1
                i += 1

            move_number += 1

        # Show illegal move info at the END of PGN notation (after last move)
        has_errors = hasattr(game, 'errors') and game.errors
        if has_errors:
            import re
            for error in game.errors:
                san_match = re.search(r"illegal san: '([^']+)'", str(error))
                fullmove_match = re.search(r"w - - (\d+) (\d+)", str(error))
                
                if san_match and fullmove_match:
                    illegal_san = san_match.group(1)
                    fullmove_num = int(fullmove_match.group(2))
                    # Add at the end of moves with red color, like 3-fold notation
                    html_parts.append(
                        f'<span style="color:red; font-weight:bold;"> [{fullmove_num}] {illegal_san} - illegal move!</span>'
                    )
                elif san_match:
                    illegal_san = san_match.group(1)
                    html_parts.append(
                        f'<span style="color:red; font-weight:bold;"> ... {illegal_san} - illegal move!</span>'
                    )

        return "".join(html_parts)

    # ---------------------------------------------------------
    # LIVE PGN RELOAD (from controller)
    # ---------------------------------------------------------
    def reload_pgn(self, pgn_path):
        """
        Reload PGN file safely.
        If the PGN is temporarily broken (live write), keep old games.
        """
        old_move_index = self.move_index
        old_len = len(self.move_list) if self.move_list else 0

        try:
            with open(pgn_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            return

        # temporary list – don't touch self.games until parsing succeeds
        new_games = []

        pgn_io = io.StringIO(text)
        index = 0  # ← CHANGED: 0-based to match ClaimsStore!

        while True:
            try:
                game = chess.pgn.read_game(pgn_io)
            except Exception:
                # parser failed – abort and DON'T update the list
                return

            if game is None:
                break

            # skip incomplete / erroneous games
            if not game.headers.get("White") or not game.headers.get("Black"):
                continue

            new_games.append((index, game))
            index += 1

        # if parsing returned 0 games – DON'T update the list
        if not new_games:
            return

        # only now we replace
        self.pgn_path = pgn_path
        self.games = new_games
        self.filtered_games = list(self.games)

        self._apply_filter()

        # restore move / auto-follow
        if self.current_game and self.move_list:
            # user was at the end of the OLD game if their index = old length
            was_at_end = (old_move_index == old_len)

            if was_at_end:
                # auto-follow → go to the end of the NEW game
                self.move_index = len(self.move_list)
            else:
                # restore previous move (within the bounds of the new list)
                self.move_index = max(0, min(old_move_index, len(self.move_list)))

            self.update_board()
            self._refresh_pgn_with_highlight()

    # ---------------------------------------------------------
    # REPETITION SNAPSHOTS (Referee version: only key sequence)
    # ---------------------------------------------------------
    def _compute_repetition_snapshots(self):
        """Compute repetition snapshots using helper function."""
        self.repetition_snapshots = compute_repetition_snapshots(self.move_list)

    # ---------------------------------------------------------
    # CLOCK PARSING
    # ---------------------------------------------------------
    def extract_clock(self, comment: str):
        """
        Extracts [%clk HH:MM:SS] from a PGN comment.
        Returns string "HH:MM:SS" or None.
        """
        if "[%clk" not in comment:
            return None

        try:
            start = comment.index("[%clk") + 6
            end = comment.index("]", start)
            return comment[start:end].strip()
        except Exception:
            return None

    def extract_emt(self, comment: str):
        """
        Extracts [%emt HH:MM:SS] from PGN comment.
        Returns string "HH:MM:SS" (or "MM:SS"), or None.
        """
        if "[%emt" not in comment:
            return None

        try:
            start = comment.index("[%emt") + 6
            end = comment.index("]", start)
            return comment[start:end].strip()
        except Exception:
            return None

    # ---------------------------------------------------------
    # BOARD RENDERING
    # ---------------------------------------------------------
    def update_board(self) -> None:
        if self.current_board is None:
            self.board_label.clear()
            self.white_name_label.setText("White: --:--:--")
            self.black_name_label.setText("Black: --:--:--")
            return

        board = self.current_board.copy()

        current_index = self.move_index - 1
        is_snapshot = current_index in self.repetition_snapshots

        border_color = Qt.GlobalColor.green if is_snapshot else Qt.GlobalColor.transparent
        
        # Red border for illegal moves - ONLY when at the last valid position
        has_illegal_move = hasattr(self.current_game, 'errors') and self.current_game.errors
        if has_illegal_move and self.move_index == len(self.move_list):
            # Show red border only when viewing the final (last valid) position
            border_color = Qt.GlobalColor.red

        last_move = None
        for move in self.move_list[:self.move_index]:
            last_move = move
            board.push(move)

        svg = chess.svg.board(
            board,
            lastmove=last_move,
            colors={
                "square light lastmove": "#fff066",
                "square dark lastmove": "#fff066"
            }
        )

        renderer = QSvgRenderer(bytearray(svg, encoding="utf-8"))

        label_size = self.board_label.size()
        border = 12
        available = min(label_size.width(), label_size.height())
        side = max(available - border * 2, 280)

        pixmap = QPixmap(side + border * 2, side + border * 2)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(border_color)
        pen.setWidth(border)
        painter.setPen(pen)

        offset = border // 2
        painter.drawRect(
            offset,
            offset,
            side + border * 2 - border,
            side + border * 2 - border
        )

        renderer.render(painter, QRectF(border, border, side, side))
        painter.end()

        self.board_label.setPixmap(pixmap)

        # Refresh PGN view with highlight (includes illegal move message)
        if self.current_game:
            highlight = self.move_index - 1 if self.move_index > 0 else None
            html = self.build_pgn_html(self.current_game, highlight_index=highlight)
            self.pgn_view.setHtml(html)
            self._apply_no_underline_style()

        # --- PLAYER NAMES AND CLOCK UPDATE ---
        if self.current_game is None:
            return

        white_name = self.current_game.headers.get("White", "White")
        black_name = self.current_game.headers.get("Black", "Black")

        # If we are BEFORE the first move → show only names
        if self.move_index == 0:
            self.white_name_label.setText(white_name)
            self.black_name_label.setText(black_name)
            return

        # Normal move → move_idx points to the executed move
        move_idx = self.move_index - 1

        nodes = list(self.current_game.mainline())

        # If move out of range → do nothing
        if not (0 <= move_idx < len(nodes)):
            return

        node = nodes[move_idx]
        comment = getattr(node, "comment", "") or ""

        clk = self.extract_clock(comment)
        emt = self.extract_emt(comment)

        # Whose move is it?
        is_white_move = (move_idx % 2 == 0)

        # Calculate times for both players
        black_clk = self._last_clk_for_color(nodes, move_idx - 1, is_white=False)
        white_clk = self._last_clk_for_color(nodes, move_idx - 1, is_white=True)

        # Format: Name (XX:XX:XX) - Last move: XX:XX:XX
        white_time_format = f"{white_name} ({white_clk})"
        black_time_format = f"{black_name} ({black_clk})"

        emt_white = self._last_emt_for_color(nodes, move_idx - 1, is_white=True)
        emt_black = self._last_emt_for_color(nodes, move_idx - 1, is_white=False)

        # --- WHITE MOVE ---
        if is_white_move:
            if emt is not None:
                self.white_name_label.setText(f"<u>{white_time_format}</u> - Last move ({emt})")
            else:
                self.white_name_label.setText(f"<u>{white_time_format}</u>")

            if emt_black is not None:
                self.black_name_label.setText(f"{black_time_format} - Last move ({emt_black})")
            else:
                self.black_name_label.setText(black_time_format)

        # --- BLACK MOVE ---
        else:
            if emt is not None:
                self.black_name_label.setText(f"<u>{black_time_format}</u> - Last move ({emt})")
            else:
                self.black_name_label.setText(f"<u>{black_time_format}</u>")

            if emt_white is not None:
                self.white_name_label.setText(f"{white_time_format} - Last move ({emt_white})")
            else:
                self.white_name_label.setText(white_time_format)




    # ---------------------------------------------------------
    # KEYBOARD CONTROL
    # ---------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key.Key_Left:
            self.go_prev()
            return
        if key == Qt.Key.Key_Right:
            self.go_next()
            return
        if key == Qt.Key.Key_Home:
            self.go_start()
            return
        if key == Qt.Key.Key_End:
            self.go_end()
            return
        if key == Qt.Key.Key_Up:
            self.go_prev_game()
            return
        if key == Qt.Key.Key_Down:
            self.go_next_game()
            return        

        super().keyPressEvent(event)

    # ---------------------------------------------------------
    # MOVE NAVIGATION
    # ---------------------------------------------------------
    def _refresh_pgn_with_highlight(self):
        if not self.current_game:
            return
        highlight = self.move_index - 1 if self.move_index > 0 else None
        html = self.build_pgn_html(self.current_game, highlight_index=highlight)
        self.pgn_view.setHtml(html)
        self._apply_no_underline_style()

    def go_start(self) -> None:
        self.move_index = 0
        self.update_board()
        self._refresh_pgn_with_highlight()

    def go_prev(self) -> None:
        if self.move_index > 0:
            self.move_index -= 1
        self.update_board()
        self._refresh_pgn_with_highlight()

    def go_next(self) -> None:
        if self.move_index < len(self.move_list):
            self.move_index += 1
        self.update_board()
        self._refresh_pgn_with_highlight()

    def go_end(self) -> None:
        self.move_index = len(self.move_list)
        self.update_board()
        self._refresh_pgn_with_highlight()

    # ---------------------------------------------------------
    # MOVE CLICK
    # ---------------------------------------------------------
    def on_move_clicked(self, url):
        move_str = url.toString()
        index = int(move_str.split("_")[1])

        self.move_index = index + 1
        self.update_board()
        self.highlight_current_move(index)

    # ---------------------------------------------------------
    # MOVE HIGHLIGHT
    # ---------------------------------------------------------
    def highlight_current_move(self, index):
        if self.current_game is None:
            return

        html = self.build_pgn_html(self.current_game, highlight_index=index)
        self.pgn_view.setHtml(html)
        self._apply_no_underline_style()

    # ---------------------------------------------------------
    # JUMP TO MOVE (for controller)
    # ---------------------------------------------------------
    def jump_to_move(self, move_index: int):
        if not self.move_list:
            return

        if move_index < 0:
            move_index = 0
        if move_index > len(self.move_list):
            move_index = len(self.move_list)

        self.move_index = move_index
        self.update_board()
        self._refresh_pgn_with_highlight()

    # ---------------------------------------------------------
    # GAME NAVIGATION
    # ---------------------------------------------------------
    def go_first_game(self):
        if not self.filtered_games:
            return
        self.load_game_at_index(0)

    def go_prev_game(self):
        if not self.filtered_games:
            return
        row = self.game_list.currentRow()
        if row > 0:
            self.load_game_at_index(row - 1)

    def go_next_game(self):
        if not self.filtered_games:
            return
        row = self.game_list.currentRow()
        if row < len(self.filtered_games) - 1:
            self.load_game_at_index(row + 1)

    def go_last_game(self):
        if not self.filtered_games:
            return
        last_row = len(self.filtered_games) - 1
        self.load_game_at_index(last_row)

