import sqlite3
import json
from paths import get_db_path   # импортируем из paths

# Путь к базе данных – используем функцию из paths
DB_PATH = get_db_path()

def init_db():
    """Создаёт таблицы, если они не существуют."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Таблица услуг (актуальные параметры)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('metered', 'fixed')),
                enabled INTEGER NOT NULL DEFAULT 1,
                tariff REAL NOT NULL,
                fee REAL NOT NULL DEFAULT 0,
                start_value REAL
            )
        """)
        
        # Таблица замен счётчиков
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meter_replacements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                old_final REAL NOT NULL,
                new_start REAL NOT NULL,
                date TEXT,
                is_paid INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
            )
        """)
        
        # Таблица счетов (основная запись о расчёте)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_amount REAL NOT NULL,
                total_fee REAL NOT NULL,
                total_with_fee REAL NOT NULL
            )
        """)
        
        # Таблица деталей счёта (по каждой услуге)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bill_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL,
                service_id INTEGER,
                service_name TEXT NOT NULL,
                start_reading REAL,
                end_reading REAL,
                consumption REAL,
                tariff REAL NOT NULL,
                amount REAL NOT NULL,
                fee REAL NOT NULL,
                total REAL NOT NULL,
                FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL
            )
        """)
        
        # Таблица связей замен с конкретным счётом
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bill_replacements (
                bill_id INTEGER NOT NULL,
                replacement_id INTEGER NOT NULL,
                FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
                FOREIGN KEY (replacement_id) REFERENCES meter_replacements(id) ON DELETE CASCADE,
                PRIMARY KEY (bill_id, replacement_id)
            )
        """)
        
        conn.commit()

def save_bill(bill_data):
    """
    Сохраняет результаты расчёта в БД.
    bill_data: {
        'date': str,
        'total_amount': float,
        'total_fee': float,
        'total_with_fee': float,
        'details': [
            {
                'service_key': str,
                'service_name': str,
                'start_reading': float or None,
                'end_reading': float or None,
                'consumption': float or None,
                'tariff': float,
                'amount': float,
                'fee': float,
                'total': float
            },
            ...
        ],
        'used_replacements': [replacement_id, ...]  # опционально, id замен, которые были учтены в расчёте
    }
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Вставляем счёт
        cursor.execute("""
            INSERT INTO bills (date, total_amount, total_fee, total_with_fee)
            VALUES (?, ?, ?, ?)
        """, (bill_data['date'], bill_data['total_amount'], bill_data['total_fee'], bill_data['total_with_fee']))
        bill_id = cursor.lastrowid
        
        # Вставляем детали
        for detail in bill_data['details']:
            # Находим service_id по ключу (если услуга ещё существует)
            cursor.execute("SELECT id FROM services WHERE key = ?", (detail['service_key'],))
            row = cursor.fetchone()
            service_id = row[0] if row else None
            
            cursor.execute("""
                INSERT INTO bill_details (
                    bill_id, service_id, service_name, start_reading, end_reading,
                    consumption, tariff, amount, fee, total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bill_id, service_id, detail['service_name'],
                detail['start_reading'], detail['end_reading'], detail['consumption'],
                detail['tariff'], detail['amount'], detail['fee'], detail['total']
            ))
        
        # Связываем замены с этим счётом, если есть
        used_rep_ids = bill_data.get('used_replacements', [])
        for rep_id in used_rep_ids:
            cursor.execute("INSERT OR IGNORE INTO bill_replacements (bill_id, replacement_id) VALUES (?, ?)", (bill_id, rep_id))
            # Помечаем замену как оплаченную
            cursor.execute("UPDATE meter_replacements SET is_paid = 1 WHERE id = ?", (rep_id,))
        
        conn.commit()
        return bill_id

def migrate_from_json():
    """Переносит данные из calculator_config.json и readings_history.json в SQLite.
       Вызывается при первом запуске после перехода на SQLite."""
    import json
    from pathlib import Path
    import config
    from decimal import Decimal
    
    # Перенос услуг из config.services
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for key, service in config.services.items():
            cursor.execute("""
                INSERT OR REPLACE INTO services (key, name, type, enabled, tariff, fee, start_value)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                key, service['name'], service['type'],
                1 if service.get('enabled', True) else 0,
                service['tariff'], service.get('fee', 0.0),
                service.get('start_value')
            ))
        conn.commit()
    
    # Перенос истории из readings_history.json
    history_file = Path(__file__).parent / "readings_history.json"
    if not history_file.exists():
        return
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    for record in history:
        # Преобразуем старый формат в новый
        # record имеет вид: {"date": "...", "readings": {"gas": 123, ...}, "costs": {...}, "total": 123.45}
        # Нужно создать bill_data
        bill_data = {
            'date': record['date'],
            'total_amount': sum(record['costs'].values()),
            'total_fee': 0,  # в старом формате отдельно комиссия не хранилась? У вас total уже с комиссией? Разберём.
            'total_with_fee': record['total'],
            'details': []
        }
    pass

# ===== УСЛУГИ =====

def save_service(key, service):
    """Сохраняет услугу в таблицу services (вставка или обновление)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO services (key, name, type, enabled, tariff, fee, start_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            key,
            service['name'],
            service['type'],
            1 if service.get('enabled', True) else 0,
            service['tariff'],
            service.get('fee', 0.0),
            service.get('start_value')
        ))
        conn.commit()

def delete_service(key):
    """Удаляет услугу из таблицы services."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM services WHERE key = ?", (key,))
        conn.commit()

def load_services():
    """Загружает все услуги с их заменами из SQLite."""
    services = {}
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Загружаем услуги
        cursor.execute("SELECT id, key, name, type, enabled, tariff, fee, start_value FROM services")
        rows = cursor.fetchall()
        for row in rows:
            id_, key, name, type_, enabled, tariff, fee, start_value = row
            services[key] = {
                'id': id_,
                'name': name,
                'type': type_,
                'enabled': bool(enabled),
                'tariff': tariff,
                'fee': fee,
                'start_value': start_value,
                'replacements': []   # заполним позже
            }

        # Загружаем замены для всех услуг
        cursor.execute("SELECT id, service_id, old_final, new_start, date, is_paid FROM meter_replacements")
        replacements_rows = cursor.fetchall()
        # Создаём словарь service_id -> key, чтобы связать замены с услугами
        cursor.execute("SELECT id, key FROM services")
        id_to_key = {row[0]: row[1] for row in cursor.fetchall()}

        for rep_id, service_id, old_final, new_start, date, is_paid in replacements_rows:
            key = id_to_key.get(service_id)
            if key and key in services:
                services[key]['replacements'].append({
                    'id': rep_id,                        # ← добавляем ID
                    'old_final': old_final,
                    'new_start': new_start,
                    'date': date,
                    'is_paid': bool(is_paid)
                })

    return services

# ===== ЗАМЕНЫ =====

def add_replacement(service_id, old_final, new_start, date=None):
    """Добавляет замену счётчика."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO meter_replacements (service_id, old_final, new_start, date, is_paid)
            VALUES (?, ?, ?, ?, 0)
        """, (service_id, old_final, new_start, date))
        conn.commit()
        return cursor.lastrowid

def get_service_id_by_key(key):
    """Возвращает id услуги по её ключу."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM services WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

def mark_replacements_paid(service_id, bill_id):
    """Помечает все неоплаченные замены для услуги как оплаченные и связывает с bill."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Находим все неоплаченные замены
        cursor.execute("SELECT id FROM meter_replacements WHERE service_id = ? AND is_paid = 0", (service_id,))
        rep_ids = [row[0] for row in cursor.fetchall()]
        if rep_ids:
            # Помечаем как оплаченные
            cursor.execute("UPDATE meter_replacements SET is_paid = 1 WHERE id IN ({})".format(','.join('?' * len(rep_ids))), rep_ids)
            # Связываем с bill
            for rep_id in rep_ids:
                cursor.execute("INSERT OR IGNORE INTO bill_replacements (bill_id, replacement_id) VALUES (?, ?)", (bill_id, rep_id))
        conn.commit()

def get_replacements(service_id):
    """Возвращает список замен для услуги (без учёта оплаты)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, old_final, new_start, date, is_paid FROM meter_replacements WHERE service_id = ?", (service_id,))
        rows = cursor.fetchall()
        return [{'id': r[0], 'old_final': r[1], 'new_start': r[2], 'date': r[3], 'is_paid': bool(r[4])} for r in rows]

def clear_paid_replacements(service_id):
    """Удаляет оплаченные замены для услуги (после сохранения истории)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM meter_replacements WHERE service_id = ? AND is_paid = 1", (service_id,))
        conn.commit()

def mark_replacements_paid(rep_ids, bill_id):
    """Помечает замены как оплаченные и связывает их с указанным счётом."""
    if not rep_ids:
        return
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Помечаем как оплаченные
        placeholders = ','.join('?' * len(rep_ids))
        cursor.execute(f"UPDATE meter_replacements SET is_paid = 1 WHERE id IN ({placeholders})", rep_ids)
        # Связываем с bill
        for rep_id in rep_ids:
            cursor.execute("INSERT OR IGNORE INTO bill_replacements (bill_id, replacement_id) VALUES (?, ?)", (bill_id, rep_id))
        conn.commit()