import os
from typing import Dict, Any, Optional
from notion_client import Client
from utils import now_iso, plain_text

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
OVERWRITE = os.getenv("OVERWRITE", "false").lower() == "true"

def client() -> Client:
    if not NOTION_TOKEN:
        raise RuntimeError("NOTION_TOKEN missing")
    return Client(auth=NOTION_TOKEN)

def _enc(schema: Dict[str, Any], value):
    if value in (None, ""): return None
    if "title" in schema:
        return {"title":[{"type":"text","text":{"content":str(value)}}]}
    if "rich_text" in schema:
        return {"rich_text":[{"type":"text","text":{"content":str(value)}}]}
    if "number" in schema:
        try: return {"number": float(value)}
        except Exception: return None
    if "url" in schema:
        return {"url": str(value)}
    if "select" in schema:
        return {"select":{"name":str(value)}}
    if "date" in schema:
        return {"date":{"start":str(value)}}
    return None

def _is_empty(prop: Dict[str, Any]) -> bool:
    if "title" in prop: return len(prop.get("title", []))==0
    if "rich_text" in prop: return len(prop.get("rich_text", []))==0
    if "number" in prop: return prop.get("number") is None
    if "url" in prop: return not prop.get("url")
    if "select" in prop: return prop.get("select") is None
    return True

ORDER = ["Title","Author","Additional Authors","Publisher","Language","Description",
         "Number of Pages","Year Published","Original Publication Year",
         "Average Rating","ISBN","ISBN13","Book Id","coverURL","goodreadsURL"]

def build_updates(schema: Dict[str,Any], data: Dict[str,Any], current: Dict[str,Any]) -> Dict[str,Any]:
    out={}
    for key in ORDER:
        if key not in schema: 
            continue
        if not OVERWRITE and not _is_empty(current.get(key, {})):
            continue
        enc = _enc(schema[key], data.get(key))
        if enc:
            out[key]=enc
    if "LastSynced" in schema:
        out["LastSynced"]={"date":{"start":now_iso()}}
    return out

def extract_keys(props: Dict[str,Any]) -> Dict[str,Optional[str]]:
    title = plain_text(props.get("Title",{}).get("title",[]))
    author = plain_text(props.get("Author",{}).get("rich_text",[]))
    isbn13 = plain_text(props.get("ISBN13",{}).get("rich_text",[]))
    isbn13 = isbn13.replace('"','').replace('=','').strip() if isbn13 else None
    return {"title": title or None, "author": author or None, "isbn13": isbn13}

def query_pages(page_size:int=100):
    return client().databases.query(database_id=DATABASE_ID, page_size=page_size)

def update_page(page_id: str, data: Dict[str, Any]):
    c = client()
    page = c.pages.retrieve(page_id=page_id)
    schema = page["properties"]
    updates = build_updates(schema, data, current=schema)
    if updates:
        c.pages.update(page_id=page_id, properties=updates)
