from shop import add_product, show_products
from storage import load_products, save_products


def main():
    products = []
    try:
        products = load_products()
        can_save = True
    except (OSError, ValueError) as error:
        print(f"Помилка завантаження: {error}")
        can_save = False

    while True:
        print("\n1. Додати товар\n2. Переглянути товари\n3. Завантажити список\n0. Вийти")
        try:
            choice = input("Оберіть дію: ").strip()
            if choice == "0":
                return
            if choice == "1":
                if not can_save:
                    print("Спочатку виправте JSON-файл і завантажте список повторно.")
                    continue
                name = input("Назва товару: ")
                try:
                    quantity = int(input("Кількість: "))
                except ValueError:
                    print("Кількість має бути додатним цілим числом.")
                    continue
                updated_products = add_product(products, name, quantity)
                save_products(updated_products)
                products = updated_products
                print("Товар додано та збережено.")
            elif choice == "2":
                show_products(products)
            elif choice == "3":
                try:
                    loaded_products = load_products()
                except (OSError, ValueError):
                    can_save = False
                    raise
                products = loaded_products
                can_save = True
                print("Список завантажено.")
            else:
                print("Невідома команда.")
        except (OSError, ValueError) as error:
            print(f"Помилка: {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nРоботу завершено.")
            return


if __name__ == "__main__":
    main()
