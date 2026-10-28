import enum
import os
import platform
import sys


APP_NAME = "Akiba"


def resource_path(relative_path: str) -> str:
    """
    Return the absolute path to a resource file.

    This function works correctly both when running the program normally
    and when packaged with PyInstaller. It also handles special cases
    for CSS files, icons, and certificate files based on the project's directory structure.

    Args:
        relative_path (str): Path to a resource file (e.g., "main.css", "icons/logo.png").

    Returns:
        str: Absolute path to the resource.
    """

    # PyInstaller "frozen" mode: resources are stored in sys._MEIPASS
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
        
        # Icons are stored in icons/ subfolder when frozen
        if relative_path.endswith((".png", ".jpg", ".jpeg", ".ico", ".icns")):
            base_path = os.path.join(base_path, "icons")
        
        # Certificate files (.pem) are stored in cert/ subfolder when frozen
        elif relative_path.endswith(".pem"):
            base_path = os.path.join(base_path, "cert")
        
        # Beacon config JSON is in local/ subfolder when frozen
        elif relative_path.endswith(".json"):
            base_path = os.path.join(base_path, "local")
    
    else:
        # Directory where helpers.py is located (src/)
        current_dir = os.path.abspath(os.path.dirname(__file__))

        # CSS files are stored in src/views/ - need to handle both "main.css" and paths from root
        if relative_path.endswith(".css"):
            base_path = os.path.join(current_dir, "views")
        
        # Icons are stored in icons/ (one level above src/)
        elif relative_path.endswith((".png", ".jpg", ".jpeg", ".ico", ".icns")):
            base_path = os.path.abspath(os.path.join(current_dir, "..", "icons"))

        # Certificate files (.pem) are stored in cert/ at root level
        elif relative_path.endswith(".pem"):
            return os.path.abspath(os.path.join(current_dir, "..", "cert", "cacert.pem"))

        # Markdown documentation files are stored at root level
        elif relative_path.endswith(".md"):
            base_path = os.path.abspath(os.path.join(current_dir, ".."))

        # Beacon config JSON is in local/ folder (development only)
        elif relative_path.endswith(".json"):
            # Handle both "config_url.json" and "local/config_url.json"
            if not relative_path.startswith("local/"):
                return os.path.abspath(os.path.join(current_dir, "..", "local", relative_path))
            else:
                return os.path.abspath(os.path.join(current_dir, "..", relative_path))

        # Default: use the directory of helpers.py
        else:
            base_path = current_dir

    # Extract just the filename from relative_path (handle both "main.css" and "src/views/main.css")
    filename = os.path.basename(relative_path)
    
    return os.path.join(base_path, filename)


def get_appdata_path() -> str:
    """
    Return the directory where the application should store its data.

    The location depends on the operating system:
        - Windows → %APPDATA%/Akiba
        - macOS   → ~/Library/Application Support/Akiba
        - Linux   → ~/.local/share/Akiba

    Returns:
        str: Absolute path to the application's data directory.
    """

    system = platform.system()

    if system == "Darwin":  # macOS
        base_path = os.path.join(os.getenv("HOME"), "Library", "Application Support")

    elif system == "Windows":
        base_path = os.getenv("APPDATA")

    else:
        # Linux, BSD, and other Unix-like systems
        base_path = os.path.join(os.getenv("HOME"), ".local", "share")

    return os.path.join(base_path, APP_NAME)


class Status(enum.Enum):
    """
    Enum representing different application states.

    Used for UI updates, worker status reporting, and general state handling.
    """
    OK = 1
    ERROR = 2
    STOP = 3
    ACTIVE = 4
    WAIT = 5
    INACTIVE = 6
