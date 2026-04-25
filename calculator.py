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
            raise ValueError(f"В поле '{name}' введите корректное число!")
    else:
        return None
    
def calculate_fixed_service(name, tariff, has_commission, fee):
    """Расчёт фиксированной услуги.
       Возвращает словарь с результатами."""
    from decimal import Decimal
    amount = Decimal(str(tariff))
    if has_commission:
        fee_amount = amount * Decimal(str(fee))
    else:
        fee_amount = Decimal('0')
    total = amount + fee_amount
    return {
        "Name": name,
        "Start value": "-",
        "End value": "-",
        "Consumption": "-",
        "Tariff": tariff,
        "Amount": amount,
        "Fee": fee_amount,
        "Total": total
    }
