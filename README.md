# Notion Goodreads Enricher (from an already imported Goodreads table)

Bu repo, Goodreads kitaplarını zaten **Notion veritabanına** aktardığın durumda çalışır.
Script, Notion DB içindeki her sayfa için **ISBN13 > (Title+Author)** sorgusuyla
**Google Books** verilerini çeker ve **boş alanları** tamamlar (istersen OVERWRITE=true ile üstüne yazar).

## Gerekli Notion kolon adları (birebir)
- `goodreadsURL` (URL)
- `Book Id` (Number)
- `Title` (Title)
- `Author` (Rich text)
- `Additional Authors` (Rich text)
- `ISBN` (Rich text/Text)
- `ISBN13` (Rich text/Text)
- `Publisher` (Rich text)
- `Number of Pages` (Number)
- `Year Published` (Number)
- `Original Publication Year` (Number)
- `Average Rating` (Number)
- `Language` (Select **veya** Rich text)
- `Description` (Rich text)
- `coverURL` (URL)
- `LastSynced` (Date) — opsiyonel

## Kurulum (lokalde)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # NOTION_TOKEN ve NOTION_DATABASE_ID değerlerini gir
python enrich_notion.py
```

## GitHub Actions
- Repo Secrets: `NOTION_TOKEN`, `NOTION_DATABASE_ID`, `USER_AGENT` (opsiyonel `OVERWRITE`).
- Actions → **Run workflow** ile çalıştır.
