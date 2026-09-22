"""Модели услуг для калькулятора коммунальных платежей.

Phase 1: только хранение полей и конвертация в/из словаря и БД.
calculate() и UI-методы добавляются в следующих фазах.

Формат словаря соответствует config.services[key] (см. database.load_services):
    id, name, type, enabled, tariff, fee, start_value, provider_id,
    replacements, active_verification, last_completed_verification,
    next_verification_date

Важно: `key` в этом словаре НЕ хранится — в config.services ключ лежит
снаружи (это ключ словаря). На объекте он сохраняется как атрибут self.key
и передаётся отдельным аргументом при создании из словаря.
"""


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

    def __repr__(self):
        return f"{type(self).__name__}(key={self.key!r}, name={self.name!r})"


class MeteredService(BaseService):
    """Услуга, рассчитываемая по показаниям счётчика."""

    SERVICE_TYPE = "metered"


class FixedService(BaseService):
    """Услуга с фиксированной платой (не зависит от показаний)."""

    SERVICE_TYPE = "fixed"
