# goodreads.py
import re
import requests
from typing import Optional

def cover_from_goodreads(url_or_id: Optional[str], user_agent: Optional[str] = None) -> Optional[str]:
    """
    Verilen Goodreads kitap linkinden (veya Book Id'den) sayfanın <meta property="og:image"> değerini döndürür.
    """
    if not url_or_id:
        return None

    # Book Id mi, URL mi?
    if url_or_id.isdigit():
        url = f"https://www.goodreads.com/book/show/{url_or_id}"
    else:
        url = url_or_id

    try:
        headers = {"User-Agent": user_agent or "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        if r.status_code != 200 or not r.text:
            return None

        # og:image meta etiketini yakala
        m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', r.text, flags=re.I)
        if m:
            return m.group(1)
    except Exception:
        pass

    return None
