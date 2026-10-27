def add_product(products, name, quantity):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Назва товару не може бути порожньою.")
    if type(quantity) is not int or quantity <= 0:
        raise ValueError("Кількість має бути додатним цілим числом.")

    product = {
        "id": max((item["id"] for item in products), default=0) + 1,
        "name": name.strip(),
        "quantity": quantity,
        "status": "Не придбано",
    }
    return products + [product]


def filter_products(products, status):
    if status not in ("Не придбано", "Придбано"):
        raise ValueError("Статус має бути «Не придбано» або «Придбано».")
    return [product for product in products if product["status"] == status]


def show_products(products):
    if not products:
        print("Список покупок порожній.")
        return
    for product in products:
        print(
            f"ID: {product['id']} | Назва: {product['name']} | "
            f"Кількість: {product['quantity']} | Статус: {product['status']}"
        )
