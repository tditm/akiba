# Stockfish Engine Setup Instructions

## Required File

This folder should contain a file named **`stockfish.exe`**.

## Tested Version

The application has been tested with:
- `stockfish_15_x64_avx2.exe`

## Setup Steps

1. Download Stockfish chess engine from the official website: https://stockfishchess.org/download/
2. Rename the downloaded file to **`stockfish.exe`**
3. Place the renamed file in this folder (`engine/`)

## Compatibility Notes

### Recommended Versions
- **Stockfish 15+** (64-bit AVX2 versions) - Fully tested and recommended
- **Stockfish 16/17** - Should work without issues
- Any modern Stockfish version supporting the UCI protocol should be compatible

### Potentially Incompatible Versions
- **32-bit versions** - May have performance limitations or compatibility issues on modern systems
- **Very old versions (pre-Stockfish 10)** - May lack features or have different UCI command syntax
- **Non-standard builds** - Custom or modified builds that deviate significantly from standard UCI protocol may not work correctly
- **macOS/Linux versions** - This application requires the Windows executable (`stockfish.exe`)

### Version Selection Tips
When downloading Stockfish, look for:
- **x64** or **64-bit** architecture
- **AVX2** support if your CPU supports it (better performance)
- Official releases from stockfishchess.org are recommended over third-party builds

## Verification

After placing `stockfish.exe` in this folder, the application should automatically detect and use the engine. If you encounter any issues:
1. Verify the file is named exactly `stockfish.exe` (case-insensitive on Windows)
2. Ensure the file is not blocked by Windows (right-click → Properties → Unblock if present)
3. Check that your Stockfish version supports the UCI protocol (all modern versions do)
