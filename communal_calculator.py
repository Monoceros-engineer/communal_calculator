from calculator import calculate_service
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

            if service_type == "metered":
                entry = entries.get(key)
                if entry is None:
                    continue
                value_str = entry.get().strip()
                if not value_str:
                    continue
                try:
                    end = Decimal(value_str)
                    start = Decimal(service.get("start_value", 0))
                    consumption = end - start
                    amount = consumption * Decimal(str(tariff))
                except InvalidOperation:
                    error_callback(name, "Введите корректное число!")
                    return
            else:  # fixed
                value_str = None
                consumption = 1
                amount = Decimal(str(tariff))

            checkbox_var = checkboxes.get(key)
            has_commission = checkbox_var.get() if checkbox_var else 0
            if has_commission:
                fee_amount = amount * Decimal(str(fee))
            else:
                fee_amount = Decimal('0')
            total = amount + fee_amount

            result_item = {
                "Name": name,
                "Start value": service.get("start_value", "—") if service_type == "metered" else "—",
                "End value": value_str if value_str else "—",
                "Consumption": consumption if service_type == "metered" else "—",
                "Tariff": tariff,
                "Amount": amount,
                "Fee": fee_amount,
                "Total": total
            }
            results_data.append(result_item)
            if service_type == "metered":
                current_readings[key] = int(value_str)
                costs[key] = amount

        if not results_data:
            warning_callback("Предупреждение", "Заполните хотя бы одно поле!")
            return

        total_amount = sum(item["Amount"] for item in results_data)
        total_fee = sum(item["Fee"] for item in results_data)
        total_sum_with_fee = sum(item["Total"] for item in results_data)

        # Функция сохранения (обновляет начальные значения в services)
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
