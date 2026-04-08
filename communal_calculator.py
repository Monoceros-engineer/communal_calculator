from tkinter import *
import tkinter.messagebox as box
from datetime import datetime
from decimal import Decimal, getcontext, InvalidOperation
import os
import json

# Настройка точности Decimal
getcontext().prec = 28

# Файлы для хранения настроек и истории
CONFIG_FILE = 'calculator_config.json'
HISTORY_FILE = 'readings_history.json'

# Функции для работы с настройками
def load_settings():
    """Загружает настройки из файла"""
    global start_value_gas, start_value_electricity, start_value_water
    global tarif_gas, tarif_electricity, tarif_water
    global fee_gas, fee_electricity, fee_water
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                
            start_value_gas = settings.get('start_value_gas', 25745)
            start_value_electricity = settings.get('start_value_electricity', 9838)
            start_value_water = settings.get('start_value_water', 502)
            
            tarif_gas = settings.get('tarif_gas', 8.7)
            tarif_electricity = settings.get('tarif_electricity', 7.1)
            tarif_water = settings.get('tarif_water', 84.44)
            
            fee_gas = settings.get('fee_gas', 0.01)
            fee_electricity = settings.get('fee_electricity', 0.01)
            fee_water = settings.get('fee_water', 0.01)
            
            return True  # Настройки загружены
        except:
            return False  # Ошибка загрузки
    else:
        return False  # Файл не найден - первый запуск

def save_settings():
    """Сохраняет настройки в файл"""
    settings = {
        'start_value_gas': start_value_gas,
        'start_value_electricity': start_value_electricity,
        'start_value_water': start_value_water,
        'tarif_gas': tarif_gas,
        'tarif_electricity': tarif_electricity,
        'tarif_water': tarif_water,
        'fee_gas': fee_gas,
        'fee_electricity': fee_electricity,
        'fee_water': fee_water
    }
    
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False

def save_readings_to_history(current_readings, costs, total):
    """Сохраняет текущие показания в историю и обновляет начальные значения"""
    global start_value_gas, start_value_electricity, start_value_water
    
    # Загружаем существующую историю
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
    
    # Создаем запись о текущем расчете
    record = {
        'date': datetime.now().strftime("%d.%m.%Y %H:%M"),
        'readings': {
            'gas': current_readings['gas'],
            'electricity': current_readings['electricity'],
            'water': current_readings['water']
        },
        'costs': {
            'gas': float(costs['gas']),
            'electricity': float(costs['electricity']),
            'water': float(costs['water'])
        },
        'total': float(total)
    }
    
    history.append(record)
    
    # Сохраняем историю
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    # ОБНОВЛЯЕМ НАЧАЛЬНЫЕ ЗНАЧЕНИЯ текущими показаниями
    start_value_gas = current_readings['gas']
    start_value_electricity = current_readings['electricity']
    start_value_water = current_readings['water']
    
    # Сохраняем обновленные начальные значения
    save_settings()
    
    return True

# Значения по умолчанию (будут перезаписаны при загрузке)
start_value_gas = 25745
start_value_electricity = 9838
start_value_water = 502

# Тарифы
tarif_gas = 8.7
tarif_electricity = 7.1
tarif_water = 84.44

# Комиссия банка (1% = 0.01)
fee_gas = 0.01
fee_electricity = 0.01
fee_water = 0.01

# Приветственное окно для первого запуска
def show_welcome_window():
    """Показывает приветственное окно для ввода начальных значений"""
    global start_value_gas, start_value_electricity, start_value_water
    
    welcome_window = Toplevel()
    welcome_window.title("Добро пожаловать!")
    welcome_window.geometry("400x350")
    welcome_window.grab_set()  # Блокирует главное окно
    
    # Заголовок
    Label(welcome_window, text="Добро пожаловать в Калькулятор коммуналки!", 
          font=("Arial", 12, "bold"), fg="blue").pack(pady=15)
    
    # Пояснение
    explanation = ("Это ваш первый запуск программы.\n\n"
                   "Пожалуйста, введите начальные показания счетчиков:\n"
                   "(эти значения можно будет изменить позже в настройках)")
    
    Label(welcome_window, text=explanation, 
          font=("Arial", 10), justify=LEFT).pack(pady=10, padx=20)
    
    # Фрейм для полей ввода
    frame = Frame(welcome_window)
    frame.pack(pady=10)
    
    # Поля ввода
    Label(frame, text="Газ:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=5, sticky="e")
    gas_entry = Entry(frame, width=20, font=("Arial", 10))
    gas_entry.insert(0, str(start_value_gas))
    gas_entry.grid(row=0, column=1, padx=5, pady=5)
    
    Label(frame, text="Электричество:", font=("Arial", 10)).grid(row=1, column=0, padx=5, pady=5, sticky="e")
    electricity_entry = Entry(frame, width=20, font=("Arial", 10))
    electricity_entry.insert(0, str(start_value_electricity))
    electricity_entry.grid(row=1, column=1, padx=5, pady=5)
    
    Label(frame, text="Вода:", font=("Arial", 10)).grid(row=2, column=0, padx=5, pady=5, sticky="e")
    water_entry = Entry(frame, width=20, font=("Arial", 10))
    water_entry.insert(0, str(start_value_water))
    water_entry.grid(row=2, column=1, padx=5, pady=5)
    
    # Подсказка
    Label(welcome_window, text="Введите целые числа (показания счетчиков)", 
          font=("Arial", 9), fg="gray").pack()

    # Дополнительное пояснение
    Label(welcome_window, 
          text="Эти значения будут использоваться как начальная точка отсчета.\n"
               "После каждого расчета они будут автоматически обновляться\n"
               "новыми показаниями для следующего месяца.",
          font=("Arial", 9), fg="blue", justify=LEFT).pack(pady=10)
    
    def save_initial_settings():
        """Сохраняет начальные значения и закрывает окно"""
        nonlocal gas_entry, electricity_entry, water_entry
        global start_value_gas, start_value_electricity, start_value_water
        
        try:
            # Получаем значения
            new_gas = int(gas_entry.get())
            new_electricity = int(electricity_entry.get())
            new_water = int(water_entry.get())
            
            # Проверяем, что значения положительные
            if new_gas < 0 or new_electricity < 0 or new_water < 0:
                box.showerror('Ошибка', 'Значения должны быть неотрицательными!')
                return
            
            # Сохраняем значения
            start_value_gas = new_gas
            start_value_electricity = new_electricity
            start_value_water = new_water
            
            # Сохраняем все настройки в файл
            save_settings()
            
            # Показываем сообщение об успехе
            box.showinfo('Готово!', 
                        'Начальные значения сохранены!\n\n'
                        'Теперь вы можете вводить текущие показания и рассчитывать сумму к оплате.\n'
                        'После оплаты новые показания автоматически станут начальными для следующего месяца.')
            
            # Закрываем приветственное окно
            welcome_window.destroy()
            
        except ValueError:
            box.showerror('Ошибка', 'Введите целые числа!')
    
    # Кнопки
    Button(welcome_window, text="Сохранить и продолжить", 
           command=save_initial_settings,
           bg="lightgreen", font=("Arial", 11), width=20).pack(pady=15)
    
    Button(welcome_window, text="Использовать значения по умолчанию", 
           command=lambda: [save_settings(), welcome_window.destroy()],
           bg="lightgray", font=("Arial", 10)).pack(pady=5)

# Загружаем настройки при запуске
is_first_run = not load_settings()

# Создание главного окна
window = Tk()
window.title('Калькулятор коммуналки')
window.geometry("500x350")

# Если это первый запуск, показываем приветственное окно
if is_first_run:
    # Показываем приветственное окно после загрузки главного окна
    window.after(100, show_welcome_window)
else:
    # Если это не первый запуск, показываем подсказку с текущими начальными значениями
    window.after(100, lambda: box.showinfo(
        'Информация',
        f'Текущие начальные показания (предыдущий месяц):\n\n'
        f'Газ: {start_value_gas}\n'
        f'Электричество: {start_value_electricity}\n'
        f'Вода: {start_value_water}\n\n'
        f'Введите новые показания и нажмите "Рассчитать"'
    ))

# СОЗДАЕМ ПЕРЕМЕННЫЕ ДЛЯ ЧЕКБОКСОВ (до функций)
box_gas_var = IntVar()  # 0 - не отмечен, 1 - отмечен
box_electricity_var = IntVar()
box_water_var = IntVar()

# СОЗДАЕМ ПЕРЕМЕННЫЕ ДЛЯ ТЕКСТА ЧЕКБОКСОВ
box_gas_text = StringVar(value=f"{int(fee_gas * 100)}%")
box_electricity_text = StringVar(value=f"{int(fee_electricity * 100)}%")
box_water_text = StringVar(value=f"{int(fee_water * 100)}%")

# ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЯ ТЕКСТА ЧЕКБОКСОВ
def update_checkbutton_texts():
    """Обновляет текст на чекбоксах в соответствии с текущими значениями комиссии"""
    box_gas_text.set(f"{int(fee_gas * 100)}%")
    box_electricity_text.set(f"{int(fee_electricity * 100)}%")
    box_water_text.set(f"{int(fee_water * 100)}%")

# ФУНКЦИИ ДЛЯ НАСТРОЕК

def open_settings_window():
    """Открывает главное окно настроек"""
    settings_window = Toplevel()
    settings_window.title("Настройки")
    settings_window.geometry("300x250")
    settings_window.grab_set()  # Блокирует главное окно пока открыты настройки
    
    Label(settings_window, text="Выберите категорию:", 
          font=("Arial", 12, "bold")).pack(pady=20)
    
    Button(settings_window, text="Тарифы", command=open_tarif_window,
           bg="lightblue", font=("Arial", 11), width=20).pack(pady=5)
    
    Button(settings_window, text="Комиссия", command=open_fee_window,
           bg="lightblue", font=("Arial", 11), width=20).pack(pady=5)
    
    Button(settings_window, text="Начальные настройки", command=open_start_values_window,
           bg="lightblue", font=("Arial", 11), width=20).pack(pady=5)
    
    Button(settings_window, text="Закрыть", command=settings_window.destroy,
           bg="lightcoral", font=("Arial", 11), width=20).pack(pady=20)

def open_tarif_window():
    """Открывает окно редактирования тарифов"""
    global tarif_gas, tarif_electricity, tarif_water
    
    tarif_window = Toplevel()
    tarif_window.title("Редактирование тарифов")
    tarif_window.geometry("350x250")
    tarif_window.grab_set()
    
    # Создаем переменные для редактирования
    tarif_gas_var = StringVar(value=str(tarif_gas))
    tarif_electricity_var = StringVar(value=str(tarif_electricity))
    tarif_water_var = StringVar(value=str(tarif_water))
    
    # Заголовок
    Label(tarif_window, text="Редактирование тарифов", 
          font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
    
    # Поля ввода
    Label(tarif_window, text="Газ (руб.):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
    entry_gas = Entry(tarif_window, textvariable=tarif_gas_var, width=15)
    entry_gas.grid(row=1, column=1, padx=10, pady=5)
    
    Label(tarif_window, text="Электричество (руб.):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
    entry_electricity = Entry(tarif_window, textvariable=tarif_electricity_var, width=15)
    entry_electricity.grid(row=2, column=1, padx=10, pady=5)
    
    Label(tarif_window, text="Вода (руб.):").grid(row=3, column=0, padx=10, pady=5, sticky="e")
    entry_water = Entry(tarif_window, textvariable=tarif_water_var, width=15)
    entry_water.grid(row=3, column=1, padx=10, pady=5)
    
    def apply_tarif_changes():
        """Применяет изменения тарифов"""
        nonlocal tarif_gas_var, tarif_electricity_var, tarif_water_var
        global tarif_gas, tarif_electricity, tarif_water
        
        try:
            # Пробуем преобразовать введенные значения в float
            new_gas = float(tarif_gas_var.get())
            new_electricity = float(tarif_electricity_var.get())
            new_water = float(tarif_water_var.get())
            
            # Проверяем, что значения положительные
            if new_gas <= 0 or new_electricity <= 0 or new_water <= 0:
                box.showerror('Ошибка', 'Тарифы должны быть положительными числами!')
                return
            
            # Применяем изменения
            tarif_gas = new_gas
            tarif_electricity = new_electricity
            tarif_water = new_water
            
            box.showinfo('Успех', 'Тарифы успешно обновлены!')
            tarif_window.destroy()
            
        except ValueError:
            box.showerror('Ошибка', 'Введите корректные числа!')
    
    def cancel_tarif_changes():
        """Отменяет изменения и закрывает окно"""
        tarif_window.destroy()
    
    # Кнопки
    Button(tarif_window, text="Применить", command=apply_tarif_changes,
           bg="lightgreen", width=10).grid(row=4, column=0, pady=20)
    Button(tarif_window, text="Отмена", command=cancel_tarif_changes,
           bg="lightcoral", width=10).grid(row=4, column=1, pady=20)

def open_fee_window():
    """Открывает окно редактирования комиссии"""
    global fee_gas, fee_electricity, fee_water
    
    fee_window = Toplevel()
    fee_window.title("Редактирование комиссии")
    fee_window.geometry("350x250")
    fee_window.grab_set()
    
    # Создаем переменные для редактирования (умножаем на 100 для отображения в процентах)
    fee_gas_var = StringVar(value=str(int(fee_gas * 100)))
    fee_electricity_var = StringVar(value=str(int(fee_electricity * 100)))
    fee_water_var = StringVar(value=str(int(fee_water * 100)))
    
    # Заголовок
    Label(fee_window, text="Редактирование комиссии банка", 
          font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
    
    # Поля ввода
    Label(fee_window, text="Газ (%):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
    entry_gas = Entry(fee_window, textvariable=fee_gas_var, width=15)
    entry_gas.grid(row=1, column=1, padx=10, pady=5)
    
    Label(fee_window, text="Электричество (%):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
    entry_electricity = Entry(fee_window, textvariable=fee_electricity_var, width=15)
    entry_electricity.grid(row=2, column=1, padx=10, pady=5)
    
    Label(fee_window, text="Вода (%):").grid(row=3, column=0, padx=10, pady=5, sticky="e")
    entry_water = Entry(fee_window, textvariable=fee_water_var, width=15)
    entry_water.grid(row=3, column=1, padx=10, pady=5)
    
    def apply_fee_changes():
        """Применяет изменения комиссии"""
        nonlocal fee_gas_var, fee_electricity_var, fee_water_var
        global fee_gas, fee_electricity, fee_water
        
        try:
            # Пробуем преобразовать введенные значения в float
            new_gas = float(fee_gas_var.get()) / 100  # Переводим проценты в коэффициент
            new_electricity = float(fee_electricity_var.get()) / 100
            new_water = float(fee_water_var.get()) / 100
            
            # Проверяем, что значения в допустимом диапазоне
            if new_gas < 0 or new_electricity < 0 or new_water < 0 or new_gas > 1 or new_electricity > 1 or new_water > 1:
                box.showerror('Ошибка', 'Комиссия должна быть от 0% до 100%!')
                return
            
            # Применяем изменения
            fee_gas = new_gas
            fee_electricity = new_electricity
            fee_water = new_water
            
            # Обновляем текст на чекбоксах
            update_checkbutton_texts()
            
            box.showinfo('Успех', 'Комиссия успешно обновлена!')
            fee_window.destroy()
            
        except ValueError:
            box.showerror('Ошибка', 'Введите корректные числа!')
    
    def cancel_fee_changes():
        """Отменяет изменения и закрывает окно"""
        fee_window.destroy()
    
    # Кнопки
    Button(fee_window, text="Применить", command=apply_fee_changes,
           bg="lightgreen", width=10).grid(row=4, column=0, pady=20)
    Button(fee_window, text="Отмена", command=cancel_fee_changes,
           bg="lightcoral", width=10).grid(row=4, column=1, pady=20)

def open_start_values_window():
    """Открывает окно редактирования начальных значений с предупреждением"""
    global start_value_gas, start_value_electricity, start_value_water
    
    # Сначала показываем предупреждение
    box.showwarning(
        'Внимание!', 
        'Изменение начальных настроек может привести к \nнекорректным результатам расчетов!\n\n'
        'Убедитесь, что вы действительно хотите \nизменить эти значения.'
    )
    
    start_window = Toplevel()
    start_window.title("Редактирование начальных значений")
    start_window.geometry("350x300")
    start_window.grab_set()
    
    # Создаем переменные для редактирования
    start_gas_var = StringVar(value=str(start_value_gas))
    start_electricity_var = StringVar(value=str(start_value_electricity))
    start_water_var = StringVar(value=str(start_value_water))
    
    # Заголовок
    Label(start_window, text="Редактирование начальных значений", 
          font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
    
    # Добавляем предупреждение прямо в окно
    warning_label = Label(start_window, 
                         text="⚠️ Будьте внимательны!\nИзменение этих значений повлияет на все будущие расчеты",
                         font=("Arial", 9), fg="red", justify=CENTER)
    warning_label.grid(row=1, column=0, columnspan=2, pady=5)
    
    # Поля ввода
    Label(start_window, text="Газ (начало):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
    entry_gas = Entry(start_window, textvariable=start_gas_var, width=15)
    entry_gas.grid(row=2, column=1, padx=10, pady=5)
    
    Label(start_window, text="Электричество (начало):").grid(row=3, column=0, padx=10, pady=5, sticky="e")
    entry_electricity = Entry(start_window, textvariable=start_electricity_var, width=15)
    entry_electricity.grid(row=3, column=1, padx=10, pady=5)
    
    Label(start_window, text="Вода (начало):").grid(row=4, column=0, padx=10, pady=5, sticky="e")
    entry_water = Entry(start_window, textvariable=start_water_var, width=15)
    entry_water.grid(row=4, column=1, padx=10, pady=5)
    
    def apply_start_changes():
        """Применяет изменения начальных значений с подтверждением"""
        nonlocal start_gas_var, start_electricity_var, start_water_var
        global start_value_gas, start_value_electricity, start_value_water
        
        try:
            # Пробуем преобразовать введенные значения в int
            new_gas = int(start_gas_var.get())
            new_electricity = int(start_electricity_var.get())
            new_water = int(start_water_var.get())
            
            # Проверяем, что значения положительные
            if new_gas < 0 or new_electricity < 0 or new_water < 0:
                box.showerror('Ошибка', 'Начальные значения должны быть неотрицательными!')
                return
            
            # Запрашиваем подтверждение
            confirm = box.askyesno(
                'Подтверждение', 
                f'Вы уверены, что хотите изменить начальные значения?\n\n'
                f'Было:\n'
                f'Газ: {start_value_gas}\n'
                f'Электричество: {start_value_electricity}\n'
                f'Вода: {start_value_water}\n\n'
                f'Станет:\n'
                f'Газ: {new_gas}\n'
                f'Электричество: {new_electricity}\n'
                f'Вода: {new_water}'
            )
            
            if confirm:
                # Применяем изменения
                start_value_gas = new_gas
                start_value_electricity = new_electricity
                start_value_water = new_water
                
                box.showinfo('Успех', 'Начальные значения успешно обновлены!')
                start_window.destroy()
            else:
                # Если пользователь отказался, ничего не меняем
                box.showinfo('Отмена', 'Изменения отменены')
            
        except ValueError:
            box.showerror('Ошибка', 'Введите целые числа!')
    
    def cancel_start_changes():
        """Отменяет изменения и закрывает окно"""
        # Спрашиваем, точно ли хочет отменить
        if box.askyesno('Подтверждение', 'Вы действительно хотите отменить изменения?'):
            start_window.destroy()
    
    # Кнопки
    Button(start_window, text="Применить", command=apply_start_changes,
           bg="lightgreen", width=10).grid(row=5, column=0, pady=20)
    Button(start_window, text="Отмена", command=cancel_start_changes,
           bg="lightcoral", width=10).grid(row=5, column=1, pady=20)

# ФУНКЦИИ ДЛЯ ОСНОВНОГО РАСЧЕТА

def show_results_window(results_data, current_readings, costs, total_with_fee):
    """Создает окно с результатами в виде таблицы и предлагает обновить начальные значения"""
    results_window = Toplevel()
    results_window.title("Результаты расчета")
    results_window.geometry("1200x450")
    
    # Заголовки таблицы
    headers = ["Ресурс", "Начало", "Конец", "Расход", "Тариф", "Сумма", "Комиссия", "Итого"]
    for col, header in enumerate(headers):
        Label(results_window, text=header, 
              font=("Arial", 10, "bold"), 
              bg="lightgray", relief="ridge", 
              padx=10, pady=5, width=12).grid(row=0, column=col, sticky="nsew")
    
    # Данные по каждой позиции
    row = 1
    total_sum = Decimal('0')
    
    for data in results_data:
        name, start, end, consumption, tarif, amount, fee_amount, total = data
        
        Label(results_window, text=name, relief="ridge", padx=10, pady=5).grid(row=row, column=0, sticky="nsew")
        Label(results_window, text=str(start), relief="ridge", padx=10, pady=5).grid(row=row, column=1, sticky="nsew")
        Label(results_window, text=str(end), relief="ridge", padx=10, pady=5).grid(row=row, column=2, sticky="nsew")
        Label(results_window, text=str(consumption), relief="ridge", padx=10, pady=5).grid(row=row, column=3, sticky="nsew")
        Label(results_window, text=f"{tarif:.2f}", relief="ridge", padx=10, pady=5).grid(row=row, column=4, sticky="nsew")
        Label(results_window, text=f"{amount:.2f}", relief="ridge", padx=10, pady=5).grid(row=row, column=5, sticky="nsew")
        
        # Показываем комиссию только если она применялась
        if fee_amount > 0:
            Label(results_window, text=f"{fee_amount:.2f}", relief="ridge", padx=10, pady=5).grid(row=row, column=6, sticky="nsew")
        else:
            Label(results_window, text="-", relief="ridge", padx=10, pady=5).grid(row=row, column=6, sticky="nsew")
            
        Label(results_window, text=f"{total:.2f}", relief="ridge", padx=10, pady=5, 
              font=("Arial", 10, "bold"), fg="green").grid(row=row, column=7, sticky="nsew")
        
        total_sum += amount
        row += 1
    
    # Итоговая строка (если больше одного ресурса)
    if len(results_data) > 1:
        # Пустые ячейки для первых колонок
        for col in range(5):
            Label(results_window, text="", relief="ridge", padx=10, pady=5).grid(row=row, column=col, sticky="nsew")
        
        Label(results_window, text="ИТОГО:", relief="ridge", padx=10, pady=5,
              font=("Arial", 10, "bold"), bg="lightyellow").grid(row=row, column=5, sticky="nsew")
        Label(results_window, text=f"{total_sum:.2f}", relief="ridge", padx=10, pady=5,
              font=("Arial", 10, "bold"), bg="lightyellow").grid(row=row, column=6, sticky="nsew")
        Label(results_window, text=f"{total_with_fee:.2f}", relief="ridge", padx=10, pady=5,
              font=("Arial", 10, "bold"), bg="lightyellow", fg="blue").grid(row=row, column=7, sticky="nsew")
        row += 1
    
    # Разделитель
    Label(results_window, text="-"*100, bg="lightgray").grid(row=row, column=0, columnspan=8, sticky="ew", pady=10)
    row += 1
    
    # Предложение сохранить новые показания как начальные для следующего месяца
    save_frame = Frame(results_window, bg="lightblue", relief="ridge", bd=2)
    save_frame.grid(row=row, column=0, columnspan=8, padx=10, pady=10, sticky="ew")
    
    Label(save_frame, 
          text="После оплаты новые показания станут начальными для следующего месяца",
          font=("Arial", 10, "bold"), bg="lightblue", fg="darkblue").pack(pady=5)
    
    def save_and_close():
        """Сохраняет показания в историю, обновляет начальные значения и закрывает окно"""
        save_readings_to_history(current_readings, costs, total_with_fee)
        box.showinfo('Готово', 
                    f'Показания сохранены!\n\n'
                    f'Новые начальные значения для следующего месяца:\n'
                    f'Газ: {current_readings["gas"]}\n'
                    f'Электричество: {current_readings["electricity"]}\n'
                    f'Вода: {current_readings["water"]}')
        results_window.destroy()
    
    def close_without_saving():
        """Закрывает окно без сохранения показаний"""
        if box.askyesno('Подтверждение', 
                        'Вы уверены, что не хотите сохранить новые показания?\n'
                        'В следующий раз начальные значения останутся прежними.'):
            results_window.destroy()
    
    # Кнопки
    button_frame = Frame(results_window)
    button_frame.grid(row=row+1, column=0, columnspan=8, pady=10)
    
    Button(button_frame, text="✅ Сохранить и закрыть", 
           command=save_and_close,
           bg="lightgreen", font=("Arial", 11), width=20).pack(side=LEFT, padx=5)
    
    Button(button_frame, text="❌ Закрыть без сохранения", 
           command=close_without_saving,
           bg="lightcoral", font=("Arial", 11), width=20).pack(side=LEFT, padx=5)
    
    # Настройка растяжения колонок
    for col in range(8):
        results_window.grid_columnconfigure(col, weight=1)

def calculate():
    """Основная функция расчета"""
    try:
        results_data = []  # Список для хранения данных по каждой позиции
        current_readings = {}  # Словарь для текущих показаний
        costs = {}  # Словарь для стоимостей без комиссии
        
        # Обработка газа
        if enter_gas.get().strip():
            try:
                gas_end = Decimal(enter_gas.get())
                gas_start = Decimal(start_value_gas)
                gas_consumption = gas_end - gas_start
                gas_amount = gas_consumption * Decimal(str(tarif_gas))
                
                # Проверяем, установлен ли чекбокс для газа
                if box_gas_var.get() == 1:
                    gas_fee = gas_amount * Decimal(str(fee_gas))
                else:
                    gas_fee = Decimal('0')
                    
                gas_total = gas_amount + gas_fee
                
                results_data.append(("Газ", gas_start, gas_end, gas_consumption, 
                                    tarif_gas, gas_amount, gas_fee, gas_total))
                
                current_readings['gas'] = int(enter_gas.get())
                costs['gas'] = gas_amount
                
            except InvalidOperation:
                box.showerror('Ошибка', 'В поле "Газ" введите корректное число!')
                return
        
        # Обработка электричества
        if enter_electricity.get().strip():
            try:
                elec_end = Decimal(enter_electricity.get())
                elec_start = Decimal(start_value_electricity)
                elec_consumption = elec_end - elec_start
                elec_amount = elec_consumption * Decimal(str(tarif_electricity))
                
                if box_electricity_var.get() == 1:
                    elec_fee = elec_amount * Decimal(str(fee_electricity))
                else:
                    elec_fee = Decimal('0')
                    
                elec_total = elec_amount + elec_fee
                
                results_data.append(("Электричество", elec_start, elec_end, elec_consumption,
                                    tarif_electricity, elec_amount, elec_fee, elec_total))
                
                current_readings['electricity'] = int(enter_electricity.get())
                costs['electricity'] = elec_amount
                
            except InvalidOperation:
                box.showerror('Ошибка', 'В поле "Электричество" введите корректное число!')
                return
        
        # Обработка воды
        if enter_water.get().strip():
            try:
                water_end = Decimal(enter_water.get())
                water_start = Decimal(start_value_water)
                water_consumption = water_end - water_start
                water_amount = water_consumption * Decimal(str(tarif_water))
                
                if box_water_var.get() == 1:
                    water_fee = water_amount * Decimal(str(fee_water))
                else:
                    water_fee = Decimal('0')
                    
                water_total = water_amount + water_fee
                
                results_data.append(("Вода", water_start, water_end, water_consumption,
                                    tarif_water, water_amount, water_fee, water_total))
                
                current_readings['water'] = int(enter_water.get())
                costs['water'] = water_amount
                
            except InvalidOperation:
                box.showerror('Ошибка', 'В поле "Вода" введите корректное число!')
                return
        
        # Проверка, что хотя бы одно поле заполнено
        if not results_data:
            box.showwarning('Предупреждение', 'Заполните хотя бы одно поле!')
            return
        
        # Вычисляем общую сумму с комиссией
        total_with_fee = sum(data[7] for data in results_data)
        
        # Показываем окно с результатами
        show_results_window(results_data, current_readings, costs, total_with_fee)
        
    except Exception as e:
        box.showerror('Ошибка', f'Произошла ошибка: {type(e).__name__}\n{e}')

# СОЗДАНИЕ ИНТЕРФЕЙСА

# Верхняя панель с датой и кнопкой настроек
current_date = datetime.now().strftime("%d.%m.%Y")
label_date = Label(window, text=f'Сегодня: {current_date}', font=("Arial", 10))
label_date.grid(row=0, column=0, padx=10, pady=10, sticky="w")

# Кнопка настроек (теперь вызывает open_settings_window)
btn_settings = Button(window, text='Настройки', bg="lightgray", command=open_settings_window)
btn_settings.grid(row=0, column=2, padx=10, pady=10, sticky="e")

# Отображение текущих начальных значений (для информации)
info_frame = Frame(window, bg="lightyellow", relief="ridge", bd=1)
info_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

Label(info_frame, 
      text=f"Начальные показания (предыдущий месяц): Газ: {start_value_gas} | "
           f"Электричество: {start_value_electricity} | Вода: {start_value_water}",
      font=("Arial", 9), bg="lightyellow", fg="darkblue").pack(pady=2)

# Заголовки колонок
Label(window, text="Ресурс", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=5, pady=5)
Label(window, text="Показания", font=("Arial", 10, "bold")).grid(row=1, column=1, padx=5, pady=5)
Label(window, text="Комиссия", font=("Arial", 10, "bold")).grid(row=1, column=2, padx=5, pady=5)

# Строка для газа
label_gas = Label(window, text='Газ')
label_gas.grid(row=2, column=0, padx=5, pady=5, sticky="w")

enter_gas = Entry(window, width=20)
enter_gas.grid(row=2, column=1, padx=5, pady=5)

# Важно: привязываем переменную к чекбоксу и используем textvariable для динамического текста
box_gas = Checkbutton(window, textvariable=box_gas_text, variable=box_gas_var)
box_gas.grid(row=2, column=2, padx=5, pady=5)

# Строка для электричества
label_electricity = Label(window, text='Электричество')
label_electricity.grid(row=3, column=0, padx=5, pady=5, sticky="w")

enter_electricity = Entry(window, width=20)
enter_electricity.grid(row=3, column=1, padx=5, pady=5)

box_electricity = Checkbutton(window, textvariable=box_electricity_text, variable=box_electricity_var)
box_electricity.grid(row=3, column=2, padx=5, pady=5)

# Строка для воды
label_water = Label(window, text='Вода')
label_water.grid(row=4, column=0, padx=5, pady=5, sticky="w")

enter_water = Entry(window, width=20)
enter_water.grid(row=4, column=1, padx=5, pady=5)

box_water = Checkbutton(window, textvariable=box_water_text, variable=box_water_var)
box_water.grid(row=4, column=2, padx=5, pady=5)

# Кнопка расчета
btn_check = Button(window, text='Рассчитать', command=calculate, 
                   bg="lightblue", font=("Arial", 12), width=20)
btn_check.grid(row=5, column=0, columnspan=3, pady=20)

window.mainloop()