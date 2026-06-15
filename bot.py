"""
╔══════════════════════════════════════════════════════════════════╗
║   TOAN AAS BOT V16.0 - TELEGRAM SUPER BOT                        ║
║   Đồng bộ 100% Database với Web App (Dùng chung Ví Xu)           ║
║   Tích hợp Menu chuẩn 12 Nút & Translation Hub                   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import os
import logging
from datetime import datetime

# Đọc Token từ biến môi trường của hệ thống
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", os.environ.get("BOT_TOKEN", ""))
bot = telebot.TeleBot(BOT_TOKEN)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TOAN_AAS_BOT")

# Cấu hình Admin
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", os.environ.get("ADMIN_ID", "0"))
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip().isdigit()]

# Web App URL (Để bot điều hướng khách sang Web)
WEB_URL = os.environ.get("PUBLIC_BASE_URL", "https://app.toanaas.vn")

# ==========================================
# 1. KẾT NỐI DATABASE CHUNG VỚI WEB
# ==========================================
def get_db():
    return sqlite3.connect("toanaas.db", check_same_thread=False)

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def init_bot_db():
    conn = get_db()
    c = conn.cursor()
    # Bảng Users dùng chung với Web
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT PRIMARY KEY, username TEXT, credits INTEGER DEFAULT 0, 
                 role TEXT DEFAULT 'user', created_at TEXT)''')
    conn.commit()
    conn.close()

init_bot_db()

def create_or_get_user(user_id: str, username: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT credits, role FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row:
        conn.close()
        return row[0], row[1]
    
    # User mới tinh -> Tặng 20 Xu trải nghiệm
    role = 'admin' if int(user_id) in ADMIN_IDS else 'user'
    initial_credits = 999999 if role == 'admin' else 20 
    
    c.execute("INSERT INTO users (user_id, username, credits, role, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, username, initial_credits, role, now_text()))
    conn.commit()
    conn.close()
    return initial_credits, role

# ==========================================
# 2. KHỞI TẠO MENU CHUẨN THEO HÌNH ẢNH SẾP GỬI
# ==========================================
def get_main_menu(user_id: int):
    markup = InlineKeyboardMarkup()
    
    # Dòng 1
    markup.row(
        InlineKeyboardButton("🆓 Công cụ miễn phí", callback_data="menu_free"),
        InlineKeyboardButton("👤 Tài khoản", callback_data="menu_account")
    )
    # Dòng 2
    markup.row(
        InlineKeyboardButton("🖼 Tạo ảnh AI", callback_data="menu_image"),
        InlineKeyboardButton("🎬 Tạo video AI", callback_data="menu_video")
    )
    # Dòng 3 (Đã tách Dịch thuật thành Hub riêng)
    markup.row(
        InlineKeyboardButton("📝 Ghi chú / Tài liệu", callback_data="menu_docs"),
        InlineKeyboardButton("🌐 Dịch thuật", callback_data="menu_translation_hub")
    )
    # Dòng 4
    markup.row(
        InlineKeyboardButton("🎤 Voice / Nhạc", callback_data="menu_voice"),
        InlineKeyboardButton("💰 Nạp Xu / Bảng giá", callback_data="menu_topup")
    )
    # Dòng 5
    markup.row(
        InlineKeyboardButton("📚 Hướng dẫn", callback_data="menu_guide"),
        InlineKeyboardButton("👨‍💻 Hỗ trợ", callback_data="menu_support")
    )
    # Dòng 6
    markup.row(
        InlineKeyboardButton("💬 Góp ý / Báo lỗi", callback_data="menu_feedback"),
        InlineKeyboardButton("🌐 Hub", url=WEB_URL)
    )
    
    # Dòng 7: Chỉ hiển thị nút Admin nếu là Sếp
    if user_id in ADMIN_IDS:
        markup.row(InlineKeyboardButton("🔐 Admin Control", callback_data="menu_admin"))
        
    return markup

# Menu Hub Dịch Thuật
def get_translation_hub_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📝 Dịch Văn Bản", callback_data="trans_text"))
    markup.row(InlineKeyboardButton("🎬 Dịch / Lồng tiếng Video", callback_data="trans_video"))
    markup.row(InlineKeyboardButton("📄 Dịch File / Document", callback_data="trans_file"))
    markup.row(InlineKeyboardButton("🔙 Quay lại Menu Chính", callback_data="back_to_main"))
    return markup

# ==========================================
# 3. LỆNH START VÀ XỬ LÝ NÚT BẤM (CALLBACK)
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.chat.id)
    username = message.from_user.first_name or "Khách hàng"
    
    # Khởi tạo user & Lấy Xu
    credits, role = create_or_get_user(user_id, username)
    
    welcome_text = (
        f"🚀 Xin chào <b>{username}</b>! Chào mừng bạn đến với TOAN AAS OS.\n\n"
        f"💡 Hệ sinh thái AI & Quản trị Doanh nghiệp All-in-One.\n"
        f"💳 Số dư hiện tại của bạn: <b>{credits} Xu</b>\n\n"
        f"Vui lòng chọn tính năng bên dưới để bắt đầu:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=get_main_menu(message.chat.id))

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = str(call.message.chat.id)
    
    if call.data == "back_to_main":
        bot.edit_message_text(
            "🏠 <b>Menu Chính TOAN AAS OS</b>\nChọn tính năng bạn muốn sử dụng:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=get_main_menu(call.message.chat.id)
        )
        
    elif call.data == "menu_account":
        credits, role = create_or_get_user(user_id, "Unknown")
        role_name = "👑 ADMIN" if role == 'admin' else "👤 Member"
        text = f"💳 <b>TÀI KHOẢN CỦA BẠN</b>\n\n🆔 ID: <code>{user_id}</code>\n🪙 Số dư: <b>{credits} Xu</b>\n🎖 Cấp bậc: {role_name}\n\n👉 Truy cập Web App để xem lịch sử chi tiết: {WEB_URL}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode="HTML")

    # XỬ LÝ HUB DỊCH THUẬT (Đúng như Sếp dặn)
    elif call.data == "menu_translation_hub":
        bot.edit_message_text(
            "🌐 <b>TRUNG TÂM DỊCH THUẬT AI (HUB)</b>\n\nVui lòng chọn loại định dạng bạn muốn dịch:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=get_translation_hub_menu()
        )
        
    elif call.data == "menu_admin":
        # Khúc này lấy KPI từ Database cho Sếp
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            total_users = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM erp_customers")
            total_leads = c.fetchone()[0]
            conn.close()
            
            text = f"🔐 <b>BÁO CÁO ADMIN</b>\n\n👥 Tổng User Bot: {total_users}\n🎯 Khách hàng CRM: {total_leads}\n\nSếp vui lòng truy cập Trang Quản trị: {WEB_URL}/admin-app để xem full 19 Module."
            bot.send_message(call.message.chat.id, text, parse_mode="HTML")
        except:
            bot.send_message(call.message.chat.id, "Lỗi truy xuất Database.")
            
    elif call.data == "menu_topup":
        text = f"💰 <b>NẠP XU TỰ ĐỘNG</b>\n\nHệ thống hỗ trợ nạp Xu bằng QR Code (PayOS) siêu tốc.\n\n👉 Vui lòng truy cập Web App để lấy mã QR Nạp Xu: {WEB_URL}"
        bot.send_message(call.message.chat.id, text, parse_mode="HTML")

    # CÁC TÍNH NĂNG ĐIỀU HƯỚNG SANG WEB
    elif call.data in ["menu_video", "menu_image", "menu_voice", "menu_docs"]:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"🚀 Tính năng này đã được nâng cấp với giao diện xịn sò trên Web App!\n\n👉 Hãy bấm vào đây để sử dụng: {WEB_URL}")

    else:
        bot.answer_callback_query(call.id, "Tính năng đang được cập nhật!")

# Chạy Bot
if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("LỖI: Chưa có BOT_TOKEN trong biến môi trường!")
    else:
        logger.info("🤖 TOAN AAS TELEGRAM BOT STARTED SUCCESSFULLY!")
        bot.infinity_polling()