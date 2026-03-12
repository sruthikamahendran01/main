from dataclasses import asdict
import math
import re
from functools import lru_cache

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from .config import settings
from .dummy_data import PRODUCTS
from .models import Product, RetrievedProduct

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "best",
    "for",
    "i",
    "in",
    "is",
    "me",
    "need",
    "of",
    "or",
    "the",
    "to",
    "want",
    "with",
}


class HashingEmbeddingFunction(EmbeddingFunction[Documents]):
    def __call__(self, input: Documents) -> Embeddings:
        return [self._embed_text(text) for text in input]

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * settings.embedding_dim
        tokens = _tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            index = hash(token) % settings.embedding_dim
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 1 and token not in STOPWORDS
    }


def _product_search_text(product: Product) -> str:
    return " ".join(
        [
            product.title,
            product.category,
            product.root_category,
            product.brand,
            product.description,
            " ".join(product.tags),
        ]
    )


def _product_to_metadata(product: Product) -> dict:
    return {
        "product_id": product.product_id,
        "title": product.title,
        "category": product.category,
        "root_category": product.root_category,
        "brand": product.brand,
        "price": product.price,
        "currency": product.currency,
        "description": product.description,
        "tags": " | ".join(product.tags),
        "rating": product.rating if product.rating is not None else -1.0,
        "review_count": product.review_count if product.review_count is not None else -1,
        "image_url": product.image_url or "",
        "seller": product.seller or "",
        "available_for_delivery": product.available_for_delivery,
        "available_for_pickup": product.available_for_pickup,
    }


def _metadata_to_product(metadata: dict) -> Product:
    tags = tuple(
        part.strip() for part in str(metadata.get("tags", "")).split("|") if part.strip()
    )
    return Product(
        product_id=str(metadata["product_id"]),
        title=str(metadata["title"]),
        category=str(metadata["category"]),
        root_category=str(metadata["root_category"]),
        brand=str(metadata["brand"]),
        price=float(metadata["price"]),
        currency=str(metadata.get("currency", "USD")),
        description=str(metadata["description"]),
        tags=tags,
        rating=float(metadata["rating"]) if float(metadata.get("rating", -1.0)) >= 0 else None,
        review_count=int(metadata["review_count"]) if int(metadata.get("review_count", -1)) >= 0 else None,
        image_url=str(metadata.get("image_url", "")) or None,
        seller=str(metadata.get("seller", "")) or None,
        available_for_delivery=bool(metadata.get("available_for_delivery", False)),
        available_for_pickup=bool(metadata.get("available_for_pickup", False)),
    )


@lru_cache(maxsize=1)
def _get_collection():
    client = chromadb.EphemeralClient()
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
        embedding_function=HashingEmbeddingFunction(),
    )


def ensure_product_index() -> None:
    collection = _get_collection()
    existing_ids = set(collection.get(include=[])["ids"])
    products_by_id = {product.product_id: product for product in PRODUCTS}
    current_ids = set(products_by_id)
    stale_ids = sorted(existing_ids - current_ids)
    if stale_ids:
        collection.delete(ids=stale_ids)
    ordered_products = [products_by_id[product_id] for product_id in sorted(current_ids)]
    collection.upsert(
        ids=[product.product_id for product in ordered_products],
        documents=[_product_search_text(product) for product in ordered_products],
        metadatas=[_product_to_metadata(product) for product in ordered_products],
    )


def get_index_stats() -> dict[str, str | int]:
    collection = _get_collection()
    return {
        "collection": settings.chroma_collection,
        "path": "in-memory",
        "items": collection.count(),
    }


def retrieve_products(query: str, top_k: int | None = None) -> list[RetrievedProduct]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    ensure_product_index()
    result_limit = top_k or settings.top_k
    query_result = _get_collection().query(
        query_texts=[query],
        n_results=min(len(PRODUCTS), max(result_limit * 5, result_limit)),
        include=["metadatas", "distances"],
    )

    metadatas = query_result.get("metadatas", [[]])[0]
    distances = query_result.get("distances", [[]])[0]
    matches: list[RetrievedProduct] = []
    for metadata, distance in zip(metadatas, distances):
        product = _metadata_to_product(metadata)
        semantic_score = max(0.0, 1.0 - float(distance))
        product_tokens = _tokenize(_product_search_text(product))
        title_tokens = _tokenize(product.title)
        tag_tokens = _tokenize(" ".join(product.tags))
        lexical_score = (
            len(query_tokens & product_tokens)
            + (2 * len(query_tokens & title_tokens))
            + (1.5 * len(query_tokens & tag_tokens))
        )
        score = semantic_score + (0.1 * lexical_score)
        if score < settings.min_score:
            continue
        matches.append(
            RetrievedProduct(
                product=product,
                score=score,
            )
        )

    return sorted(matches, key=lambda item: item.score, reverse=True)[:result_limit]


def generate_answer(query: str, matches: list[RetrievedProduct]) -> str:
    if not matches:
        return (
            "I could not find a close product match in the current catalog. "
            "Try asking about curtains, bedding, beauty products, tees, leggings, sweaters, or work boots."
        )

    lead = matches[0].product
    rating_text = ""
    if lead.rating is not None:
        rating_text = f" It is rated {lead.rating:.1f}/5"
        if lead.review_count:
            rating_text += f" from {lead.review_count} reviews"
        rating_text += "."

    delivery_text = ""
    if lead.available_for_delivery:
        delivery_text = " Delivery is available."

    lines = [
        f"Best match for '{query}' is {lead.title} by {lead.brand} at {lead.currency} {lead.price:.2f}.",
        f"It fits because {lead.description}{rating_text}{delivery_text}",
    ]

    if len(matches) > 1:
        alternatives = ", ".join(
            f"{item.product.title} (${item.product.price:.2f})" for item in matches[1:]
        )
        lines.append(f"Other relevant options: {alternatives}.")

    return " ".join(lines)


def answer_query(query: str, top_k: int | None = None) -> dict:
    matches = retrieve_products(query=query, top_k=top_k)
    return {
        "query": query,
        "answer": generate_answer(query=query, matches=matches),
        "sources": [
            {
                **asdict(item.product),
                "score": round(item.score, 2),
            }
            for item in matches
        ],
    }
