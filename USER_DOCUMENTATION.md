# Akiba – Chess Arbiter Monitoring System
## User Documentation (Version 1.0)

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

---

## Introduction

**Akiba** is a Chess Arbiter Monitoring System for chess arbiters that automatically analyzes chess games and detects claim situations and reminders. The program supports games from various sources: local files, websites, and the LiveChessCloud platform.

---

## Data Sources

The application supports **three types of sources** that can be added in the "Add Sources" dialog. **All sources have LIVE functionality** - the program monitors them every 4 seconds:

### 1. Web URL (Option 0)
- URL to a PGN file on a website  
- Example: `https://example.com/tournament/games.pgn`
- **LIVE:** Program downloads the file **every 4 seconds** in real-time
- Ideal for live tournaments where the webpage is updated continuously

### 2. Local File (Option 1)
- Path to a PGN file on your computer
- Example: `C:\Tournaments\my_games.pgn`
- **LIVE:** Program checks the file size **every 4 seconds** - if it changes, it re-reads the file
- Ideal when an external program writes games to a file in real-time

### 3. LiveChessCloud Live (Option 2)
- Link to a tournament on the LiveChessCloud platform
- Example: `https://view.livechesscloud.com/#abcd1234-....`
- **LIVE:** Program downloads games from the tournament **every 4 seconds** in real-time (polling)
- **Round Number:** Default is round 1, you can select any round (1-9999)
- Each round is saved to a separate PGN file

**LIVE Summary:** All sources are monitored every 4 seconds - Web URL and LiveChessCloud re-download data, Local File checks if the size has changed.

---

## Claims

**Claims** are situations where a player can **file an official claim** according to FIDE rules. The program automatically detects the following types of claims:

### Claim Types

| Claim Type | Description | When it appears |
|------------|-------------|-----------------|
| **3-fold repetition** | Position repeated three times | When the same position on the board occurs for the third time |
| **5-fold repetition** | Position repeated five times | When the same position on the board occurs for the fifth time |
| **50-move rule** | 50-move rule | After 50 moves without pawn movement or capture (claimable draw) |
| **75-move rule** | 75-move rule | After 75 moves without pawn movement or capture (automatic game end) |
| **Stalemate** | Stalemate | When the player has no legal move but is not in check |
| **Checkmate** | Checkmate | When the player is checkmated |
| **Dead position** | Dead position | When neither player can deliver checkmate (e.g., king vs king) |

### How Claim Detection Works?
- The program scans games **move by move**
- Each claim is recorded with:
  - Board number (table number)
  - Player names
  - Move number when the claim occurred
  - Explanatory comment (e.g., "First counting move: X")

---

## Reminders

**Reminders** are informational warnings to help the arbiter prepare for upcoming situations. They do NOT end the game automatically but require the arbiter's attention.

### Reminder Types

| Reminder Type | Description | When it appears |
|---------------|-------------|-----------------|
| **Two fold repetition** | Position repeated twice (warning before 3-fold) | When the same position occurs for the second time - **Warning:** "Be careful, player may soon claim 3-fold repetition" |
| **45-move reminder** | Warning before 50-move rule | After 45 moves without pawn movement or capture - **Warning:** "In 5 more moves, 50-move claim will be possible" |
| **Time control warning** | Time control approaching | 2 moves before reaching the time control (e.g., at move 38 for control at move 40) - "Be careful, arbiter should be near the board" |
| **Low on time** | Player has low time remaining | When a player has less time than your threshold setting - "Warning, player may soon flag" |
| **Flag fall reminder** | Flag fall detected (time expired) | When a player's time reaches 0:00:00 - **Alert:** "Check if the flag has fallen on this board!" |
| **Illegal move warning** | Illegal move detected in game | When the program detects an illegal move in PGN - **Alert:** "Check the board situation immediately - there may be a mistake in recording or execution" |
| **Scoresheet change warning** | Scoresheet nearly full | When players are about to fill all fields (e.g., 60 moves) - "Bring new scoresheets" |
| **Sofia rule violation** | Illegal offer of draw | Offer of draw made before move 30 (default threshold, adjustable by arbiter) |

### Important Notes:
- **Two fold:** Warning that position has been repeated twice. Arbiter should pay attention as player may soon claim 3-fold repetition.
- **45-move reminder:** Not the actual 50-move rule, but a warning to prepare for it. After 45 moves without capture or pawn move, only 5 more moves until claimable draw.
- **Time control:** Reminder that time control is approaching. If control is at move 40 and current move is 38, remind arbiter to be ready!
- **Low on time:** Means "niedoczas" - player has less seconds remaining than the configured threshold. Arbiter should check if the player may flag soon.
- **Flag fall:** Time has expired (0:00:00). This is different from "low on time" - this means the clock actually hit zero!
- **Illegal move:** Program detected an illegal move in PGN analysis. Check immediately if there was a mistake in move execution or notation.
- **Scoresheet change:** Warning that players are about to fill their scoresheets (typically 60 fields). Arbiter should bring new paper.
- **Sofia rule:** Only flags draw offers before move 30. Draw offers after move 30 don't violate the rules.

---

## Differences between Claims and Reminders

| Feature | Claims | Reminders |
|---------|--------|-----------|
| **Status** | **MANDATORY** - cannot be disabled, always active | **OPTIONAL** - can be enabled/disabled in settings |
| **Purpose** | Detecting official claims according to FIDE rules | Helping the arbiter monitor tournament situations |
| **Consequences** | Most cause immediate game end (checkmate, stalemate, dead position, 75-move, non-legal). 3-fold and 50-move require arbiter verification with player involvement. | Only informational warning - does NOT automatically end the game |
| **Disableable** | ❌ NO - claims are always active | ✅ YES - reminders can be disabled |

### Key Differences in Practice:

**Claims (always active):**
- Detect situations that end games according to FIDE rules
- Cannot be disabled - they're an integral part of the monitoring system
- Examples: Checkmate, Stalemate, Dead Position, 75-move rule, 3-fold repetition, 50-move rule

**Reminders (optional):**
- Help the arbiter prepare for upcoming situations
- Can be disabled if not needed in a particular tournament
- Examples: 45-move reminder (warning before 50-moves), Time control approaching, Low on time, Scoresheet change

### Example Usage:

| Situation | Type | Arbiter Action |
|-----------|------|----------------|
| Player claims draw after position repetition (3-fold) | **Claim** | Check the position, confirm or reject the claim |
| Program shows "45 moves played" | **Reminder** | Be alert - in 5 moves player can claim draw with 50-move rule |
| Player has less time on clock than threshold (e.g., <30s) | **Reminder** | Go to the table - player may flag soon |
| Illegal move detected in game | **Claim** | Check what happened - player might have made a wrong move or there's an error in PGN |

---

## ACK (Acknowledgment) System

The ACK system allows you to mark claims as "resolved" once you've handled them. This helps keep your claim list clean and focused on active issues.

### How it works?
1. When a claim is detected, it appears in the claims table
2. After resolving the situation, you can mark it as **ACK** (acknowledged)
3. ACK claims remain in the system for history and can be restored with the **"Restore Resolved Claims"** button

### Example Usage:
- Players claimed 3-fold repetition → arbiter comes with scoresheets, resolves the issue → mark as ACK ✅
- Players passed time control (50-move) without claiming → situation no longer relevant → mark as ACK ✅  
- Player did not file a claim based on 3-fold repetition in due time → situation no longer relevant → mark as ACK ✅

**Note:** ACK claims can be restored with the **"Restore Resolved Claims"** button if they turn out to need attention again.

---

## Notifications

---

## Other Buttons

In the main window there are three main buttons:

### Start (Blue)
- **Function:** Starts scanning games and downloading data from sources
- For all sources, enables automatic refresh every 4 seconds

### Stop (Red)  
- Stops scanning. Entries with ACK status will not reappear after pressing start again.

### Clear Resolved Claims Button
- Clears all acknowledged claims from the table
- Use this when you want to start fresh for a new round/tournament

---

## Board Viewer – Game Visualization

Board Viewer is the main interface for browsing and analyzing games. Here's how to interpret visual markings:

### Colors and Markings in Board Viewer

| Element | Color/Meaning | When it appears |
|---------|---------------|-----------------|
| **Green board border** | Position repeated 3rd or 5th time (3-fold/5-fold repetition snapshot) | When position on the board occurs for the 3rd or 5th time - key position for repetition claim |
| **Red board border** | Illegal move detected in game | Only when you're on the last correct move before the illegal move |
| **Yellow board highlight** | Last executed move | Always after a move is made - the target square of the last move is highlighted yellow |
| **Yellow background in PGN notation** | Currently selected move | After clicking on a specific move in the notation below the board |

### Where are information shown?

#### 1. Chess Board (left side)
- Shows current position after selected move
- **Green border** = 3-fold/5-fold repetition snapshot
- **Red border** = illegal move in game (viewing last valid position)

#### 2. PGN Game Notation (right side under board)
- List of all moves in algebraic notation
- Clicking on any move moves the board to that position
- **Yellow background** = currently selected move

#### 3. Time Information (under player names)
- Format: `Lastname (Time)` 
- Shows remaining time after each player's **last move** (static)
- Example: `Karpov, A. (00:15:32) – Kasparov, G. (00:42:18)`
- **Thinking time in last move:** Shows how long the player thought about their last move

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

For questions or issues, check application logs in `%APPDATA%\Akiba\` directory.

### Data Collection (Beacon)

The Akiba application sends anonymous data to Google Sheets for usage statistics. Each time you click the "Start" button, one entry is sent containing:
- **Device ID** - unique anonymous hash (cannot be linked to you)
- **Application version** - e.g., "1.0"  
- **Operating system** - e.g., "Windows 10"

Data is collected solely for statistical purposes (how many people use the program, which versions). We do NOT collect any personal data or information about chess games.

---