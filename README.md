# Simple E-Commerce RAG Demo

This project contains a minimal retrieval-augmented generation demo for an e-commerce catalog using a local Walmart-style product snapshot indexed in Chroma.

## What it does

- loads a local tab-separated product catalog and indexes it into a local Chroma collection
- retrieves relevant products from Chroma using a small offline embedding function
- returns a grounded answer plus the matched source products
- exposes the flow through a FastAPI endpoint and a CLI entry point

## Project structure

```text
backend/
  app/
    config.py
    dummy_data.py
    main.py
    models.py
    rag.py
  data/
    products.tsv
requirements.txt
```

The catalog used for indexing lives in `backend/data/products.tsv`.

## Install

```bash
pip install -r requirements.txt
```

The app rebuilds an in-memory Chroma index from `backend/data/products.tsv` on startup.

## Run the API

```bash
uvicorn backend.app.main:app --reload
```

Frontend:

- Open `http://127.0.0.1:8000/`
- Static assets are served from `http://127.0.0.1:8000/static/...`
- Health and index status are available at `http://127.0.0.1:8000/health`

You can still call the API directly:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"I need blackout curtains for my living room\"}"
```

## Run from the terminal

```bash
python -m backend.app.main "I want a soft fleece sheet set for winter"
```

## Example response

```json
{
  "query": "I need blackout curtains for my living room",
  "answer": "Best match for 'I need blackout curtains for my living room' is Exultantex Grey Blackout Curtains for Living Room,Pom Pom Thermal Window Curtains,50\"\"W x 95\"\"L, 2 Panels, Rod Pocket by Exultantex at USD 47.88.",
  "sources": [
    {
      "product_id": "430528189",
      "title": "Exultantex Grey Blackout Curtains for Living Room,Pom Pom Thermal Window Curtains,50\"\"W x 95\"\"L, 2 Panels, Rod Pocket",
      "category": "Blackout Curtains",
      "root_category": "Home",
      "brand": "Exultantex",
      "price": 47.88,
      "currency": "USD"
    }
  ]
}
```

## Notes

This is intentionally simple. Chroma handles storage and nearest-neighbor retrieval, while the answer text is still a deterministic template grounded in the retrieved products.
