# Akiba – Chess Arbiter Monitoring System
## User Documentation (Version 1.1)

---

## Table of Contents

1. [Introduction](#introduction)
2. [Data Sources](#data-sources)
3. [Claims](#claims)
4. [Reminders](#reminders)
5. [Differences between Claims and Reminders](#differences-between-claims-and-reminders)
6. [ACK (Acknowledgment) System](#ack-acknowledgment-system)
7. [Notifications](#notifications)
8. [Other Buttons](#other-buttons)
9. [Board Viewer – Game Visualization](#board-viewer–game-visualization)
10. [Fair-Play Analysis](#fair-play-analysis)

---

## Introduction

**Akiba** is a Monitoring System for Chess Arbiters that automatically analyzes chess games in real-time and alerts arbiters about important situations that require attention. Think of it as an independent tool, based on live chess broadcasts, that helps arbiters make informed decisions during tournaments.

---

## Data Sources

The application supports **three types of sources** that can be added in the "Add Sources" dialog. **All sources have LIVE functionality** - the program monitors them every 4 seconds:

### 1. Web URL
- URL to a PGN file on a website  
- Example: `https://example.com/tournament/games.pgn`
- **LIVE:** Program downloads the file **every 4 seconds** in real-time
- Ideal for live tournaments where the webpage is updated continuously

### 2. Local File
- Path to a PGN file on your computer
- Example: `C:\Tournaments\my_games.pgn`
- **LIVE:** Program checks the file size **every 4 seconds** - if it changes, it re-reads the file
- Ideal when an external program writes games to a file in real-time

### 3. LiveChessCloud Live
- Link to a tournament on the LiveChessCloud platform
- Example: `https://view.livechesscloud.com/#abcd1234-....`
- **LIVE:** Program downloads games from the tournament **every 4 seconds** in real-time (polling)
- **Round Number:** Default is round 1, you can select any round
- Each round is saved to a separate PGN file

**LIVE Summary:** All sources are monitored every 4 seconds - Web URL and LiveChessCloud re-download data, Local File checks if the size has changed.

---

## Claims

**Claims** are situations where a chess game ends immediately or a player can **file an official claim** according to FIDE rules. The program automatically detects the following types of claims:

### Claim Types

| Claim Type | Description | When it appears |
|------------|-------------|-----------------|
| **3-fold repetition** | Position repeated three times | When the same position on the board occurs for the third time (claimable draw) |
| **5-fold repetition** | Position repeated five times | When the same position on the board occurs for the fifth time (automatic game end) |
| **50-move rule** | 50-move rule | After 50 moves without pawn movement or capture (claimable draw) |
| **75-move rule** | 75-move rule | After 75 moves without pawn movement or capture (automatic game end) |
| **Stalemate** | Stalemate | When the player has no legal move but is not in check (automatic game end) |
| **Checkmate** | Checkmate | When the player is checkmated (automatic game end) |
| **Dead position** | Dead position | When neither player can deliver checkmate (automatic game end) |

### How Does Claim Detection Work?
- The program scans games **move by move**
- Each claim is recorded with:
  - Board number
  - Player names
  - Move number when the claim occurred
  - Explanatory comment

---

## Reminders

**Reminders** are informational warnings to help the arbiter prepare for upcoming situations or to inform about possible rule violations that must be verified by the arbiter. They do NOT end the game automatically but require the arbiter's attention.

### Reminder Types

| Reminder Type | Description | When it appears |
|---------------|-------------|-----------------|
| **Two fold repetition** | Position repeated twice (warning before 3-fold) | When the same position occurs for the second time - **Warning:** "Be careful, player may soon claim 3-fold repetition" |
| **45-move reminder** | Warning before 50-move rule | After 45 moves without pawn movement or capture - **Warning:** "In 5 more moves, 50-move claim will be possible" |
| **Time control warning** | Time control approaching | 2 moves before reaching the time control (e.g., at move 38 for control at move 40) - "Be careful, arbiter should be near the board" |
| **Low on time** | Player has low time remaining | When a player has less time than your threshold setting - "Warning, player may soon flag" |
| **Flag fall reminder** | Flag fall detected (time expired) | When a player's time reaches 0:00:00 - **Alert:** "Check if the flag has fallen on this board!" |
| **Illegal move warning** | Illegal move detected in game | When the program detects an illegal move in PGN - **Alert:** "Check the board situation immediately - there may be an illegal move or mistake in recording" |
| **Scoresheet change warning** | Scoresheet nearly full | When players are about to fill all fields (e.g., 55 moves) - "Bring new scoresheets" |
| **Sofia rule violation** | Illegal draw agreement | Draw made before move 30 (default threshold, adjustable by arbiter) |
| **Possible incorrect result** | Declared game result doesn't match Stockfish evaluation | When the recorded result in PGN headers (1-0, 0-1, 1/2-1/2) significantly differs from engine evaluation of the final position - **Alert:** "Check the game result - position evaluation suggests a different outcome" |

---

## Fair-Play Analysis

**Fair-Play Analysis** is a preliminary assessment tool that helps arbiters identify potentially suspicious games. The system analyzes each player's moves independently and assigns one of three risk levels:

### Level Indicators

| Level | Color | Action |
|-------|-------|-------------|
| **LOW** | 🟢 Green | None |
| **MEDIUM** | 🟠 Orange | Routine observation recommended |
| **HIGH** | 🔴 Red | Further review recommended |

### How to Run Fair-Play Analysis

1. Open a PGN file in the Board Viewer
2. Right-click on any game in the game list
3. Select **"Fair-Play Analysis"** from the context menu
4. View results with level indicators for both White and Black players

### Results Display

The analysis shows separate results for each player including:
- **T1 (Top Match Rate)** - Percentage of moves matching Stockfish's #1 choice
- **BR (Blunder Resistance)** - Resistance to blunders (0-100%)
- **APL (Average Point Loss)** - Average error margin in points
- **SPI (Sigmoidal Precision Index)** - Sigmoidal precision index score (~50 = human norm)

The level indicator is determined by either T1/BR or SPI thresholds, whichever triggers first.

🛡️ **SPI (Sigmoidal Precision Index) — Beta Version**

This tool is intended strictly for arbiters and is currently in its scaling phase. The data below does not imply any rule violation. Drawing conclusions from a single game carries high statistical risk; therefore, system outputs, if any, should be treated solely as suggestions for further routine actions.

---

## Differences between Claims and Reminders

| Feature | Claims | Reminders |
|---------|--------|-----------|
| **Status** | **MANDATORY** - cannot be disabled, always active | **OPTIONAL** - can be enabled/disabled in settings |
| **Purpose** | Detecting potential claims or automatic game ends according to FIDE rules | Helping the arbiter monitor tournament situations |
| **Recurrence** | Repeated as long as the condition persists | One-time per specific type (not repeated) |
| **Consequences** | Most cause immediate game end (checkmate, stalemate, dead position, 75-move, 5-fold). 3-fold and 50-move require arbiter verification with player involvement. | Only informational warning - does NOT automatically end the game |

---

## ACK (Acknowledgment) System

The ACK system allows you to mark claims or reminders as "resolved" once you've handled them. This helps keep your claim list clean and focused on active issues.

### How Does It Work?
1. When a claim or reminder is triggered, it appears in the claims table
2. After resolving the situation, you can mark it as **ACK** (acknowledged) ✅, using the right mouse button
3. Resolved (ACK) ✅ claims and reminders can be deleted from the claims table using the **"Clear Resolved (Claims)"** button

---

## Other Buttons

In the main window there are three main buttons:

### Start (Blue)
- **Function:** Starts scanning games and downloading data from sources
- For all sources, enables automatic refresh every 4 seconds

### Stop (Red)  
- Stops scanning

### Clear Resolved Claims Button
- Clears all acknowledged claims and reminders from the table

---

## Notifications

The application includes a notification system to alert arbiters about important events:

### Notification Types

| Notification Type | When it triggers | Purpose |
|-------------------|------------------|---------|
| **Claim detected** | When a claim situation is identified (3-fold, 50-move, checkmate, etc.) | Alert arbiter to verify and handle the claim |
| **Reminder triggered** | When a reminder condition is met (illegal move, low time, Sofia rule violation) | Inform arbiter of situations requiring attention |

### Notification Behavior
- Notifications appear as system alerts that require acknowledgment
- Sound alerts can be configured in application settings
- Critical notifications (checkmate, flag fall) have higher priority
- Notifications can be turned on or off

---

## Board Viewer – Game Visualization

Board Viewer is the main interface for browsing and analyzing games. Here's how to interpret visual markings:

### Colors and Markings in Board Viewer

| Element | Color/Meaning | When it appears |
|---------|---------------|-----------------|
| **Green board border** | Position repeated 3rd or 5th time (3-fold/5-fold repetition snapshot) | When position on the board occurs for the 3rd or 5th time |
| **Blue board border** | 50 or 75 moves from an irreversible move (50-moves/75-moves snapshot) | When 50 or 75 moves have passed since the last pawn move or a capture |
| **Red board border** | Illegal move detected in game | Indicates a position after the last legal move (the illegal move is added in the scoreshhet) |
| **Yellow board highlight** | Last executed move | Always after a move is made - the target square of the last move is highlighted yellow |

### Colors and Markings in a game notation (scoresheet)

| Element | Color/Meaning | When it appears |
|---------|---------------|-----------------|
| **Green text marking** | Position repeated 3rd or 5th time (concrete moves) | When position on the board occurs for the 3rd or 5th time |
| **Blue text marking** | 50 or 75 moves from a irreversible move (concrete moves) | When 50 or 75 moves have passed since the last pawn move or a capture |
| **Red text marking** | Illegal move detected in game (concrete move) | When an illegal move is made or a recording error occurs |
| **Yellow background** | Currently selected move | After clicking on a specific move in the notation below the board |

### Time Information (under player names)

- Format: `Lastname (Remaining Time)` + `Last move (Thinking Time)`
- Shows remaining time after each player's last move **remaining time** (time is static)
- Shows how long the player thought about their last move **last move thinking time** 

### Navigation in Board Viewer

#### Navigation buttons:
| Button | Function |
|--------|----------|
| **⏮** | First game in list / Start of current game |
| **◀** | Previous game / Previous move in game |
| **▶** | Next game / Next move in game |
| **⏭** | Last game in list / End of current game |

#### Keyboard navigation:
- Use **left/right arrow keys** to navigate between games (when list is active) or moves (when board/PGN is active)
- Use **up/down arrow keys** to scroll through the game list

### Game Filtering

- **Search field:** Enter player name or board number (e.g., "12")
- **"Show only active games" checkbox:** Shows only games with result `*` (ongoing)

---

## Summary

Akiba is a powerful tool for chess arbiters that:
- ✅ Automatically detects claims and reminders in games
- ✅ Supports multiple data sources simultaneously (URL, local files, LiveChessCloud)
- ✅ Combines games from different sources into one PGN file
- ✅ Visualizes key positions (3-fold/5-fold snapshots, illegal moves)
- ✅ Allows management of resolved claims through ACK system
- ✅ Has notification system for important events

### Data Collection

Data files are stored in `%APPDATA%\Akiba\` directory.

**Beacons**

The Akiba application sends anonymous data to Google Sheets for usage statistics. Each time you click the "Start" button, one entry is sent containing:
- **Device ID** - unique anonymous hash (cannot be linked to you)
- **Application version** - e.g., "1.1"  
- **Operating system** - e.g., "Windows 11"

Data is collected solely for statistical purposes (how many people use the program, which versions). We do NOT collect any personal data or information about chess games.

---