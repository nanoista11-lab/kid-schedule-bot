import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DATA_FILE = Path("data/events.json")
DATA_FILE.parent.mkdir(exist_ok=True)

TYPE_LABELS = {
    "sport": "ספורט / חוג",
    "medical": "רפואי",
    "birthday": "יום הולדת",
    "school": "בית ספר",
    "other": "אחר",
}

TYPE_EMOJI = {
    "sport": "⚽",
    "medical": "🏥",
    "birthday": "🎂",
    "school": "🎒",
    "other": "📌",
}

def load_events():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_events(events):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def format_event_message(event, title=None):
    emoji = TYPE_EMOJI.get(event.get("type", "other"), "📌")
    label = TYPE_LABELS.get(event.get("type", "other"), "אחר")
    date_parts = event["date"].split("-")
    formatted_date = f"{date_parts[2]}/{date_parts[1]}/{date_parts[0]}"
    lines = []
    if title:
        lines.append(f"*{title}*\n")
    lines.append(f"{emoji} *{label} — {event['child']}*")
    lines.append(f"📆 תאריך: {formatted_date}" + (f" בשעה {event['time']}" if event.get('time') else ""))
    if event.get("location"):
        lines.append(f"📍 מיקום: {event['location']}")
    if event.get("pickup_by"):
        lines.append(f"🚗 לוקח: {event['pickup_by']}")
    if event.get("dropoff_by"):
        lines.append(f"🏠 אוסף: {event['dropoff_by']}")
    if event.get("notes"):
        lines.append(f"📝 הערות: {event['notes']}")
    return "\n".join(lines)

async def send_reminder(bot, event, reminder_type):
    if reminder_type == "evening":
        title = "🔔 תזכורת — מחר יש אירוע!"
    else:
        title = "☀️ בוקר טוב — היום יש אירוע!"

    text = format_event_message(event, title=title)
    wa_text = format_event_message(event).replace("*", "")
    wa_url = f"https://wa.me/?text={wa_text}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📲 שלח לוואצאפ", url=wa_url)],
        [InlineKeyboardButton("✅ ראיתי, תודה", callback_data=f"ack_{event['id']}")]
    ])
    await bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def check_and_send_reminders(bot):
    events = load_events()
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    hour = datetime.now().hour

    for event in events:
        event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()

        if event_date == tomorrow and hour == 20:
            await send_reminder(bot, event, "evening")

        if event_date == today and hour == 7:
            await send_reminder(bot, event, "morning")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"👋 שלום! אני בוט ניהול לוז הילדים שלך.\n\n"
        f"ה-Chat ID שלך הוא: `{chat_id}`\n\n"
        f"שמור/י אותו ב-Railway כ-TELEGRAM\\_CHAT\\_ID\n\n"
        f"פקודות:\n"
        f"/events — כל האירועים\n"
        f"/today — אירועי היום\n"
        f"/tomorrow — אירועי מחר\n"
        f"/test — שלח תזכורת בדיקה",
        parse_mode="Markdown"
    )

async def cmd_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = load_events()
    if not events:
        await update.message.reply_text("אין אירועים שמורים עדיין.")
        return
    today = datetime.now().date()
    upcoming = [e for e in events if datetime.strptime(e["date"], "%Y-%m-%d").date() >= today]
    upcoming.sort(key=lambda e: e["date"])
    if not upcoming:
        await update.message.reply_text("אין אירועים קרובים.")
        return
    for event in upcoming[:10]:
        text = format_event_message(event)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 מחק אירוע", callback_data=f"del_{event['id']}")]
        ])
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = load_events()
    today = datetime.now().date().isoformat()
    todays = [e for e in events if e["date"] == today]
    if not todays:
        await update.message.reply_text("אין אירועים היום 🎉")
        return
    for event in todays:
        await update.message.reply_text(format_event_message(event), parse_mode="Markdown")

async def cmd_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = load_events()
    tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
    tomorrows = [e for e in events if e["date"] == tomorrow]
    if not tomorrows:
        await update.message.reply_text("אין אירועים מחר 🎉")
        return
    for event in tomorrows:
        await update.message.reply_text(format_event_message(event), parse_mode="Markdown")

async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = load_events()
    if not events:
        await update.message.reply_text("אין אירועים לבדיקה. הוסף/י קודם דרך הממשק.")
        return
    await send_reminder(context.bot, events[0], "evening")
    await update.message.reply_text("✅ נשלחה תזכורת בדיקה!")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("ack_"):
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("✅ מעולה! סומן כנקרא.")

    elif data.startswith("del_"):
        event_id = int(data.split("_")[1])
        events = load_events()
        events = [e for e in events if e["id"] != event_id]
        save_events(events)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("🗑 האירוע נמחק.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "להוספת אירועים השתמש/י בממשק הוויזואלי 👆\n"
        "פקודות זמינות: /events /today /tomorrow /test"
    )

def main():
    if not TOKEN:
        raise ValueError("חסר TELEGRAM_BOT_TOKEN בסביבה")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("events", cmd_events))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("tomorrow", cmd_tomorrow))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler = AsyncIOScheduler(timezone="Asia/Jerusalem")
    scheduler.add_job(
        lambda: asyncio.create_task(check_and_send_reminders(app.bot)),
        "cron", hour="7,20", minute=0
    )
    scheduler.start()

    print("🤖 בוט עולה...")
    app.run_polling()

if __name__ == "__main__":
    main()
