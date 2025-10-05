# enrich_notion.py
import os, re, requests
from typing import Optional
from dotenv import load_dotenv
from googlebooks import fetch_google_books
from notion_sync import query_rows_with_gr_and_missing_fields, update_page
from utils import blocks_to_text

load_dotenv()
UA = os.getenv("USER_AGENT", "Mozilla/5.0")

# ---- Goodreads kapak: og:image ----
def cover_from_goodreads(url_or_id: Optional[str], user_agent: Optional[str] = None) -> Optional[str]:
    if not url_or_id:
        return None
    url = f"https://www.goodreads.com/book/show/{url_or_id}" if str(url_or_id).isdigit() else url_or_id
    try:
        r = requests.get(url, headers={"User-Agent": user_agent or "Mozilla/5.0"}, timeout=30, allow_redirects=True)
        if r.status_code != 200 or not r.text:
            return None
        m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', r.text, flags=re.I)
        return m.group(1) if m else None
    except Exception:
        return None

def clean_isbn(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.replace('"', '').replace('=', '').strip()
    m = re.search(r"\b(\d{13}|\d{10})\b", s)
    return m.group(1) if m else None

def extract_slug_from_gr(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    m = re.search(r"/book/show/\d+-([A-Za-z0-9\-]+)", url)
    return m.group(1).replace("-", " ") if m else None

def run_once():
    resp = query_rows_with_gr_and_missing_fields()
    for row in resp.get("results", []):
        pid = row["id"]
        props = row["properties"]

        gr_url = props.get("goodreadsURL", {}).get("url")
        title  = blocks_to_text(props.get("Title", {}).get("title", []))
        author = blocks_to_text(props.get("Author", {}).get("rich_text", []))
        isbn13 = clean_isbn(blocks_to_text(props.get("ISBN13", {}).get("rich_text", [])))

        # Metaveri araması için öncelik: ISBN13 > Title+Author > Goodreads slug
        query = isbn13 or (f"{title} {author}".strip() if (title or author) else extract_slug_from_gr(gr_url))
        gb = fetch_google_books(query, UA) if query else {}

        # Kapak önceliği: Goodreads -> Google Books
        book_id = None
        if "Book Id" in props and props["Book Id"].get("number") is not None:
            book_id = str(int(props["Book Id"]["number"]))
        cover_gr = cover_from_goodreads(book_id or gr_url, UA)
        cover_final = cover_gr or gb.get("coverURL")

        data = dict(gb) if gb else {}
        if cover_final:
            data["coverURL"] = cover_final
            data["Cover URL"] = cover_final  # kolon adı Cover URL ise de dolsun

        update_page(pid, data)
        print(f"Updated: {pid} ← Title: {data.get('Title')} | Cover: {'GR' if cover_gr else 'GB' if cover_final else 'none'}")

if __name__ == "__main__":
    run_once()
