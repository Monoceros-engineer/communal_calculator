"""Вспомогательные функции для расчётов.

Вынесены из communal_calculator.py, чтобы классы услуг (services.py)
могли считать себя сами без импорта UI-логики.
"""

from decimal import Decimal


def normalize_decimal(s):
    """Преобразует строку с запятой или точкой в формат с точкой."""
    s = s.strip().replace(',', '.')
    # удаляем возможные пробелы между цифрами
    s = s.replace(' ', '')
    return s


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
