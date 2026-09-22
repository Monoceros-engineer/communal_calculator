"""Модели услуг для калькулятора коммунальных платежей.

Хранение полей, конвертация в/из словаря и БД, а также расчёт суммы
к оплате (метод calculate()). UI-методы не реализованы.

Формат словаря соответствует config.services[key] (см. database.load_services):
    id, name, type, enabled, tariff, fee, start_value, provider_id,
    replacements, active_verification, last_completed_verification,
    next_verification_date

Важно: `key` в этом словаре НЕ хранится — в config.services ключ лежит
снаружи (это ключ словаря). На объекте он сохраняется как атрибут self.key
и передаётся отдельным аргументом при создании из словаря.
"""

from decimal import Decimal, InvalidOperation
from calculations import normalize_decimal, calculate_consumption_with_replacements


class BaseService:
    """Базовый класс услуги: общие поля и сериализация.

    Конкретный тип ('metered' | 'fixed') задаётся подклассом через SERVICE_TYPE.
    """

    SERVICE_TYPE = None

    def __init__(self, key=None, *, id=None, name="", enabled=True, tariff=0.0,
                 fee=0.0, start_value=None, provider_id=None, replacements=None,
                 active_verification=None, last_completed_verification=None,
                 next_verification_date=None):
        self.key = key
        self.id = id
        self.name = name
        self.type = self.SERVICE_TYPE
        self.enabled = bool(enabled)
        self.tariff = tariff
        self.fee = fee
        self.start_value = start_value
        self.provider_id = provider_id
        self.replacements = list(replacements) if replacements else []
        self.active_verification = active_verification
        self.last_completed_verification = last_completed_verification
        self.next_verification_date = next_verification_date

    @classmethod
    def from_dict(cls, data, key=None):
        """Создать объект из словаря формата config.services[key].

        При вызове на базовом классе автоматически выбирается нужный подкласс
        по полю 'type'. При вызове на подклассе создаётся объект этого подкласса.

        `key` берётся из аргумента, либо (если не задан) из data['key'].
        """
        if cls is BaseService:
            service_type = (data or {}).get("type")
            target = MeteredService if service_type == "metered" else FixedService
            return target.from_dict(data, key=key)

        data = data or {}
        return cls(
            key=key if key is not None else data.get("key"),
            id=data.get("id"),
            name=data.get("name", ""),
            enabled=data.get("enabled", True),
            tariff=data.get("tariff", 0.0),
            fee=data.get("fee", 0.0),
            start_value=data.get("start_value"),
            provider_id=data.get("provider_id"),
            replacements=data.get("replacements"),
            active_verification=data.get("active_verification"),
            last_completed_verification=data.get("last_completed_verification"),
            next_verification_date=data.get("next_verification_date"),
        )

    def to_dict(self):
        """Вернуть словарь в том же формате, что config.services[key].

        `key` в словарь не включается, чтобы формат совпадал с тем, что
        возвращает database.load_services() (там ключ — это ключ словаря).
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "enabled": self.enabled,
            "tariff": self.tariff,
            "fee": self.fee,
            "start_value": self.start_value,
            "provider_id": self.provider_id,
            "replacements": self.replacements,
            "active_verification": self.active_verification,
            "last_completed_verification": self.last_completed_verification,
            "next_verification_date": self.next_verification_date,
        }

    def to_db_params(self):
        """Вернуть словарь для database.save_service(key, params).

        Содержит только поля, которые сохраняются в таблицу services.
        """
        return {
            "name": self.name,
            "type": self.type,
            "enabled": self.enabled,
            "tariff": self.tariff,
            "fee": self.fee,
            "start_value": self.start_value,
            "provider_id": self.provider_id,
        }

    def __getitem__(self, item):
        """Совместимость со словарём: service['name'] → self.name."""
        return getattr(self, item)

    def __setitem__(self, item, value):
        """Совместимость со словарём: service['name'] = 'X' → self.name = 'X'."""
        setattr(self, item, value)

    def get(self, item, default=None):
        """Совместимость со словарём: service.get('fee', 0.0)."""
        return getattr(self, item, default)

    def __contains__(self, item):
        """Совместимость со словарём: 'fee' in service → True, если поле есть."""
        return hasattr(self, item)

    def calculate(self, reading_str, has_commission):
        """Рассчитать сумму к оплате. Реализуется в подклассах.

        Возвращает словарь с ключами:
            result, current_reading, cost, amount, fee, total,
            used_replacement_ids, verification_ids_used, norm_verification_ids
        или None, если услугу нужно пропустить.
        """
        raise NotImplementedError

    def __repr__(self):
        return f"{type(self).__name__}(key={self.key!r}, name={self.name!r})"


class MeteredService(BaseService):
    """Услуга, рассчитываемая по показаниям счётчика."""

    SERVICE_TYPE = "metered"

    def calculate(self, reading_str, has_commission):
        """Расчёт по показаниям с учётом замен счётчиков и поверок.

        Логика перенесена из communal_calculator.process_services_data()
        без изменений (ветка 'metered').
        """
        name = self.name
        tariff = Decimal(str(self.tariff))
        fee = Decimal(str(self.fee if self.fee is not None else 0.0))

        # --- 1. Активная поверка (счётчик на поверке) ---
        if self.active_verification:
            amount_norm = Decimal(str(self.active_verification.get('amount_norm') or 0.0))
            fee_amount = amount_norm * fee if has_commission else Decimal('0')
            total = amount_norm + fee_amount
            result = {
                "Name": name + " (норматив)",
                "Start value": None,
                "End value": None,
                "Consumption": 0,
                "Tariff": None,
                "Amount": amount_norm,
                "Fee": fee_amount,
                "Total": total
            }
            return {
                'result': result,
                'current_reading': None,
                'cost': amount_norm,
                'amount': amount_norm,
                'fee': fee_amount,
                'total': total,
                'used_replacement_ids': [],
                'verification_ids_used': [],
                'norm_verification_ids': [],
            }

        # --- 2. Обычный расчёт по показаниям ---
        value_str = (reading_str or "").strip()
        if not value_str:
            return None
        normalized = normalize_decimal(value_str)
        end = Decimal(normalized)   # может поднять InvalidOperation
        start = Decimal(self.start_value if self.start_value is not None else 0)
        replacements = self.replacements if self.replacements else []
        dec_replacements = []
        for rep in replacements:
            if not rep.get('is_paid', False):   # добавляем только неоплаченные замены
                dec_replacements.append({
                    "old_final": Decimal(rep["old_final"]),
                    "new_start": Decimal(rep["new_start"])
                })

        # Проверяем завершённую поверку (если есть и не оплачена)
        verification_ids_used = []
        norm_verification_ids = []
        norm_amount = None
        last_verif = self.last_completed_verification
        if last_verif:
            # Расход до снятия — если не оплачен
            if not last_verif.get('is_consumption_paid', False):
                dec_replacements.append({
                    "old_final": Decimal(last_verif['old_final']),
                    "new_start": Decimal(last_verif['new_start'])
                })
                verification_ids_used.append(last_verif['id'])
            # Норматив — если не оплачен
            if not last_verif.get('is_norm_paid', False):
                norm_amount = Decimal(str(last_verif.get('amount_norm') or 0))
                if norm_amount:
                    norm_verification_ids.append(last_verif['id'])   # запоминаем ID

        total_consumption = calculate_consumption_with_replacements(start, dec_replacements, end)
        amount = total_consumption * tariff
        # Добавляем норматив, если он есть
        if norm_amount:
            amount += norm_amount
        # Теперь рассчитываем комиссию, если она есть
        if has_commission:
            fee_amount = amount * fee
        else:
            fee_amount = Decimal('0')
        # Ну и теперь добавляем комиссию к общей сумме
        total = amount + fee_amount

        # Сохраняем ID использованных замен
        used_replacement_ids = [rep['id'] for rep in replacements if 'id' in rep]

        result = {
            "Name": name,
            "Start value": start,
            "End value": end,
            "Consumption": total_consumption,
            "Tariff": tariff,
            "Amount": amount,
            "Fee": fee_amount,
            "Total": total
        }
        return {
            'result': result,
            'current_reading': float(end),
            'cost': amount,
            'amount': amount,
            'fee': fee_amount,
            'total': total,
            'used_replacement_ids': used_replacement_ids,
            'verification_ids_used': verification_ids_used,
            'norm_verification_ids': norm_verification_ids,
        }


class FixedService(BaseService):
    """Услуга с фиксированной платой (не зависит от показаний)."""

    SERVICE_TYPE = "fixed"

    def calculate(self, reading_str, has_commission):
        # Импорт на уровне метода, чтобы избежать циклического импорта.
        from calculator import calculate_fixed_service

        # tariff передаём как Decimal(str(...)) — так делал старый код
        # (process_services_data), чтобы в result['Tariff'] лежал Decimal.
        result = calculate_fixed_service(
            self.name, Decimal(str(self.tariff)), has_commission, self.fee)
        amount = Decimal(str(result['Amount']))
        fee_amount = Decimal(str(result['Fee']))
        return {
            'result': result,
            'current_reading': None,
            'cost': amount,
            'amount': amount,
            'fee': fee_amount,
            'total': Decimal(str(result['Total'])),
            'used_replacement_ids': [],
            'verification_ids_used': [],
            'norm_verification_ids': [],
        }
