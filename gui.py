from tkinter import *
import tkinter.messagebox as box
from decimal import Decimal
from file_manager import save_readings_to_history


def show_results_window(results_data, current_readings, costs, total_with_fee):
    """Создает окно с результатами в виде таблицы и предлагает обновить начальные значения"""
    results_window = Toplevel()
    results_window.title("Результаты расчета")
    results_window.geometry("1200x450")

    # Заголовки таблицы
    headers = [
        "Ресурс",
        "Начало",
        "Конец",
        "Расход",
        "Тариф",
        "Сумма",
        "Комиссия",
        "Итого",
    ]
    for col, header in enumerate(headers):
        Label(
            results_window,
            text=header,
            font=("Arial", 10, "bold"),
            bg="lightgray",
            relief="ridge",
            padx=10,
            pady=5,
            width=12,
        ).grid(row=0, column=col, sticky="nsew")

    # Данные по каждой позиции
    row = 1
    total_sum = Decimal("0")

    for data in results_data:
        name = data["Name"]
        start = data["Start value"]
        end = data["End value"]
        consumption = data["Consumption"]
        tarif = data["Tariff"]
        amount = data["Amount"]
        fee_amount = data["Fee"]
        total = data["Total"]

        Label(results_window, text=name, relief="ridge", padx=10, pady=5).grid(
            row=row, column=0, sticky="nsew"
        )
        Label(results_window, text=str(start), relief="ridge", padx=10, pady=5).grid(
            row=row, column=1, sticky="nsew"
        )
        Label(results_window, text=str(end), relief="ridge", padx=10, pady=5).grid(
            row=row, column=2, sticky="nsew"
        )
        Label(
            results_window, text=str(consumption), relief="ridge", padx=10, pady=5
        ).grid(row=row, column=3, sticky="nsew")
        Label(
            results_window, text=f"{tarif:.2f}", relief="ridge", padx=10, pady=5
        ).grid(row=row, column=4, sticky="nsew")
        Label(
            results_window, text=f"{amount:.2f}", relief="ridge", padx=10, pady=5
        ).grid(row=row, column=5, sticky="nsew")

        # Показываем комиссию только если она применялась
        if fee_amount > 0:
            Label(
                results_window,
                text=f"{fee_amount:.2f}",
                relief="ridge",
                padx=10,
                pady=5,
            ).grid(row=row, column=6, sticky="nsew")
        else:
            Label(results_window, text="-", relief="ridge", padx=10, pady=5).grid(
                row=row, column=6, sticky="nsew"
            )

        Label(
            results_window,
            text=f"{total:.2f}",
            relief="ridge",
            padx=10,
            pady=5,
            font=("Arial", 10, "bold"),
            fg="green",
        ).grid(row=row, column=7, sticky="nsew")

        total_sum += amount
        row += 1

    # Итоговая строка (если больше одного ресурса)
    if len(results_data) > 1:
        # Пустые ячейки для первых колонок
        for col in range(5):
            Label(results_window, text="", relief="ridge", padx=10, pady=5).grid(
                row=row, column=col, sticky="nsew"
            )

        Label(
            results_window,
            text="ИТОГО:",
            relief="ridge",
            padx=10,
            pady=5,
            font=("Arial", 10, "bold"),
            bg="lightyellow",
        ).grid(row=row, column=5, sticky="nsew")
        Label(
            results_window,
            text=f"{total_sum:.2f}",
            relief="ridge",
            padx=10,
            pady=5,
            font=("Arial", 10, "bold"),
            bg="lightyellow",
        ).grid(row=row, column=6, sticky="nsew")
        Label(
            results_window,
            text=f"{total_with_fee:.2f}",
            relief="ridge",
            padx=10,
            pady=5,
            font=("Arial", 10, "bold"),
            bg="lightyellow",
            fg="blue",
        ).grid(row=row, column=7, sticky="nsew")
        row += 1

    # Разделитель
    Label(results_window, text="-" * 100, bg="lightgray").grid(
        row=row, column=0, columnspan=8, sticky="ew", pady=10
    )
    row += 1

    # Предложение сохранить новые показания как начальные для следующего месяца
    save_frame = Frame(results_window, bg="lightblue", relief="ridge", bd=2)
    save_frame.grid(row=row, column=0, columnspan=8, padx=10, pady=10, sticky="ew")

    Label(
        save_frame,
        text="После оплаты новые показания станут начальными для следующего месяца",
        font=("Arial", 10, "bold"),
        bg="lightblue",
        fg="darkblue",
    ).pack(pady=5)

    def save_and_close():
        """Сохраняет показания в историю, обновляет начальные значения и закрывает окно"""
        save_readings_to_history(current_readings, costs, total_with_fee)
        box.showinfo(
            "Готово",
            f"Показания сохранены!\n\n"
            f"Новые начальные значения для следующего месяца:\n"
            f'Газ: {current_readings["gas"]}\n'
            f'Электричество: {current_readings["electricity"]}\n'
            f'Вода: {current_readings["water"]}',
        )
        results_window.destroy()

    def close_without_saving():
        """Закрывает окно без сохранения показаний"""
        if box.askyesno(
            "Подтверждение",
            "Вы уверены, что не хотите сохранить новые показания?\n"
            "В следующий раз начальные значения останутся прежними.",
        ):
            results_window.destroy()

    # Кнопки
    button_frame = Frame(results_window)
    button_frame.grid(row=row + 1, column=0, columnspan=8, pady=10)

    Button(
        button_frame,
        text="✅ Сохранить и закрыть",
        command=save_and_close,
        bg="lightgreen",
        font=("Arial", 11),
        width=20,
    ).pack(side=LEFT, padx=5)

    Button(
        button_frame,
        text="❌ Закрыть без сохранения",
        command=close_without_saving,
        bg="lightcoral",
        font=("Arial", 11),
        width=20,
    ).pack(side=LEFT, padx=5)

    # Настройка растяжения колонок
    for col in range(8):
        results_window.grid_columnconfigure(col, weight=1)
