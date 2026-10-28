from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QStandardItemModel, QPixmap, QStandardItem, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeView,
    QHeaderView,
    QAbstractItemView,
    QMenu,
)

from src.helpers import resource_path
from src.models.events import ClaimType

if TYPE_CHECKING:
    from src.controllers import ChessClaimController


class ClaimsTable(QWidget):
    """
    Claims table component with styling and interaction logic.
    
    Displays detected claims/reminders in a sortable table.
    Handles row clicks to open Board Viewer at specific game positions.
    """
    
    __slots__ = [
        "controller",
        "table",
        "model",
        "ok_pixmap",
        "error_pixmap",
        "current_entry_game_index",
        "notification",
    ]

    def __init__(self, controller: ChessClaimController) -> None:
        super().__init__()
        self.controller = controller
        
        # Use same ClaimsStore as controller - SINGLE SOURCE OF TRUTH
        self.claims_store = controller.claims_store

        # Status icons
        self.ok_pixmap = QPixmap(resource_path("check_icon.png"))
        self.error_pixmap = QPixmap(resource_path("error_icon.png"))

        # Table setup
        self.table = QTreeView()
        self.model = QStandardItemModel()
        
        # Initialize notification system
        import platform
        if platform.system() == "Darwin":
            from src.notifications.mac import Notification
            self.notification = Notification()
        elif platform.system() == "Windows":
            from windows_toasts import WindowsToaster, ToastImageAndText2, ToastDisplayImage, ToastDuration
            self.notification = WindowsToaster("Akiba")
        else:
            self.notification = None

        self._setup_table()
        self._build_layout()

    def keyPressEvent(self, event):
        """
        Handle keyboard events for the table.
        Space bar toggles Ack status on selected row(s).
        
        Args:
            event: The key event object
        """
        if event.key() == Qt.Key.Key_Space:
            # Get currently selected rows
            selected_rows = self.get_selected_rows()
            
            if selected_rows:
                # Toggle Ack status for the first selected row
                self.toggle_ack(selected_rows[0])
                return  # Event handled
        
        super().keyPressEvent(event)

    def _setup_table(self) -> None:
        """Configure the claims table view and model."""
        # Allow focus for keyboard events (space bar handling)
        self.table.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setSortingEnabled(True)
        self.table.setIndentation(0)
        self.table.setUniformRowHeights(True)
        
        # Allow multiple row selection with Ctrl/Cmd or Shift
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # IMPORTANT: Set selection behavior to preserve existing selection on clicks
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Set column headers - added "Ack" column at the end (after Move)
        labels = ["#", "Timestamp", "Type", "Board", "Players", "Move", "Ack"]
        self.model.setHorizontalHeaderLabels(labels)
        self.table.setModel(self.model)

        # Row click → open Board Viewer on DOUBLE CLICK (not single click)
        self.table.doubleClicked.connect(self.on_claim_double_clicked)

        # Context menu for Ack toggle (right-click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        header = self.table.header()

        # Auto-size for small columns
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)   # #
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)   # Timestamp
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)   # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)   # Board
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)   # Ack

        # Players → stretch (fills available space), with minimum width of 150px
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(4, 150)   # Minimum width

        # Move → fixed width (250px - 50px = 200px)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 200)   # Fixed width reduced by 50px

        # Make sure header does not stretch the last section
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(20)

        # Allow horizontal scrollbar if needed
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def _build_layout(self) -> None:
        """Build the widget layout."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def add_claim(self, entry) -> None:
        """
        Add a new row to the claims table.
        
        Args:
            entry: ClaimEntry object with all claim data
        """
        # Skip adding to table if already cleared (was marked via Clear Resolved)
        if entry.cleared:
            return
            
        claim_type = entry.type.value
        board_number = entry.board_number
        players = entry.players
        move = entry.move

        # Store game_index for safe row removal
        self.current_entry_game_index = entry.game_index

        # Remove previous rows for same players and claim type (or weaker claim)
        self.remove_rows_by_claim_type(claim_type, players)

        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Items to display in the table - added empty Ack column at the end
        items = [
            str(self.model.rowCount() + 1),  # Sequential number
            timestamp,
            claim_type,
            board_number,
            players,
            move,
            "",                               # Ack (empty by default)
        ]

        row = []
        for idx, item in enumerate(items):
            standard_item = self._create_standard_item(item, idx)
            row.append(standard_item)

        self.model.appendRow(row)

        # Store game and move index for Board Viewer navigation
        first_item = self.model.item(self.model.rowCount() - 1, 0)
        first_item.setData({
            "game_index": entry.game_index,
            "move_index": entry.move_counter,
            "start_move_index": entry.start_move_counter,
            "game_id": entry.game_id,
        }, Qt.ItemDataRole.UserRole)

        # Set fixed row height for the new row to maintain consistency
        # Note: QTreeView doesn't support setRowHeight, relying on uniform row heights instead
        
        # No resize - let Stretch mode handle Move column automatically
        # Backup calls resizeColumnToContents but it may cause issues with Fixed columns
        self.table.scrollToBottom()

        # Desktop notification
        self._notify(claim_type, players, move)
        self.table.clearSelection()

    def show_context_menu(self, pos):
        """
        Show context menu on right-click to toggle Ack status.
        
        Args:
            pos: Mouse position in table coordinates
        """
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        
        row = index.row()
        
        # Create simple context menu with only Add/Remove ✅ option
        context_menu = QMenu(self)
        
        # Check current Ack status (Ack column is at position 6 - the last one)
        ack_item = self.model.item(row, 6)
        has_ack = ack_item.text() == "✅"
        
        if has_ack:
            action = context_menu.addAction("Unacknowledge")
        else:
            action = context_menu.addAction("Acknowledge")
        
        action.triggered.connect(lambda: self.toggle_ack(row))
        
        # Show menu at global position
        context_menu.exec(self.table.mapToGlobal(pos))

    def toggle_ack(self, row):
        """
        Toggle Ack status (add/remove ✅) for a specific row.
        Maintains fixed row height by using consistent font sizing.
        
        Args:
            row: Row index to toggle
        """
        ack_item = self.model.item(row, 6)  # Ack column at position 6 (last)
        
        if ack_item.text() == "✅":
            ack_item.setText("")
        else:
            ack_item.setText("✅")

    @staticmethod
    def _create_standard_item(item: str, idx: int) -> QStandardItem:
        """
        Create a styled QStandardItem for the claims table.
        
        Bold for claim type column, red color for strong claims.
        
        Args:
            item: Text to display
            idx: Column index
            
        Returns:
            Configured QStandardItem
        """
        standard_item = QStandardItem(item)
        standard_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set slightly larger font size for all items to give more vertical space (prevents height changes with emoji)
        font = standard_item.font()
        font.setPixelSize(13)
        standard_item.setFont(font)

        # Bold text for claim type column (now at position 3 after adding Ack column)
        if idx == 3:
            font = standard_item.font()
            font.setBold(True)
            standard_item.setFont(font)

        # Fixed font size for Ack column (position 6) to prevent row height changes
        if idx == 6:
            font = standard_item.font()
            font.setPixelSize(15)  # Slightly larger for emoji visibility
            standard_item.setFont(font)

        # Red color for strong claims (automatic game-ending results)
        if idx == 2 and item in ["5-fold repetition", "75-move rule", "Stalemate", "Checkmate", "Dead position"]:
            brush = standard_item.foreground()
            brush.setColor(QColor("red"))
            standard_item.setForeground(brush)

        return standard_item

    def on_claim_double_clicked(self, index) -> None:
        """
        Handle double-click on a claim row and open Board Viewer
        at the correct game and move.
        
        Args:
            index: QModelIndex of the clicked cell
        """
        # Get data from column 0 of the SAME row (regardless of which column was clicked)
        first_col_index = index.model().index(index.row(), 0, index.parent())
        first_col_item = self.model.itemFromIndex(first_col_index)
        
        if first_col_item is None:
            return

        # Get data from userData (stored as dictionary)
        data = first_col_item.data(Qt.ItemDataRole.UserRole)
        
        if data is None:
            return
        
        game_index = data.get("game_index")
        move_index = data.get("move_index")
        game_id = data.get("game_id")

        if game_index is None or move_index is None:
            return

        # Open Board Viewer for this claim
        self.controller.open_viewer_for_claim(game_index, move_index, game_id)

    def _notify(self, claim_type: str, players: str, move: str) -> None:
        """Send a desktop notification depending on the OS."""
        import platform
        from src.helpers import resource_path
        
        # Check if notifications are enabled in controller settings
        if not getattr(self.controller, 'notifications_enabled', True):
            return  # Skip notification if disabled
        
        if platform.system() == "Darwin":
            self.notification.clearNotifications()
            self.notification.notify(claim_type, players, move)

        elif platform.system() == "Windows":
            try:
                from windows_toasts import ToastImageAndText2, ToastDisplayImage, ToastDuration
                toast = ToastImageAndText2()
                toast.SetHeadline(str(claim_type))
                toast.SetBody(f"{players}\n{move}")
                toast.AddImage(ToastDisplayImage.fromPath(resource_path("notification_icon.png")))
                toast.SetDuration(ToastDuration("short"))
                self.notification.show_toast(toast)
            except Exception:
                # Fallback to simple text notification
                try:
                    from windows_toasts import ToastText1
                    toast = ToastText1()
                    toast.SetHeadline(str(claim_type))
                    toast.SetBody(f"{players}\n{move}")
                    self.notification.show_toast(toast)
                except Exception:
                    pass

    def remove_rows_by_claim_type(self, claim_type: str, players: str) -> None:
        """
        Remove previous rows for the same players and same or weaker claim type.
        Uses game_index instead of players string to avoid mismatches.
        
        Args:
            claim_type: Type of claim to match
            players: Player names (not used in comparison, kept for API compatibility)
        """
        model = self.model
        rows_to_remove = []

        for row in range(model.rowCount()):
            # Claim type is now at column 3 (was 2 before adding Ack column)
            model_type = model.item(row, 3).text()

            data = model.item(row, 0).data(Qt.ItemDataRole.UserRole)
            model_game_index = data.get("game_index") if data else None

            if model_type == claim_type and model_game_index == self.current_entry_game_index:
                rows_to_remove.append(row)

        for row in reversed(rows_to_remove):
            model.removeRow(row)

        # Re-number remaining rows
        for i in range(model.rowCount()):
            model.item(i, 0).setText(str(i + 1))

    def clear(self) -> None:
        """Clear all rows from the claims table."""
        # Use removeRow like baseline to preserve model structure and column settings
        while self.model.rowCount() > 0:
            self.model.removeRow(0)

    # Aliases for backward compatibility with controller
    refresh_table = resize_table = lambda self: None  # No-op to avoid layout issues

    def currentIndex(self):
        """Alias for table.currentIndex() - returns current selected index."""
        return self.table.currentIndex()

    def get_selected_rows(self) -> list:
        """
        Get list of selected row indices.
        
        Returns:
            List of unique row indices that are currently selected, sorted in ascending order
        """
        # Use selectionModel to get all selected indexes and extract unique rows
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return []
        # Use set to ensure uniqueness and sort for consistent order
        return sorted(set([index.row() for index in selection]))

    def clear_ack_rows(self) -> None:
        """
        Clear only acknowledged (✅) rows from the table view.
        
        Does NOT remove from ClaimsStore - these claims may reappear after restart
        if user hasn't explicitly cleared them via Clear Resolved button.
        """
        model = self.model
        rows_to_remove = []
        
        # Find all rows with Ack status (✅ in column 6) that have cleared=True
        for row in range(model.rowCount()):
            ack_item = model.item(row, 6)
            if ack_item and ack_item.text() == "✅":
                data = model.item(row, 0).data(Qt.ItemDataRole.UserRole)
                game_index = data.get("game_index") if data else None
                
                # Only remove rows that have cleared=True (were explicitly cleared via Clear Resolved)
                if game_index is not None:
                    claim = self.claims_store.get_claim_by_game_index(game_index)
                    if claim and claim.cleared:
                        rows_to_remove.append(row)
        
        if not rows_to_remove:
            return  # No acknowledged rows found
        
        # Remove from highest to lowest to maintain valid indices
        for row in reversed(rows_to_remove):
            self.model.removeRow(row)
        
        # Re-number remaining rows
        for i in range(self.model.rowCount()):
            self.model.item(i, 0).setText(str(i + 1))
        
        # Clear selection after removing
        self.table.clearSelection()

    def clear_selected_rows(self) -> None:
        """
        Remove all acknowledged (✅) rows from the table and mark them as cleared.
        These claims will NOT reappear after restart.
        
        Called when user clicks "Clear Resolved" button.
        """
        model = self.model
        rows_to_remove = []
        
        # Find all rows with Ack status (✅ in column 6)
        for row in range(model.rowCount()):
            ack_item = model.item(row, 6)
            if ack_item and ack_item.text() == "✅":
                # Get game_index to mark as cleared in ClaimsStore
                data = model.item(row, 0).data(Qt.ItemDataRole.UserRole)
                game_index = data.get("game_index") if data else None
                
                # Mark claim as cleared in ClaimsStore
                if game_index is not None:
                    self.claims_store.mark_cleared(game_index)
                
                rows_to_remove.append(row)
        
        if not rows_to_remove:
            return  # No acknowledged rows found
        
        # Remove from highest to lowest to maintain valid indices
        for row in reversed(rows_to_remove):
            self.model.removeRow(row)

        # Re-number remaining rows
        for i in range(self.model.rowCount()):
            self.model.item(i, 0).setText(str(i + 1))
        
        # Clear selection
        self.table.clearSelection()
