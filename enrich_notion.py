import os
from dotenv import load_dotenv
from googlebooks import fetch_google_books
from notion_sync import query_pages, extract_keys, update_page

load_dotenv()
UA = os.getenv("USER_AGENT", "Mozilla/5.0")

def run_once():
    resp = query_pages(page_size=100)
    for row in resp.get("results", []):
        pid = row["id"]
        props = row["properties"]
        keys = extract_keys(props)
        query = keys.get("isbn13") or f"{keys.get('title','')} {keys.get('author','')}".strip()
        if not query:
            print(f"SKIP: {pid} (no query)"); continue
        data = fetch_google_books(query, UA)
        if not data:
            print(f"WARN: No GB result for {pid}"); continue
        update_page(pid, data)
        print(f"Updated: {pid} ← GoogleBooks : {data.get('Title')}")

if __name__ == "__main__":
    run_once()
