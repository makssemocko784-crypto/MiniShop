from copy import deepcopy
from unittest.mock import Mock

import pytest

import main
from shop import add_product


@pytest.mark.parametrize("quantity", [1, 5])
def test_fr01_add_product(quantity):
    products = []

    result = add_product(products, "  Молоко  ", quantity)

    assert len(result) == 1
    assert result[0] == {
        "id": 1,
        "name": "Молоко",
        "quantity": quantity,
        "status": "Не придбано",
    }


def test_fr01_assigns_unique_ids_with_existing_products():
    products = [
        {"id": 7, "name": "Хліб", "quantity": 1, "status": "Придбано"},
        {"id": 2, "name": "Сир", "quantity": 2, "status": "Не придбано"},
    ]
    original = deepcopy(products)

    result = add_product(products, "Молоко", 1)
    result = add_product(result, "Яблука", 3)

    assert result[:2] == original
    assert len(result) == 4
    ids = [product["id"] for product in result]
    assert len(set(ids)) == len(ids)
    assert all(product["status"] == "Не придбано" for product in result[2:])


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_fr01_rejects_empty_name_without_changing_products(name):
    products = [{"id": 3, "name": "Хліб", "quantity": 1, "status": "Придбано"}]
    original = deepcopy(products)

    with pytest.raises(ValueError, match="Назва"):
        add_product(products, name, 1)

    assert products == original


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "2", "abc", None, True, False])
def test_fr01_rejects_invalid_quantity_without_changing_products(quantity):
    products = [{"id": 3, "name": "Хліб", "quantity": 1, "status": "Придбано"}]
    original = deepcopy(products)

    with pytest.raises(ValueError, match="Кількість"):
        add_product(products, "Молоко", quantity)

    assert products == original


@pytest.mark.parametrize(
    ("name", "quantity", "message"),
    [
        ("", "1", "Назва"),
        ("   ", "1", "Назва"),
        ("Молоко", "0", "Кількість"),
        ("Молоко", "-1", "Кількість"),
        ("Молоко", "1.5", "Кількість"),
        ("Молоко", "abc", "Кількість"),
    ],
)
def test_fr01_invalid_input_reports_error_without_autosave(
    monkeypatch, capsys, name, quantity, message
):
    products = [{"id": 3, "name": "Хліб", "quantity": 1, "status": "Придбано"}]
    original = deepcopy(products)
    inputs = iter(["1", name, quantity, "2", "0"])
    save = Mock()
    show = Mock()
    monkeypatch.setattr(main, "load_products", lambda: products)
    monkeypatch.setattr(main, "save_products", save)
    monkeypatch.setattr(main, "show_products", show)
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

    main.main()

    assert message in capsys.readouterr().out
    assert products == original
    show.assert_called_once_with(original)
    save.assert_not_called()
