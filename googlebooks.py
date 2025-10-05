import requests
from typing import Dict, Optional

def fetch_google_books(query: str, ua: Optional[str]=None) -> Dict:
    if not query:
        return {}
    headers = {"User-Agent": ua or "Mozilla/5.0"}
    r = requests.get("https://www.googleapis.com/books/v1/volumes",
                     params={"q": query}, headers=headers, timeout=30)
    if r.status_code != 200:
        return {}
    j = r.json()
    items = j.get("items") or []
    if not items:
        return {}
    v = items[0].get("volumeInfo", {})
    # ISBN13
    isbn13 = None
    for ident in v.get("industryIdentifiers", []) or []:
        if ident.get("type") == "ISBN_13":
            isbn13 = ident.get("identifier"); break
    # Year
    year = None
    if isinstance(v.get("publishedDate"), str) and v["publishedDate"][:4].isdigit():
        year = int(v["publishedDate"][:4])
    # Cover
    cover = None
    if isinstance(v.get("imageLinks"), dict):
        cover = v["imageLinks"].get("thumbnail") or v["imageLinks"].get("smallThumbnail")
    # Lang
    lang = (v.get("language") or "").upper() if v.get("language") else None
    return {
        "Title": v.get("title"),
        "Author": ", ".join(v.get("authors", [])) if v.get("authors") else None,
        "Publisher": v.get("publisher"),
        "Year Published": year,
        "Number of Pages": v.get("pageCount"),
        "coverURL": cover,
        "Language": lang,
        "Description": v.get("description"),
        "ISBN13": isbn13,
        "source": "googlebooks",
    }
