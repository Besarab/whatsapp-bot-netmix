from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, render_template, send_file, flash
from twilio.rest import Client
import sqlite3
import openpyxl
import os

app = Flask(__name__, template_folder="templates")

app.secret_key = os.getenv("FLASK_SECRET_KEY", "change_this_in_production")

ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN")
FROM_WHATSAPP = "whatsapp:+14155238886"
client = Client(ACCOUNT_SID, AUTH_TOKEN)

sessions = {}

DB_PATH = os.path.join(os.getcwd(), "submissions.db")

def init_db():
    """Ініціалізація бази та створення таблиці, якщо її нема."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT,
                name TEXT,
                address TEXT,
                contact TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


init_db()

@app.route("/webhook", methods=["POST"])
def webhook():
    """Обробка вхідних WhatsApp-повідомлень через Twilio."""
    incoming = request.values.get('Body', '').strip()
    from_number = request.values.get('From')
    lower_msg = incoming.lower()

    if lower_msg == "заявка":
        reply = (
            "📋 Надішліть нам заявку у форматі:\n"
            "ПІБ, адреса, телефон\n"
            "Приклад:\n"
            "Іваненко Іван, вул. Лесі Українки 5, +380501112233"
        )
        sessions[from_number] = "waiting_for_application"

    elif sessions.get(from_number) == "waiting_for_application" and "," in incoming:
        parts = [p.strip() for p in incoming.split(",")]
        if len(parts) == 3:
            name, address, contact = parts
            
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO submissions (phone, name, address, contact) VALUES (?, ?, ?, ?)",
                    (from_number, name, address, contact)
                )
            
            host = request.host_url.rstrip("/") + "/"
            reply = (
                "✅ Заявку збережено. Дякуємо!\n"
                f"📋 Переглянути всі заявки: {host}"
            )
            sessions[from_number] = None
        else:
            reply = "❗️ Невірний формат. Надішліть: ПІБ, адреса, телефон"

    elif "підключення" in lower_msg:
        reply = (
            "🌐 Компанія Netmix надає підключення через:\n"
            "- Волоконно-оптичну мережу\n"
            "- Радіоканал (у віддалених районах)\n"
            "💬 Щоб подати заявку, напишіть *заявка*"
        )
    elif "faq" in lower_msg or "питання" in lower_msg:
        reply = (
            "❓ Найпоширеніші питання:\n"
            "- Як змінити тариф?\n"
            "- Як оплатити?\n"
            "- Як підключити IPTV?\n"
            "🔧 Напишіть конкретне питання."
        )
    elif "оператор" in lower_msg:
        reply = (
            "👨‍💻 Наш оператор зв'яжеться з вами найближчим часом.\n"
            "📞 Телефон: +380-XX-XXX-XXXX"
        )
    else:
        reply = (
            "👋 Вітаю! Я чат-бот компанії *Netmix*.\n"
            "Ось чим можу допомогти:\n"
            "- *підключення* — варіанти підключення\n"
            "- *заявка* — залишити заявку\n"
            "- *faq* — часті питання\n"
            "- *оператор* — зв'язок із підтримкою"
        )

    client.messages.create(
        body=reply,
        from_=FROM_WHATSAPP,
        to=from_number
    )
    return "OK", 200

@app.route("/")
def home():
    """Головна сторінка з формою фільтра та кнопкою експорту."""
    return render_template("home.html")

@app.route("/filter")
def filter_table():
    """Показує таблицю заявок за діапазоном дат."""
    start = request.args.get("start")
    end   = request.args.get("end")

    query = "SELECT name, address, contact, phone, timestamp FROM submissions WHERE 1=1"
    params = []
    if start:
        query += " AND date(timestamp) >= ?"
        params.append(start)
    if end:
        query += " AND date(timestamp) <= ?"
        params.append(end)

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(query, params).fetchall()

    return render_template(
        "filter.html",
        rows=rows,
        start=start or "...",
        end=end or "..."
    )

@app.route("/export")
def export_excel():
    """Експортує всі заявки у файл Excel."""
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT name, address, contact, phone, timestamp FROM submissions"
        ).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Заявки"
    # Заголовки
    ws.append(["ПІБ", "Адреса", "Телефон", "WhatsApp", "Час"])
    for row in rows:
        ws.append(row)

    file_path = "submissions_export.xlsx"
    wb.save(file_path)

    flash("✅ Файл експортовано успішно!", "success")
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)