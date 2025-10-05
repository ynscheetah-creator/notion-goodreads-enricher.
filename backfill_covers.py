# backfill_covers.py
import os, re, requests
from typing import Optional, Dict, List
from dotenv import load_dotenv
from notion_client import Client
from googlebooks import fetch_google_books

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID  = os.getenv("NOTION_DATABASE_ID")
USER_AGENT   = os.getenv("USER_AGENT", "Mozilla/5.0")
OVERWRITE    = os.getenv("OVERWRITE", "false").lower() == "true"

client = Client(auth=NOTION_TOKEN)

# ---------- helpers ----------
def blocks_to_text(blocks) -> str:
    if not blocks: return ""
    return "".join([b.get("plain_text", "") for b in blocks]).strip()

def clean_isbn(s: Optional[str]) -> Optional[str]:
    if not s: return None
    s = s.replace('"', '').replace('=', '').strip()
    m = re.search(r"\b(\d{13}|\d{10})\b", s)
    return m.group(1) if m else None

def cover_from_goodreads(url_or_id: Optional[str]) -> Optional[str]:
    """Goodreads kitap sayfasındaki <meta property='og:image'> değerini döndür."""
    if not url_or_id:
        return None
    url = f"https://www.goodreads.com/book/show/{url_or_id}" if str(url_or_id).isdigit() else url_or_id
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30, allow_redirects=True)
        if r.status_code != 200 or not r.text:
            return None
        m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', r.text, flags=re.I)
        return m.group(1) if m else None
    except Exception:
        return None

def schema() -> Dict:
    return client.databases.retrieve(DATABASE_ID)["properties"]

def has_any_cover(page: Dict) -> bool:
    props = page["properties"]
    page_cover = page.get("cover")
    url1 = props.get("coverURL", {}).get("url") if "coverURL" in props else None
    url2 = props.get("Cover URL", {}).get("url") if "Cover URL" in props else None
    return bool(page_cover or url1 or url2)

def update_cover(page_id: str, cover_url: str):
    sc = schema()
    props_update = {}
    if "coverURL" in sc:
        props_update["coverURL"] = {"url": cover_url}
    if "Cover URL" in sc:
        props_update["Cover URL"] = {"url": cover_url}

    page = client.pages.retrieve(page_id=page_id)
    cover_payload = {}
    if cover_url and (page.get("cover") is None or OVERWRITE):
        cover_payload = {"cover": {"type": "external", "external": {"url": cover_url}}}

    if props_update or cover_payload:
        client.pages.update(page_id=page_id, properties=props_update, **cover_payload)

def query_pages_without_cover() -> List[Dict]:
    """coverURL/Cover URL boş olan sayfaları getir (pagination destekli)."""
    sc = schema()
    or_list = []
    if "coverURL" in sc:
        or_list.append({"property": "coverURL", "url": {"is_empty": True}})
    if "Cover URL" in sc:
        or_list.append({"property": "Cover URL", "url": {"is_empty": True}})
    # Eğer iki kolon da yoksa yine de tüm sayfaları dolaşalım
    filter_obj = {"and": [{"or": or_list}]} if or_list else {}

    pages, start = [], None
    while True:
        resp = client.databases.query(
            database_id=DATABASE_ID,
            filter=filter_obj or None,
            start_cursor=start,
            page_size=100,
        )
        pages.extend(resp.get("results", []))
        if not resp.get("has_more"): break
        start = resp.get("next_cursor")
    return pages

# ---------- main ----------
def run_once():
    pages = query_pages_without_cover()
    print(f"Found {len(pages)} pages without coverURL/Cover URL")

    for page in pages:
        pid   = page["id"]
        props = page["properties"]

        # mevcut kapak ve OVERWRITE politikası
        if has_any_cover(page) and not OVERWRITE:
            print(f"SKIP (has cover): {pid}")
            continue

        # Goodreads verileri
        gr_url  = props.get("goodreadsURL", {}).get("url") if "goodreadsURL" in props else None
        book_id = None
        if "Book Id" in props and props["Book Id"].get("number") is not None:
            book_id = str(int(props["Book Id"]["number"]))

        # 1) Goodreads og:image
        cover_url = cover_from_goodreads(book_id or gr_url)

        # 2) Google Books yedeği (ISBN13 > Title+Author)
        if not cover_url:
            title  = blocks_to_text(props.get("Title", {}).get("title", [])) if "Title" in props else ""
            author = blocks_to_text(props.get("Author", {}).get("rich_text", [])) if "Author" in props else ""
            isbn13 = clean_isbn(blocks_to_text(props.get("ISBN13", {}).get("rich_text", []))) if "ISBN13" in props else None
            q = isbn13 or f"{title} {author}".strip()
            if q:
                gb = fetch_google_books(q, USER_AGENT)
                cover_url = gb.get("coverURL")

        if cover_url:
            update_cover(pid, cover_url)
            print(f"Updated cover: {pid} ← {cover_url}")
        else:
            print(f"WARN no cover found: {pid}")

if __name__ == "__main__":
    run_once()
