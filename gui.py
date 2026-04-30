from tkinter import *
import tkinter.messagebox as box
from datetime import datetime


#Создаем главное окно
def create_main_window(calculate_func, start_values, save_initial_callback,
                       tariffs, save_tariffs_callback, fees, save_fees_callback,
                       services, save_services_callback):
    window = Tk()
    window.title("Калькулятор коммуналки")
    window.resizable(0,0)
    
    # Информационное сообщение о начальных значениях
    msg_lines = ["В прошлом месяце показания ваших счётчиков были:"]
    for key, srv in services.items():
        if srv.get("enabled") and srv["type"] == "metered" and "start_value" in srv:
            msg_lines.append(f"{srv['name']}: {srv['start_value']}")
    msg = "\n".join(msg_lines) + "\n\nВведите новые показания и нажмите 'Рассчитать'"
    window.after(100, lambda: box.showinfo("Информация", msg))

    # Словари для виджетов
    entries = {}
    checkboxes = {}
    checkbox_texts = {}

    # Функция обновления текста чекбоксов (будет вызываться после изменения комиссий)
    def update_checkbutton_texts():
        for key, service in services.items():
            if key in checkbox_texts:
                new_text = f"{int(service.get('fee', 0.0) * 100)}%"
                checkbox_texts[key].set(new_text)

    # Верхняя панель
    current_date = datetime.now().strftime("%d.%m.%Y")
    label_date = Label(window, text=f"Сегодня: {current_date}", font=("Arial", 10))
    label_date.grid(row=0, column=0, padx=10, pady=10, sticky="w")

    btn_settings = Button(
        window, text="Настройки", bg="lightgray",
        command=lambda: open_settings_window(
            tariffs, save_tariffs_callback,
            fees, save_fees_callback,
            update_checkbutton_texts,
            services, save_services_callback, refresh_services_callback
        )
    )
    btn_settings.grid(row=0, column=2, padx=10, pady=10, sticky="e")

    def refresh_services_callback():
        rebuild_services_frame()

    # Заголовки колонок
    Label(window, text="Ресурс", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=5, pady=5)
    Label(window, text="Показания", font=("Arial", 10, "bold")).grid(row=1, column=1, padx=5, pady=5)
    Label(window, text="Комиссия", font=("Arial", 10, "bold")).grid(row=1, column=2, padx=5, pady=5)

    # Фрейм для динамических виджетов услуг
    services_frame = Frame(window)
    services_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

    # Словари для виджетов (будут заполняться в build_services_frame)
    entries = {}
    checkboxes = {}
    checkbox_texts = {}

    def build_services_frame(frame, services, entries, checkboxes, checkbox_texts, window):
        # очищаем фрейм перед построением
        for widget in frame.winfo_children():
            widget.destroy()
        entries.clear()
        checkboxes.clear()
        checkbox_texts.clear()
        row = 0
        for key, service in services.items():
            if not service.get("enabled", True):
                continue
            # Название
            Label(frame, text=service["name"], font=("Arial", 10)).grid(row=row, column=0, padx=5, pady=5, sticky="w")
            # Поле ввода (только для metered)
            if service["type"] == "metered":
                entry = Entry(frame, width=20)
                entry.grid(row=row, column=1, padx=5, pady=5)
                entries[key] = entry
            else:
                Label(frame, text="—", width=20, relief="ridge").grid(row=row, column=1, padx=5, pady=5)
            # Чекбокс комиссии
            var = IntVar()
            text_var = StringVar(value=f"{int(service['fee']*100)}%")
            Checkbutton(frame, textvariable=text_var, variable=var).grid(row=row, column=2, padx=5, pady=5)
            checkboxes[key] = var
            checkbox_texts[key] = text_var
            row += 1

    def rebuild_services_frame():
        build_services_frame(services_frame, services, entries, checkboxes, checkbox_texts, window)

    # Построение интерфейса услуг при запуске
    rebuild_services_frame()

    btn_check = Button(
        window,
        text="Рассчитать",
        command=lambda: calculate_func(entries, checkboxes, services, show_warning, show_error, save_services_callback),
        bg="lightblue",
        font=("Arial", 12),
        width=20,
    )
    btn_check.grid(row=100, column=0, columnspan=3, pady=20, sticky="n")

    # Настройка колонок
    for col in range(3):
        window.grid_columnconfigure(col, weight=0, minsize=100)

    rebuild_services_frame()

    return window

    #Создаем функцию, открывающую окно настроек
def open_settings_window(tariffs, save_tariffs_callback, fees, save_fees_callback, update_fees_callback, services, save_services_callback,
                         refresh_callback):
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
        command=lambda: open_tarif_window(services, save_tariffs_callback),
        bg="lightblue",
        font=("Arial", 11),
        width=20,
    ).pack(pady=5)

    Button(
        settings_window,
        text="Комиссия",
        command=lambda: open_fee_window(services, save_fees_callback, update_fees_callback),
        bg="lightblue",
        font=("Arial", 11),
        width=20,
    ).pack(pady=5)

    Button(
        settings_window,
        text="Управление услугами",
        command=lambda: open_manage_services_window(services, save_services_callback,
                                                   first_run=False,
                                                   refresh_callback=refresh_callback),
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


   
def open_tarif_window(services, save_tariffs_callback):
    win = Toplevel()
    win.title("Редактирование тарифов")
    win.geometry("400x400")
    win.resizable(0,0)
    win.grab_set()

    canvas = Canvas(win, borderwidth=0)
    scrollbar = Scrollbar(win, orient="vertical", command=canvas.yview)
    scrollable_frame = Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    Label(scrollable_frame, text="Редактирование тарифов", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

    vars = {}
    row = 1
    for key, service in services.items():
        if not service.get("enabled", True):
            continue
        name = service["name"]
        tariff = service.get("tariff", 0.0)
        Label(scrollable_frame, text=f"{name}:", font=("Arial", 10)).grid(row=row, column=0, padx=10, pady=5, sticky="e")
        var = StringVar(value=str(tariff))
        Entry(scrollable_frame, textvariable=var, width=15).grid(row=row, column=1, padx=10, pady=5)
        vars[key] = var
        row += 1

    def save_tariffs():
        new_tariffs = {}
        try:
            for key, var in vars.items():
                val = float(var.get())
                if val <= 0:
                    raise ValueError
                new_tariffs[key] = val
            save_tariffs_callback(new_tariffs)
            box.showinfo("Успех", "Тарифы обновлены")
            win.destroy()
        except ValueError:
            box.showerror("Ошибка", "Тарифы должны быть положительными числами")

    Button(scrollable_frame, text="Сохранить", command=save_tariffs, bg="lightgreen", width=10).grid(row=row, column=0, pady=20)
    Button(scrollable_frame, text="Отмена", command=win.destroy, bg="lightcoral", width=10).grid(row=row, column=1, pady=20)

def open_fee_window(services, save_fees_callback, update_callback):
    win = Toplevel()
    win.title("Редактирование комиссии")
    win.geometry("400x400")
    win.resizable(0,0)
    win.grab_set()

    canvas = Canvas(win, borderwidth=0)
    scrollbar = Scrollbar(win, orient="vertical", command=canvas.yview)
    scrollable_frame = Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    Label(scrollable_frame, text="Редактирование комиссии банка", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

    vars = {}
    row = 1
    for key, service in services.items():
        if not service.get("enabled", True):
            continue
        name = service["name"]
        fee_percent = int(service.get("fee", 0.0) * 100)
        Label(scrollable_frame, text=f"{name} (%):", font=("Arial", 10)).grid(row=row, column=0, padx=10, pady=5, sticky="e")
        var = StringVar(value=str(fee_percent))
        Entry(scrollable_frame, textvariable=var, width=15).grid(row=row, column=1, padx=10, pady=5)
        vars[key] = var
        row += 1

    def save_fees():
        new_fees = {}
        try:
            for key, var in vars.items():
                val = float(var.get())
                if val < 0 or val > 100:
                    raise ValueError
                new_fees[key] = val / 100.0
            save_fees_callback(new_fees)
            update_callback()
            box.showinfo("Успех", "Комиссия успешно обновлена!")
            win.destroy()
        except ValueError:
            box.showerror("Ошибка", "Комиссия должна быть от 0% до 100%")

    Button(scrollable_frame, text="Сохранить", command=save_fees, bg="lightgreen", width=10).grid(row=row, column=0, pady=20)
    Button(scrollable_frame, text="Отмена", command=win.destroy, bg="lightcoral", width=10).grid(row=row, column=1, pady=20)

def open_manage_services_window(services, save_callback, first_run=False, on_finish=None, refresh_callback=None):
    win = Toplevel()
    win.title("Управление услугами" if not first_run else "Настройка услуг (первый запуск)")
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

    if first_run:
        btn_finish = Button(button_frame, text="Готово", width=12)
        btn_close = None
    else:
        btn_finish = None
        btn_close = Button(button_frame, text="Закрыть", width=12)

    btn_add.pack(side=LEFT, padx=5)
    btn_edit.pack(side=LEFT, padx=5)
    btn_delete.pack(side=LEFT, padx=5)
    btn_toggle.pack(side=LEFT, padx=5)
    if btn_finish:
        btn_finish.pack(side=LEFT, padx=5)
    if btn_close:
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

    listbox.bind('<<ListboxSelect>>', lambda e: update_buttons_state())

    # --- функции для кнопок ---
    def add_service():
        choose_type_dialog(lambda st: add_service_dialog(services, save_callback, refresh_list, st, refresh_callback))

    def edit_service():
        selection = listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        key = service_keys[idx]
        edit_service_dialog(services, key, save_callback, refresh_list, refresh_callback)

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
            if refresh_callback:
                refresh_callback()

    def toggle_service():
        selection = listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        key = service_keys[idx]
        services[key]["enabled"] = not services[key].get("enabled", True)
        save_callback()
        refresh_list(select_key=key)
        if refresh_callback:
            refresh_callback()

    def finish():
        if on_finish:
            on_finish()
        win.destroy()

    btn_add.config(command=add_service)
    btn_edit.config(command=edit_service)
    btn_delete.config(command=delete_service)
    btn_toggle.config(command=toggle_service)
    if btn_finish:
        btn_finish.config(command=finish)
    if btn_close:
        btn_close.config(command=win.destroy)



def show_results_window(results_data, current_readings, costs, total_amount, total_fee, total_sum_with_fee, on_save, services):
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
        on_save(current_readings, costs, total_sum_with_fee)
        msg_lines = ["Новые начальные значения для следующего месяца:"]
        for key, reading in current_readings.items():
            service_name = services.get(key, {}).get("name", key)
            msg_lines.append(f"{service_name}: {reading}")
        msg = "\n".join(msg_lines)
        box.showinfo("Готово", f"Показания сохранены!\n\n{msg}")
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

def add_service_dialog(services, save_callback, refresh_list, service_type, refresh_callback=None):
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
        refresh_list()
        if refresh_callback:
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

def edit_service_dialog(services, key, save_callback, refresh_list, refresh_callback=None):
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
        refresh_list()
        if refresh_callback:
            refresh_callback()
        win.destroy()

    Button(win, text="Сохранить", command=save_edit, bg="lightgreen", width=15).pack(pady=10)
    Button(win, text="Отмена", command=win.destroy, bg="lightcoral", width=15).pack(pady=5)