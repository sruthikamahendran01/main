from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    product_id: str
    title: str
    category: str
    root_category: str
    brand: str
    price: float
    currency: str
    description: str
    tags: tuple[str, ...]
    rating: float | None = None
    review_count: int | None = None
    image_url: str | None = None
    seller: str | None = None
    available_for_delivery: bool = False
    available_for_pickup: bool = False


@dataclass(frozen=True)
class RetrievedProduct:
    product: Product
    score: float
