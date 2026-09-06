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
                start_value REAL,
                provider_id INTEGER,
                FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE SET NULL
            )
        """)
        
        # Таблица замен/поверок счётчиков (единая)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meter_replacements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                old_final REAL NOT NULL,
                new_start REAL,
                date TEXT,
                is_paid INTEGER NOT NULL DEFAULT 0,
                date_start TEXT,
                date_end TEXT,
                amount_norm REAL,
                next_verification_date TEXT,
                is_active INTEGER DEFAULT 0,
                type TEXT DEFAULT 'replacement',
                is_consumption_paid INTEGER DEFAULT 0,
                is_norm_paid INTEGER DEFAULT 0,
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

        # Таблица организаций (реквизиты)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                inn TEXT,
                kpp TEXT,
                account TEXT,
                bank TEXT,
                bik TEXT,
                corr_account TEXT,
                personal_account TEXT,
                payment_purpose TEXT,
                payment_identifier TEXT,
                extra_info TEXT,
                address TEXT
            )
        """)
        # Добавляем новые колонки, если их ещё нет (для существующих БД)
        cursor.execute("PRAGMA table_info(meter_replacements)")
        existing_cols = [col[1] for col in cursor.fetchall()]
        if 'date_start' not in existing_cols:
            cursor.execute("ALTER TABLE meter_replacements ADD COLUMN date_start TEXT")
        if 'date_end' not in existing_cols:
            cursor.execute("ALTER TABLE meter_replacements ADD COLUMN date_end TEXT")
        if 'amount_norm' not in existing_cols:
            cursor.execute("ALTER TABLE meter_replacements ADD COLUMN amount_norm REAL")
        if 'next_verification_date' not in existing_cols:
            cursor.execute("ALTER TABLE meter_replacements ADD COLUMN next_verification_date TEXT")
        if 'is_active' not in existing_cols:
            cursor.execute("ALTER TABLE meter_replacements ADD COLUMN is_active INTEGER DEFAULT 0")
        if 'type' not in existing_cols:
            cursor.execute("ALTER TABLE meter_replacements ADD COLUMN type TEXT DEFAULT 'replacement'")

        # Для старых записей (замен) устанавливаем корректные значения
        cursor.execute("UPDATE meter_replacements SET type = 'replacement', is_active = 0 WHERE type IS NULL AND is_active IS NULL")
        conn.commit()

# ===== ФУНКЦИИ ДЛЯ СОХРАНЕНИЯ СЧЕТОВ =====
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

            # Округляем до 2 знаков
            amount = round(detail['amount'], 2)
            fee = round(detail['fee'], 2)
            total = round(detail['total'], 2)
            
            cursor.execute("""
                INSERT INTO bill_details (
                    bill_id, service_id, service_name, start_reading, end_reading,
                    consumption, tariff, amount, fee, total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bill_id, service_id, detail['service_name'],
                detail['start_reading'], detail['end_reading'], detail['consumption'],
                detail['tariff'], amount, fee, total
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

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С УСЛУГАМИ =====

def save_service(key, service):
    """Сохраняет услугу в таблицу services (обновляет или вставляет)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Проверяем, существует ли уже услуга с таким ключом
        cursor.execute("SELECT id FROM services WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            # Обновляем существующую запись, сохраняя ID
            service_id = row[0]
            cursor.execute("""
                UPDATE services
                SET name = ?, type = ?, enabled = ?, tariff = ?, fee = ?, start_value = ?, provider_id = ?
                WHERE id = ?
            """, (
                service['name'],
                service['type'],
                1 if service.get('enabled', True) else 0,
                service['tariff'],
                service.get('fee', 0.0),
                service.get('start_value'),
                service.get('provider_id'),
                service_id
            ))
        else:
            # Вставляем новую запись
            cursor.execute("""
                INSERT INTO services (key, name, type, enabled, tariff, fee, start_value, provider_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key,
                service['name'],
                service['type'],
                1 if service.get('enabled', True) else 0,
                service['tariff'],
                service.get('fee', 0.0),
                service.get('start_value'),
                service.get('provider_id')
            ))
        conn.commit()

def delete_service(key):
    """Удаляет услугу из таблицы services."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM services WHERE key = ?", (key,))
        conn.commit()

def load_services():
    """Загружает все услуги с их заменами и завершёнными поверками из SQLite."""
    init_db()
    services = {}
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # --- Загружаем услуги ---
        cursor.execute("SELECT id, key, name, type, enabled, tariff, fee, start_value, provider_id FROM services")
        rows = cursor.fetchall()
        for row in rows:
            id_, key, name, type_, enabled, tariff, fee, start_value, provider_id = row
            services[key] = {
                'id': id_,
                'name': name,
                'type': type_,
                'enabled': bool(enabled),
                'tariff': tariff,
                'fee': fee,
                'start_value': start_value,
                'provider_id': provider_id,
                'replacements': [],
                'last_completed_verification': None   # ← добавляем поле
            }

        # --- Загружаем замены ---
        cursor.execute("SELECT id, service_id, old_final, new_start, date, is_paid FROM meter_replacements")
        replacements_rows = cursor.fetchall()
        cursor.execute("SELECT id, key FROM services")
        id_to_key = {row[0]: row[1] for row in cursor.fetchall()}

        for rep_id, service_id, old_final, new_start, date, is_paid in replacements_rows:
            key = id_to_key.get(service_id)
            if key and key in services:
                services[key]['replacements'].append({
                    'id': rep_id,
                    'old_final': old_final,
                    'new_start': new_start,
                    'date': date,
                    'is_paid': bool(is_paid)
                })

        # --- Загружаем завершённые поверки (is_active = 0) ---
        cursor.execute("""
            SELECT service_id, id, old_final, new_start, date_start, date_end,
                amount_norm, next_verification_date,
                is_consumption_paid, is_norm_paid
            FROM meter_replacements
            WHERE type = 'verification' AND is_active = 0
        """)
        verif_rows = cursor.fetchall()
        for row in verif_rows:
            service_id, verif_id, old_final, new_start, date_start, date_end, amount_norm, next_verif_date, is_consumption_paid, is_norm_paid = row
            key = id_to_key.get(service_id)
            if key and key in services:
                services[key]['last_completed_verification'] = {
                    'id': verif_id,
                    'old_final': old_final,
                    'new_start': new_start,
                    'date_start': date_start,
                    'date_end': date_end,
                    'amount_norm': amount_norm,
                    'next_verification_date': next_verif_date,
                    'is_consumption_paid': bool(is_consumption_paid),
                    'is_norm_paid': bool(is_norm_paid)
                }

        # --- Загружаем активные поверки (is_active = 1) ---
        cursor.execute("""
            SELECT service_id, id, old_final, new_start, date_start, date_end,
                amount_norm, next_verification_date, is_paid
            FROM meter_replacements
            WHERE type = 'verification' AND is_active = 1
        """)
        active_rows = cursor.fetchall()
        for row in active_rows:
            service_id, verif_id, old_final, new_start, date_start, date_end, amount_norm, next_verif_date, is_paid = row
            key = id_to_key.get(service_id)
            if key and key in services:
                services[key]['active_verification'] = {
                    'id': verif_id,
                    'old_final': old_final,
                    'new_start': new_start,
                    'date_start': date_start,
                    'date_end': date_end,
                    'amount_norm': amount_norm,
                    'next_verification_date': next_verif_date,
                    'is_paid': bool(is_paid)
                }

        # --- Загружаем дату следующей поверки для каждой услуги ---
        for key in services:
            active = services[key].get('active_verification')
            if active and active.get('next_verification_date'):
                services[key]['next_verification_date'] = active['next_verification_date']
            else:
                last = services[key].get('last_completed_verification')
                if last and last.get('next_verification_date'):
                    services[key]['next_verification_date'] = last['next_verification_date']
                else:
                    services[key]['next_verification_date'] = None

    return services

# ===== ЗАМЕНЫ =====

def add_replacement(service_id, old_final, new_start, date=None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO meter_replacements (service_id, old_final, new_start, date, is_paid, type, is_active)
            VALUES (?, ?, ?, ?, 0, 'replacement', 0)
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

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ПРОВАЙДЕРАМИ =====
def save_provider(data):
    """Сохраняет организацию (вставка или обновление)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if 'id' in data and data['id']:
            cursor.execute("""
                UPDATE providers SET name=?, inn=?, kpp=?, account=?, bank=?, bik=?, corr_account=?, personal_account=?, payment_purpose=?, payment_identifier=?, address=?, extra_info=?
                WHERE id=?
            """, (data['name'], data.get('inn'), data.get('kpp'), data.get('account'), data.get('bank'),
                data.get('bik'), data.get('corr_account'), data.get('personal_account'),
                data.get('payment_purpose'), data.get('payment_identifier'), data.get('address'), data.get('extra_info'), data['id']))
        else:
            cursor.execute("""
                INSERT INTO providers (name, inn, kpp, account, bank, bik, corr_account, personal_account, payment_purpose, payment_identifier, address, extra_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data['name'], data.get('inn'), data.get('kpp'), data.get('account'), data.get('bank'),
                data.get('bik'), data.get('corr_account'), data.get('personal_account'),
                data.get('payment_purpose'), data.get('payment_identifier'), data.get('address'), data.get('extra_info')))
        conn.commit()
        return cursor.lastrowid if not data.get('id') else data['id']

def get_provider(provider_id):
    """Возвращает данные организации по id."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
    SELECT id, name, inn, kpp, account, bank, bik, corr_account, personal_account, payment_purpose, payment_identifier, address, extra_info
    FROM providers WHERE id=?
    """, (provider_id,))
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'inn': row[2],
                'kpp': row[3],
                'account': row[4],
                'bank': row[5],
                'bik': row[6],
                'corr_account': row[7],
                'personal_account': row[8],
                'payment_purpose': row[9],
                'payment_identifier': row[10],
                'address': row[11],
                'extra_info': row[12]
            }
        return None

def get_all_providers():
    """Возвращает список всех организаций."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM providers ORDER BY name")
        return [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]

def delete_provider(provider_id):
    """Удаляет организацию."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM providers WHERE id=?", (provider_id,))
        conn.commit()

def set_service_provider(service_key, provider_id):
    """Привязывает организацию к услуге."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE services SET provider_id=? WHERE key=?", (provider_id, service_key))
        conn.commit()

# ===== ПОВЕРКИ (новая логика на основе meter_replacements) =====

def add_verification(service_id, data):
    """
    Создаёт запись о поверке в таблице meter_replacements.
    data: dict с полями old_final, new_start, date_start, date_end,
          amount_norm, next_verification_date
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO meter_replacements (
                service_id, old_final, new_start, date_start, date_end,
                amount_norm, next_verification_date, is_active, type,
                is_consumption_paid, is_norm_paid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            service_id,
            data.get('old_final'),
            data.get('new_start'),
            data.get('date_start'),
            data.get('date_end'),
            data.get('amount_norm'),
            data.get('next_verification_date'),
            1 if not data.get('date_end') else 0,
            'verification',
            data.get('is_consumption_paid', 0),
            data.get('is_norm_paid', 0)
        ))
        conn.commit()
        return cursor.lastrowid

def update_verification(verification_id, data):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE meter_replacements
            SET old_final = ?, new_start = ?, date_start = ?, date_end = ?,
                amount_norm = ?, next_verification_date = ?, is_active = ?,
                is_consumption_paid = ?, is_norm_paid = ?
            WHERE id = ?
        """, (
            data.get('old_final'),
            data.get('new_start'),
            data.get('date_start'),
            data.get('date_end'),
            data.get('amount_norm'),
            data.get('next_verification_date'),
            1 if not data.get('date_end') else 0,
            data.get('is_consumption_paid', 0),
            data.get('is_norm_paid', 0),
            verification_id
        ))
        conn.commit()

def get_active_verification(service_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, old_final, new_start, date_start, date_end, amount_norm, next_verification_date
            FROM meter_replacements
            WHERE service_id = ? AND type = 'verification' AND is_active = 1
            ORDER BY date_start DESC LIMIT 1
        """, (service_id,))
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'old_final': row[1],
                'new_start': row[2],
                'date_start': row[3],
                'date_end': row[4],
                'amount_norm': row[5],
                'next_verification_date': row[6]
            }
        return None

def get_last_completed_verification(service_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, old_final, new_start, date_start, date_end, amount_norm, next_verification_date
            FROM meter_replacements
            WHERE service_id = ? AND type = 'verification' AND is_active = 0
            ORDER BY date_start DESC LIMIT 1
        """, (service_id,))
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'old_final': row[1],
                'new_start': row[2],
                'date_start': row[3],
                'date_end': row[4],
                'amount_norm': row[5],
                'next_verification_date': row[6]
            }
        return None

def get_next_verification_date(service_id):
    # Сначала ищем активную поверку с указанной датой
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT next_verification_date
            FROM meter_replacements
            WHERE service_id = ? AND type = 'verification' AND is_active = 1
              AND next_verification_date IS NOT NULL
            ORDER BY id DESC LIMIT 1
        """, (service_id,))
        row = cursor.fetchone()
        if row:
            return row[0]
        # Иначе последнюю завершённую с датой
        cursor.execute("""
            SELECT next_verification_date
            FROM meter_replacements
            WHERE service_id = ? AND type = 'verification' AND is_active = 0
              AND next_verification_date IS NOT NULL
            ORDER BY date_start DESC LIMIT 1
        """, (service_id,))
        row = cursor.fetchone()
        return row[0] if row else None

def get_verification_by_id(verification_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, service_id, old_final, new_start, date_start, date_end,
                   amount_norm, next_verification_date, is_active,
                   is_consumption_paid, is_norm_paid
            FROM meter_replacements
            WHERE id = ? AND type = 'verification'
        """, (verification_id,))
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'service_id': row[1],
                'old_final': row[2],
                'new_start': row[3],
                'date_start': row[4],
                'date_end': row[5],
                'amount_norm': row[6],
                'next_verification_date': row[7],
                'is_active': bool(row[8]),
                'is_consumption_paid': bool(row[9]),
                'is_norm_paid': bool(row[10])
            }
        return None

def delete_verification(verification_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM meter_replacements WHERE id = ? AND type = 'verification'", (verification_id,))
        conn.commit()

def create_payment_record(service_key, amount, consumption,
                          start_reading, end_reading, tariff,
                          fee, date, replacement_ids=None):
    """
    Сохраняет один платёж (расход) в БД и при необходимости помечает замены/поверки как оплаченные.

    Аргументы:
        service_key (str): ключ услуги (например, 'gas').
        amount (float): сумма к оплате (без комиссии).
        consumption (float or None): расход (в куб.м, кВт·ч и т.д.) – может быть None для нормативной суммы.
        start_reading (float or None): начальное показание (может быть None).
        end_reading (float or None): конечное показание (может быть None).
        tariff (float or None): тариф (может быть None для нормативной суммы).
        fee (float): комиссия (для простоты пока оставляем 0, т.к. при оплате сразу комиссия не применяется).
        date (str): дата в формате "ГГГГ-ММ-ДД ЧЧ:ММ:СС".
        replacement_ids (list or None): список ID записей из meter_replacements, которые нужно пометить оплаченными.

    Возвращает:
        int: ID созданного счёта (bills.id).
    """
    import sqlite3
    from paths import get_db_path
    from config import services

    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.cursor()

        # 1. Получаем service_id по ключу
        cursor.execute("SELECT id FROM services WHERE key = ?", (service_key,))
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Услуга с ключом '{service_key}' не найдена")
        service_id = row[0]

        # 2. Вставляем запись в таблицу bills (один счёт)
        # total_amount = amount (без комиссии)
        # total_fee = 0 (комиссия не применяется при оплате напрямую)
        # total_with_fee = amount (т.к. fee = 0)
        cursor.execute("""
            INSERT INTO bills (date, total_amount, total_fee, total_with_fee)
            VALUES (?, ?, ?, ?)
        """, (date, amount, 0.0, amount))
        bill_id = cursor.lastrowid

        # 3. Вставляем деталь счёта (одна услуга в этом счете)
        cursor.execute("""
            INSERT INTO bill_details (
                bill_id, service_id, service_name,
                start_reading, end_reading,
                consumption, tariff, amount, fee, total
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bill_id,
            service_id,
            services.get(service_key, {}).get('name', service_key),
            start_reading,
            end_reading,
            consumption,
            tariff if tariff is not None else 0.0,
            amount,
            0.0,  # fee = 0
            amount  # total = amount + fee
        ))

        # 4. Если передан список замен/поверок, связываем их с этим счётом и помечаем оплаченными
        if replacement_ids:
            for rep_id in replacement_ids:
                # Добавляем связь в bill_replacements
                cursor.execute("""
                    INSERT OR IGNORE INTO bill_replacements (bill_id, replacement_id)
                    VALUES (?, ?)
                """, (bill_id, rep_id))
                # Помечаем замену/поверку как оплаченную
                cursor.execute("""
                    UPDATE meter_replacements SET is_paid = 1 WHERE id = ?
                """, (rep_id,))

        conn.commit()
        return bill_id