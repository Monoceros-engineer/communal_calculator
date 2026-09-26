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


# Стиль серых кнопок («Счётчик», «Реквизиты») — та же строка, что и раньше в
# InputPanel. Храним как обычную строку, чтобы не импортировать PySide6 на уровне модуля.
_GREY_BUTTON_STYLE = """
    QPushButton {
        background-color: #e0e0e0;
        border: 1px solid #aaa;
        border-radius: 4px;
        padding: 4px;
    }
    QPushButton:hover {
        background-color: #c0c0c0;
    }
    QPushButton:pressed {
        background-color: #a0a0a0;
    }
"""


class BaseService:
    """Базовый класс услуги: общие поля и сериализация.

    Конкретный тип ('metered' | 'fixed') задаётся подклассом через SERVICE_TYPE.
    """

    SERVICE_TYPE = None

    def __init__(self, key=None, *, id=None, name="", enabled=True, tariff=0.0,
                 fee=None, start_value=None, provider_id=None, replacements=None,
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
            fee=data.get("fee"),
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

    def render_input_row(self, parent_widget):
        """Вернуть виджеты строки ввода для InputPanel. Реализуется в подклассах.

        Возвращает словарь с ключами:
            name_label, value_widget, commission_cb, action_widget,
            provider_btn, entry, checkbox
        """
        raise NotImplementedError

    def render_dashboard_card(self):
        """Вернуть виджеты карточки для DashboardWidget. Реализуется в подклассах.

        Возвращает словарь с ключами:
            name_label, reading_label, tariff_label
        """
        raise NotImplementedError

    # --- Общие части строки ввода (общие для metered и fixed) ---

    def _build_name_label(self):
        from PySide6.QtWidgets import QLabel

        tariff = self.tariff if self.tariff is not None else 0.0
        name_label = QLabel(f"<b>{self.name.upper()}</b> (тариф {tariff: .2f})")
        name_label.setWordWrap(True)  # Перенос длинных слов
        return name_label

    def _build_commission_cb(self, parent_widget):
        from PySide6.QtWidgets import (
            QCheckBox, QDialog, QVBoxLayout, QLabel, QLineEdit,
            QDialogButtonBox, QMessageBox)
        from communal_calculator import save_services

        cb = QCheckBox()
        if self.fee is not None:
            cb.setText(f"{int(self.fee * 100)}%")
        else:
            cb.setText("Мой банк берёт комиссию")

        def on_checkbox_toggled(checked):
            if not checked:
                return
            if self.fee is not None:
                return
            # Комиссия не задана – открываем диалог
            dialog = QDialog(parent_widget)
            dialog.setStyleSheet("background-color: white;")  # белый фон окна
            dialog.setWindowTitle("Настройка комиссии банка")
            dialog.setMinimumWidth(300)
            layout = QVBoxLayout(dialog)
            layout.addWidget(QLabel("Укажите размер комиссии (в процентах), которую берёт банк за оплату данной услуги:"))
            percent_edit = QLineEdit()
            layout.addWidget(percent_edit)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            if dialog.exec():
                try:
                    percent = float(percent_edit.text())
                    if percent < 0 or percent > 100:
                        raise ValueError
                    self.fee = percent / 100.0
                    save_services()
                    cb.setText(f"{int(percent)}%")
                except:
                    QMessageBox.warning(parent_widget, "Ошибка", "Введите число от 0 до 100")
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)
            else:
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)

        cb.toggled.connect(on_checkbox_toggled)
        return cb

    def _build_provider_btn(self, parent_widget):
        from PySide6.QtWidgets import QPushButton

        provider_btn = QPushButton("🏦 Реквизиты")
        provider_btn.setFixedWidth(130)
        provider_btn.setStyleSheet(_GREY_BUTTON_STYLE)
        provider_btn.clicked.connect(
            lambda checked, k=self.key: parent_widget.show_provider_info(k))
        return provider_btn

    # --- Общие части карточки дашборда (общие для metered и fixed) ---

    def _card_name_label(self):
        from PySide6.QtWidgets import QLabel

        return QLabel(self.name)

    def _card_tariff_label(self):
        from PySide6.QtWidgets import QLabel

        tariff = self.tariff if self.tariff is not None else 0.0
        return QLabel(f"{tariff:.2f} руб.")

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

    def render_input_row(self, parent_widget):
        """Строка ввода для услуги по счётчику: QLineEdit + кнопка «Счётчик»."""
        from PySide6.QtWidgets import QLineEdit, QPushButton

        name_label = self._build_name_label()
        entry = QLineEdit()
        entry.setFixedWidth(200)  # фиксированная ширина
        commission_cb = self._build_commission_cb(parent_widget)

        counter_btn = QPushButton("🔧 Счётчик")
        counter_btn.setFixedWidth(130)
        counter_btn.setStyleSheet(_GREY_BUTTON_STYLE)
        counter_btn.clicked.connect(
            lambda checked, k=self.key: parent_widget.show_counter_actions(k))

        provider_btn = self._build_provider_btn(parent_widget)

        return {
            "name_label": name_label,
            "value_widget": entry,
            "commission_cb": commission_cb,
            "action_widget": counter_btn,
            "provider_btn": provider_btn,
            "entry": entry,
            "checkbox": commission_cb,
        }

    def render_dashboard_card(self):
        """Карточка дашборда для услуги по счётчику."""
        from PySide6.QtWidgets import QLabel

        if self.active_verification is not None:
            reading_text = "🔴 На поверке"
        else:
            reading_text = f"{self.start_value or 0:.2f}"

        return {
            "name_label": self._card_name_label(),
            "reading_label": QLabel(reading_text),
            "tariff_label": self._card_tariff_label(),
        }


class FixedService(BaseService):
    """Услуга с фиксированной платой (не зависит от показаний)."""

    SERVICE_TYPE = "fixed"

    def calculate(self, reading_str, has_commission):
        # Импорт на уровне метода, чтобы избежать циклического импорта.
        from calculator import calculate_fixed_service

        # tariff передаём как Decimal(str(...)) — так делал старый код
        # (process_services_data), чтобы в result['Tariff'] лежал Decimal.
        # fee=None трактуем как 0, иначе calculate_fixed_service упадёт на
        # Decimal(str(None)).
        fee = self.fee if self.fee is not None else 0.0
        result = calculate_fixed_service(
            self.name, Decimal(str(self.tariff)), has_commission, fee)
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

    def render_input_row(self, parent_widget):
        """Строка ввода для фиксированной услуги: метка вместо поля и пустая метка вместо кнопки."""
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt

        name_label = self._build_name_label()
        label = QLabel("Показания счетчика не требуются")
        label.setFixedWidth(200)
        label.setAlignment(Qt.AlignCenter)  # Выравниваем по центру
        commission_cb = self._build_commission_cb(parent_widget)
        provider_btn = self._build_provider_btn(parent_widget)

        return {
            "name_label": name_label,
            "value_widget": label,
            "commission_cb": commission_cb,
            "action_widget": QLabel(""),
            "provider_btn": provider_btn,
            "entry": None,
            "checkbox": commission_cb,
        }

    def render_dashboard_card(self):
        """Карточка дашборда для фиксированной услуги (показаний нет)."""
        from PySide6.QtWidgets import QLabel

        return {
            "name_label": self._card_name_label(),
            "reading_label": QLabel("—"),
            "tariff_label": self._card_tariff_label(),
        }
