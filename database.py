# ============================================================
# PocketFinance AI
# database.py
# Python 3.13+
# SQLite
# ============================================================

import sqlite3
import os
from datetime import datetime
from typing import Optional


# ============================================================
# DATABASE
# ============================================================

DATABASE_NAME = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "finance.db",
)


# ============================================================
# CONNECTION
# ============================================================

def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(
        DATABASE_NAME,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA busy_timeout = 30000"
    )

    connection.execute(
        "PRAGMA journal_mode = WAL"
    )

    connection.execute(
        "PRAGMA synchronous = NORMAL"
    )

    return connection

# ============================================================
# HELPERS
# ============================================================

def column_exists(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> bool:

    cursor = connection.cursor()

    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    return column_name in columns


def add_column_if_missing(
    connection: sqlite3.Connection,
    table_name: str,
    column_definition: str,
) -> None:

    column_name = column_definition.split()[0]

    if not column_exists(
        connection,
        table_name,
        column_name,
    ):
        connection.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_definition}
            """
        )


# ============================================================
# INIT DATABASE
# ============================================================

def init_database() -> None:

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # ====================================================
        # USERS
        # ====================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                language TEXT,
                username TEXT,
                first_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                documents_accepted INTEGER NOT NULL DEFAULT 0,
                documents_accepted_at TEXT
            )
        """)

        # ----------------------------------------------------
        # TRANSACTIONS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'RUB',
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                comment TEXT,
                created_at TEXT NOT NULL,

                FOREIGN KEY (telegram_id)
                    REFERENCES users(telegram_id)
                    ON DELETE CASCADE
            )
        """)

        # ----------------------------------------------------
        # SETTINGS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                telegram_id INTEGER PRIMARY KEY,
                default_currency TEXT NOT NULL DEFAULT 'RUB',
                reminders_enabled INTEGER NOT NULL DEFAULT 0,
                reminder_time TEXT DEFAULT '20:00',
                ai_advice_enabled INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL,

                FOREIGN KEY (telegram_id)
                    REFERENCES users(telegram_id)
                    ON DELETE CASCADE
            )
        """)

        # Добавляем часовой пояс, если его ещё нет
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = [row[1] for row in cursor.fetchall()]

        if "timezone" not in columns:
            cursor.execute("""
                ALTER TABLE user_settings
                ADD COLUMN timezone TEXT
            """)

        # ----------------------------------------------------
        # REMINDERS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                reminder_type TEXT NOT NULL DEFAULT 'daily',
                reminder_time TEXT NOT NULL DEFAULT '20:00',
                enabled INTEGER NOT NULL DEFAULT 1,
                last_sent_at TEXT,
                created_at TEXT NOT NULL,

                FOREIGN KEY (telegram_id)
                    REFERENCES users(telegram_id)
                    ON DELETE CASCADE
            )
        """)

        # ----------------------------------------------------
        # AI ADVICE HISTORY
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_advice (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                advice TEXT NOT NULL,
                created_at TEXT NOT NULL,

                FOREIGN KEY (telegram_id)
                    REFERENCES users(telegram_id)
                    ON DELETE CASCADE
            )
        """)

        # ----------------------------------------------------
        # PREMIUM SUBSCRIPTIONS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS premium_subscriptions (
                telegram_id INTEGER PRIMARY KEY,
                started_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,

                FOREIGN KEY (telegram_id)
                    REFERENCES users(telegram_id)
                    ON DELETE CASCADE
            )
        """)

        # ----------------------------------------------------
        # TELEGRAM STARS PAYMENTS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS star_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                telegram_payment_charge_id TEXT NOT NULL UNIQUE,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL,
                payment_type TEXT NOT NULL,
                payload TEXT,
                created_at TEXT NOT NULL,

                FOREIGN KEY (telegram_id)
                    REFERENCES users(telegram_id)
                    ON DELETE CASCADE
            )
        """)

        # ====================================================
        # INDEXES
        # ====================================================

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_transactions_user
            ON transactions(telegram_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_transactions_created
            ON transactions(created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_transactions_user_created
            ON transactions(telegram_id, created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_transactions_user_type
            ON transactions(telegram_id, type)
        """)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

# ============================================================
# USERS
# ============================================================

def add_user(
    telegram_id: int,
    language: str = "pending",
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> None:

    now = datetime.now().isoformat()

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO users (
                telegram_id,
                language,
                username,
                first_name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(telegram_id)
            DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                updated_at = excluded.updated_at
            """,
            (
                telegram_id,
                language,
                username,
                first_name,
                now,
                now,
            ),
        )

        cursor.execute(
            """
            INSERT INTO user_settings (
                telegram_id,
                updated_at
            )
            VALUES (?, ?)

            ON CONFLICT(telegram_id)
            DO NOTHING
            """,
            (
                telegram_id,
                now,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_user(
    telegram_id: int,
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


def get_user_language(
    telegram_id: int,
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT language
            FROM users
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return row["language"]

    finally:
        connection.close()

def change_language(
    telegram_id: int,
    language: str,
) -> None:
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE users
            SET
                language = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                language,
                datetime.now().isoformat(),
                telegram_id,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def update_user_profile(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> None:
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE users
            SET
                username = ?,
                first_name = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                username,
                first_name,
                datetime.now().isoformat(),
                telegram_id,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

# ============================================================
# USER PROFILE
# ============================================================

def update_user_profile(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> None:

    connection = get_connection()

    connection.execute(
        """
        UPDATE users
        SET
            username = ?,
            first_name = ?,
            updated_at = ?
        WHERE telegram_id = ?
        """,
        (
            username,
            first_name,
            datetime.now().isoformat(),
            telegram_id,
        ),
    )

    connection.commit()
    connection.close()


# ============================================================
# DOCUMENT ACCEPTANCE
# ============================================================

def accept_documents(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> None:

    now = datetime.now().isoformat()

    connection = get_connection()

    try:
        connection.execute(
            """
            PRAGMA busy_timeout = 10000
            """
        )

        connection.execute(
            """
            UPDATE users
            SET
                documents_accepted = 1,
                documents_accepted_at = ?,
                username = ?,
                first_name = ?,
                updated_at = ?
            WHERE telegram_id = ?
            """,
            (
                now,
                username,
                first_name,
                now,
                telegram_id,
            ),
        )

        connection.commit()

    finally:
        connection.close()


def has_accepted_documents(
    telegram_id: int,
) -> bool:

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT documents_accepted
            FROM users
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )

        result = cursor.fetchone()

        if result is None:
            return False

        return bool(result["documents_accepted"])

    finally:
        connection.close()

# ============================================================
# TRANSACTIONS
# ============================================================

def add_transaction(
    telegram_id: int,
    amount: float,
    currency: str,
    transaction_type: str,
    category: str,
    comment: str = "",
    created_at: str = None,
) -> int:

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO transactions (
            telegram_id,
            amount,
            currency,
            type,
            category,
            comment,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_id,
            float(amount),
            currency,
            transaction_type,
            category,
            comment,
            created_at or datetime.now().isoformat(),
        ),
    )

    transaction_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return int(transaction_id)


def get_transaction(
    transaction_id: int,
) -> Optional[dict]:

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            telegram_id,
            amount,
            currency,
            type,
            category,
            comment,
            created_at
        FROM transactions
        WHERE id = ?
        """,
        (transaction_id,),
    )

    row = cursor.fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)


def get_transactions(
    telegram_id: int,
) -> list[dict]:

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                telegram_id,
                amount,
                currency,
                type,
                category,
                comment,
                created_at
            FROM transactions
            WHERE CAST(telegram_id AS TEXT)
                  = CAST(? AS TEXT)
            ORDER BY created_at DESC
            """,
            (
                telegram_id,
            ),
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()


# ============================================================
# ПОЛУЧЕНИЕ ОПЕРАЦИЙ ЗА ПЕРИОД
# ============================================================

def get_transactions_between(
    telegram_id: int,
    start_date: str,
    end_date: str,
) -> list[dict]:

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                telegram_id,
                amount,
                currency,
                type,
                category,
                comment,
                created_at
            FROM transactions
            WHERE telegram_id = ?
              AND datetime(created_at) >= datetime(?)
              AND datetime(created_at) < datetime(?)
            ORDER BY datetime(created_at) DESC
            """,
            (
                telegram_id,
                start_date,
                end_date,
            ),
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()


# ============================================================
# TRANSACTIONS — EDIT
# ============================================================

def update_transaction(
    transaction_id: int,
    telegram_id: int,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
    transaction_type: Optional[str] = None,
    category: Optional[str] = None,
    comment: Optional[str] = None,
) -> bool:

    connection = get_connection()
    cursor = connection.cursor()

    fields = []
    values = []

    if amount is not None:
        fields.append("amount = ?")
        values.append(float(amount))

    if currency is not None:
        fields.append("currency = ?")
        values.append(currency)

    if transaction_type is not None:
        fields.append("type = ?")
        values.append(transaction_type)

    if category is not None:
        fields.append("category = ?")
        values.append(category)

    if comment is not None:
        fields.append("comment = ?")
        values.append(comment)

    if not fields:
        connection.close()
        return False

    values.extend([
        transaction_id,
        telegram_id,
    ])

    cursor.execute(
        f"""
        UPDATE transactions
        SET {", ".join(fields)}
        WHERE id = ?
          AND telegram_id = ?
        """,
        values,
    )

    updated = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return updated

# ============================================================
# TRANSACTIONS — DELETE
# ============================================================

def delete_transaction(
    transaction_id: int,
    telegram_id: int,
) -> bool:

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM transactions
        WHERE id = ?
          AND telegram_id = ?
        """,
        (
            transaction_id,
            telegram_id,
        ),
    )

    deleted = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return deleted


def delete_transactions_by_category(
    telegram_id: int,
    category: str,
) -> int:

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM transactions
        WHERE telegram_id = ?
          AND category = ?
        """,
        (
            telegram_id,
            category,
        ),
    )

    deleted_count = cursor.rowcount

    connection.commit()
    connection.close()

    return deleted_count

# ============================================================
# TRANSACTIONS — DELETE BY PERIOD
# ============================================================

def delete_transactions_between(
    telegram_id: int,
    start_date: str,
    end_date: str,
) -> int:

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM transactions
        WHERE telegram_id = ?
          AND created_at >= ?
          AND created_at < ?
        """,
        (
            telegram_id,
            start_date,
            end_date,
        ),
    )

    deleted_count = cursor.rowcount

    connection.commit()
    connection.close()

    return deleted_count

# ============================================================
# STATISTICS
# ============================================================

def get_transaction_totals(
    telegram_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            type,
            currency,
            SUM(amount) AS total,
            COUNT(*) AS count
        FROM transactions
        WHERE telegram_id = ?
    """

    params = [telegram_id]

    if start_date is not None:
        query += " AND created_at >= ?"
        params.append(start_date)

    if end_date is not None:
        query += " AND created_at < ?"
        params.append(end_date)

    query += """
        GROUP BY type, currency
        ORDER BY total DESC
    """

    cursor.execute(
        query,
        params,
    )

    result = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return result


def get_category_statistics(
    telegram_id: int,
    transaction_type: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            category,
            currency,
            SUM(amount) AS total,
            COUNT(*) AS count
        FROM transactions
        WHERE telegram_id = ?
          AND type = ?
    """

    params = [
        telegram_id,
        transaction_type,
    ]

    if start_date is not None:
        query += " AND created_at >= ?"
        params.append(start_date)

    if end_date is not None:
        query += " AND created_at < ?"
        params.append(end_date)

    query += """
        GROUP BY category, currency
        ORDER BY total DESC
    """

    cursor.execute(
        query,
        params,
    )

    result = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return result


def get_monthly_statistics(
    telegram_id: int,
    year: int,
    month: int,
):

    start_date = datetime(
        year,
        month,
        1,
    )

    if month == 12:
        end_date = datetime(
            year + 1,
            1,
            1,
        )
    else:
        end_date = datetime(
            year,
            month + 1,
            1,
        )

    return get_transaction_totals(
        telegram_id,
        start_date.isoformat(),
        end_date.isoformat(),
    )


def get_transaction_count(
    telegram_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> int:

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT COUNT(*)
        FROM transactions
        WHERE telegram_id = ?
    """

    params = [telegram_id]

    if start_date is not None:
        query += " AND created_at >= ?"
        params.append(start_date)

    if end_date is not None:
        query += " AND created_at < ?"
        params.append(end_date)

    cursor.execute(
        query,
        params,
    )

    result = cursor.fetchone()[0]

    connection.close()

    return result

# ============================================================
# ДАННЫЕ ДЛЯ ИИ — ПОСЛЕДНИЕ 30 ДНЕЙ
# ============================================================

def get_ai_transaction_totals(
    telegram_id: int,
    start_date: str,
    end_date: str,
):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                type,
                currency,
                SUM(amount) AS total,
                COUNT(*) AS count
            FROM transactions
            WHERE telegram_id = ?
              AND date(created_at) >= date(?)
              AND date(created_at) <= date(?)
            GROUP BY type, currency
            ORDER BY total DESC
            """,
            (
                telegram_id,
                start_date,
                end_date,
            ),
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:

        connection.close()



# ============================================================
# USER SETTINGS
# ============================================================

def get_user_settings(
    telegram_id: int,
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            telegram_id,
            default_currency,
            reminders_enabled,
            reminder_time,
            ai_advice_enabled,
            updated_at,
            timezone
        FROM user_settings
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    result = cursor.fetchone()

    connection.close()

    if result:
        return dict(result)

    return None





def create_default_settings(
    telegram_id: int,
):

    connection = get_connection()
    cursor = connection.cursor()

    # Проверяем наличие столбца timezone
    cursor.execute(
        "PRAGMA table_info(user_settings)"
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    # Если столбца нет — добавляем его
    if "timezone" not in columns:
        cursor.execute(
            """
            ALTER TABLE user_settings
            ADD COLUMN timezone TEXT
            """
        )

    # Создаём настройки пользователя
    cursor.execute(
        """
        INSERT OR IGNORE INTO user_settings
        (
            telegram_id,
            default_currency,
            reminders_enabled,
            reminder_time,
            ai_advice_enabled,
            updated_at,
            timezone
        )
        VALUES (?, 'RUB', 0, '20:00', 1, ?, NULL)
        """,
        (
            telegram_id,
            datetime.now().isoformat(),
        ),
    )

    connection.commit()
    connection.close()



def update_user_settings(
    telegram_id: int,
    default_currency: Optional[str] = None,
    reminders_enabled: Optional[bool] = None,
    reminder_time: Optional[str] = None,
    ai_advice_enabled: Optional[bool] = None,
    timezone: Optional[str] = None,
):

    create_default_settings(telegram_id)

    connection = get_connection()
    cursor = connection.cursor()

    fields = []
    values = []

    if default_currency is not None:
        fields.append(
            "default_currency = ?"
        )
        values.append(default_currency)

    if reminders_enabled is not None:
        fields.append(
            "reminders_enabled = ?"
        )
        values.append(
            int(reminders_enabled)
        )

    if reminder_time is not None:
        fields.append(
            "reminder_time = ?"
        )
        values.append(reminder_time)

    if ai_advice_enabled is not None:
        fields.append(
            "ai_advice_enabled = ?"
        )
        values.append(
            int(ai_advice_enabled)
        )

    if timezone is not None:
        fields.append(
            "timezone = ?"
        )
        values.append(timezone)

    if fields:
        fields.append(
            "updated_at = ?"
        )
        values.append(
            datetime.now().isoformat()
        )

        values.append(telegram_id)

        cursor.execute(
            f"""
            UPDATE user_settings
            SET {", ".join(fields)}
            WHERE telegram_id = ?
            """,
            values,
        )

    connection.commit()
    connection.close()


def get_default_currency(
    telegram_id: int,
) -> str:

    settings = get_user_settings(
        telegram_id
    )

    if settings and settings["default_currency"]:
        return settings["default_currency"]

    return "RUB"


def get_user_timezone(
    telegram_id: int,
) -> Optional[str]:

    settings = get_user_settings(
        telegram_id
    )

    if not settings:
        return None

    if "timezone" not in settings.keys():
        return None

    return settings["timezone"]


# ============================================================
# REMINDERS
# ============================================================

def _ensure_reminder_timezone_column(
    connection,
):
    cursor = connection.cursor()

    cursor.execute(
        "PRAGMA table_info(reminders)"
    )

    columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "timezone" not in columns:

        cursor.execute(
            """
            ALTER TABLE reminders
            ADD COLUMN timezone TEXT NOT NULL
            DEFAULT 'Europe/Moscow'
            """
        )

        connection.commit()


def add_reminder(
    telegram_id: int,
    reminder_type: str,
    reminder_time: str,
    timezone: str = "Europe/Moscow",
) -> int:

    connection = get_connection()

    try:

        _ensure_reminder_timezone_column(
            connection
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO reminders
            (
                telegram_id,
                reminder_type,
                reminder_time,
                timezone,
                enabled,
                created_at
            )
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (
                telegram_id,
                reminder_type,
                reminder_time,
                timezone,
                datetime.now().isoformat(),
            ),
        )

        reminder_id = cursor.lastrowid

        connection.commit()

        return int(reminder_id)

    finally:

        connection.close()


def get_reminders(
    telegram_id: int,
):

    connection = get_connection()

    try:

        _ensure_reminder_timezone_column(
            connection
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                telegram_id,
                reminder_type,
                reminder_time,
                timezone,
                enabled,
                last_sent_at,
                created_at
            FROM reminders
            WHERE telegram_id = ?
            ORDER BY reminder_time
            """,
            (
                telegram_id,
            ),
        )

        result = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return result

    finally:

        connection.close()


def get_enabled_reminders():

    connection = get_connection()

    try:

        _ensure_reminder_timezone_column(
            connection
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                telegram_id,
                reminder_type,
                reminder_time,
                timezone,
                enabled,
                last_sent_at,
                created_at
            FROM reminders
            WHERE enabled = 1
            ORDER BY reminder_time
            """
        )

        result = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return result

    finally:

        connection.close()


def update_reminder(
    reminder_id: int,
    telegram_id: int,
    enabled: Optional[bool] = None,
    reminder_time: Optional[str] = None,
    timezone: Optional[str] = None,
) -> bool:

    connection = get_connection()

    try:

        _ensure_reminder_timezone_column(
            connection
        )

        cursor = connection.cursor()

        fields = []
        values = []

        if enabled is not None:

            fields.append(
                "enabled = ?"
            )

            values.append(
                int(enabled)
            )

        if reminder_time is not None:

            fields.append(
                "reminder_time = ?"
            )

            values.append(
                reminder_time
            )

        if timezone is not None:

            fields.append(
                "timezone = ?"
            )

            values.append(
                timezone
            )

        if not fields:

            return False

        values.extend([
            reminder_id,
            telegram_id,
        ])

        cursor.execute(
            f"""
            UPDATE reminders
            SET {", ".join(fields)}
            WHERE id = ?
              AND telegram_id = ?
            """,
            values,
        )

        updated = (
            cursor.rowcount > 0
        )

        connection.commit()

        return updated

    finally:

        connection.close()


def delete_reminder(
    reminder_id: int,
    telegram_id: int,
) -> bool:

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM reminders
            WHERE id = ?
              AND telegram_id = ?
            """,
            (
                reminder_id,
                telegram_id,
            ),
        )

        deleted = (
            cursor.rowcount > 0
        )

        connection.commit()

        return deleted

    finally:

        connection.close()


def mark_reminder_sent(
    reminder_id: int,
):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE reminders
            SET last_sent_at = ?
            WHERE id = ?
            """,
            (
                datetime.now().isoformat(),
                reminder_id,
            ),
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# AI ADVICE
# ============================================================

def save_ai_advice(
    telegram_id: int,
    advice: str,
) -> int:

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO ai_advice
        (
            telegram_id,
            advice,
            created_at
        )
        VALUES (?, ?, ?)
        """,
        (
            telegram_id,
            advice,
            datetime.now().isoformat(),
        ),
    )

    advice_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return int(advice_id)


def get_latest_ai_advice(
    telegram_id: int,
    limit: int = 5,
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            advice,
            created_at
        FROM ai_advice
        WHERE telegram_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (
            telegram_id,
            limit,
        ),
    )

    result = [
        dict(row)
        for row in cursor.fetchall()
    ]

    connection.close()

    return result


# ============================================================
# FINANCIAL DISCIPLINE
# ============================================================

def calculate_financial_discipline(
    telegram_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):

    totals = get_transaction_totals(
        telegram_id,
        start_date,
        end_date,
    )

    income = 0.0
    expenses = 0.0
    transaction_count = 0

    for item in totals:

        transaction_count += item["count"]

        if item["type"] == "income":
            income += item["total"]

        elif item["type"] == "expense":
            expenses += item["total"]

    if transaction_count == 0:
        return {
            "score": 0,
            "level": "no_data",
            "income": 0.0,
            "expenses": 0.0,
            "balance": 0.0,
            "transaction_count": 0,
        }

    balance = income - expenses

    score = 50

    if income > 0:

        expense_ratio = expenses / income

        if expense_ratio < 0.50:
            score += 35

        elif expense_ratio < 0.70:
            score += 25

        elif expense_ratio < 0.85:
            score += 15

        elif expense_ratio < 1.00:
            score += 5

        else:
            score -= 15

    if balance > 0:
        score += 10

    elif balance < 0:
        score -= 15

    if transaction_count >= 5:
        score += 5

    score = max(
        0,
        min(100, score),
    )

    if score >= 85:
        level = "excellent"

    elif score >= 70:
        level = "good"

    elif score >= 50:
        level = "average"

    elif score >= 30:
        level = "weak"

    else:
        level = "critical"

    return {
        "score": score,
        "level": level,
        "income": income,
        "expenses": expenses,
        "balance": balance,
        "transaction_count": transaction_count,
    }


# ============================================================
# FULL USER DATA DELETION
# ============================================================

def delete_user_data(
    telegram_id: int,
) -> bool:

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM ai_advice WHERE telegram_id = ?",
        (telegram_id,),
    )

    cursor.execute(
        "DELETE FROM reminders WHERE telegram_id = ?",
        (telegram_id,),
    )

    cursor.execute(
        "DELETE FROM user_settings WHERE telegram_id = ?",
        (telegram_id,),
    )

    cursor.execute(
        "DELETE FROM transactions WHERE telegram_id = ?",
        (telegram_id,),
    )

    cursor.execute(
        "DELETE FROM users WHERE telegram_id = ?",
        (telegram_id,),
    )

    deleted = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return deleted

# ============================================================
# ADMIN — BROADCAST USERS
# ============================================================

def get_broadcast_users():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                telegram_id,
                language
            FROM users
            WHERE language IN ('ru', 'en')
            ORDER BY telegram_id
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()