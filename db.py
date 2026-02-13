import aiosqlite

DB_NAME = "database.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            points INTEGER DEFAULT 0,
            invited_by INTEGER DEFAULT NULL,
            is_banned INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            giveaway_active INTEGER DEFAULT 0,
            giveaway_prize TEXT DEFAULT '🎁 Sovg‘a yo‘q'
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS ads_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            package TEXT,
            price INTEGER,
            ad_text TEXT,
            receipt_file_id TEXT DEFAULT NULL,
            status TEXT DEFAULT 'pending'
        )
        """)

        await db.execute("""
        INSERT OR IGNORE INTO settings (id, giveaway_active, giveaway_prize)
        VALUES (1, 0, '🎁 Sovg‘a yo‘q')
        """)

        await db.commit()


# ==========================
# USERS
# ==========================
async def add_user(user_id, username, first_name, invited_by=None):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        exists = await cur.fetchone()

        if exists:
            return

        await db.execute(
            "INSERT INTO users (user_id, username, first_name, invited_by) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, invited_by)
        )

        if invited_by and invited_by != user_id:
            await db.execute("UPDATE users SET points = points + 1 WHERE user_id=?", (invited_by,))

        await db.commit()


async def get_user_points(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else 0


async def add_points(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET points = points + ? WHERE user_id=?", (amount, user_id))
        await db.commit()


async def remove_points(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET points = points - ? WHERE user_id=?", (amount, user_id))
        await db.commit()


async def is_banned(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row and row[0] == 1


async def ban_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
        await db.commit()


async def unban_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
        await db.commit()


async def get_user_info(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT user_id, username, first_name, points, is_banned FROM users WHERE user_id=?",
            (user_id,)
        )
        return await cur.fetchone()


async def total_users():
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        row = await cur.fetchone()
        return row[0] if row else 0


async def total_banned():
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
        row = await cur.fetchone()
        return row[0] if row else 0


async def top_users(limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT first_name, points FROM users WHERE is_banned=0 ORDER BY points DESC LIMIT ?",
            (limit,)
        )
        return await cur.fetchall()


async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE is_banned=0")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def get_users_page(page=1, per_page=10):
    offset = (page - 1) * per_page
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT user_id, first_name, points FROM users ORDER BY points DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        )
        return await cur.fetchall()


async def get_top_user():
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT user_id, first_name, points FROM users WHERE is_banned=0 ORDER BY points DESC LIMIT 1"
        )
        return await cur.fetchone()


# ==========================
# GIVEAWAY
# ==========================
async def set_giveaway(status: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE settings SET giveaway_active=? WHERE id=1", (status,))
        await db.commit()


async def get_giveaway():
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT giveaway_active FROM settings WHERE id=1")
        row = await cur.fetchone()
        return row[0] if row else 0


async def set_giveaway_prize(prize):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE settings SET giveaway_prize=? WHERE id=1", (prize,))
        await db.commit()


async def get_giveaway_prize():
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT giveaway_prize FROM settings WHERE id=1")
        row = await cur.fetchone()
        return row[0] if row else "🎁 Sovg‘a yo‘q"


# ==========================
# ADS SYSTEM
# ==========================
async def create_ads_order(user_id, package, price, ad_text):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO ads_orders (user_id, package, price, ad_text, status) VALUES (?, ?, ?, ?, 'pending')",
            (user_id, package, price, ad_text)
        )
        await db.commit()


async def get_last_pending_order(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT id FROM ads_orders WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1",
            (user_id,)
        )
        return await cur.fetchone()


async def attach_receipt(order_id, receipt_file_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE ads_orders SET receipt_file_id=?, status='waiting_admin' WHERE id=?",
            (receipt_file_id, order_id)
        )
        await db.commit()


async def get_waiting_orders():
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT id, user_id, package, price, ad_text, receipt_file_id FROM ads_orders WHERE status='waiting_admin' ORDER BY id DESC"
        )
        return await cur.fetchall()


async def set_ads_status(order_id, status):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE ads_orders SET status=? WHERE id=?", (status, order_id))
        await db.commit()


async def get_ads_order(order_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT id, user_id, package, price, ad_text, receipt_file_id, status FROM ads_orders WHERE id=?",
            (order_id,)
        )
        return await cur.fetchone()
