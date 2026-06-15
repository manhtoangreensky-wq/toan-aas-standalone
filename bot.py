import telebot
import sqlite3
import time
from config import settings

# Sếp thay Token Bot của sếp vào đây (Lấy từ @BotFather trên Telegram)
BOT_TOKEN = "ĐIỀN_TOKEN_BOT_CỦA_SẾP_VÀO_ĐÂY"
bot = telebot.TeleBot(BOT_TOKEN)

# Kết nối thẳng vào chung Database của Web
def get_db():
    return sqlite3.connect("toanaas.db", check_same_thread=False)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🚀 Xin chào Sếp! Tôi là Trợ lý ảo của TOAN AAS OS.\n\nSếp có thể dùng các lệnh sau:\n/kpi - Xem tổng doanh thu & khách hàng\n/khachhang - Xem 5 khách hàng mới nhất")

@bot.message_handler(commands=['kpi'])
def kpi_report(message):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM erp_customers")
        total_kh = c.fetchone()[0]
        
        c.execute("SELECT SUM(amount) FROM payos_orders WHERE status='PAID'")
        total_doanhthu = c.fetchone()[0] or 0
        
        report = f"📊 BÁO CÁO NHANH TOAN AAS:\n\n👥 Tổng khách hàng: {total_kh}\n💰 Doanh thu PayOS: {total_doanhthu:,} VNĐ"
        bot.reply_to(message, report)
    except Exception as e:
        bot.reply_to(message, "Lỗi khi lấy dữ liệu!")

@bot.message_handler(commands=['khachhang'])
def recent_customers(message):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT name, phone, type FROM erp_customers ORDER BY id DESC LIMIT 5")
        rows = c.fetchall()
        
        if not rows:
            bot.reply_to(message, "Chưa có khách hàng nào trong hệ thống ERP.")
            return
            
        msg = "👥 5 KHÁCH HÀNG MỚI NHẤT:\n\n"
        for r in rows:
            msg += f"- {r[0]} ({r[1]}) | Trạng thái: {r[2]}\n"
            
        bot.reply_to(message, msg)
    except Exception as e:
        bot.reply_to(message, "Lỗi truy xuất dữ liệu!")

print("🤖 Bot Telegram TOAN AAS đang chạy...")
bot.infinity_polling()