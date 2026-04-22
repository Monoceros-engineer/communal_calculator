from calculator import calculate_service
from gui import show_results_window
import config
from file_manager import save_settings, save_readings_to_history

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

def calculate(enter_gas, enter_electricity, enter_water, 
              box_gas_var, box_electricity_var, box_water_var,
              start_value_gas, start_value_electricity, start_value_water,
              tarif_gas, tarif_electricity, tarif_water,
              fee_gas, fee_electricity, fee_water, warning_callback, error_callback):
    """Основная функция расчета"""
    try:
        results_data = []  # Список для хранения данных по каждой позиции
        current_readings = {}  # Словарь для текущих показаний
        costs = {}  # Словарь для стоимостей без комиссии

        # Обработка газа
        resuslts_gas = calculate_service(
            "Газ",
            enter_gas.get(),
            start_value_gas,
            tarif_gas,
            box_gas_var.get(),
            fee_gas,
        )  # Это возвращаемый кортеж данных функции calculate_service для газа
        if resuslts_gas is not None:
            results_data.append(resuslts_gas)
            current_readings["gas"] = int(enter_gas.get())
            costs["gas"] = resuslts_gas["Amount"]
        
        # Обработка электричества
        results_electricity = calculate_service(
            "Электричество",
            enter_electricity.get(),
            start_value_electricity,
            tarif_electricity,
            box_electricity_var.get(),
            fee_electricity,
        )  # Это возвращаемый кортеж функции calculate_service для электричества
        if results_electricity is not None:
            results_data.append(results_electricity)
            current_readings["electricity"] = int(enter_electricity.get())
            costs["electricity"] = results_electricity["Amount"]

        # Обработка воды
        resultrs_water = calculate_service(
            "Вода",
            enter_water.get(),
            start_value_water,
            tarif_water,
            box_water_var.get(),
            fee_water,
        )  # Это возвращаемый кортеж функции calculate_service для воды
        if resultrs_water is not None:
            results_data.append(resultrs_water)
            current_readings["water"] = int(enter_water.get())
            costs["water"] = resultrs_water["Amount"]

        # Проверка, что хотя бы одно поле заполнено
        if not results_data:
            warning_callback("Предупреждение", "Заполните хотя бы одно поле!")
            return

        # Вычисляем общую сумму с комиссией
        total_amount=sum(data["Amount"] for data in results_data)
        total_fee = sum(data["Fee"] for data in results_data)
        total_sum_with_fee = sum(data["Total"] for data in results_data)


        # Показываем окно с результатами
        show_results_window(results_data, current_readings, costs, total_amount, total_fee, total_sum_with_fee, save_readings)

    except ValueError as e:
        error_callback("Ошибка", str(e))
        return

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

def save_tariffs(gas, electricity, water):
    """Сохраняет тарифы и записывает в файл."""
    config.services["gas"]["tariff"] = gas
    config.services["electricity"]["tariff"] = electricity
    config.services["water"]["tariff"] = water
    save_settings()      

def save_fees(gas, electricity, water):
    """Сохраняет комиссии и записывает в файл."""
    config.services["gas"]["fee"] = gas
    config.services["electricity"]["fee"] = electricity
    config.services["water"]["fee"] = water
    save_settings()
