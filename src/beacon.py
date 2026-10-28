"""
Akiba - Beacon Module
Anonymous application launch reporting to Google Forms/Sheets.
Data is collected to understand the scale of application usage.

Beacon is sent after clicking the "Start Scan" button - the user sees this 
as a natural part of the application's operation (fetching data from livechess/API).
"""

import requests
import json
import os
from hashlib import sha256
import uuid
import platform


def get_beacon_url():
    """
    Reads beacon URL from local/config_url.json or returns None (disables beacon).
    
    Uses resource_path() from helpers.py which properly handles both:
    - Development mode (reads from local/config_url.json in project root)
    - Compiled .exe mode (would read from bundled resources if config is included)
    
    Returns:
        str: Beacon URL if found, None otherwise
    """
    # Use resource_path to get the correct path for config file
    from src.helpers import resource_path
    
    config_path = resource_path('local/config_url.json')  # Include 'local/' folder like 'cert/' for pem files
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                url = config.get('beacon_url')
                # Skip placeholder URLs
                if url and url != "YOUR_BEACON_URL_HERE" and not url.startswith("https://script.google.com/macros/s/YOUR_"):
                    return url
        except (json.JSONDecodeError, KeyError, IOError):
            pass
    
    return None  # Beacon disabled - no valid config


def get_device_id():
    """
    Generates or retrieves a unique device_id from config.json in the APPDATA folder.
    The ID is generated once and saved locally - the user doesn't need to do anything.
    
    Returns:
        str: Unique device_id (16 characters)
    """
    # Use helpers.get_appdata_path() which already exists and is tested
    from src.helpers import get_appdata_path
    
    app_data_dir = get_appdata_path()
    config_path = os.path.join(app_data_dir, 'config.json')
    
    # Ensure the directory exists
    try:
        if not os.path.exists(app_data_dir):
            os.makedirs(app_data_dir, exist_ok=True)
    except Exception:
        pass
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                device_id = data.get('device_id')
                if device_id:
                    return device_id
        except Exception:
            pass
    
    # First run - generate new ID
    device_id = sha256(str(uuid.uuid4()).encode()).hexdigest()[:16]
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump({'device_id': device_id}, f)
    except Exception:
        pass
    
    return device_id


def send_beacon():
    """
    Sends beacon to Google Apps Script (anonymous launch report).
    
    Data sent:
    - Device ID: unique hash (anonymous)
    - Version: application version
    - OS: operating system
    
    All errors are ignored - the application must work without internet!
    If no config_url.json is found, beacon is silently disabled.
    """
    # Get beacon URL from config
    SCRIPT_URL = get_beacon_url()
    
    if SCRIPT_URL is None:
        # Beacon disabled - no valid configuration
        return
    
    try:
        device_id = get_device_id()
        
        # Data to send as JSON
        data = {
            "device_id": device_id,
            "version": "1.0",
            "os": f"{platform.system()} {platform.release()}"
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Log to beacon.log file in APPDATA
        from src.helpers import get_appdata_path
        app_data_dir = get_appdata_path()
        log_file = os.path.join(app_data_dir, 'beacon.log')
        
        try:
            if not os.path.exists(app_data_dir):
                os.makedirs(app_data_dir, exist_ok=True)
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"Beacon: Sending data - Device ID: {device_id}\n")
        except Exception:
            pass  # Ignore logging errors
        
        response = requests.post(SCRIPT_URL, json=data, timeout=10)
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"Beacon: Response status = {response.status_code}\n")
            
            if response.status_code != 200:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"Beacon error: {response.status_code} - {response.text}\n")
        except Exception:
            pass
        
    except Exception as e:
        # Log error to file
        from src.helpers import get_appdata_path
        app_data_dir = get_appdata_path()
        log_file = os.path.join(app_data_dir, 'beacon.log')
        
        try:
            if not os.path.exists(app_data_dir):
                os.makedirs(app_data_dir, exist_ok=True)
            
            with open(log_file, 'a', encoding='utf-8') as f:
                import traceback
                f.write(f"Beacon exception: {str(e)}\n")
                f.write(traceback.format_exc())
        except Exception:
            pass  # Ignore all errors


def send_beacon_async():
    """
    Sends beacon in the background (non-blocking).
    Used after clicking the "Start Scan" button.
    
    Example usage:
        import threading
        threading.Thread(target=send_beacon_async, daemon=True).start()
    """
    send_beacon()


