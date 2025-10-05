import os
from typing import Dict, Any, Optional
from notion_client import Client
from utils import now_iso

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
OVERWRITE = os.getenv("OVERWRITE", "false").lower() == "true"

# ---------- client ----------
def client() -> Client:
    if not NOTION_TOKEN:
        raise RuntimeError("NOTION_TOKEN missing")
    return Client(auth=NOTION_TOKEN)

# ---------- encoding helpers ----------
def _enc(schema: Dict[str, Any], value):
    if value in (None, ""):
        return None
    if "title" in schema:
        return {"title": [{"type": "text", "text": {"content": str(value)}}]}
    if "rich_text" in schema:
        return {"rich_text": [{"type": "text", "text": {"content": str(value)}}]}
    if "number" in schema:
        try:
            return {"number": float(value)}
        except Exception:
            return None
    if "url" in schema:
        return {"url": str(value)}
    if "select" in schema:
        return {"select": {"name": str(value)}}
    if "date" in schema:
        return {"date": {"start": str(value)}}
    return None

def _is_empty(prop: Dict[str, Any]) -> bool:
    if not prop:
        return True
    if "title" in prop:      return len(prop.get("title", [])) == 0
    if "rich_text" in prop:  return len(prop.get("rich_text", [])) == 0
    if "number" in prop:     return prop.get("number") is None
    if "url" in prop:        return not prop.get("url")
    if "select" in prop:     return prop.get("select") is None
    return True

# Notion'da desteklediğimiz kolonlar (sıra yalnızca yazım önceliği)
ORDER = [
    "Title","Author","Additional Authors","Publisher","Language","Description",
    "Number of Pages","Year Published","Original Publication Year",
    "Average Rating","ISBN","ISBN13","Book Id","coverURL","Cover URL","goodreadsURL"
]

def build_updates(schema: Dict[str, Any], data: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}
    for key in ORDER:
        if key not in schema:
            continue
        if not OVERWRITE and not _is_empty(current.get(key)):
            continue
        enc = _enc(schema[key], data.get(key))
        if enc:
            updates[key] = enc
    if "LastSynced" in schema:
        updates["LastSynced"] = {"date": {"start": now_iso()}}
    return updates

# ---------- DB query helpers ----------
def query_rows_with_gr_and_missing_fields() -> Dict[str, Any]:
    """
    goodreadsURL dolu OLAN ve hedef alanlardan en az biri boş OLAN sayfaları getirir.
    """
    c = client()
    target_missing = {
        "or": [
            {"property": "Title", "title": {"is_empty": True}},
            {"property": "Author", "rich_text": {"is_empty": True}},
            {"property": "Publisher", "rich_text": {"is_empty": True}},
            {"property": "Language", "select": {"is_empty": True}},
            {"property": "Language", "rich_text": {"is_empty": True}},
            {"property": "Description", "rich_text": {"is_empty": True}},
            {"property": "Number of Pages", "number": {"is_empty": True}},
            {"property": "Year Published", "number": {"is_empty": True}},
            {"property": "ISBN13", "rich_text": {"is_empty": True}},
            {"property": "coverURL", "url": {"is_empty": True}},
        ]
    }
    return c.databases.query(
        database_id=DATABASE_ID,
        filter={
            "and": [
                {"property": "goodreadsURL", "url": {"is_not_empty": True}},
                target_missing,
            ]
        },
        page_size=100,
    )

# ---------- update page (properties + cover) ----------
def update_page(page_id: str, data: Dict[str, Any]):
    c = client()
    page = c.pages.retrieve(page_id=page_id)
    schema = page["properties"]

    updates = build_updates(schema, data, current=schema)

    # Kapak URL'ini bul (ikisine de bak)
    cover_url = data.get("Cover URL") or data.get("coverURL")
    cover_payload = {}
    if cover_url and (page.get("cover") is None or OVERWRITE):
        cover_payload = {"cover": {"type": "external", "external": {"url": str(cover_url)}}}

    if updates or cover_payload:
        c.pages.update(page_id=page_id, properties=updates or {}, **cover_payload)
