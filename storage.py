import json
from pathlib import Path


DATA_FILE = Path(__file__).with_name("products.json")


def load_products(path=DATA_FILE):
    try:
        with open(path, encoding="utf-8") as file:
            products = json.load(file)
    except FileNotFoundError:
        return []

    if not isinstance(products, list):
        raise ValueError("JSON має містити список товарів.")
    ids = set()
    for product in products:
        if (
            not isinstance(product, dict)
            or set(product) != {"id", "name", "quantity", "status"}
            or type(product["id"]) is not int
            or product["id"] <= 0
            or product["id"] in ids
            or not isinstance(product["name"], str)
            or not product["name"].strip()
            or type(product["quantity"]) is not int
            or product["quantity"] <= 0
            or product["status"] not in ("Не придбано", "Придбано")
        ):
            raise ValueError("Некоректні дані товару у JSON.")
        ids.add(product["id"])
    return products


def save_products(products, path=DATA_FILE):
    path = Path(path)
    temporary_path = path.with_name(path.name + ".tmp")
    try:
        with open(temporary_path, "w", encoding="utf-8") as file:
            json.dump(products, file, ensure_ascii=False, indent=2)
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
