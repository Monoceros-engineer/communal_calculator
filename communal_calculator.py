from calculator import calculate_service, calculate_fixed_service
import config
from file_manager import save_settings
from decimal import Decimal, InvalidOperation

def normalize_decimal(s):
    """Преобразует строку с запятой или точкой в формат с точкой."""
    s = s.strip().replace(',', '.')
    # удаляем возможные пробелы между цифрами
    s = s.replace(' ', '')
    return s

def get_services():
    """Возвращает словарь services со всеми параметрами."""
    return config.services

def get_start_values():
    """Возвращает словарь с начальными показаниями."""
    return {
        "gas": config.services["gas"]["start_value"],
        "electricity": config.services["electricity"]["start_value"],
        "water": config.services["water"]["start_value"]
    }

def calculate_consumption_with_replacements(start_value, replacements, current_reading):
    """
    Рассчитывает общий расход ресурса с учётом замен счётчиков.
    start_value: показания на начало периода (последние оплаченные)
    replacements: список замен, каждая: {'old_final': float, 'new_start': float, 'date': str (optional)}
    current_reading: текущее показание (последнее введённое)
    Возвращает общий расход (float).
    """
    total = Decimal('0')
    last = start_value
    # Сортируем замены по дате, если даты нет, то по порядку добавления (оставляем как есть)
    # Для простоты сортируем по 'date', если поле отсутствует, ставим пустую строку
    sorted_reps = sorted(replacements, key=lambda x: x.get('date', ''))
    for rep in sorted_reps:
        old_final = rep['old_final']
        new_start = rep['new_start']
        if old_final < last:
            # некорректные данные, но можно просто пропустить или добавить 0
            continue
        total += old_final - last
        last = new_start
    total += current_reading - last
    return total

def get_tariffs():
    """Возвращает словарь с текущими тарифами."""
    return {
        "gas": config.services["gas"]["tariff"],
        "electricity": config.services["electricity"]["tariff"],
        "water": config.services["water"]["tariff"]
    }

def get_fees():
    """Возвращает словарь с текущими комиссиями."""
    return {
        "gas": config.services["gas"]["fee"],
        "electricity": config.services["electricity"]["fee"],
        "water": config.services["water"]["fee"]
    }

# ФУНКЦИИ ДЛЯ ОСНОВНОГО РАСЧЕТА

def calculate_dynamic(entries, services_frame, services, warning_callback, error_callback, save_services_callback):
    try:
        results_data = []
        current_readings = {}
        costs = {}

        for key, service in services.items():
            if not service.get("enabled", True):
                continue

            name = service["name"]
            service_type = service["type"]
            tariff = service["tariff"]
            fee = service["fee"]
            # Получаем состояние чекбокса напрямую из виджета
            has_commission = 0
            for child in services_frame.winfo_children():
                if hasattr(child, 'service_key') and child.service_key == key:
                    print(f"Found child: {child.service_key}, checked={getattr(child, 'checked', False)}")
                    has_commission = 1 if getattr(child, 'checked', False) else 0
                    break
            print(f"DEBUG: {key} has_commission = {has_commission}")

            if service_type == "metered":
                entry = entries.get(key)
                if entry is None:
                    continue
                value_str = entry.get().strip()
                if not value_str:
                    continue
                normalized = normalize_decimal(value_str)
                try:
                    result = calculate_service(name, normalized, service.get("start_value", 0), tariff, has_commission, fee)
                except ValueError as e:
                    error_callback(name, str(e))
                    return
                if result is None:
                    continue
                results_data.append(result)
                current_readings[key] = float(normalized)
                costs[key] = result["Amount"]
            else:  # fixed
                result = calculate_fixed_service(name, tariff, has_commission, fee)
                results_data.append(result)
                costs[key] = result["Amount"]

        if not results_data:
            warning_callback("Предупреждение", "Заполните хотя бы одно поле!")
            return

        total_amount = sum(item["Amount"] for item in results_data)
        total_fee = sum(item["Fee"] for item in results_data)
        total_sum_with_fee = sum(item["Total"] for item in results_data)

    except Exception as e:
        print(f"ERROR in calculate_dynamic: {e}")
        error_callback("Ошибка", f"Произошла ошибка: {type(e).__name__}\n{e}")


def save_initial_settings_multi(initial_values, services, save_services_callback):
    """Сохраняет начальные значения для нескольких услуг (по счётчику)."""
    for key, value in initial_values.items():
        if key in services and services[key]["type"] == "metered":
            services[key]["start_value"] = value
    save_services_callback()

def save_tariffs(new_tariffs):
    """Сохраняет тарифы и записывает в файл."""
    for key, new_tariff in new_tariffs.items():
        if key in config.services:
            config.services[key]["tariff"] = new_tariff
    save_settings()      

def save_fees(new_fees):
    """Сохраняет комиссии и записывает в файл."""
    for key, new_fee in new_fees.items():
        if key in config.services:
            config.services[key]["fee"] = new_fee
    save_settings()

def save_services():
    """Сохраняет текущее состояние services в файл."""
    from file_manager import save_settings
    save_settings()

def process_services_data(readings, commissions, warning_callback=None, error_callback=None):
    """
    Обрабатывает услуги на основе введённых показаний и состояния чекбоксов комиссии.
    readings: dict {service_key: str} – строковые показания (могут быть пустыми)
    commissions: dict {service_key: bool} – True если комиссия включена
    Возвращает кортеж (results_data, current_readings, costs, total_amount, total_fee, total_sum_with_fee)
    """
    results_data = []
    current_readings = {}
    costs = {}
    total_amount = Decimal('0')
    total_fee = Decimal('0')
    total_sum_with_fee = Decimal('0')
    used_replacement_ids = [] 
    new_start_values = {}

    for key, service in config.services.items():
        if not service.get("enabled", True):
            continue
        name = service["name"]
        service_type = service["type"]
        tariff = service["tariff"]
        fee = service.get('fee', 0.0)
        has_commission = commissions.get(key, False)

        if service_type == "metered":
            # --- 1. Активная поверка (счётчик на поверке) ---
            active_verification = service.get('active_verification')
            if active_verification:
                amount_norm = active_verification.get('amount_norm', 0.0)
                if amount_norm is None:
                    amount_norm = 0.0
                fee = service.get('fee', 0.0)
                fee_amount = amount_norm * fee if has_commission else 0.0
                total = amount_norm + fee_amount
                result = {
                    "Key": key,
                    "Name": name + " (норматив)",
                    "Start value": None,
                    "End value": None,
                    "Consumption": 0,
                    "Tariff": None,
                    "Amount": amount_norm,
                    "Fee": fee_amount,
                    "Total": total
                }
                results_data.append(result)
                costs[key] = amount_norm
                total_amount += amount_norm
                total_fee += fee_amount
                total_sum_with_fee += total
                continue  # пропускаем обычный расчёт

            # --- 2. Обычный расчёт по показаниям ---
            value_str = readings.get(key, "").strip()
            if not value_str:
                continue
            normalized = normalize_decimal(value_str)
            try:
                end = Decimal(normalized)
                start = Decimal(service.get("start_value", 0))
                replacements = service.get("replacements", [])
                # Преобразуем замены в Decimal
                dec_replacements = []
                for rep in replacements:
                    dec_replacements.append({
                        "old_final": Decimal(rep["old_final"]),
                        "new_start": Decimal(rep["new_start"])
                    })

                # === ДОБАВЛЕНО ДЛЯ ПОВЕРКИ ===
                # Проверяем завершённую поверку (если есть и не оплачена)
                last_verif = service.get('last_completed_verification')
                if last_verif and not last_verif.get('is_paid', False):
                    # Добавляем поверку как замену
                    dec_replacements.append({
                        "old_final": Decimal(last_verif['old_final']),
                        "new_start": Decimal(last_verif['new_start'])
                    })
                    # Запоминаем ID для последующей оплаты
                    used_replacement_ids.append(last_verif['id'])
                    # Запоминаем новое начальное значение для услуги
                    new_start_values[key] = last_verif['new_start']
                # === КОНЕЦ ДОБАВЛЕННОГО БЛОКА ===

                total_consumption = calculate_consumption_with_replacements(start, dec_replacements, end)
                amount = total_consumption * Decimal(str(tariff))
                if has_commission:
                    fee_amount = amount * Decimal(str(fee))
                else:
                    fee_amount = Decimal('0')
                total = amount + fee_amount
                # Сохраняем ID использованных замен (если они есть)
                # Для этого нужно знать ID каждой замены. В текущей структуре service["replacements"] может содержать ID?
                # В `load_services` мы загружаем замены с полем 'id'. Добавим его.
                # Пока допустим, что replacements содержит словари с 'id'.
                # В будущем нужно, чтобы `load_services` добавляла id.
                for rep in replacements:
                    if 'id' in rep:
                        used_replacement_ids.append(rep['id'])
            except InvalidOperation:
                if error_callback:
                    error_callback(name, "Введите корректное число!")
                else:
                    raise ValueError(f"В поле '{name}' введите корректное число!")
                return None
            result = {
                "Key": key,
                "Name": name,
                "Start value": start,
                "End value": end,
                "Consumption": total_consumption,
                "Tariff": tariff,
                "Amount": amount,
                "Fee": fee_amount,
                "Total": total
            }
            results_data.append(result)
            current_readings[key] = float(end)
            costs[key] = amount
            total_amount += amount
            total_fee += fee_amount
            total_sum_with_fee += total
        else:  # fixed
            result = calculate_fixed_service(name, tariff, has_commission, fee)
            result["Key"] = key
            results_data.append(result)
            costs[key] = result["Amount"]
            total_amount += result["Amount"]
            total_fee += result["Fee"]
            total_sum_with_fee += result["Total"]

    if not results_data:
        if warning_callback:
            warning_callback("Предупреждение", "Заполните хотя бы одно поле!")
        else:
            pass
        return None

    return (results_data, current_readings, costs, total_amount, total_fee, total_sum_with_fee, used_replacement_ids, new_start_values)
