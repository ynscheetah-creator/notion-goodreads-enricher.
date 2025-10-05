import os, re, requests
from typing import Optional, Dict
from dotenv import load_dotenv
from notion_client import Client
from googlebooks import fetch_google_books
from utils import blocks_to_text

load_dotenv()
UA = os.getenv("USER_AGENT", "Mozilla/5.0")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
OVERWRITE = os.getenv("OVERWRITE", "false").lower() == "true"

c = Client(auth=NOTION_TOKEN)

def _clean_isbn(s: Optional[str]) -> Optional[str]:
    if not s: return None
    s = s.replace('"','').replace('=','').strip()
    m = re.search(r"\b(\d{13}|\d{10})\b", s)
    return m.group(1) if m else None

def _get_prop(props: Dict, name: str):
    return props.get(name)

def _cover_present(page: Dict) -> bool:
    # page cover veya kolon dolu mu?
    cover = page.get("cover")
    props = page["properties"]
    url1 = props.get("coverURL", {}).get("url") if "coverURL" in props else None
    url2 = props.get("Cover URL", {}).get("url") if "Cover URL" in props else None
    return bool(cover or url1 or url2)

def _fetch_gr_og_image(book_id: str) -> Optional[str]:
    # Goodreads kapak: og:image
    try:
        url = f"https://www.goodreads.com/book/show/{book_id}"
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        if r.status_code != 200:
            return None
        m = re.search(r'<meta property="og:image"\s+content="([^"]+)"', r.text)
        return m.group(1) if m else None
    except Exception:
        return None

def _first_text(blocks): return blocks_to_text(blocks)

def _db_schema():
    return c.databases.retrieve(DATABASE_ID)["properties"]

def _query_pages_without_cover():
    # coverURL/Cover URL boş olan VEYA page.cover boş olan kayıtlar; ayrıca goodreadsURL dolu olsun (opsiyonel)
    # Notion filtreyle page.cover boşluğu ayırt edemiyoruz; kolonları baz alacağız.
    schema = _db_schema()
    filters = [{"or": []}]
    if "coverURL" in schema:
        filters[0]["or"].append({"property":"coverURL","url":{"is_empty":True}})
    if "Cover URL" in schema:
        filters[0]["or"].append({"property":"Cover URL","url":{"is_empty":True}})
    base = filters[0]["or"] or [{"property":"goodreadsURL","url":{"is_not_empty":True}}]  # garanti olsun
    return c.databases.query(database_id=DATABASE_ID, filter={"and":[{"or":base}]}, page_size=100)

def _update_cover(page_id: str, cover_url: str):
    props_update = {}
    schema = _db_schema()
    if "coverURL" in schema:
        props_update["coverURL"] = {"url": cover_url}
    if "Cover URL" in schema:
        props_update["Cover URL"] = {"url": cover_url}
    # Sayfa kapağı—mevcut kapak varsa OVERWRITE kontrolü
    page = c.pages.retrieve(page_id=page_id)
    cover_payload = {}
    if cover_url and (page.get("cover") is None or OVERWRITE):
        cover_payload = {"cover": {"type": "external", "external": {"url": cover_url}}}
    if props_update or cover_payload:
        c.pages.update(page_id=page_id, properties=props_update, **cover_payload)

def run_once():
    resp = _query_pages_without_cover()
    for page in resp.get("results", []):
        pid = page["id"]
        if _cover_present(page) and not OVERWRITE:
            print(f"SKIP has cover: {pid}"); continue

        props = page["properties"]
        isbn13 = _clean_isbn(_first_text(props.get("ISBN13",{}).get("rich_text",[]))) if "ISBN13" in props else None
        title  = _first_text(props.get("Title",{}).get("title",[])) if "Title" in props else ""
        author = _first_text(props.get("Author",{}).get("rich_text",[])) if "Author" in props else ""
        book_id = None
        if "Book Id" in props and props["Book Id"].get("number") is not None:
            book_id = str(int(props["Book Id"]["number"]))

        cover_url = None

        # 1) ISBN13 / Title Author → Google Books
        query = isbn13 or f"{title} {author}".strip()
        if query:
            gb = fetch_google_books(query, UA)
            cover_url = gb.get("coverURL")

        # 2) Goodreads og:image (yalnızca Book Id varsa)
        if not cover_url and book_id:
            cover_url = _fetch_gr_og_image(book_id)

        if cover_url:
            _update_cover(pid, cover_url)
            print(f"Updated cover: {pid} ← {cover_url}")
        else:
            print(f"WARN no cover found: {pid}")

if __name__ == "__main__":
    run_once()
