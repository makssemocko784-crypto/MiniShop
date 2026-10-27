from copy import deepcopy
from unittest.mock import Mock

import pytest

import main
from shop import filter_products, show_products


@pytest.fixture
def products():
    return [
        {"id": 7, "name": "Хліб", "quantity": 2, "status": "Придбано"},
        {"id": 3, "name": "Молоко", "quantity": 1, "status": "Не придбано"},
        {"id": 9, "name": "Сир", "quantity": 4, "status": "Придбано"},
        {"id": 5, "name": "Яблука", "quantity": 3, "status": "Не придбано"},
    ]


@pytest.mark.parametrize(
    ("status", "positions"),
    [("Придбано", [0, 2]), ("Не придбано", [1, 3])],
)
def test_fr07_filters_status_preserving_fields_order_and_source(products, status, positions):
    original = deepcopy(products)

    result = filter_products(products, status)

    assert result == [original[position] for position in positions]
    assert products == original
    assert result is not products
    result.clear()
    assert products == original


@pytest.mark.parametrize("status", ["Придбано", "Не придбано"])
@pytest.mark.parametrize("empty_source", [True, False])
def test_fr07_empty_source_or_no_matches_returns_empty_list(status, empty_source):
    opposite_status = "Не придбано" if status == "Придбано" else "Придбано"
    products = [] if empty_source else [
        {"id": 1, "name": "Хліб", "quantity": 1, "status": opposite_status}
    ]
    original = deepcopy(products)

    result = filter_products(products, status)

    assert result == []
    assert result is not products
    assert products == original


@pytest.mark.parametrize("status", ["", "Усі", "придбано", None, True, 0, []])
def test_fr07_invalid_status_is_rejected_without_mutation(products, status):
    original = deepcopy(products)

    with pytest.raises(ValueError, match="Статус"):
        filter_products(products, status)

    assert products == original


def run_console(monkeypatch, products, inputs):
    commands = iter(inputs)
    save = Mock()
    show = Mock(wraps=show_products)
    monkeypatch.setattr(main, "load_products", lambda: products)
    monkeypatch.setattr(main, "save_products", save)
    monkeypatch.setattr(main, "show_products", show)
    monkeypatch.setattr("builtins.input", lambda prompt: next(commands))
    main.main()
    return save, show


@pytest.mark.parametrize("status", ["Придбано", "Не придбано"])
def test_fr07_console_shows_filtered_then_full_list_without_saving(
    monkeypatch, capsys, products, status
):
    original = deepcopy(products)

    save, show = run_console(monkeypatch, products, ["4", f" {status} ", "2", "0"])

    expected = [product for product in original if product["status"] == status]
    assert show.call_count == 2
    assert show.call_args_list[0].args == (expected,)
    assert show.call_args_list[1].args == (original,)
    assert products == original
    save.assert_not_called()
    output = capsys.readouterr().out
    for product in expected:
        assert (
            f"ID: {product['id']} | Назва: {product['name']} | "
            f"Кількість: {product['quantity']} | Статус: {product['status']}"
        ) in output


@pytest.mark.parametrize("empty_source", [True, False])
def test_fr07_console_reports_no_matches_and_keeps_full_list(
    monkeypatch, capsys, products, empty_source
):
    products = [] if empty_source else [products[1]]
    original = deepcopy(products)

    save, show = run_console(monkeypatch, products, ["4", "Придбано", "2", "0"])

    assert "Товарів із вибраним статусом немає." in capsys.readouterr().out
    show.assert_called_once_with(original)
    assert products == original
    save.assert_not_called()


@pytest.mark.parametrize("status", ["", "Усі"])
def test_fr07_console_handles_invalid_status_and_continues(
    monkeypatch, capsys, products, status
):
    original = deepcopy(products)

    save, show = run_console(monkeypatch, products, ["4", status, "2", "0"])

    assert "Помилка: Статус" in capsys.readouterr().out
    show.assert_called_once_with(original)
    assert products == original
    save.assert_not_called()


def test_fr07_filter_does_not_discard_products_before_next_add(monkeypatch, products):
    original = deepcopy(products)

    save, show = run_console(
        monkeypatch, products, ["4", "Придбано", "1", "Груші", "2", "2", "0"]
    )

    expected = original + [
        {"id": 10, "name": "Груші", "quantity": 2, "status": "Не придбано"}
    ]
    save.assert_called_once_with(expected)
    assert show.call_args_list[-1].args == (expected,)
    assert products == original
