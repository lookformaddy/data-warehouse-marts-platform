"""Synthetic seed data (generic e-commerce, invented records).

``seed_v1`` is the initial load; ``seed_v2_changes`` re-states the
customers/products with two tracked-attribute changes, which is what
makes the demo's SCD2 history visible: one customer moves city, one
product changes price. Nothing here is real customer or company data.
"""

from __future__ import annotations

from .store import Store


def seed_v1(store: Store) -> None:
    store.put("customers", [
        {"customer_id": "C1", "name": "Ada Example", "city": "Springfield", "segment": "retail"},
        {"customer_id": "C2", "name": "Ben Sample", "city": "Riverton", "segment": "retail"},
        {"customer_id": "C3", "name": "Cara Demo", "city": "Lakeside", "segment": "wholesale"},
    ])
    store.put("products", [
        {"product_id": "P1", "name": "Trail Mug", "category": "kitchen", "unit_price": 20.0},
        {"product_id": "P2", "name": "Desk Lamp", "category": "home", "unit_price": 45.0},
    ])
    store.put("orders", [
        {"order_id": "O1", "customer_id": "C1", "order_date": "2026-10-20", "status": "completed"},
        {"order_id": "O2", "customer_id": "C2", "order_date": "2026-10-22", "status": "shipped"},
    ])
    store.put("order_items", [
        {"order_item_id": "OI1", "order_id": "O1", "customer_id": "C1", "product_id": "P1",
         "quantity": 2, "unit_price": 20.0, "discount": 5.0},
        {"order_item_id": "OI2", "order_id": "O2", "customer_id": "C2", "product_id": "P2",
         "quantity": 1, "unit_price": 45.0, "discount": 0.0},
    ])


def seed_v2_changes(store: Store) -> None:
    """Second load: C1 moves city, P1 changes price; others unchanged."""
    store.put("customers", [
        {"customer_id": "C1", "name": "Ada Example", "city": "Harborview", "segment": "retail"},
        {"customer_id": "C2", "name": "Ben Sample", "city": "Riverton", "segment": "retail"},
        {"customer_id": "C3", "name": "Cara Demo", "city": "Lakeside", "segment": "wholesale"},
    ])
    store.put("products", [
        {"product_id": "P1", "name": "Trail Mug", "category": "kitchen", "unit_price": 22.0},
        {"product_id": "P2", "name": "Desk Lamp", "category": "home", "unit_price": 45.0},
    ])
