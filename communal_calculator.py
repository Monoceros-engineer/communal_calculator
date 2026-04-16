from tkinter import *
import tkinter.messagebox as box
from datetime import datetime
from decimal import Decimal
from calculator import calculate_service
from file_manager import load_settings, save_settings, save_readings_to_history
from gui import show_results_window
import config


# Приветственное окно для первого запуска
def show_welcome_window():
    """Показывает приветственное окно для ввода начальных значений"""

    welcome_window = Toplevel()
    welcome_window.title("Добро пожаловать!")
    welcome_window.geometry("400x350")
    welcome_window.grab_set()  # Блокирует главное окно

    # Заголовок
    Label(
        welcome_window,
        text="Добро пожаловать в Калькулятор коммуналки!",
        font=("Arial", 12, "bold"),
        fg="blue",
    ).pack(pady=15)

    # Пояснение
    explanation = (
        "Это ваш первый запуск программы.\n\n"
        "Пожалуйста, введите начальные показания счетчиков:\n"
        "(эти значения можно будет изменить позже в настройках)"
    )

    Label(welcome_window, text=explanation, font=("Arial", 10), justify=LEFT).pack(
        pady=10, padx=20
    )

    # Фрейм для полей ввода
    frame = Frame(welcome_window)
    frame.pack(pady=10)

    # Поля ввода
    Label(frame, text="Газ:", font=("Arial", 10)).grid(
        row=0, column=0, padx=5, pady=5, sticky="e"
    )
    gas_entry = Entry(frame, width=20, font=("Arial", 10))
    gas_entry.insert(0, str(config.start_value_gas))
    gas_entry.grid(row=0, column=1, padx=5, pady=5)

    Label(frame, text="Электричество:", font=("Arial", 10)).grid(
        row=1, column=0, padx=5, pady=5, sticky="e"
    )
    electricity_entry = Entry(frame, width=20, font=("Arial", 10))
    electricity_entry.insert(0, str(config.start_value_electricity))
    electricity_entry.grid(row=1, column=1, padx=5, pady=5)

    Label(frame, text="Вода:", font=("Arial", 10)).grid(
        row=2, column=0, padx=5, pady=5, sticky="e"
    )
    water_entry = Entry(frame, width=20, font=("Arial", 10))
    water_entry.insert(0, str(config.start_value_water))
    water_entry.grid(row=2, column=1, padx=5, pady=5)

    # Подсказка
    Label(
        welcome_window,
        text="Введите целые числа (показания счетчиков)",
        font=("Arial", 9),
        fg="gray",
    ).pack()

    # Дополнительное пояснение
    Label(
        welcome_window,
        text="Эти значения будут использоваться как начальная точка отсчета.\n"
        "После каждого расчета они будут автоматически обновляться\n"
        "новыми показаниями для следующего месяца.",
        font=("Arial", 9),
        fg="blue",
        justify=LEFT,
    ).pack(pady=10)

    def save_initial_settings():
        """Сохраняет начальные значения и закрывает окно"""
        nonlocal gas_entry, electricity_entry, water_entry

        try:
            # Получаем значения
            new_gas = int(gas_entry.get())
            new_electricity = int(electricity_entry.get())
            new_water = int(water_entry.get())

            # Проверяем, что значения положительные
            if new_gas < 0 or new_electricity < 0 or new_water < 0:
                box.showerror("Ошибка", "Значения должны быть неотрицательными!")
                return

            # Сохраняем значения
            config.start_value_gas = new_gas
            config.start_value_electricity = new_electricity
            config.start_value_water = new_water

            # Сохраняем все настройки в файл
            save_settings()

            # Показываем сообщение об успехе
            box.showinfo(
                "Готово!",
                "Начальные значения сохранены!\n\n"
                "Теперь вы можете вводить текущие показания и рассчитывать сумму к оплате.\n"
                "После оплаты новые показания автоматически станут начальными для следующего месяца.",
            )

            # Закрываем приветственное окно
            welcome_window.destroy()

        except ValueError:
            box.showerror("Ошибка", "Введите целые числа!")

    # Кнопки
    Button(
        welcome_window,
        text="Сохранить и продолжить",
        command=save_initial_settings,
        bg="lightgreen",
        font=("Arial", 11),
        width=20,
    ).pack(pady=15)

    Button(
        welcome_window,
        text="Использовать значения по умолчанию",
        command=lambda: [save_settings(), welcome_window.destroy()],
        bg="lightgray",
        font=("Arial", 10),
    ).pack(pady=5)


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
        command=open_fee_window,
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


def open_tarif_window():
    """Открывает окно редактирования тарифов"""

    tarif_window = Toplevel()
    tarif_window.title("Редактирование тарифов")
    tarif_window.geometry("350x250")
    tarif_window.grab_set()

    # Создаем переменные для редактирования
    tarif_gas_var = StringVar(value=str(config.tarif_gas))
    tarif_electricity_var = StringVar(value=str(config.tarif_electricity))
    tarif_water_var = StringVar(value=str(config.tarif_water))

    # Заголовок
    Label(tarif_window, text="Редактирование тарифов", font=("Arial", 12, "bold")).grid(
        row=0, column=0, columnspan=2, pady=10
    )

    # Поля ввода
    Label(tarif_window, text="Газ (руб.):").grid(
        row=1, column=0, padx=10, pady=5, sticky="e"
    )
    entry_gas = Entry(tarif_window, textvariable=tarif_gas_var, width=15)
    entry_gas.grid(row=1, column=1, padx=10, pady=5)

    Label(tarif_window, text="Электричество (руб.):").grid(
        row=2, column=0, padx=10, pady=5, sticky="e"
    )
    entry_electricity = Entry(
        tarif_window, textvariable=tarif_electricity_var, width=15
    )
    entry_electricity.grid(row=2, column=1, padx=10, pady=5)

    Label(tarif_window, text="Вода (руб.):").grid(
        row=3, column=0, padx=10, pady=5, sticky="e"
    )
    entry_water = Entry(tarif_window, textvariable=tarif_water_var, width=15)
    entry_water.grid(row=3, column=1, padx=10, pady=5)

    def apply_tarif_changes():
        """Применяет изменения тарифов"""
        nonlocal tarif_gas_var, tarif_electricity_var, tarif_water_var

        try:
            # Пробуем преобразовать введенные значения в float
            new_gas = float(tarif_gas_var.get())
            new_electricity = float(tarif_electricity_var.get())
            new_water = float(tarif_water_var.get())

            # Проверяем, что значения положительные
            if new_gas <= 0 or new_electricity <= 0 or new_water <= 0:
                box.showerror("Ошибка", "Тарифы должны быть положительными числами!")
                return

            # Применяем изменения
            config.tarif_gas = new_gas
            config.tarif_electricity = new_electricity
            config.tarif_water = new_water

            box.showinfo("Успех", "Тарифы успешно обновлены!")
            tarif_window.destroy()

        except ValueError:
            box.showerror("Ошибка", "Введите корректные числа!")

    def cancel_tarif_changes():
        """Отменяет изменения и закрывает окно"""
        tarif_window.destroy()

    # Кнопки
    Button(
        tarif_window,
        text="Применить",
        command=apply_tarif_changes,
        bg="lightgreen",
        width=10,
    ).grid(row=4, column=0, pady=20)
    Button(
        tarif_window,
        text="Отмена",
        command=cancel_tarif_changes,
        bg="lightcoral",
        width=10,
    ).grid(row=4, column=1, pady=20)


def open_fee_window():
    """Открывает окно редактирования комиссии"""

    fee_window = Toplevel()
    fee_window.title("Редактирование комиссии")
    fee_window.geometry("350x250")
    fee_window.grab_set()

    # Создаем переменные для редактирования (умножаем на 100 для отображения в процентах)
    fee_gas_var = StringVar(value=str(int(config.fee_gas * 100)))
    fee_electricity_var = StringVar(value=str(int(config.fee_electricity * 100)))
    fee_water_var = StringVar(value=str(int(config.fee_water * 100)))

    # Заголовок
    Label(
        fee_window, text="Редактирование комиссии банка", font=("Arial", 12, "bold")
    ).grid(row=0, column=0, columnspan=2, pady=10)

    # Поля ввода
    Label(fee_window, text="Газ (%):").grid(
        row=1, column=0, padx=10, pady=5, sticky="e"
    )
    entry_gas = Entry(fee_window, textvariable=fee_gas_var, width=15)
    entry_gas.grid(row=1, column=1, padx=10, pady=5)

    Label(fee_window, text="Электричество (%):").grid(
        row=2, column=0, padx=10, pady=5, sticky="e"
    )
    entry_electricity = Entry(fee_window, textvariable=fee_electricity_var, width=15)
    entry_electricity.grid(row=2, column=1, padx=10, pady=5)

    Label(fee_window, text="Вода (%):").grid(
        row=3, column=0, padx=10, pady=5, sticky="e"
    )
    entry_water = Entry(fee_window, textvariable=fee_water_var, width=15)
    entry_water.grid(row=3, column=1, padx=10, pady=5)

    def apply_fee_changes():
        """Применяет изменения комиссии"""
        nonlocal fee_gas_var, fee_electricity_var, fee_water_var

        try:
            # Пробуем преобразовать введенные значения в float
            new_gas = float(fee_gas_var.get()) / 100  # Переводим проценты в коэффициент
            new_electricity = float(fee_electricity_var.get()) / 100
            new_water = float(fee_water_var.get()) / 100

            # Проверяем, что значения в допустимом диапазоне
            if (
                new_gas < 0
                or new_electricity < 0
                or new_water < 0
                or new_gas > 1
                or new_electricity > 1
                or new_water > 1
            ):
                box.showerror("Ошибка", "Комиссия должна быть от 0% до 100%!")
                return

            # Применяем изменения
            config.fee_gas = new_gas
            config.fee_electricity = new_electricity
            config.fee_water = new_water

            # Обновляем текст на чекбоксах
            update_checkbutton_texts()

            box.showinfo("Успех", "Комиссия успешно обновлена!")
            fee_window.destroy()

        except ValueError:
            box.showerror("Ошибка", "Введите корректные числа!")

    def cancel_fee_changes():
        """Отменяет изменения и закрывает окно"""
        fee_window.destroy()

    # Кнопки
    Button(
        fee_window,
        text="Применить",
        command=apply_fee_changes,
        bg="lightgreen",
        width=10,
    ).grid(row=4, column=0, pady=20)
    Button(
        fee_window, text="Отмена", command=cancel_fee_changes, bg="lightcoral", width=10
    ).grid(row=4, column=1, pady=20)


def open_start_values_window():
    """Открывает окно редактирования начальных значений с предупреждением"""

    # Сначала показываем предупреждение
    box.showwarning(
        "Внимание!",
        "Изменение начальных настроек может привести к \nнекорректным результатам расчетов!\n\n"
        "Убедитесь, что вы действительно хотите \nизменить эти значения.",
    )

    start_window = Toplevel()
    start_window.title("Редактирование начальных значений")
    start_window.geometry("350x300")
    start_window.grab_set()

    # Создаем переменные для редактирования
    start_gas_var = StringVar(value=str(config.start_value_gas))
    start_electricity_var = StringVar(value=str(config.start_value_electricity))
    start_water_var = StringVar(value=str(config.start_value_water))

    # Заголовок
    Label(
        start_window,
        text="Редактирование начальных значений",
        font=("Arial", 12, "bold"),
    ).grid(row=0, column=0, columnspan=2, pady=10)

    # Добавляем предупреждение прямо в окно
    warning_label = Label(
        start_window,
        text="⚠️ Будьте внимательны!\nИзменение этих значений повлияет на все будущие расчеты",
        font=("Arial", 9),
        fg="red",
        justify=CENTER,
    )
    warning_label.grid(row=1, column=0, columnspan=2, pady=5)

    # Поля ввода
    Label(start_window, text="Газ (начало):").grid(
        row=2, column=0, padx=10, pady=5, sticky="e"
    )
    entry_gas = Entry(start_window, textvariable=start_gas_var, width=15)
    entry_gas.grid(row=2, column=1, padx=10, pady=5)

    Label(start_window, text="Электричество (начало):").grid(
        row=3, column=0, padx=10, pady=5, sticky="e"
    )
    entry_electricity = Entry(
        start_window, textvariable=start_electricity_var, width=15
    )
    entry_electricity.grid(row=3, column=1, padx=10, pady=5)

    Label(start_window, text="Вода (начало):").grid(
        row=4, column=0, padx=10, pady=5, sticky="e"
    )
    entry_water = Entry(start_window, textvariable=start_water_var, width=15)
    entry_water.grid(row=4, column=1, padx=10, pady=5)

    def apply_start_changes():
        """Применяет изменения начальных значений с подтверждением"""
        nonlocal start_gas_var, start_electricity_var, start_water_var

        try:
            # Пробуем преобразовать введенные значения в int
            new_gas = int(start_gas_var.get())
            new_electricity = int(start_electricity_var.get())
            new_water = int(start_water_var.get())

            # Проверяем, что значения положительные
            if new_gas < 0 or new_electricity < 0 or new_water < 0:
                box.showerror(
                    "Ошибка", "Начальные значения должны быть неотрицательными!"
                )
                return

            # Запрашиваем подтверждение
            confirm = box.askyesno(
                "Подтверждение",
                f"Вы уверены, что хотите изменить начальные значения?\n\n"
                f"Было:\n"
                f"Газ: {config.start_value_gas}\n"
                f"Электричество: {config.start_value_electricity}\n"
                f"Вода: {config.start_value_water}\n\n"
                f"Станет:\n"
                f"Газ: {new_gas}\n"
                f"Электричество: {new_electricity}\n"
                f"Вода: {new_water}",
            )

            if confirm:
                # Применяем изменения
                config.start_value_gas = new_gas
                config.start_value_electricity = new_electricity
                config.start_value_water = new_water

                box.showinfo("Успех", "Начальные значения успешно обновлены!")
                start_window.destroy()
            else:
                # Если пользователь отказался, ничего не меняем
                box.showinfo("Отмена", "Изменения отменены")

        except ValueError:
            box.showerror("Ошибка", "Введите целые числа!")

    def cancel_start_changes():
        """Отменяет изменения и закрывает окно"""
        # Спрашиваем, точно ли хочет отменить
        if box.askyesno("Подтверждение", "Вы действительно хотите отменить изменения?"):
            start_window.destroy()

    # Кнопки
    Button(
        start_window,
        text="Применить",
        command=apply_start_changes,
        bg="lightgreen",
        width=10,
    ).grid(row=5, column=0, pady=20)
    Button(
        start_window,
        text="Отмена",
        command=cancel_start_changes,
        bg="lightcoral",
        width=10,
    ).grid(row=5, column=1, pady=20)


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
