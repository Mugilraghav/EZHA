from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class Vendor:
    id: str
    name: str
    city: str
    category: str
    rating: float
    price_start: int
    tags: List[str]
    image: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Service:
    id: str
    vendor_id: str
    title: str
    category: str
    duration: str
    price: int
    description: str
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CatalogStore:
    def __init__(self) -> None:
        self.vendors = [
            Vendor(
                id="vend_001",
                name="Aditi Mehra",
                city="Bengaluru",
                category="Bridal Makeup",
                rating=4.9,
                price_start=8500,
                tags=["Bridal", "Luxury", "HD Makeup"],
                image="https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=900&q=80",
            ),
            Vendor(
                id="vend_002",
                name="Naina Studio",
                city="Delhi",
                category="Fashion Styling",
                rating=4.8,
                price_start=4200,
                tags=["Styling", "Photoshoot", "Personal Brand"],
                image="https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?auto=format&fit=crop&w=900&q=80",
            ),
            Vendor(
                id="vend_003",
                name="Saffron Atelier",
                city="Mumbai",
                category="Bridal Wear",
                rating=4.7,
                price_start=12000,
                tags=["Designer", "Wedding", "Custom Fittings"],
                image="https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=80",
            ),
        ]
        self.services = [
            Service(
                id="svc_001",
                vendor_id="vend_001",
                title="Bridal Makeup Trial",
                category="Bridal Makeup",
                duration="2.5 hours",
                price=8500,
                description="Luxury bridal makeup and skin prep with HD finish and custom color matching.",
                tags=["Bridal", "Luxury", "Trial"],
            ),
            Service(
                id="svc_002",
                vendor_id="vend_002",
                title="Styling Session",
                category="Fashion Styling",
                duration="90 minutes",
                price=4200,
                description="A curated styling session for portraits, events, and personal brand shoots.",
                tags=["Photoshoot", "Styling", "Wardrobe"],
            ),
            Service(
                id="svc_003",
                vendor_id="vend_003",
                title="Bridal Lehenga Customization",
                category="Bridal Wear",
                duration="3 days",
                price=12000,
                description="Custom bridal lehenga consultation, fitting, and finishing touches for the big day.",
                tags=["Custom", "Bridal", "Designer"],
            ),
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vendors": [vendor.to_dict() for vendor in self.vendors],
            "services": [service.to_dict() for service in self.services],
        }


def get_demo_catalog() -> Dict[str, Any]:
    return CatalogStore().to_dict()
