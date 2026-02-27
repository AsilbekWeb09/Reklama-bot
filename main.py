import os
import asyncio
import random
import time
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from db import (
    init_db,
    add_user,
    get_user_points,
    top_users,
    total_users,
    is_banned,
    set_giveaway,
    get_giveaway,
    get_all_users,
    get_users_page,
    ban_user,
    unban_user,
    add_points,
    remove_points,
    get_user_info,
    total_banned,
    create_ads_order,
    get_last_pending_order,
    attach_receipt,
    get_waiting_orders,
    set_ads_status,
    get_ads_order,
    set_giveaway_prize,
    get_giveaway_prize,
    get_top_user
)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

PAYMENT_CARD = os.getenv("PAYMENT_CARD")
PAYMENT_OWNER = os.getenv("PAYMENT_OWNER")

sub_cache = {}
flood_cache = {}

def anti_flood(user_id):
    now = time.time()
    if user_id in flood_cache:
        if now - flood_cache[user_id] < 1.2:
            return False
    flood_cache[user_id] = now
    return True

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    if user_id in sub_cache and sub_cache[user_id] is True:
        return True

    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ["member", "administrator", "creator"]:
            sub_cache[user_id] = True
            return True
        return False
    except Exception as e:
        print("SUBSCRIBE ERROR:", e)
        return False

async def send_subscribe_message(chat_id, context):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")]
    ])

    await context.bot.send_message(
        chat_id=chat_id,
        text="❌ Botdan foydalanish uchun kanalga obuna bo‘lish shart!\n\n"
             "📌 Kanalga obuna bo‘ling va keyin 'Tekshirish' tugmasini bosing.",
        reply_markup=keyboard
    )

async def send_menu(chat_id, user_id, context, first_name="User"):
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"

    points = await get_user_points(user_id)
    users_count = await total_users()
    giveaway_status = await get_giveaway()
    prize = await get_giveaway_prize()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Profil", callback_data="profile")],
        [InlineKeyboardButton("🏆 Top 10", callback_data="top")],
        [InlineKeyboardButton("🎁 Giveaway", callback_data="giveaway")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats_user")],
        [InlineKeyboardButton("📢 Reklama berish", callback_data="ads_menu")],
        [InlineKeyboardButton("🔗 Referral Link", callback_data="referral")]
    ])

    text = (
        f"✅ Xush kelibsiz, {first_name}!\n\n"
        f"📢 Kanal: {CHANNEL_USERNAME}\n\n"
        f"👥 Userlar: {users_count}\n"
        f"🎯 Ballaringiz: {points}\n\n"
        f"🎁 Giveaway: {'✅ ACTIVE' if giveaway_status == 1 else '❌ OFF'}\n"
        f"🏆 Sovg‘a: {prize}\n\n"
        f"🔗 Referral link:\n{referral_link}\n\n"
        f"📌 Odam chaqiring → ball yig‘ing!"
    )

    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if not anti_flood(user_id):
        return

    if await is_banned(user_id):
        await update.message.reply_text("❌ Siz bloklangansiz.")
        return

    invited_by = None
    if context.args:
        try:
            invited_by = int(context.args[0])
        except:
            invited_by = None

    await add_user(user_id, user.username, user.first_name, invited_by)

    if not await is_subscribed(user_id, context):
        await send_subscribe_message(update.effective_chat.id, context)
        return

    await send_menu(update.effective_chat.id, user_id, context, user.first_name)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not anti_flood(user_id):
        return

    if await is_banned(user_id):
        await query.message.reply_text("❌ Siz bloklangansiz.")
        return

    if query.data == "check_sub":
        if await is_subscribed(user_id, context):
            await query.message.reply_text("✅ Obuna tasdiqlandi!")
            await send_menu(query.message.chat_id, user_id, context, query.from_user.first_name)
        else:
            await query.message.reply_text("❌ Siz hali kanalga obuna bo‘lmagansiz!")

    elif query.data == "profile":
        points = await get_user_points(user_id)
        await query.message.reply_text(
            f"👤 Profil\n\n"
            f"👨 Ism: {query.from_user.first_name}\n"
            f"🆔 ID: {user_id}\n"
            f"🎯 Ball: {points}"
        )

    elif query.data == "top":
        users = await top_users(10)
        text = "🏆 Top 10:\n\n"
        for i, (name, pts) in enumerate(users, start=1):
            text += f"{i}) {name} — {pts}\n"
        await query.message.reply_text(text)

    elif query.data == "giveaway":
        status = await get_giveaway()
        prize = await get_giveaway_prize()

        if status == 0:
            await query.message.reply_text("❌ Giveaway OFF.")
        else:
            await query.message.reply_text(
                f"🎁 Giveaway ACTIVE!\n\n"
                f"🏆 Sovg‘a: {prize}\n\n"
                f"📌 Qoidalar:\n"
                f"• Referral orqali ball yig‘ing\n"
                f"• Kimning bali ko‘p bo‘lsa o‘sha sovg‘a oladi"
            )

    elif query.data == "stats_user":
        users_count = await total_users()
        await query.message.reply_text(f"📊 Statistika\n\n👥 Jami userlar: {users_count}")

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        await query.message.reply_text(f"🔗 Referral link:\n\n{referral_link}")

    elif query.data == "ads_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🕐 1 soat - 10 000 so‘m", callback_data="ads_1h")],
            [InlineKeyboardButton("🕕 6 soat - 30 000 so‘m", callback_data="ads_6h")],
            [InlineKeyboardButton("🕛 24 soat - 60 000 so‘m", callback_data="ads_24h")],
            [InlineKeyboardButton("📌 Pinned 24h - 100 000 so‘m", callback_data="ads_pin")],
        ])
        await query.message.reply_text("📢 Reklama paketini tanlang:", reply_markup=keyboard)

    elif query.data in ["ads_1h", "ads_6h", "ads_24h", "ads_pin"]:
        packages = {
            "ads_1h": ("1 soat", 10000),
            "ads_6h": ("6 soat", 30000),
            "ads_24h": ("24 soat", 60000),
            "ads_pin": ("Pinned 24 soat", 100000),
        }

        package_name, price = packages[query.data]

        context.user_data["ads_package"] = package_name
        context.user_data["ads_price"] = price
        context.user_data["ads_text_mode"] = True

        await query.message.reply_text(
            f"✅ Paket: {package_name}\n"
            f"💰 Narx: {price} so‘m\n\n"
            f"📌 Endi reklama matnini yuboring:"
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.user_data.get("ads_text_mode"):
        if update.message.text is None:
            await update.message.reply_text("❗ Reklama matnini TEXT qilib yuboring.")
            return

        context.user_data["ads_text_mode"] = False

        package_name = context.user_data.get("ads_package")
        price = context.user_data.get("ads_price")
        ad_text = update.message.text.strip()

        await create_ads_order(user_id, package_name, price, ad_text)

        context.user_data["waiting_receipt"] = True

        await update.message.reply_text(
            f"✅ Reklama buyurtmangiz yaratildi!\n\n"
            f"📦 Paket: {package_name}\n"
            f"💰 Narx: {price} so‘m\n\n"
            f"💳 To‘lov:\n"
            f"👤 Egasi: {PAYMENT_OWNER}\n"
            f"💳 Karta: {PAYMENT_CARD}\n\n"
            f"📌 Endi chek screenshot yuboring!"
        )
        return

    if context.user_data.get("waiting_receipt"):
        if not update.message.photo:
            await update.message.reply_text("❗ Chekni rasm ko‘rinishida yuboring (screenshot).")
            return

        context.user_data["waiting_receipt"] = False
        receipt_file_id = update.message.photo[-1].file_id

        last = await get_last_pending_order(user_id)
        if not last:
            await update.message.reply_text("❌ Sizda aktiv reklama order yo‘q.")
            return

        order_id = last[0]
        await attach_receipt(order_id, receipt_file_id)

        await update.message.reply_text("✅ Chek qabul qilindi! Admin tekshiradi.")

        order = await get_ads_order(order_id)
        oid, uid, package, price, ad_text, receipt, status = order

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{oid}"),
                InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{oid}")
            ]
        ])

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=receipt_file_id,
            caption=
            f"📢 REKLAMA BUYURTMA!\n\n"
            f"📦 Order ID: {oid}\n"
            f"👤 User ID: {uid}\n"
            f"📦 Paket: {package}\n"
            f"💰 Narx: {price} so‘m\n\n"
            f"📝 Reklama:\n{ad_text}",
            reply_markup=keyboard
        )
        return

    if user_id == ADMIN_ID:
        if update.message.text is None:
            return

        text = update.message.text.strip()

        if context.user_data.get("broadcast_mode"):
            context.user_data["broadcast_mode"] = False
            users = await get_all_users()

            sent = 0
            failed = 0

            await update.message.reply_text("⏳ Broadcast yuborilmoqda...")

            for uid in users:
                try:
                    await context.bot.send_message(chat_id=uid, text=text)
                    sent += 1
                except:
                    failed += 1

            await update.message.reply_text(f"✅ Tugadi!\n\nYuborildi: {sent}\nXato: {failed}")
            return

        if context.user_data.get("ban_mode"):
            context.user_data["ban_mode"] = False
            try:
                uid = int(text)
                await ban_user(uid)
                await update.message.reply_text(f"🚫 Ban qilindi: {uid}")
            except:
                await update.message.reply_text("❌ ID xato!")
            return

        if context.user_data.get("unban_mode"):
            context.user_data["unban_mode"] = False
            try:
                uid = int(text)
                await unban_user(uid)
                await update.message.reply_text(f"✅ Unban qilindi: {uid}")
            except:
                await update.message.reply_text("❌ ID xato!")
            return

        if context.user_data.get("add_points_mode"):
            context.user_data["add_points_mode"] = False
            try:
                uid, pts = text.split()
                await add_points(int(uid), int(pts))
                await update.message.reply_text(f"➕ {uid} ga {pts} ball qo‘shildi.")
            except:
                await update.message.reply_text("❌ Format: user_id ball")
            return

        if context.user_data.get("remove_points_mode"):
            context.user_data["remove_points_mode"] = False
            try:
                uid, pts = text.split()
                await remove_points(int(uid), int(pts))
                await update.message.reply_text(f"➖ {uid} dan {pts} ball ayirildi.")
            except:
                await update.message.reply_text("❌ Format: user_id ball")
            return

        if context.user_data.get("userinfo_mode"):
            context.user_data["userinfo_mode"] = False
            try:
                uid = int(text)
                info = await get_user_info(uid)

                if not info:
                    await update.message.reply_text("❌ User topilmadi.")
                    return

                uid, username, name, pts, banned = info
                await update.message.reply_text(
                    f"👤 USER INFO\n\n"
                    f"🆔 ID: {uid}\n"
                    f"👨 Ism: {name}\n"
                    f"🔗 Username: @{username}\n"
                    f"🎯 Ball: {pts}\n"
                    f"🚫 Ban: {'Ha' if banned == 1 else 'Yo‘q'}"
                )
            except:
                await update.message.reply_text("❌ ID xato!")
            return

        if context.user_data.get("prize_custom_mode"):
            context.user_data["prize_custom_mode"] = False
            await set_giveaway_prize(text)
            await update.message.reply_text(f"✅ Prize saqlandi: {text}")
            return

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin emassiz.")
        return

    users_count = await total_users()
    banned_count = await total_banned()
    giveaway_status = await get_giveaway()
    prize = await get_giveaway_prize()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 User ro‘yxati", callback_data="admin_users_1")],
        [InlineKeyboardButton("📦 Reklama orderlar", callback_data="admin_ads")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],

        [InlineKeyboardButton("🎁 Giveaway ON", callback_data="admin_giveaway_on"),
         InlineKeyboardButton("❌ Giveaway OFF", callback_data="admin_giveaway_off")],

        [InlineKeyboardButton("🎁 Prize tanlash", callback_data="admin_set_prize")],
        [InlineKeyboardButton("🏆 Winner (Top ball)", callback_data="admin_winner_top")],

        [InlineKeyboardButton("🚫 Ban user", callback_data="admin_ban")],
        [InlineKeyboardButton("✅ Unban user", callback_data="admin_unban")],
        [InlineKeyboardButton("➕ Ball qo‘shish", callback_data="admin_add_points")],
        [InlineKeyboardButton("➖ Ball ayirish", callback_data="admin_remove_points")],
        [InlineKeyboardButton("🔍 User info", callback_data="admin_userinfo")],
    ])

    await update.message.reply_text(
        f"👑 ADMIN PANEL\n\n"
        f"👥 Userlar: {users_count}\n"
        f"🚫 Ban: {banned_count}\n\n"
        f"🎁 Giveaway: {'ON' if giveaway_status == 1 else 'OFF'}\n"
        f"🏆 Prize: {prize}",
        reply_markup=keyboard
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data

    if data.startswith("admin_users_"):
        page = int(data.split("_")[-1])
        users = await get_users_page(page=page, per_page=10)

        if not users:
            await query.message.reply_text("❌ User yo‘q.")
            return

        text = f"👥 USER RO‘YXATI (Page {page})\n\n"
        for uid, name, pts in users:
            text += f"🆔 {uid} | {name} | 🎯 {pts}\n"

        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"admin_users_{page-1}"))
        nav_buttons.append(InlineKeyboardButton("➡️ Keyingi", callback_data=f"admin_users_{page+1}"))

        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([nav_buttons]))

    elif data == "admin_ads":
        orders = await get_waiting_orders()

        if not orders:
            await query.message.reply_text("📦 Tasdiqlash uchun reklama order yo‘q.")
            return

        for oid, uid, package, price, ad_text, receipt in orders[:5]:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{oid}"),
                    InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{oid}")
                ]
            ])

            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=receipt,
                caption=
                f"📦 Order ID: {oid}\n"
                f"👤 User: {uid}\n"
                f"📦 Paket: {package}\n"
                f"💰 Narx: {price} so‘m\n\n"
                f"📝 Reklama:\n{ad_text}",
                reply_markup=keyboard
            )

    elif data.startswith("approve_"):
        oid = int(data.split("_")[1])
        order = await get_ads_order(oid)

        if not order:
            await query.message.reply_text("❌ Order topilmadi.")
            return

        oid, uid, package, price, ad_text, receipt, status = order
        await set_ads_status(oid, "approved")

        await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=ad_text)

        await context.bot.send_message(
            chat_id=uid,
            text="✅ Reklamangiz tasdiqlandi va kanalga joylandi!"
        )

        await query.message.reply_text(f"✅ Order tasdiqlandi! (ID: {oid})")

    elif data.startswith("reject_"):
        oid = int(data.split("_")[1])
        order = await get_ads_order(oid)

        if not order:
            await query.message.reply_text("❌ Order topilmadi.")
            return

        oid, uid, package, price, ad_text, receipt, status = order
        await set_ads_status(oid, "rejected")

        await context.bot.send_message(
            chat_id=uid,
            text="❌ Reklama buyurtmangiz admin tomonidan rad etildi."
        )

        await query.message.reply_text(f"❌ Order rad etildi. (ID: {oid})")

    elif data == "admin_broadcast":
        context.user_data["broadcast_mode"] = True
        await query.message.reply_text("📢 Broadcast matnini yuboring:")

    elif data == "admin_giveaway_on":
        prize = await get_giveaway_prize()

        if prize == "🎁 Sovg‘a yo‘q":
            await query.message.reply_text("❌ Prize tanlanmagan!\n\nAvval 🎁 Prize tanlang.")
            return

        await set_giveaway(1)
        await query.message.reply_text(f"✅ Giveaway yoqildi!\n🎁 Prize: {prize}")

    elif data == "admin_giveaway_off":
        await set_giveaway(0)
        await query.message.reply_text("❌ Giveaway o‘chirildi!")

    elif data == "admin_set_prize":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖼 NFT", callback_data="prize_nft")],
            [InlineKeyboardButton("🎁 Gift", callback_data="prize_gift")],
            [InlineKeyboardButton("⭐ Stars", callback_data="prize_stars")],
            [InlineKeyboardButton("✍️ Custom prize", callback_data="prize_custom")]
        ])
        await query.message.reply_text("🎁 Sovg‘ani tanlang:", reply_markup=keyboard)

    elif data == "prize_nft":
        await set_giveaway_prize("🖼 NFT")
        await query.message.reply_text("✅ Prize tanlandi: 🖼 NFT")

    elif data == "prize_gift":
        await set_giveaway_prize("🎁 Telegram Gift")
        await query.message.reply_text("✅ Prize tanlandi: 🎁 Telegram Gift")

    elif data == "prize_stars":
        await set_giveaway_prize("⭐ Telegram Stars")
        await query.message.reply_text("✅ Prize tanlandi: ⭐ Telegram Stars")

    elif data == "prize_custom":
        context.user_data["prize_custom_mode"] = True
        await query.message.reply_text("✍️ Prize nomini yozing (misol: ⭐ 200 Stars yoki 🎁 Premium 1 oy)")

    elif data == "admin_winner_top":
        status = await get_giveaway()
        if status == 0:
            await query.message.reply_text("❌ Giveaway OFF.")
            return

        prize = await get_giveaway_prize()
        top_user = await get_top_user()

        if not top_user:
            await query.message.reply_text("❌ User topilmadi.")
            return

        uid, name, pts = top_user

        await query.message.reply_text(
            f"🏆 TOP WINNER!\n\n"
            f"👤 Ism: {name}\n"
            f"🆔 ID: {uid}\n"
            f"🎯 Ball: {pts}\n\n"
            f"🎁 Sovg‘a: {prize}"
        )

        try:
            await context.bot.send_message(
                chat_id=uid,
                text=
                f"🎉 TABRIKLAYMIZ!\n\n"
                f"🏆 Siz eng ko‘p ball yig‘ib winner bo‘ldingiz!\n\n"
                f"🎯 Ball: {pts}\n"
                f"🎁 Sovg‘a: {prize}\n\n"
                f"📌 Admin siz bilan bog‘lanadi."
            )
        except:
            await query.message.reply_text("⚠️ Winnerga xabar yuborilmadi (user botni bloklagan).")

    elif data == "admin_ban":
        context.user_data["ban_mode"] = True
        await query.message.reply_text("🚫 Ban qilinadigan user ID yuboring:")

    elif data == "admin_unban":
        context.user_data["unban_mode"] = True
        await query.message.reply_text("✅ Unban qilinadigan user ID yuboring:")

    elif data == "admin_add_points":
        context.user_data["add_points_mode"] = True
        await query.message.reply_text("➕ Format: user_id ball")

    elif data == "admin_remove_points":
        context.user_data["remove_points_mode"] = True
        await query.message.reply_text("➖ Format: user_id ball")

    elif data == "admin_userinfo":
        context.user_data["userinfo_mode"] = True
        await query.message.reply_text("🔍 User ID yuboring:")

async def run_bot():
    await init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(admin_|approve_|reject_|prize_)"))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))

    print("✅ NovaReach FULL PRO BOT ishga tushdi...")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(run_bot())
