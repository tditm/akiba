import urllib.request
from urllib.error import HTTPError, URLError
import certifi
import time

# Fixed header that mimics a regular browser
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "X-Client": "ChessClaimTool/0.4.3"
}

def download_pgn(url: str, timeout=30) -> bytes:
    """
    Download PGN from URL with up to 3 retries.
    Handles 404 as 'PGN not ready yet' and retries.
    Returns bytes() on failure.
    """

    for attempt in range(1, 4):  # 3 attempts
        try:
            req = urllib.request.Request(url, headers=BROWSER_HEADERS)

            response = urllib.request.urlopen(
                req,
                timeout=timeout,
                cafile=certifi.where()
            )
            return response.read()

        except HTTPError as e:
            if e.code == 404:
                time.sleep(3)
                continue
            else:
                pass  # HTTP error, will retry
        except URLError as e:
            pass  # Network error, will retry
        except TimeoutError:
            pass  # Timeout, will retry
        except Exception as e:
            pass  # Unexpected error, will retry

    time.sleep(1)

    return bytes()


def check_download(url: str, timeout=10) -> bool:
    """
    Check if URL is reachable.
    Returns True if server responds, False otherwise.
    """

    try:
        req = urllib.request.Request(url, headers=BROWSER_HEADERS)

        urllib.request.urlopen(
            req,
            timeout=timeout,
            cafile=certifi.where()
        )
        return True

    except Exception as e:
        return False


def check_livechess_download(url: str, timeout=10) -> bool:
    """
    Check if LiveChessCloud URL is valid by extracting tournament ID and fetching tournament data.
    Returns True if tournament exists, False otherwise.
    """
    from src.models.livechesscloud import extract_tournament_id, fetch_tournament
    
    tournament_id = extract_tournament_id(url)
    if not tournament_id:
        return False
    
    # Try to fetch tournament metadata
    tournament = fetch_tournament(tournament_id)
    return tournament is not None
