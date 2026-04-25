from calculator import calculate_service, calculate_fixed_service
from gui import show_results_window
import config
from file_manager import save_settings, save_readings_to_history
from decimal import Decimal, InvalidOperation

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

def calculate_dynamic(entries, checkboxes, services, warning_callback, error_callback, save_services_callback):
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
            has_commission = checkboxes.get(key).get() if checkboxes.get(key) else 0

            if service_type == "metered":
                entry = entries.get(key)
                if entry is None:
                    continue
                value_str = entry.get().strip()
                if not value_str:
                    continue
                has_commission = 1 if (checkboxes.get(key) and checkboxes.get(key).get()) else 0
                try:
                    result = calculate_service(name, value_str, service.get("start_value", 0), tariff, has_commission, fee)
                except ValueError as e:
                    error_callback(name, str(e))
                    return
                if result is None:
                    # этот случай невозможен, так как поле не пустое, но оставим
                    continue
                results_data.append(result)
                current_readings[key] = int(value_str)
                costs[key] = result["Amount"]
            else:  # fixed
                result = calculate_fixed_service(name, tariff, has_commission, fee)
                results_data.append(result)
                # Для fixed не обновляем current_readings и costs (они не нужны для сохранения)

        if not results_data:
            warning_callback("Предупреждение", "Заполните хотя бы одно поле!")
            return

        total_amount = sum(item["Amount"] for item in results_data)
        total_fee = sum(item["Fee"] for item in results_data)
        total_sum_with_fee = sum(item["Total"] for item in results_data)

        def save_readings(current_readings, costs, total_sum_with_fee):
            for key, reading in current_readings.items():
                if key in services and services[key]["type"] == "metered":
                    services[key]["start_value"] = reading
            save_services_callback()

        show_results_window(results_data, current_readings, costs, total_amount, total_fee, total_sum_with_fee, save_readings, services)

    except Exception as e:
        error_callback("Ошибка", f"Произошла ошибка: {type(e).__name__}\n{e}")

def save_readings(current_readings, costs, total_sum_with_fee):
    """Сохраняет показания в историю, обновляет начальные значения."""
    save_readings_to_history(current_readings, costs, total_sum_with_fee)

def save_initial_settings(gas, electricity, water):
    """Сохраняет начальные показания."""
    config.services["gas"]["start_value"] = gas
    config.services["electricity"]["start_value"] = electricity
    config.services["water"]["start_value"] = water
    save_settings()  

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
