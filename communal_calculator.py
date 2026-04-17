from tkinter import *
import tkinter.messagebox as box
from calculator import calculate_service
from gui import show_results_window

# ФУНКЦИИ ДЛЯ ОСНОВНОГО РАСЧЕТА

def calculate(enter_gas, enter_electricity, enter_water, 
              box_gas_var, box_electricity_var, box_water_var,
              start_value_gas, start_value_electricity, start_value_water,
              tarif_gas, tarif_electricity, tarif_water,
              fee_gas, fee_electricity, fee_water):
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
            box.showwarning("Предупреждение", "Заполните хотя бы одно поле!")
            return

        # Вычисляем общую сумму с комиссией
        total_with_fee = sum(data["Fee"] for data in results_data)

        # Показываем окно с результатами
        show_results_window(results_data, current_readings, costs, total_with_fee)

    except Exception as e:
        box.showerror("Ошибка", f"Произошла ошибка: {type(e).__name__}\n{e}")
