from calculator import calculate_service, calculate_fixed_service
import config
from file_manager import save_settings
from decimal import Decimal, InvalidOperation
from calculations import normalize_decimal, calculate_consumption_with_replacements

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
    verification_ids_used = []   # для ID поверок, где расход был использован
    norm_verification_ids = []   # для ID поверок, где норматив был использован

    for key, service in config.services.items():
        if not service.get("enabled", True):
            continue
        reading = readings.get(key, '')
        has_commission = commissions.get(key, False)
        try:
            calc = service.calculate(reading, has_commission)
        except InvalidOperation:
            if error_callback:
                error_callback(service["name"], "Введите корректное число!")
            else:
                raise ValueError(f"В поле '{service['name']}' введите корректное число!")
            return None
        if calc is None:
            continue
        result = calc['result']
        result['Key'] = key
        results_data.append(result)
        if calc['current_reading'] is not None:
            current_readings[key] = calc['current_reading']
        costs[key] = calc['cost']
        total_amount += calc['amount']
        total_fee += calc['fee']
        total_sum_with_fee += calc['total']
        used_replacement_ids.extend(calc['used_replacement_ids'])
        verification_ids_used.extend(calc['verification_ids_used'])
        norm_verification_ids.extend(calc['norm_verification_ids'])

    if not results_data:
        if warning_callback:
            warning_callback("Предупреждение", "Заполните хотя бы одно поле!")
        else:
            pass
        return None

    return (results_data, current_readings, costs, total_amount, total_fee, total_sum_with_fee, used_replacement_ids, verification_ids_used, norm_verification_ids)
