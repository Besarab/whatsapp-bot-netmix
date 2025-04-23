from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, send_file, render_template, redirect, url_for, flash
from twilio.rest import Client
import sqlite3
import openpyxl
from datetime import datetime
import os
import webbrowser
import threading

app = Flask(__name__, template_folder="templates")
app.secret_key = "supersecretkey"


ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_WHATSAPP = "whatsapp:+14155238886"
client = Client(ACCOUNT_SID, AUTH_TOKEN)

sessions = {}

def init_db():
    with sqlite3.connect("submissions.db") as conn:
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
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From')
    print(f"🔔 Повідомлення від {from_number}: {incoming_msg}")

    lower_msg = incoming_msg.lower()

    if "заявка" in lower_msg:
        reply = (
            "📋 Надішліть нам заявку у форматі:\n"
            "`ПІБ, адреса, телефон`\n"
            "Приклад:\n"
            "Нікітюк Олексій, вул. Центральна 10, 093-123-45-67"
        )

    elif "," in incoming_msg:
        parts = incoming_msg.split(",")
        if len(parts) == 3:
            name = parts[0].strip()
            address = parts[1].strip()
            contact = parts[2].strip()
            with sqlite3.connect("submissions.db") as conn:
                conn.execute("""
                    INSERT INTO submissions (phone, name, address, contact)
                    VALUES (?, ?, ?, ?)
                """, (from_number, name, address, contact))
            flash("✅ Заявка прийнята та збережена!", "success")
            reply = "✅ Заявку збережено. Дякуємо! Ви можете перевірити свою заявку в інтерфейсі за адресою: http://127.0.0.1:5000/"
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
            "Ви також можете зателефонувати: +380-XX-XXX-XXXX"
        )

    else:
        reply = (
            "👋 Вітаю! Я чат-бот компанії *Netmix*.\n"
            "Ось чим можу допомогти:\n"
            "- *підключення* — дізнатися варіанти\n"
            "- *заявка* — залишити заявку\n"
            "- *faq* — часті питання\n"
            "- *оператор* — зв'язок з підтримкою"
        )

    client.messages.create(
        body=reply,
        from_=FROM_WHATSAPP,
        to=from_number
    )

    return "OK", 200

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/export")
def export_excel():
    conn = sqlite3.connect("submissions.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, address, contact, phone, timestamp FROM submissions")
    rows = cursor.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Заявки"
    ws.append(["ПІБ", "Адреса", "Телефон", "Номер WhatsApp", "Час"])
    for row in rows:
        ws.append(row)
    file_path = "submissions_export.xlsx"
    wb.save(file_path)
    flash("✅ Файл експортовано успішно!", "success")
    return send_file(file_path, as_attachment=True)

@app.route("/filter")
def filter_table():
    start = request.args.get("start")
    end = request.args.get("end")
    query = "SELECT name, address, contact, phone, timestamp FROM submissions WHERE 1=1"
    params = []
    if start:
        query += " AND date(timestamp) >= ?"
        params.append(start)
    if end:
        query += " AND date(timestamp) <= ?"
        params.append(end)
    conn = sqlite3.connect("submissions.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return render_template("filter.html", rows=rows, start=start or "...", end=end or "...")

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    threading.Timer(1.25, open_browser).start()
    app.run(host="0.0.0.0", port=10000)