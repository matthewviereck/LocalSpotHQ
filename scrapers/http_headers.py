"""Shared HTTP headers for the venue scrapers.

Several venue hosts (uptownwestchester.org among them) return 403 to a bare
`User-Agent: Mozilla/5.0`. A full browser-shaped header set gets a normal 200
from every venue we scrape, so all scrapers share this one definition rather
than each carrying its own half-complete version.

Discovered 2026-08-29: Uptown Knauer had been 403ing since ~2026-03-11 purely
because of the short UA, and the silent cache fallback meant nobody noticed.
"""

BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
    ),
    'Accept': (
        'text/html,application/xhtml+xml,application/xml;q=0.9,'
        'image/avif,image/webp,*/*;q=0.8'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
}
