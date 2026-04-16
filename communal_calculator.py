from tkinter import *
import tkinter.messagebox as box
from datetime import datetime
from calculator import calculate_service
from file_manager import load_settings
from gui import (
    show_results_window,
    show_welcome_window,
    open_tarif_window,
    open_fee_window,
    open_start_values_window,
)
import config


# Загружаем настройки при запуске
is_first_run = not load_settings()

# Создание главного окна
window = Tk()
window.title("Калькулятор коммуналки")
window.geometry("500x350")

# Если это первый запуск, показываем приветственное окно
if is_first_run:
    # Показываем приветственное окно после загрузки главного окна
    window.after(100, show_welcome_window)
else:
    # Если это не первый запуск, показываем подсказку с текущими начальными значениями
    window.after(
        100,
        lambda: box.showinfo(
            "Информация",
            f"Текущие начальные показания (предыдущий месяц):\n\n"
            f"Газ: {config.start_value_gas}\n"
            f"Электричество: {config.start_value_electricity}\n"
            f"Вода: {config.start_value_water}\n\n"
            f'Введите новые показания и нажмите "Рассчитать"',
        ),
    )

# СОЗДАЕМ ПЕРЕМЕННЫЕ ДЛЯ ЧЕКБОКСОВ (до функций)
box_gas_var = IntVar()  # 0 - не отмечен, 1 - отмечен
box_electricity_var = IntVar()
box_water_var = IntVar()

# СОЗДАЕМ ПЕРЕМЕННЫЕ ДЛЯ ТЕКСТА ЧЕКБОКСОВ
box_gas_text = StringVar(value=f"{int(config.fee_gas * 100)}%")
box_electricity_text = StringVar(value=f"{int(config.fee_electricity * 100)}%")
box_water_text = StringVar(value=f"{int(config.fee_water * 100)}%")


# ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЯ ТЕКСТА ЧЕКБОКСОВ
def update_checkbutton_texts():
    """Обновляет текст на чекбоксах в соответствии с текущими значениями комиссии"""
    box_gas_text.set(f"{int(config.fee_gas * 100)}%")
    box_electricity_text.set(f"{int(config.fee_electricity * 100)}%")
    box_water_text.set(f"{int(config.fee_water * 100)}%")


# ФУНКЦИИ ДЛЯ НАСТРОЕК


def open_settings_window():
    """Открывает главное окно настроек"""
    settings_window = Toplevel()
    settings_window.title("Настройки")
    settings_window.geometry("300x250")
    settings_window.grab_set()  # Блокирует главное окно пока открыты настройки

    Label(settings_window, text="Выберите категорию:", font=("Arial", 12, "bold")).pack(
        pady=20
    )

    Button(
        settings_window,
        text="Тарифы",
        command=open_tarif_window,
        bg="lightblue",
        font=("Arial", 11),
        width=20,
    ).pack(pady=5)

    Button(
        settings_window,
        text="Комиссия",
        command=lambda: open_fee_window(update_checkbutton_texts),
        bg="lightblue",
        font=("Arial", 11),
        width=20,
    ).pack(pady=5)

    Button(
        settings_window,
        text="Начальные настройки",
        command=open_start_values_window,
        bg="lightblue",
        font=("Arial", 11),
        width=20,
    ).pack(pady=5)

    Button(
        settings_window,
        text="Закрыть",
        command=settings_window.destroy,
        bg="lightcoral",
        font=("Arial", 11),
        width=20,
    ).pack(pady=20)


# ФУНКЦИИ ДЛЯ ОСНОВНОГО РАСЧЕТА


def calculate():
    """Основная функция расчета"""
    try:
        results_data = []  # Список для хранения данных по каждой позиции
        current_readings = {}  # Словарь для текущих показаний
        costs = {}  # Словарь для стоимостей без комиссии

        # Обработка газа
        resuslts_gas = calculate_service(
            "Газ",
            enter_gas.get(),
            config.start_value_gas,
            config.tarif_gas,
            box_gas_var.get(),
            config.fee_gas,
        )  # Это возвращаемый кортеж данных функции calculate_service для газа
        if resuslts_gas is not None:
            results_data.append(resuslts_gas)
            current_readings["gas"] = int(enter_gas.get())
            costs["gas"] = resuslts_gas["Amount"]

        # Обработка электричества
        results_electricity = calculate_service(
            "Электричество",
            enter_electricity.get(),
            config.start_value_electricity,
            config.tarif_electricity,
            box_electricity_var.get(),
            config.fee_electricity,
        )  # Это возвращаемый кортеж функции calculate_service для электричества
        if results_electricity is not None:
            results_data.append(results_electricity)
            current_readings["electricity"] = int(enter_electricity.get())
            costs["electricity"] = results_electricity["Amount"]

        # Обработка воды
        resultrs_water = calculate_service(
            "Вода",
            enter_water.get(),
            config.start_value_water,
            config.tarif_water,
            box_water_var.get(),
            config.fee_water,
        )  # Это возвращаемый кортеж функции calculate_service для воды
        if resultrs_water is not None:
            results_data.append(resultrs_water)
            current_readings["water"] = int(enter_water.get())
            costs["water"] = resultrs_water["Amount"]

        # Проверка, что хотя бы одно поле заполнено
        if not results_data:
            box.showwarning("Предупреждение", "Заполните хотя бы одно поле!")
            return

        # Вычисляем общую сумму с комиссией
        total_with_fee = sum(data["Fee"] for data in results_data)

        # Показываем окно с результатами
        show_results_window(results_data, current_readings, costs, total_with_fee)

    except Exception as e:
        box.showerror("Ошибка", f"Произошла ошибка: {type(e).__name__}\n{e}")


# СОЗДАНИЕ ИНТЕРФЕЙСА

# Верхняя панель с датой и кнопкой настроек
current_date = datetime.now().strftime("%d.%m.%Y")
label_date = Label(window, text=f"Сегодня: {current_date}", font=("Arial", 10))
label_date.grid(row=0, column=0, padx=10, pady=10, sticky="w")

# Кнопка настроек (теперь вызывает open_settings_window)
btn_settings = Button(
    window, text="Настройки", bg="lightgray", command=open_settings_window
)
btn_settings.grid(row=0, column=2, padx=10, pady=10, sticky="e")

# Отображение текущих начальных значений (для информации)
info_frame = Frame(window, bg="lightyellow", relief="ridge", bd=1)
info_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

Label(
    info_frame,
    text=f"Начальные показания (предыдущий месяц): Газ: {config.start_value_gas} | "
    f"Электричество: {config.start_value_electricity} | Вода: {config.start_value_water}",
    font=("Arial", 9),
    bg="lightyellow",
    fg="darkblue",
).pack(pady=2)

# Заголовки колонок
Label(window, text="Ресурс", font=("Arial", 10, "bold")).grid(
    row=1, column=0, padx=5, pady=5
)
Label(window, text="Показания", font=("Arial", 10, "bold")).grid(
    row=1, column=1, padx=5, pady=5
)
Label(window, text="Комиссия", font=("Arial", 10, "bold")).grid(
    row=1, column=2, padx=5, pady=5
)

# Строка для газа
label_gas = Label(window, text="Газ")
label_gas.grid(row=2, column=0, padx=5, pady=5, sticky="w")

enter_gas = Entry(window, width=20)
enter_gas.grid(row=2, column=1, padx=5, pady=5)

# Важно: привязываем переменную к чекбоксу и используем textvariable для динамического текста
box_gas = Checkbutton(window, textvariable=box_gas_text, variable=box_gas_var)
box_gas.grid(row=2, column=2, padx=5, pady=5)

# Строка для электричества
label_electricity = Label(window, text="Электричество")
label_electricity.grid(row=3, column=0, padx=5, pady=5, sticky="w")

enter_electricity = Entry(window, width=20)
enter_electricity.grid(row=3, column=1, padx=5, pady=5)

box_electricity = Checkbutton(
    window, textvariable=box_electricity_text, variable=box_electricity_var
)
box_electricity.grid(row=3, column=2, padx=5, pady=5)

# Строка для воды
label_water = Label(window, text="Вода")
label_water.grid(row=4, column=0, padx=5, pady=5, sticky="w")

enter_water = Entry(window, width=20)
enter_water.grid(row=4, column=1, padx=5, pady=5)

box_water = Checkbutton(window, textvariable=box_water_text, variable=box_water_var)
box_water.grid(row=4, column=2, padx=5, pady=5)

# Кнопка расчета
btn_check = Button(
    window,
    text="Рассчитать",
    command=calculate,
    bg="lightblue",
    font=("Arial", 12),
    width=20,
)
btn_check.grid(row=5, column=0, columnspan=3, pady=20)

window.mainloop()
