from argparse import ArgumentParser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .dummy_data import PRODUCTS
from .rag import answer_query, ensure_product_index, get_index_stats


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_product_index()
    yield


app = FastAPI(title="Simple E-Commerce RAG", version="0.2.0", lifespan=lifespan)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AskRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Customer shopping question")
    top_k: int | None = Field(default=None, ge=1, le=5)


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def healthcheck() -> dict[str, str | int]:
    return {"status": "ok", **get_index_stats()}


@app.get("/products")
def list_products() -> dict[str, list[dict]]:
    return {
        "items": [
            {
                "product_id": product.product_id,
                "title": product.title,
                "category": product.category,
                "brand": product.brand,
                "price": product.price,
            }
            for product in PRODUCTS
        ]
    }


@app.post("/ask")
def ask_rag(payload: AskRequest) -> dict:
    return answer_query(query=payload.query, top_k=payload.top_k)


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Query the demo e-commerce RAG from the terminal.")
    parser.add_argument("query", help="Shopping question or product need")
    parser.add_argument("--top-k", type=int, default=None, dest="top_k")
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    print(answer_query(query=args.query, top_k=args.top_k))
