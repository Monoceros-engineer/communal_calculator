from tkinter import *
import tkinter.messagebox as box
from datetime import datetime

# Приветственное окно для первого запуска
def show_welcome_window(start_values, on_save):
    """Показывает приветственное окно для ввода начальных значений"""

    welcome_window = Toplevel()
    welcome_window.title("Добро пожаловать!")
    welcome_window.geometry("400x350")
    welcome_window.resizable(0,0)
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
    gas_entry.insert(0, str(start_values['gas']))
    gas_entry.grid(row=0, column=1, padx=5, pady=5)

    Label(frame, text="Электричество:", font=("Arial", 10)).grid(
        row=1, column=0, padx=5, pady=5, sticky="e"
    )
    electricity_entry = Entry(frame, width=20, font=("Arial", 10))
    electricity_entry.insert(0, str(start_values['electricity']))
    electricity_entry.grid(row=1, column=1, padx=5, pady=5)

    Label(frame, text="Вода:", font=("Arial", 10)).grid(
        row=2, column=0, padx=5, pady=5, sticky="e"
    )
    water_entry = Entry(frame, width=20, font=("Arial", 10))
    water_entry.insert(0, str(start_values['water']))
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

            # Сохраняем значения и все настройки в файл
            on_save(new_gas, new_electricity, new_water)

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

    def reset_to_default():
        # Устанавливаем значения по умолчанию в поля ввода
        gas_entry.delete(0, END)
        gas_entry.insert(0, str(start_values["gas"]))
        electricity_entry.delete(0, END)
        electricity_entry.insert(0, str(start_values["electricity"]))
        water_entry.delete(0, END)
        water_entry.insert(0, str(start_values["water"]))
        # Сохраняем значения по умолчанию через callback
        on_save(start_values["gas"], start_values["electricity"], start_values["water"])
        welcome_window.destroy()

    Button(
        welcome_window,
        text="Использовать значения по умолчанию",
        command=reset_to_default,
        bg="lightgray",
        font=("Arial", 10),
    ).pack(pady=5)

#Создаем главное окно
def create_main_window(calculate_func, is_first_run, start_values, save_initial_callback,
                       tariffs, save_tariffs_callback, get_fees_callback, save_fees_callback,
                       services, save_services_callback):
    window = Tk()
    window.title("Калькулятор коммуналки")
    window.resizable(0,0)

    # Если это первый запуск, показываем приветственное окно
    if is_first_run:
        # Показываем приветственное окно после загрузки главного окна
        window.after(100, lambda: show_welcome_window(start_values, save_initial_callback))
    else:
        # Если это не первый запуск, показываем подсказку с текущими начальными значениями
        window.after(
            100,
            lambda: box.showinfo(
                "Информация",
                f"В прошлом месяце показанивя ваших счетчиков были:\n\n"
                f"Газ: {start_values['gas']}\n"
                f"Электричество: {start_values['electricity']}\n"
                f"Вода: {start_values['water']}\n\n"
                f'Введите новые показания и нажмите "Рассчитать"',
            ),
        )

    # СОЗДАЕМ ПЕРЕМЕННЫЕ ДЛЯ ЧЕКБОКСОВ (до функций)
    box_gas_var = IntVar()  # 0 - не отмечен, 1 - отмечен
    box_electricity_var = IntVar()
    box_water_var = IntVar()

    # СОЗДАЕМ ПЕРЕМЕННЫЕ ДЛЯ ТЕКСТА ЧЕКБОКСОВ
    fees = get_fees_callback()
    box_gas_text = StringVar(value=f"{int(fees['gas'] * 100)}%")
    box_electricity_text = StringVar(value=f"{int(fees['electricity'] * 100)}%")
    box_water_text = StringVar(value=f"{int(fees['water'] * 100)}%")

    # ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЯ ТЕКСТА ЧЕКБОКСОВ
    def update_checkbutton_texts():
        fees = get_fees_callback()
        box_gas_text.set(f"{int(fees['gas'] * 100)}%")
        box_electricity_text.set(f"{int(fees['electricity'] * 100)}%")
        box_water_text.set(f"{int(fees['water'] * 100)}%")

    # СОЗДАНИЕ ИНТЕРФЕЙСА

    # Верхняя панель с датой и кнопкой настроек
    current_date = datetime.now().strftime("%d.%m.%Y")
    label_date = Label(window, text=f"Сегодня: {current_date}", font=("Arial", 10))
    label_date.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    # Кнопка настроек (теперь вызывает open_settings_window)
    btn_settings = Button(
    window, text="Настройки", bg="lightgray",
    command=lambda: open_settings_window(tariffs, save_tariffs_callback,
    get_fees_callback, save_fees_callback,
    update_checkbutton_texts,
    services,
    save_services_callback))

    btn_settings.grid(row=0, column=2, padx=10, pady=10, sticky="e")

    # Отображение текущих начальных значений (для информации)
    info_frame = Frame(window, bg="lightyellow", relief="ridge", bd=1)
    info_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

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
        command=lambda: calculate_func(enter_gas, enter_electricity, enter_water,
                                        box_gas_var, box_electricity_var, box_water_var,
                                        start_values['gas'], start_values['electricity'], start_values['water'],
                                        tariffs['gas'], tariffs['electricity'], tariffs['water'],
                                        fees['gas'], fees['electricity'], fees['water'], show_warning, show_error),
        bg="lightblue",
        font=("Arial", 12),
        width=20,
    )
    btn_check.grid(row=5, column=0, columnspan=3, pady=20)

    for col in range(3):
        window.grid_columnconfigure(col, weight=0, minsize=100)

    return window

#Создаем функцию, открывающую окно настроек
def open_settings_window(tariffs, save_tariffs_callback, fees, save_fees_callback, update_fees_callback, services, save_services_callback):
    """Открывает главное окно настроек"""
    settings_window = Toplevel()
    settings_window.title("Настройки")
    settings_window.geometry("300x350")
    settings_window.resizable(0,0)
    settings_window.grab_set()  # Блокирует главное окно пока открыты настройки

    Label(settings_window, text="Выберите категорию:", font=("Arial", 12, "bold")).pack(
        pady=20
    )

    Button(
        settings_window,
        text="Тарифы",
        command=lambda: open_tarif_window(tariffs, save_tariffs_callback),
        bg="lightblue",
        font=("Arial", 11),
        width=20,
    ).pack(pady=5)

    Button(
        settings_window,
        text="Комиссия",
        command=lambda: open_fee_window(fees, save_fees_callback, update_fees_callback),
        bg="lightblue",
        font=("Arial", 11),
        width=20,
    ).pack(pady=5)

    Button(
        settings_window,
        text="Управление услугами",
        command=lambda: open_manage_services_window(services, save_services_callback),
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

   
def open_tarif_window(current_tariffs, on_save):
    """Открывает окно редактирования тарифов"""

    tarif_window = Toplevel()
    tarif_window.title("Редактирование тарифов")
    tarif_window.geometry("350x250")
    tarif_window.resizable(0,0)
    tarif_window.grab_set()

    # Создаем переменные для редактирования
    tarif_gas_var = StringVar(value=str(current_tariffs['gas']))
    tarif_electricity_var = StringVar(value=str(current_tariffs['electricity']))
    tarif_water_var = StringVar(value=str(current_tariffs['water']))

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
            on_save(new_gas, new_electricity, new_water)

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

def open_fee_window(current_fees, on_save, update_callback):
    """Открывает окно редактирования комиссии"""

    fee_window = Toplevel()
    fee_window.title("Редактирование комиссии")
    fee_window.geometry("350x250")
    fee_window.resizable(0,0)
    fee_window.grab_set()

    # Создаем переменные для редактирования (умножаем на 100 для отображения в процентах)
    fee_gas_var = StringVar(value=str(int(current_fees["gas"] * 100)))
    fee_electricity_var = StringVar(value=str(int(current_fees["electricity"] * 100)))
    fee_water_var = StringVar(value=str(int(current_fees["water"] * 100)))

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
            on_save(new_gas, new_electricity, new_water)

            # Обновляем текст на чекбоксах
            update_callback()

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

def open_manage_services_window(services, save_callback):
    win = Toplevel()
    win.title("Управление услугами")
    win.geometry("600x450")
    win.resizable(0,0)
    win.grab_set()

    Label(win, text="Список услуг", font=("Arial", 12, "bold")).pack(pady=10)

    frame = Frame(win)
    frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

    scrollbar = Scrollbar(frame)
    scrollbar.pack(side=RIGHT, fill=Y)

    listbox = Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
    listbox.pack(fill=BOTH, expand=True)
    scrollbar.config(command=listbox.yview)

    button_frame = Frame(win)
    button_frame.pack(pady=10)

    btn_edit = Button(button_frame, text="Редактировать", width=12, state="disabled")
    btn_delete = Button(button_frame, text="Удалить", width=12, state="disabled")
    btn_toggle = Button(button_frame, text="Вкл/Выкл", width=12, state="disabled")
    btn_add = Button(button_frame, text="Добавить", width=12)
    btn_close = Button(button_frame, text="Закрыть", width=12)

    btn_add.pack(side=LEFT, padx=5)
    btn_edit.pack(side=LEFT, padx=5)
    btn_delete.pack(side=LEFT, padx=5)
    btn_toggle.pack(side=LEFT, padx=5)
    btn_close.pack(side=LEFT, padx=5)

    service_keys = []

    def update_buttons_state():
        selection = listbox.curselection()
        if selection:
            state = "normal"
            idx = selection[0]
            key = service_keys[idx]
            enabled = services[key].get("enabled", True)
            btn_toggle.config(text="Выключить" if enabled else "Включить")
        else:
            state = "disabled"
            btn_toggle.config(text="Вкл/Выкл")
        btn_edit.config(state=state)
        btn_delete.config(state=state)
        btn_toggle.config(state=state)

    def refresh_list(select_key=None):
        listbox.delete(0, END)
        service_keys.clear()
        for key, data in services.items():
            status = "Вкл" if data.get("enabled", True) else "Выкл"
            display_text = f"{data['name']} ({key}) - {data['type']} - {status}"
            listbox.insert(END, display_text)
            service_keys.append(key)
        if select_key is not None and select_key in service_keys:
            idx = service_keys.index(select_key)
            listbox.selection_set(idx)
            listbox.see(idx)
        update_buttons_state()

    refresh_list()

    def on_select(event):
        update_buttons_state()

    listbox.bind('<<ListboxSelect>>', on_select)

    # --- функции для кнопок (должны быть определены до их привязки) ---
    def add_service():
        choose_type_dialog(lambda st: add_service_dialog(services, save_callback, refresh_list, st))

    def edit_service():
        selection = listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        key = service_keys[idx]
        edit_service_dialog(services, key, save_callback, refresh_list)

    def delete_service():
        selection = listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        key = service_keys[idx]
        confirm = box.askyesno("Удаление", f"Удалить услугу '{services[key]['name']}'?")
        if confirm:
            del services[key]
            save_callback()
            refresh_list()

    def toggle_service():
        selection = listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        key = service_keys[idx]
        services[key]["enabled"] = not services[key].get("enabled", True)
        save_callback()
        refresh_list(select_key=key)   # ← передаём ключ, чтобы выделение осталось

    # назначаем команды
    btn_add.config(command=add_service)
    btn_edit.config(command=edit_service)
    btn_delete.config(command=delete_service)
    btn_toggle.config(command=toggle_service)
    btn_close.config(command=win.destroy)



def show_results_window(results_data, current_readings, costs, total_amount, total_fee, total_sum_with_fee, on_save):
    """Создает окно с результатами в виде таблицы и предлагает обновить начальные значения"""
    results_window = Toplevel()
    results_window.title("Результаты расчета")
    results_window.resizable(0,0)

    # Заголовки таблицы
    headers = [
        "Ресурс",
        "Начало",
        "Конец",
        "Расход",
        "Тариф",
        "Сумма",
        "Комиссия",
        "Итого с учетом комиссии",
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

    row=1    
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
        ).grid(row=row, column=0, sticky="nsew")
        Label(
            results_window,
            text=f"{total_amount:.2f}",
            relief="ridge",
            padx=10,
            pady=5,
            font=("Arial", 10, "bold"),
            bg="lightyellow",
        ).grid(row=row, column=5, sticky="nsew")
        Label(
            results_window,
            text=f"{total_fee:.2f}",
            relief="ridge",
            padx=10,
            pady=5,
            font=("Arial", 10, "bold"),
            bg="lightyellow",
            fg="blue",
        ).grid(row=row, column=6, sticky="nsew")
        Label(
            results_window,
            text=f"{total_sum_with_fee:.2f}",
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
        on_save(current_readings, costs, total_sum_with_fee)
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
    col_widths = [80, 20, 20, 20, 20, 100, 100, 200]  # подбираем ширину ячеек
    for col, width in enumerate(col_widths):
        results_window.grid_columnconfigure(col, minsize=width, weight=0)

#Прописываем функции сообщений об ошибках
def show_warning(title, message):
    box.showwarning(title, message)

def show_error(title, message):
    box.showerror(title, message)

def add_service_dialog(services, save_callback, refresh_callback, service_type):
    """Окно добавления новой услуги"""
    win = Toplevel()
    win.title("Добавление услуги")
    win.geometry("400x450" if service_type == "metered" else "400x350")
    win.resizable(0,0)
    win.grab_set()

    Label(win, text="Новая услуга", font=("Arial", 12, "bold")).pack(pady=10)

    frame = Frame(win)
    frame.pack(pady=5, padx=10)

    # Название услуги
    Label(frame, text="Название услуги:").grid(row=0, column=0, sticky="e", pady=5)
    name_entry = Entry(frame, width=25)
    name_entry.grid(row=0, column=1, pady=5)

    row = 1
    start_entry = None
    if service_type == "metered":
        Label(frame, text="Начальное значение:").grid(row=row, column=0, sticky="e", pady=5)
        start_entry = Entry(frame, width=25)
        start_entry.grid(row=row, column=1, pady=5)
        start_entry.insert(0, "0")
        row += 1

    # Тариф
    Label(frame, text="Тариф (руб.):").grid(row=row, column=0, sticky="e", pady=5)
    tariff_entry = Entry(frame, width=25)
    tariff_entry.grid(row=row, column=1, pady=5)
    tariff_entry.insert(0, "0.0")
    row += 1

    # Комиссия (%)
    Label(frame, text="Комиссия (%):").grid(row=row, column=0, sticky="e", pady=5)
    fee_entry = Entry(frame, width=25)
    fee_entry.grid(row=row, column=1, pady=5)
    fee_entry.insert(0, "0")
    row += 1

    enabled_var = BooleanVar(value=True)
    Checkbutton(frame, text="Включена", variable=enabled_var).grid(row=row, column=1, sticky="w", pady=5)

    def save_new():
        name = name_entry.get().strip()
        if not name:
            box.showerror("Ошибка", "Введите название услуги")
            return
        key = name.lower().replace(' ', '_')
        if key in services:
            box.showerror("Ошибка", "Услуга с таким названием уже существует")
            return
        try:
            tariff = float(tariff_entry.get())
            if tariff <= 0:
                raise ValueError
        except:
            box.showerror("Ошибка", "Тариф должен быть положительным числом")
            return
        try:
            fee_percent = float(fee_entry.get())
            if fee_percent < 0 or fee_percent > 100:
                raise ValueError
            fee = fee_percent / 100.0
        except:
            box.showerror("Ошибка", "Комиссия должна быть от 0 до 100")
            return

        new_service = {
            "name": name,
            "type": service_type,
            "enabled": enabled_var.get(),
            "tariff": tariff,
            "fee": fee
        }
        if service_type == "metered":
            try:
                start_val = int(start_entry.get())
                if start_val < 0:
                    raise ValueError
                new_service["start_value"] = start_val
            except:
                box.showerror("Ошибка", "Начальное значение должно быть неотрицательным целым")
                return
        services[key] = new_service
        save_callback()
        refresh_callback()
        win.destroy()

    Button(win, text="Сохранить", command=save_new, bg="lightgreen", width=15).pack(pady=10)
    Button(win, text="Отмена", command=win.destroy, bg="lightcoral", width=15).pack(pady=5)

def choose_type_dialog(callback):
    """Выбирает тип услуги: фиксированный или по счетчику"""
    win = Toplevel()
    win.title("Выбор типа услуги")
    win.geometry("300x150")
    win.resizable(0,0)
    win.grab_set()

    Label(win, text="Выберите тип услуги:", font=("Arial", 11)).pack(pady=10)
    type_var = StringVar(value="metered")
    Radiobutton(win, text="По счётчику", variable=type_var, value="metered").pack(anchor="w", padx=20)
    Radiobutton(win, text="Фиксированный", variable=type_var, value="fixed").pack(anchor="w", padx=20)

    def on_next():
        win.destroy()
        callback(type_var.get())

    Button(win, text="Далее", command=on_next, bg="lightblue", width=10).pack(pady=10)

def edit_service_dialog(services, key, save_callback, refresh_callback):
    """Окно редактирования услуг"""
    service = services[key]
    win = Toplevel()
    win.title("Редактирование услуги")
    win.geometry("400x450" if service["type"] == "metered" else "400x350")
    win.resizable(0,0)
    win.grab_set()

    Label(win, text=f"Редактирование: {service['name']}", font=("Arial", 12, "bold")).pack(pady=10)

    frame = Frame(win)
    frame.pack(pady=5, padx=10)

    # Название
    Label(frame, text="Название услуги:").grid(row=0, column=0, sticky="e", pady=5)
    name_entry = Entry(frame, width=25)
    name_entry.insert(0, service["name"])
    name_entry.grid(row=0, column=1, pady=5)

    row = 1
    start_entry = None
    if service["type"] == "metered":
        Label(frame, text="Начальное значение:").grid(row=row, column=0, sticky="e", pady=5)
        start_entry = Entry(frame, width=25)
        start_entry.insert(0, str(service.get("start_value", 0)))
        start_entry.grid(row=row, column=1, pady=5)
        row += 1

    # Тариф
    Label(frame, text="Тариф (руб.):").grid(row=row, column=0, sticky="e", pady=5)
    tariff_entry = Entry(frame, width=25)
    tariff_entry.insert(0, str(service["tariff"]))
    tariff_entry.grid(row=row, column=1, pady=5)
    row += 1

    # Комиссия (%)
    Label(frame, text="Комиссия (%):").grid(row=row, column=0, sticky="e", pady=5)
    fee_entry = Entry(frame, width=25)
    fee_entry.insert(0, str(service["fee"] * 100))
    fee_entry.grid(row=row, column=1, pady=5)
    row += 1

    enabled_var = BooleanVar(value=service.get("enabled", True))
    Checkbutton(frame, text="Включена", variable=enabled_var).grid(row=row, column=1, sticky="w", pady=5)

    def save_edit():
        new_name = name_entry.get().strip()
        if not new_name:
            box.showerror("Ошибка", "Введите название услуги")
            return
        # Проверка на уникальность, если имя изменилось
        new_key = new_name.lower().replace(' ', '_')
        if new_key != key and new_key in services:
            box.showerror("Ошибка", "Услуга с таким названием уже существует")
            return
        try:
            tariff = float(tariff_entry.get())
            if tariff <= 0:
                raise ValueError
        except:
            box.showerror("Ошибка", "Тариф должен быть положительным числом")
            return
        try:
            fee_percent = float(fee_entry.get())
            if fee_percent < 0 or fee_percent > 100:
                raise ValueError
            fee = fee_percent / 100.0
        except:
            box.showerror("Ошибка", "Комиссия должна быть от 0 до 100")
            return

        updated_service = {
            "name": new_name,
            "type": service["type"],
            "enabled": enabled_var.get(),
            "tariff": tariff,
            "fee": fee
        }
        if service["type"] == "metered":
            try:
                start_val = int(start_entry.get())
                if start_val < 0:
                    raise ValueError
                updated_service["start_value"] = start_val
            except:
                box.showerror("Ошибка", "Начальное значение должно быть неотрицательным целым")
                return

        # Если изменилось название, удаляем старый ключ и создаём новый
        if new_key != key:
            del services[key]
        services[new_key] = updated_service
        save_callback()
        refresh_callback()
        win.destroy()

    Button(win, text="Сохранить", command=save_edit, bg="lightgreen", width=15).pack(pady=10)
    Button(win, text="Отмена", command=win.destroy, bg="lightcoral", width=15).pack(pady=5)