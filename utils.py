from datetime import datetime, timezone

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def plain_text(blocks):
    if not blocks: return ""
    return "".join([b.get("plain_text","") for b in blocks])
