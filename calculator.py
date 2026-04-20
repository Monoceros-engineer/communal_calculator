from decimal import Decimal, getcontext, InvalidOperation

# Настройка точности Decimal
getcontext().prec = 28

# Создадим общую функцию для расчета
def calculate_service(name, get_entry, start_value, tariff, get_checkbox_var, fee):
    if get_entry.strip():
        try:
            end = Decimal(get_entry)
            start = Decimal(start_value)
            consumption = end - start
            amount = consumption * Decimal(str(tariff))

            # Проверяем, установлен ли чекбокс
            if get_checkbox_var == 1:
                fee = amount * Decimal(str(fee))
            else:
                fee = Decimal("0")
            total = amount + fee
            return {
                "Name": name,
                "Start value": start,
                "End value": end,
                "Consumption": consumption,
                "Tariff": tariff,
                "Amount": amount,
                "Fee": fee,
                "Total": total,
            }
        except InvalidOperation:
            return None
    else:
        return None
