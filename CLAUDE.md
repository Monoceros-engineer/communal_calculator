# Project: Калькулятор коммуналки

## Purpose
Десктопное приложение для учёта коммунальных платежей (газ, свет, вода, интернет, экосити).
Пользователь вводит показания, приложение считает суммы, хранит историю,
ведёт учёт замен/поверок счётчиков, работает с реквизитами, строит графики.

## Stack
- Python 3.12
- PySide6 (UI)
- SQLite (БД `communal.db` в `%APPDATA%\CommunalCalculator\`)
- Matplotlib + pandas (графики)
- Nuitka (.exe) + Inno Setup (установщик)
- Git, ветка разработки: `feature/service-classes`, remote: GitHub

## Modules
- `main_pyside6.py` — главный файл, все окна и диалоги.
- `services.py` — BaseService, MeteredService, FixedService.
- `database.py` — SQLite, CRUD, миграции.
- `communal_calculator.py` — оркестратор, process_services_data.
- `calculations.py` — normalize_decimal, calculate_consumption_with_replacements.
- `config.py` — глобальные настройки (services, language).
- `file_manager.py` — загрузка/сохранение настроек, миграция.
- `paths.py` — путь к БД.
- `translations/` — app_ru.ts, app_en.ts, app_ru.qm, app_en.qm.

## Commands
- run: `python main_pyside6.py`
- lupdate: `pyside6-lupdate . -ts translations/app_ru.ts translations/app_en.ts`
- lrelease: `pyside6-lrelease translations/app_ru.ts translations/app_en.ts`
- build exe: `python -m nuitka --standalone --onefile main_pyside6.py`
- installer: Inno Setup, `installer.iss`

## Domain rules
- Комиссия (fee): NULL = не задана, число = доля (0.01 = 1%).
- meter_state: active, on_verification, on_repair, removed, replaced.
- Для fixed-услуг meter_state = NULL.
- event_type: replacement, verification_start, verification_end, removal, installation.
- Бэкап `communal.db` ОБЯЗАТЕЛЕН перед любыми миграциями.

## i18n rules (критично)
- Каждая UI-строка ОБЯЗАНА быть в `self.tr("...")`.
- f-строки: `self.tr("...{x}...").format(x=...)`.
- Строки уровня модуля через `tr()` QObject не переводятся — только через экземпляр QObject.
- После добавления строк: прогнать lupdate, заполнить .ts, прогнать lrelease.
- Русский — исходный язык, fallback. Английский — заполнен.
- Регресс: любая строка без `tr()` — баг.

## AI Rules
- Сначала читай `CLAUDE.md` и `docs/tasks/<TASK_ID>.md`.
- Сначала план, потом код. Если неясно — спроси.
- Минимальный диф. Не рефакторить то, что не просили.
- Работать только в своей ветке. В `main` не пушить.
- Перед коммитом: приложение запускается, целевой сценарий проверен.
- Для i18n-задач: приложить вывод lupdate и diff .ts файлов.
- Никаких секретов, .env, ключей в коммитах.
- Не менять схему БД без ADR.

## Definition of Done (для задачи)
- [ ] Acceptance criteria выполнены.
- [ ] Приложение запускается.
- [ ] Целевой сценарий проверен вручную (RU и EN, если задача про i18n).
- [ ] Нет регресса в существующих сценариях.
- [ ] Документация/переводы обновлены.
- [ ] Коммит с осмысленным сообщением.

## Review checklist
- Все строки в `tr()`?
- Ломает ли изменение поведение на RU?
- Не затронуты ли миграции БД без бэкапа?
- Нет ли захардкоженных строк/валюты/путей?