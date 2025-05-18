from flask import Flask
import threading
import time
from datetime import datetime
import pytz
import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# ==============================
# 📦 環境変数読み込み
# ==============================
load_dotenv()
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")
APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

# ==============================
# 🌍 日本時間の設定
# ==============================
JST = pytz.timezone("Asia/Tokyo")
TARGET_HOUR = 7
TARGET_MINUTE_RANGE = range(0, 5)  # 7:00~7:04の間に一度だけ送信

# ==============================
# 📡 Flask Web Server
# ==============================
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ SUNABACO イベント通知Bot稼働中"

# ==============================
# ✉️ メール送信処理
# ==============================
def send_event_info():
    url = "https://sunabaco.com/event/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    event_links = soup.find_all("a", href=True)
    seen_links = set()
    event_text_list = []

    for link in event_links:
        href = link["href"]
        if href in seen_links or not href.startswith("https://sunabaco.com/event/"):
            continue
        seen_links.add(href)

        card = link.find("div", class_="eventCard")
        if not card:
            continue

        title_tag = card.find("h4", class_="eventCard__name")
        date_tag = card.find("span", class_="eventCard__date")
        if not title_tag or not date_tag:
            continue

        title = title_tag.text.strip()
        date = date_tag.text.strip()

        time_text = ""
        try:
            detail_response = requests.get(href)
            detail_soup = BeautifulSoup(detail_response.text, "html.parser")
            time_tag = detail_soup.find("p", class_="eventTime")
            if time_tag:
                time_text = time_tag.text.strip()
        except Exception:
            time_text = "時間取得失敗"

        event_text = f"\ud83d\udcc5 {title}（{date}）\n\ud83d\udd52 {time_text}\n\ud83d\udd17 {href}"
        event_text_list.append(event_text)

    event_info = "\ud83d\udce9 今日のSUNABACOイベント情報\n\n" + "\n\n".join(event_text_list)

    message = MIMEMultipart()
    message["Subject"] = "\ud83c\udf1e SUNABACOイベント情報"
    message["From"] = SENDER_EMAIL
    message["To"] = RECEIVER_EMAIL
    message.attach(MIMEText(event_info, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(message)
        print("✅ メール送信完了")

# ==============================
# ⏰ 毎分チェック → 時間一致時に一度だけ送信
# ==============================
SENT_FLAG = False

def monitor_time():
    global SENT_FLAG
    while True:
        now = datetime.now(JST)
        if now.hour == TARGET_HOUR and now.minute in TARGET_MINUTE_RANGE:
            if not SENT_FLAG:
                print("\u23f3 時間になったので送信処理を開始します")
                send_event_info()
                SENT_FLAG = True
        else:
            SENT_FLAG = False  # 時間外になったらフラグリセット
        time.sleep(10)

# ==============================
# 🧵 Flask + 時間監視 並列実行
# ==============================
def start():
    threading.Thread(target=monitor_time).start()
    app.run(host="0.0.0.0", port=8080)

start()