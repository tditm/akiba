from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QMenuBar, QCheckBox, QSpinBox, QWidget, QHBoxLayout, QWidgetAction, QSizePolicy)


class MenuBarBuilder:
    def __init__(self, view):
        self.view = view

    def build_menu(self) -> None:
        menu_bar = self.view.menuBar()
        self._build_alerts_menu(menu_bar)
        self._build_reminders_menu(menu_bar)
        self._build_notifications_menu(menu_bar)
        self._build_help_menu(menu_bar)

    def _build_alerts_menu(self, menu_bar) -> None:
        """Build Alerts menu with Sofia rule, flag fall, illegal move, and incorrect result."""
        alerts_menu = menu_bar.addMenu('&Alerts')

        # Sofia rule (Draw agreement)
        widget_sofia = QWidget()
        layout_sofia = QHBoxLayout()
        layout_sofia.setContentsMargins(10, 2, 10, 2)
        self.view.sofia_action = QCheckBox('Draw before move completed (Sofia rule)')
        self.view.sofia_action.setChecked(False)
        layout_sofia.addWidget(self.view.sofia_action)
        self.view.sofia_spin.setFixedSize(60, 24)
        self.view.sofia_spin.setStyleSheet("QSpinBox { text-align: right; padding-right: 5px; }")
        layout_sofia.addWidget(self.view.sofia_spin)
        widget_sofia.setLayout(layout_sofia)
        widget_action_sofia = QWidgetAction(self.view)
        widget_action_sofia.setDefaultWidget(widget_sofia)
        alerts_menu.addAction(widget_action_sofia)

        # Flag fall
        widget_flagfall = QWidget()
        layout_flagfall = QHBoxLayout()
        layout_flagfall.setContentsMargins(10, 2, 10, 2)
        self.view.flag_fall_action = QCheckBox('Flag fall (00:00:00)')
        self.view.flag_fall_action.setChecked(False)
        layout_flagfall.addWidget(self.view.flag_fall_action)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_flagfall.addWidget(spacer)
        widget_flagfall.setLayout(layout_flagfall)
        widget_action_flagfall = QWidgetAction(self.view)
        widget_action_flagfall.setDefaultWidget(widget_flagfall)
        alerts_menu.addAction(widget_action_flagfall)

        # Illegal move reminder
        widget_illegalmove = QWidget()
        layout_illegalmove = QHBoxLayout()
        layout_illegalmove.setContentsMargins(10, 2, 10, 2)
        self.view.illegal_move_action = QCheckBox('First illegal move')
        self.view.illegal_move_action.setChecked(False)
        layout_illegalmove.addWidget(self.view.illegal_move_action)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_illegalmove.addWidget(spacer)
        widget_illegalmove.setLayout(layout_illegalmove)
        widget_action_illegalmove = QWidgetAction(self.view)
        widget_action_illegalmove.setDefaultWidget(widget_illegalmove)
        alerts_menu.addAction(widget_action_illegalmove)

        # Possible incorrect result reminder
        widget_incorrectresult = QWidget()
        layout_incorrectresult = QHBoxLayout()
        layout_incorrectresult.setContentsMargins(10, 2, 10, 2)
        self.view.possible_incorrect_result_action = QCheckBox('Possible incorrect result')
        self.view.possible_incorrect_result_action.setChecked(False)
        layout_incorrectresult.addWidget(self.view.possible_incorrect_result_action)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_incorrectresult.addWidget(spacer)
        widget_incorrectresult.setLayout(layout_incorrectresult)
        widget_action_incorrectresult = QWidgetAction(self.view)
        widget_action_incorrectresult.setDefaultWidget(widget_incorrectresult)
        alerts_menu.addAction(widget_action_incorrectresult)

    def _build_reminders_menu(self, menu_bar) -> None:
        """Build Reminders menu with low time, 50-move, threefold, scoresheet, and time control."""
        reminders_menu = menu_bar.addMenu('&Reminders')


        # Low time reminder
        widget_lowtime = QWidget()
        layout_lowtime = QHBoxLayout()
        layout_lowtime.setContentsMargins(10, 2, 10, 2)
        self.view.low_time_action = QCheckBox('Low time - if less second than')
        self.view.low_time_action.setChecked(False)
        layout_lowtime.addWidget(self.view.low_time_action)
        self.view.low_time_spin.setFixedSize(60, 24)
        self.view.low_time_spin.setStyleSheet("QSpinBox { text-align: right; padding-right: 5px; }")
        layout_lowtime.addWidget(self.view.low_time_spin)
        widget_lowtime.setLayout(layout_lowtime)
        widget_action_lowtime = QWidgetAction(self.view)
        widget_action_lowtime.setDefaultWidget(widget_lowtime)
        reminders_menu.addAction(widget_action_lowtime)

        # Possible 50-move reminder
        widget_fiftymove = QWidget()
        layout_fiftymove = QHBoxLayout()
        layout_fiftymove.setContentsMargins(10, 2, 10, 2)
        self.view.possible_fiftymove_action = QCheckBox('Possible 50-move (45 moves)')
        self.view.possible_fiftymove_action.setChecked(False)
        layout_fiftymove.addWidget(self.view.possible_fiftymove_action)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_fiftymove.addWidget(spacer)
        widget_fiftymove.setLayout(layout_fiftymove)
        widget_action_fiftymove = QWidgetAction(self.view)
        widget_action_fiftymove.setDefaultWidget(widget_fiftymove)
        reminders_menu.addAction(widget_action_fiftymove)

        # Possible threefold reminder
        widget_threefold = QWidget()
        layout_threefold = QHBoxLayout()
        layout_threefold.setContentsMargins(10, 2, 10, 2)
        self.view.possible_threefold_action = QCheckBox('Possible threefold (2 fold)')
        self.view.possible_threefold_action.setChecked(False)
        layout_threefold.addWidget(self.view.possible_threefold_action)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_threefold.addWidget(spacer)
        widget_threefold.setLayout(layout_threefold)
        widget_action_threefold = QWidgetAction(self.view)
        widget_action_threefold.setDefaultWidget(widget_threefold)
        reminders_menu.addAction(widget_action_threefold)

        # Scoresheet change reminder
        widget_scoresheet = QWidget()
        layout_scoresheet = QHBoxLayout()
        layout_scoresheet.setContentsMargins(10, 2, 10, 2)
        self.view.scoresheet_action = QCheckBox('Scoresheet change after move')
        self.view.scoresheet_action.setChecked(False)
        layout_scoresheet.addWidget(self.view.scoresheet_action)
        self.view.scoresheet_spin.setFixedSize(60, 24)
        self.view.scoresheet_spin.setStyleSheet("QSpinBox { text-align: right; padding-right: 5px; }")
        layout_scoresheet.addWidget(self.view.scoresheet_spin)
        widget_scoresheet.setLayout(layout_scoresheet)
        widget_action_scoresheet = QWidgetAction(self.view)
        widget_action_scoresheet.setDefaultWidget(widget_scoresheet)
        reminders_menu.addAction(widget_action_scoresheet)

        # Time control reminder
        widget_timecontrol = QWidget()
        layout_timecontrol = QHBoxLayout()
        layout_timecontrol.setContentsMargins(10, 2, 10, 2)
        self.view.timecontrol_action = QCheckBox('Time control after move')
        self.view.timecontrol_action.setChecked(False)
        layout_timecontrol.addWidget(self.view.timecontrol_action)
        self.view.timecontrol_spin.setFixedSize(60, 24)
        self.view.timecontrol_spin.setStyleSheet("QSpinBox { text-align: right; padding-right: 5px; }")
        layout_timecontrol.addWidget(self.view.timecontrol_spin)
        widget_timecontrol.setLayout(layout_timecontrol)
        widget_action_timecontrol = QWidgetAction(self.view)
        widget_action_timecontrol.setDefaultWidget(widget_timecontrol)
        reminders_menu.addAction(widget_action_timecontrol)

    def _build_notifications_menu(self, menu_bar) -> None:
        """Build Notifications menu with enable notifications toggle."""
        notifications_menu = menu_bar.addMenu('&Notifications')

        # Enable notifications
        widget_notifications = QWidget()
        layout_notifications = QHBoxLayout()
        layout_notifications.setContentsMargins(10, 2, 10, 2)
        self.view.notifications_enabled_action = QCheckBox('Enable Windows/Mac notifications')
        self.view.notifications_enabled_action.setChecked(True)
        layout_notifications.addWidget(self.view.notifications_enabled_action)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout_notifications.addWidget(spacer)
        widget_notifications.setLayout(layout_notifications)
        widget_action_notifications = QWidgetAction(self.view)
        widget_action_notifications.setDefaultWidget(widget_notifications)
        notifications_menu.addAction(widget_action_notifications)

    def _build_help_menu(self, menu_bar) -> None:
        """Build Help menu with About and User Manual."""
        options_menu = menu_bar.addMenu('&Help')

        # About
        about_action = QAction('About', self.view)
        options_menu.addAction(about_action)
        about_action.triggered.connect(self.view.controller.on_about_clicked)

        # User Manual
        user_manual_action = QAction('User Manual', self.view)
        options_menu.addAction(user_manual_action)
        user_manual_action.triggered.connect(self.view.controller.on_user_manual_clicked)
