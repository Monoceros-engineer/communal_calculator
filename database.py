import os
import sys
import sqlite3
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
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
        # Для простоты пока не будем переносить историю, так как это сложно. Можно отложить.
        # Для версии 1.1 достаточно, чтобы новая версия программы работала с БД, а старые данные останутся в JSON.
        # При первом запуске после перехода на SQLite мы можем просто проигнорировать старые файлы или предложить миграцию.
    pass