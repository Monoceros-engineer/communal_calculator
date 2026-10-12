# TASK-140: Довести EN-перевод UI до полного

## Goal
При переключении языка на English весь UI отображается на английском,
layout не ломается. Русский остаётся исходным, fallback.

## Context
- Ветка: feature/service-classes
- i18n инфраструктура готова: QTranslator, install_translators(),
  вкладка "Язык", сохранение языка в БД.
- app_en.qm собран, 327/327 сообщений.
- Ручная проверка выявила: Dashboard, Statistics, Enter readings
  частично или полностью остаются на русском в EN-режиме.
- Аудит проведён: см. раздел "Аудит" ниже.

## Root cause (по итогам аудита)

1. **Критично — рассинхрон контекста tr() в services.py.**
   BaseService.tr() жёстко использует контекст "services", а .ts содержит
   строки в контекстах BaseService / MeteredService / FixedService.
   Итог: все строки из services.py не переводятся, хотя переводы в .ts есть.
   Это корень симптомов в Dashboard и Enter readings.

2. **Statistics (stats_window.py) — полностью захардкожен.**
   Ни одной обёртки tr(), в .ts контекста StatisticsWindow нет.
   Плюс: логика ветвления завязана на русские строки комбобоксов.

3. **communal_calculator.py::process_services_data — user-facing диалоги ошибок.**
   2 строки хардкод, попадают в QMessageBox через error_callback/warning_callback.

## Проблемные зоны (по ручной проверке)
- Dashboard: тариф "8,70 руб." — RU в EN-режиме.
- Statistics: весь текст RU.
- Enter readings: заголовки EN, тело и кнопки услуг RU.
- Диалоги ошибок ввода в Enter readings — RU.

## AC (Acceptance Criteria)
- Given язык = English, When открываю Dashboard, Then все подписи на английском
  (кроме названий услуг — см. ниже).
- Given язык = English, When открываю Statistics, Then все подписи на английском,
  фильтрация по году/группировке работает корректно.
- Given язык = English, When открываю Enter readings, Then все кнопки и подписи
  на английском (кроме названий услуг).
- Given язык = English, When ввожу некорректное число, Then диалог ошибки на английском.
- Given язык = English, When ничего не ввёл и жму "Рассчитать", Then диалог
  "Fill in at least one field" на английском.
- Given язык = English, When переключаю обратно на Russian, Then UI возвращается
  в RU без регресса.
- Ни один layout не сломан (кнопки не обрезаны, текст не выезжает).

### Явные исключения из AC
- **Названия услуг (services.name из БД) НЕ переводятся.** Это пользовательские
  данные. Пользователь ведёт программу на своём языке и сам называет услуги.
- **Валюта "руб."** — остаётся как есть (ADR 0001, релиз 1.5).
- **Дата/время в шапке (дни недели, месяцы)** — остаётся на русском в EN-режиме.
  Вынесено в отдельную задачу "Локаль даты/времени".

## Out of Scope
- Legacy Tkinter-код (calculate_dynamic, calculate_service) — отдельный тикет
  "Удалить legacy Tkinter-код".
- Локаль даты/времени (QLocale) — отдельная задача.
- Валюта как сущность — ADR 0001, релиз 1.5.
- Схема БД, логика расчётов.

## Аудит: файлы и правки

### P0 — services.py
**Проблема:** `BaseService.tr()` использует контекст `"services"`,
а `.ts` содержит `BaseService` / `MeteredService` / `FixedService`.

**Правка (вариант B):**
- `BaseService.tr()` → контекст `"BaseService"`.
- `MeteredService` переопределяет `tr()` → контекст `"MeteredService"`.
- `FixedService` переопределяет `tr()` → контекст `"FixedService"`.
- Методы `_build_*` живут в BaseService → используют BaseService-контекст.
- Методы `render_*`, `_calc_*` в подклассах → их контексты.
- После правки — перегенерировать .ts, сверить diff.

### P0 — stats_window.py
**Проблема:** ни одной обёртки tr(), в .ts нет контекста StatisticsWindow.
Плюс архитектурный баг: логика ветвления завязана на русские строки
комбобоксов (`if selected == "Все годы"`, `if group == "По месяцам"`).
Даже при добавлении переводов фильтрация в EN-режиме сломается.

**Правки:**
- `setWindowTitle("Статистика")` → `self.tr(...)`.
- `QLabel("Год:")` → `self.tr(...)`.
- `QLabel("Группировка:")` → `self.tr(...)`.
- `addItems(["По месяцам", "По кварталам", "По годам"])` → обернуть в tr(),
  но ОБЯЗАТЕЛЬНО переключить логику на `currentData()` со значениями
  `'month' / 'quarter' / 'year'`. Это не стилистика, а фикс бага.
- `QLabel("Динамика расходов")` → `self.tr(...)`.
- `QPushButton("Закрыть")` → `self.tr(...)`.
- `addItem("Все годы")` → обернуть + `currentData()` = `'all'`.
- `addItem("Нет данных")`, `addItem("Ошибка")` → обернуть в tr().
- `if selected == "Все годы"` → `if selected_data == 'all'`.
- `if group == "По месяцам"` → `if group_data == 'month'`.
- Matplotlib:
  - `ax1.set_title("Распределение расходов")` → `self.tr(...)`.
  - `ax1.text(..., "Нет данных")` → `self.tr(...)`.
  - `ax2.set_xlabel("Период")` → `self.tr(...)`.
  - `ax2.set_ylabel("Сумма, руб.")` → `self.tr(...)`.
  - `ax2.text(..., "Нет данных")` → `self.tr(...)`.
- Дата/время в шапке — НЕ трогаем в этой задаче (отдельный тикет).

**Проверка:** grep по всему проекту на `currentText()`, `== "Все годы"`,
`== "По месяцам"`, `== "По кварталам"`, `== "По годам"` — убедиться, что
нигде больше логика не завязана на отображаемый текст.

### P1 — communal_calculator.py
**Проблема:** `process_services_data` формирует user-facing сообщения для
QMessageBox через `error_callback` / `warning_callback`.

**Правки:**
- Добавить helper:
  ```python
  from PySide6.QtCore import QCoreApplication

  def _tr(text: str) -> str:
      return QCoreApplication.translate("communal_calculator", text)