import os, re
from typing import Optional
from dotenv import load_dotenv
from googlebooks import fetch_google_books
from notion_sync import query_rows_with_gr_and_missing_fields, update_page
from utils import blocks_to_text

load_dotenv()
UA = os.getenv("USER_AGENT", "Mozilla/5.0")

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

        # Sorgu önceliği: ISBN13 > Title+Author > Goodreads slug
        query = isbn13 or (f"{title} {author}".strip() if (title or author) else extract_slug_from_gr(gr_url))
        if not query:
            print(f"SKIP: {pid} (no query derivable)"); continue

        gb = fetch_google_books(query, UA)
        if not gb:
            print(f"WARN: No GB result for {pid} (query='{query}')"); continue

        # 'Cover URL' kolon adı olan setupları da destekle
        gb["Cover URL"] = gb.get("coverURL")

        update_page(pid, gb)
        print(f"Updated: {pid} ← GoogleBooks : {gb.get('Title')}")

if __name__ == "__main__":
    run_once()
