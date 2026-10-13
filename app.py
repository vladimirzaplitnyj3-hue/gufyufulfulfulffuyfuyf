# ============================================================
# KRANZAYY | METRO SHOP BOT — ФИНАЛЬНАЯ ВЕРСИЯ v18
# Полностью переработан: приоритет в очереди, ссылки на оплату,
# кнопка "Команда свободна", premium emoji везде
# ============================================================

import requests
import json
import time
import logging
import sys
import traceback
import datetime
import re
import socket

# ============================================================
# ЛОГИРОВАНИЕ
# ============================================================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# КОНФИГ
# ============================================================
BOT_TOKEN = "8912094394:AAE7myoYE7CbVWFWRljAbrKDG-mxEVfitK4"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
OWNER_ID = 6555825110
MANAGER_LINK = "https://t.me/Manager_Kranzayy"
GROUP_ID = -1004386531637
REVIEWS_CHANNEL = -1004303735760
PHOTO_URL = "https://i.ibb.co/kVCDv7Rg/IMG-3261.jpg"
PHOTO_FILE_ID = None

PAY_PHONE = "+7 952 321-66-09"
PAY_CARD = "2202208555983213"

# Ссылка на оплату приоритета (пока заглушка, замените позже)
PAY_LINK_PRIORITY = "https://t.me/Manager_Kranzayy"
# Ссылка на оплату обычной покупки
PAY_LINK_NORMAL = "https://t.me/Manager_Kranzayy"

RECONNECT_MIN = 5
RECONNECT_MAX = 300
MAX_PARTICIPANTS = 4

# ============================================================
# ПРЕМИУМ-ЭМОДЗИ
# ============================================================
E_MENU      = "5231235536206730707"
E_SHOP      = "5278702045883292456"
E_STAR1     = "5330051403563943171"
E_STAR2     = "5330245862503236304"
E_STAR3     = "5327866716909229540"
E_ARROW     = "5219793421207629443"
E_CHECK     = "5219809810802829750"
E_CROSS     = "5219835361563275589"
E_INFO      = "5285430309720966085"
E_TIME      = "5310169226856644648"
E_USER      = "5316970857325687050"
E_MONEY     = "5219714093161671306"
E_RUB       = "5219983482100412686"
E_PRICE     = "5219919637411556483"
E_HEART     = "5346301287774323405"
E_DIAMOND   = "5465556444931718975"
E_BAG       = "5431406343917414987"
E_BOX       = "5429424809215797643"
E_FIRE      = "5346301287774323405"
E_WAIT      = "5310169226856644648"
E_STAR      = "5330051403563943171"
E_LOCK      = "5316970857325687050"
E_CROWN     = "5465556444931718975"
E_ROCKET    = "5474525938668550110"
E_MAP       = "5278702045883292456"
E_LAPTOP    = "5285430309720966085"
E_SMILE     = "5330245862503236304"

BTN_SUPPORT = "5269762028506989874"
BTN_KITS    = "5429424809215797643"
BTN_LOOT    = "5431406343917414987"
BTN_BOOST   = "5474525938668550110"
BTN_RULES   = "5346066344473297711"
BTN_PERKS   = "5474196218324228716"
BTN_REVIEWS = "5348035702942632055"
BTN_BOOST_PRICE = "5231102735817918643"

# ============================================================
# ХРАНИЛИЩЕ
# ============================================================
user_data = {}
orders = {}
orders_counter = [0]
group_messages = {}
review_pending = {}
awaiting_qr_from_admin = {}

# Очередь приоритетов: {item_key: [user_id1, user_id2, ...]}
priority_queue = {}
# Все ожидающие (обычная покупка): {item_key: [user_id1, ...]}
normal_queue = {}
# Статус приоритета для заказов
priority_status = {}  # pid -> True/False

# ============================================================
# ЭМОДЗИ-ХЕЛПЕРЫ
# ============================================================
def em(eid, fallback="⭐"):
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'

def stars_row():
    return f'{em(E_STAR1, "⭐")}{em(E_STAR2, "✨")}{em(E_STAR2, "✨")}{em(E_STAR3, "💫")}'

def arrows_row(n=6):
    return em(E_ARROW, "➡️") * n

# ============================================================
# УТИЛИТЫ
# ============================================================
def strip_html(text):
    return re.sub(r'<[^>]+>', '', text)

def check_internet():
    try:
        socket.gethostbyname("api.telegram.org")
        return True
    except:
        return False

def api_request(method, payload, timeout=30, retries=2):
    url = f"{BASE_URL}/{method}"
    for attempt in range(retries):
        try:
            r = requests.post(url, json=payload, timeout=timeout).json()
            if not r.get("ok"):
                logger.error(f"❌ {method}: {r.get('description')}")
                if r.get("error_code", 0) in (400, 403):
                    return r
            return r
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                logger.error(f"🔌 {method}: сбой")
                return {"ok": False, "error": str(e)}
        except Exception as e:
            logger.error(f"💥 {method}: {e}")
            return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "max_retries"}

def send_safe(chat_id, text, reply_markup=None):
    p = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        p["reply_markup"] = json.dumps(reply_markup)
    r = api_request("sendMessage", p)
    if r.get("ok"):
        return r
    p2 = {"chat_id": chat_id, "text": strip_html(text)}
    if reply_markup:
        p2["reply_markup"] = json.dumps(reply_markup)
    return api_request("sendMessage", p2)

def send_photo_safe(chat_id, photo, caption=None, reply_markup=None):
    p = {"chat_id": chat_id, "photo": photo, "parse_mode": "HTML"}
    if caption:
        p["caption"] = caption
    if reply_markup:
        p["reply_markup"] = json.dumps(reply_markup)
    r = api_request("sendPhoto", p)
    if r.get("ok"):
        return r
    if caption:
        p2 = {"chat_id": chat_id, "photo": photo, "caption": strip_html(caption)}
        if reply_markup:
            p2["reply_markup"] = json.dumps(reply_markup)
        return api_request("sendPhoto", p2)
    return r

def edit_safe(chat_id, message_id, text, reply_markup=None):
    p = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        p["reply_markup"] = json.dumps(reply_markup)
    r = api_request("editMessageText", p)
    if r.get("ok"):
        return r
    p2 = {"chat_id": chat_id, "message_id": message_id, "text": strip_html(text)}
    if reply_markup:
        p2["reply_markup"] = json.dumps(reply_markup)
    return api_request("editMessageText", p2)

def answer_callback(cb_id, text=None, alert=False):
    p = {"callback_query_id": cb_id}
    if text:
        p["text"] = text
    if alert:
        p["show_alert"] = True
    return api_request("answerCallbackQuery", p)

def delete_message(chat_id, message_id):
    return api_request("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

def get_username(chat_id):
    try:
        r = api_request("getChat", {"chat_id": chat_id}, retries=1)
        if r.get("ok"):
            u = r["result"]
            return u.get("username") or u.get("first_name", "Пользователь")
    except:
        pass
    return "Пользователь"

def get_full_name(chat_id):
    try:
        r = api_request("getChat", {"chat_id": chat_id}, retries=1)
        if r.get("ok"):
            u = r["result"]
            fn = u.get("first_name", "")
            ln = u.get("last_name", "")
            res = f"{fn} {ln}".strip()
            return res if res else "Пользователь"
    except:
        pass
    return "Пользователь"

def gen_order_id():
    orders_counter[0] += 1
    return f"ORD{int(time.time())}_{orders_counter[0]}"

def remember_message(user_id, message_id):
    uid = str(user_id)
    if uid not in user_data:
        user_data[uid] = {}
    user_data[uid]["last_msg_id"] = message_id

def clear_last_message(user_id):
    uid = str(user_id)
    last_id = user_data.get(uid, {}).get("last_msg_id")
    if last_id:
        delete_message(user_id, last_id)
    if uid in user_data:
        user_data[uid]["last_msg_id"] = None

# ============================================================
# ЛОГИКА ОЧЕРЕДИ
# ============================================================

def add_to_priority(item_key, user_id, username):
    """Добавляет пользователя в очередь приоритета"""
    if item_key not in priority_queue:
        priority_queue[item_key] = []
    # Проверка на дубликат
    if any(u["id"] == user_id for u in priority_queue[item_key]):
        return
    priority_queue[item_key].append({"id": user_id, "username": username})

def add_to_normal(item_key, user_id, username):
    """Добавляет пользователя в обычную очередь"""
    if item_key not in normal_queue:
        normal_queue[item_key] = []
    if any(u["id"] == user_id for u in normal_queue[item_key]):
        return
    normal_queue[item_key].append({"id": user_id, "username": username})

def get_queue_info(item_key, user_id):
    """Возвращает (перед, после, всего) для юзера"""
    prio = priority_queue.get(item_key, [])
    norm = normal_queue.get(item_key, [])
    
    # Индекс юзера в приоритете
    prio_idx = next((i for i, u in enumerate(prio) if u["id"] == user_id), None)
    
    if prio_idx is not None:
        before = prio_idx
        # После него в приоритете + вся обычная очередь
        after = (len(prio) - prio_idx - 1) + len(norm)
        return before, after, len(prio) + len(norm)
    
    # Юзер в обычной очереди
    norm_idx = next((i for i, u in enumerate(norm) if u["id"] == user_id), None)
    if norm_idx is not None:
        # Перед ним: все из приоритета + те кто в обычной раньше
        before = len(prio) + norm_idx
        after = len(norm) - norm_idx - 1
        return before, after, len(prio) + len(norm)
    
    return 0, 0, len(prio) + len(norm)

# ============================================================
# ТЕКСТЫ
# ============================================================

MAIN_CAPTION = (
    f'{em(E_MENU, "🎁")} <b>Добро пожаловать в бота !!!</b>\n'
    f'{em(E_SHOP, "🏪")} • <b>Kranzayy | Metro Shop</b>\n\n'
    f'{stars_row()}\n\n'
    f'<b>Можете пользоваться навигацией ниже</b>\n\n'
    f'{arrows_row()}'
)

KITS_TEXT = (
    f'{em(E_BOX, "📦")} <b>КОМПЛЕКТЫ</b>\n\n'
    f'{em(E_STAR, "⭐")} 1 день — 1 шестая шмотка — 7₽\n'
    f'{em(E_STAR, "⭐")} 2 день — 1 шестая шмотка — 5₽\n'
    f'{em(E_STAR, "⭐")} 3-7 день — 1 шестая шмотка — 4₽\n'
    f'{em(E_STAR, "⭐")} 2-3 неделя — 1 шестая шмотка — 3₽\n\n'
    f'{em(E_INFO, "ℹ️")} В шестую шмотку входит:\n'
    f'{em(E_INFO, "ℹ️")} хотите купить — @Manager_Kranzayy'
)

LOOT_TEXT = (
    f'{em(E_BAG, "🎒")} <b>СКУПКА ЛУТА</b>\n\n'
    f'{em(E_STAR, "⭐")} 1 день — 1 шестая шмотка — 7₽\n'
    f'{em(E_STAR, "⭐")} 2 день — 1 шестая шмотка — 5₽\n'
    f'{em(E_STAR, "⭐")} 3-7 день — 1 шестая шмотка — 4₽\n'
    f'{em(E_STAR, "⭐")} 2-3 неделя — 1 шестая шмотка — 3₽\n\n'
    f'{em(E_INFO, "ℹ️")} Если хотите купить — @Manager_Kranzayy'
)

SUPPORT_DESCRIPTIONS = {
    "default": (
        f"{em(E_CHECK, '✅')} <b>СОПРОВОЖДЕНИЕ</b>\n\n"
        f"{em(E_DIAMOND, '💎')} гарант: 10.000.000\n\n"
        f"{em(E_BOX, '📦')} Вещи с типов ваши\n\n"
        f"{em(E_MONEY, '💳')} карта: 7-ая\n\n"
        f"{em(E_LOCK, '🔒')} гарант вещей: 5\n\n"
        f"{em(E_BOX, '📦')} Выдача: ф6 сета с мк ВК\n\n"
        f"{em(E_INFO, 'ℹ️')} Если с вас снимают, не возвращаем\n\n"
        f"{em(E_PRICE, '💵')} цена — 100₽"
    ),
    "vip": (
        f"{em(E_CHECK, '✅')} <b>СОПРОВОЖДЕНИЕ</b>\n\n"
        f"{em(E_DIAMOND, '💎')} гарант: 15.000.000\n\n"
        f"{em(E_BOX, '📦')} Вещи с типов ваши\n\n"
        f"{em(E_MONEY, '💳')} карта: 7-ая\n\n"
        f"{em(E_LOCK, '🔒')} гарант вещей: 7\n\n"
        f"{em(E_BOX, '📦')} Выдача: ф6 сета с мк ВК\n\n"
        f"{em(E_INFO, 'ℹ️')} Если с вас снимают, не возвращаем\n\n"
        f"{em(E_PRICE, '💵')} цена — 150₽"
    ),
    "elite": (
        f"{em(E_CROWN, '👑')} <b>СОПРОВОЖДЕНИЕ НА 7 КАРТУ</b>\nНА 21.000.000\n\n"
        f"{em(E_CHECK, '✅')} в него входит:\n\n"
        f"{em(E_BOX, '📦')} в начале выдаем ф6 сета с мк ВК\n"
        f"{em(E_DIAMOND, '💎')} гарант выноса 21.000.000\n"
        f"{em(E_LOCK, '🔒')} гарант вещей 15 штук\n"
        f"{em(E_CHECK, '✅')} если снимают, возвращаем\n\n"
        f"{em(E_PRICE, '💵')} цена — 290₽"
    ),
    "oligarch": (
        f"{em(E_CROWN, '👑')} <b>СОПРОВОЖДЕНИЕ</b>\n\n"
        f"{em(E_DIAMOND, '💎')} гарант: 35.000.000\n\n"
        f"{em(E_BOX, '📦')} Вещи с типов ваши\n\n"
        f"{em(E_MONEY, '💳')} карта: 7-ая\n\n"
        f"{em(E_LOCK, '🔒')} гарант вещей: 20\n\n"
        f"{em(E_BOX, '📦')} Выдача: ф6 сета с мк ВК\n\n"
        f"{em(E_PRICE, '💵')} цена — 359₽"
    ),
    "default_plus": (
        f"{em(E_STAR, '⭐')} <b>СОПРОВОЖДЕНИЕ НА 7 КАРТУ</b>\nНА 10.000.000\n\n"
        f"{em(E_CHECK, '✅')} в него входит:\n\n"
        f"{em(E_BOX, '📦')} в начале выдаем ф6 сета с мк ВК\n"
        f"{em(E_DIAMOND, '💎')} гарант выноса 10.000.000\n"
        f"{em(E_LOCK, '🔒')} гарант вещей 7 штук\n"
        f"{em(E_CHECK, '✅')} если снимают, возвращаем\n\n"
        f"{em(E_PRICE, '💵')} цена — 150₽"
    ),
    "vip_plus": (
        f"{em(E_STAR, '⭐')} <b>СОПРОВОЖДЕНИЕ НА 7 КАРТУ</b>\nНА 15.000.000\n\n"
        f"{em(E_CHECK, '✅')} в него входит:\n\n"
        f"{em(E_BOX, '📦')} в начале выдаем ф6 сета с мк ВК\n"
        f"{em(E_DIAMOND, '💎')} гарант выноса 15.000.000\n"
        f"{em(E_LOCK, '🔒')} гарант вещей 12 штук\n"
        f"{em(E_CHECK, '✅')} если снимают, возвращаем\n\n"
        f"{em(E_PRICE, '💵')} цена — 210₽"
    ),
    "elite_plus": (
        f"{em(E_STAR, '⭐')} <b>СОПРОВОЖДЕНИЕ НА 7 КАРТУ</b>\nНА 21.000.000\n\n"
        f"{em(E_CHECK, '✅')} в него входит:\n\n"
        f"{em(E_BOX, '📦')} в начале выдаем ф6 сета с мк ВК\n"
        f"{em(E_DIAMOND, '💎')} гарант выноса 21.000.000\n"
        f"{em(E_LOCK, '🔒')} гарант вещей 15 штук\n"
        f"{em(E_CHECK, '✅')} если снимают, возвращаем\n\n"
        f"{em(E_PRICE, '💵')} цена — 290₽"
    ),
    "oligarch_plus": (
        f"{em(E_STAR, '⭐')} <b>СОПРОВОЖДЕНИЕ НА 7 КАРТУ</b>\nНА 35.000.000\n\n"
        f"{em(E_CHECK, '✅')} в него входит:\n"
        f"{em(E_BOX, '📦')} в начале выдаем ф6 сета с мк ВК\n"
        f"{em(E_DIAMOND, '💎')} гарант выноса 35.000.000\n"
        f"{em(E_LOCK, '🔒')} гарант вещей 20 штук\n"
        f"{em(E_CHECK, '✅')} Если с вас снимают, возвращаем\n\n"
        f"{em(E_PRICE, '💵')} цена — 425₽"
    ),
    "default_pro": (
        f"{em(E_ROCKET, '🚀')} <b>ДЕФОЛТ ПРО СОПРОВОЖДЕНИЕ</b>\n\n"
        f"{em(E_BOX, '📦')} выдаем: ф6 сета с мк ВК\n"
        f"{em(E_CHECK, '✅')} если снимают, возвращаем\n\n"
        f"{em(E_LOCK, '🔒')} <b>ГАРАНТЫ</b>\n\n"
        f"{em(E_BOX, '📦')} гарант вещей — 10 шт.\n"
        f"{em(E_BAG, '🎒')} гарант билетов — 4 шт.\n"
        f"{em(E_DIAMOND, '💎')} гарант выноса — 10кк.\n\n"
        f"{em(E_PRICE, '💵')} цена — 225₽"
    ),
    "vip_pro": (
        f"{em(E_ROCKET, '🚀')} <b>ВИП ПРО СОПРОВОЖДЕНИЕ</b>\n\n"
        f"{em(E_BOX, '📦')} выдаем: ф6 сета с мк ВК\n"
        f"{em(E_CHECK, '✅')} если снимают, возвращаем\n\n"
        f"{em(E_LOCK, '🔒')} <b>ГАРАНТЫ</b>\n\n"
        f"{em(E_BOX, '📦')} гарант вещей — 15 шт.\n"
        f"{em(E_BAG, '🎒')} гарант билетов — 6 шт.\n"
        f"{em(E_DIAMOND, '💎')} гарант выноса — 15кк.\n\n"
        f"{em(E_PRICE, '💵')} цена — 289₽"
    ),
    "elite_pro": (
        f"{em(E_ROCKET, '🚀')} <b>ЭЛИТ ПРО СОПРОВОЖДЕНИЕ</b>\n\n"
        f"{em(E_BOX, '📦')} выдаем: ф6 сета с мк ВК\n"
        f"{em(E_CHECK, '✅')} если снимают, возвращаем\n\n"
        f"{em(E_LOCK, '🔒')} <b>ГАРАНТЫ</b>\n\n"
        f"{em(E_BOX, '📦')} гарант вещей — 21 шт.\n"
        f"{em(E_BAG, '🎒')} гарант билетов — 8 шт.\n"
        f"{em(E_DIAMOND, '💎')} гарант выноса — 21кк.\n\n"
        f"{em(E_PRICE, '💵')} цена — 369₽"
    ),
    "oligarch_pro": (
        f"{em(E_CROWN, '👑')} <b>ОЛИГАРХ ПРО СОПРОВОЖДЕНИЕ</b>\n\n"
        f"{em(E_BOX, '📦')} выдаем: ф6 сета с мк ВК\n"
        f"{em(E_CHECK, '✅')} если снимают, возвращаем\n\n"
        f"{em(E_LOCK, '🔒')} <b>ГАРАНТЫ</b>\n\n"
        f"{em(E_BOX, '📦')} гарант вещей — 30 шт.\n"
        f"{em(E_BAG, '🎒')} гарант билетов — 12 шт.\n"
        f"{em(E_DIAMOND, '💎')} гарант выноса — 35кк.\n\n"
        f"{em(E_PRICE, '💵')} цена — 529₽"
    ),
}

SUPPORT_BUTTONS = [
    ("default",       "10кк | Дефолт (7 карта) — 100₽",  "success", E_CHECK),
    ("vip",           "15кк | Вип (7 карта) — 150₽",      "success", E_CHECK),
    ("elite",         "21кк | Элит (7 карта) — 290₽",     "success", E_CHECK),
    ("oligarch",      "35кк | Олигарх (7 карта) — 359₽",  "success", E_CHECK),
    ("default_plus",  "10кк | Дефолт+ (7 карта) — 150₽",  "primary", E_STAR),
    ("vip_plus",      "15кк | Вип+ (7 карта) — 210₽",     "primary", E_STAR),
    ("elite_plus",    "21кк | Элит+ (7 карта) — 290₽",    "primary", E_STAR),
    ("oligarch_plus", "35кк | Олигарх+ (7 карта) — 425₽", "primary", E_STAR),
    ("default_pro",   "10кк | Дефолт ПРО (7 карта) — 225₽","danger", E_ROCKET),
    ("vip_pro",       "15кк | Вип ПРО (7 карта) — 289₽",   "danger", E_ROCKET),
    ("elite_pro",     "21кк | Элит ПРО (7 карта) — 369₽",  "danger", E_ROCKET),
    ("oligarch_pro",  "35кк | Олигарх ПРО (7 карта) — 529₽","danger", E_CROWN),
]

BOOST_PRICES = [
    ("5.000.000", 85), ("10.000.000", 145), ("15.000.000", 250),
    ("20.000.000", 310), ("25.000.000", 390), ("35.000.000", 560),
    ("50.000.000", 790), ("75.000.000", 1190), ("100.000.000", 1590),
]

SUPPORT_PRICES = {
    "default": 100, "vip": 150, "elite": 290, "oligarch": 359,
    "default_plus": 150, "vip_plus": 210, "elite_plus": 290, "oligarch_plus": 425,
    "default_pro": 225, "vip_pro": 289, "elite_pro": 369, "oligarch_pro": 529,
}

SUPPORT_NAMES = {
    "default": "ДЕФОЛТ СОПРОВОЖДЕНИЕ", "vip": "ВИП СОПРОВОЖДЕНИЕ",
    "elite": "ЭЛИТ СОПРОВОЖДЕНИЕ", "oligarch": "ОЛИГАРХ СОПРОВОЖДЕНИЕ",
    "default_plus": "ДЕФОЛТ+ СОПРОВОЖДЕНИЕ", "vip_plus": "ВИП+ СОПРОВОЖДЕНИЕ",
    "elite_plus": "ЭЛИТ+ СОПРОВОЖДЕНИЕ", "oligarch_plus": "ОЛИГАРХ+ СОПРОВОЖДЕНИЕ",
    "default_pro": "ДЕФОЛТ ПРО СОПРОВОЖДЕНИЕ", "vip_pro": "ВИП ПРО СОПРОВОЖДЕНИЕ",
    "elite_pro": "ЭЛИТ ПРО СОПРОВОЖДЕНИЕ", "oligarch_pro": "ОЛИГАРХ ПРО СОПРОВОЖДЕНИЕ",
}

# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def main_menu():
    return {"inline_keyboard": [
        [{"text": "СОПРОВОЖДЕНИЯ", "callback_data": "menu_support", "style": "success", "icon_custom_emoji_id": BTN_SUPPORT}],
        [{"text": "КОМПЛЕКТЫ", "callback_data": "menu_kits", "style": "primary", "icon_custom_emoji_id": BTN_KITS},
         {"text": "СКУПКА ЛУТА", "callback_data": "menu_loot", "style": "primary", "icon_custom_emoji_id": BTN_LOOT}],
        [{"text": "БУСТ БАЛАНСА", "callback_data": "menu_boost", "style": "success", "icon_custom_emoji_id": BTN_BOOST}],
        [{"text": "РЕГЛАМЕНТ", "url": "https://t.me/+MU3bQoEK9rUxYTIy", "style": "danger", "icon_custom_emoji_id": BTN_RULES},
         {"text": "НИШТЯКИ", "url": "https://t.me/kranzayy_nustaku", "style": "success", "icon_custom_emoji_id": BTN_PERKS}],
        [{"text": "Отзывы", "url": "https://t.me/kranzayy_OTZ", "style": "primary", "icon_custom_emoji_id": BTN_REVIEWS}],
    ]}

def support_menu():
    kb = []
    for key, text, style, icon in SUPPORT_BUTTONS:
        kb.append([{"text": text, "callback_data": f"sup_{key}", "style": style, "icon_custom_emoji_id": icon}])
    kb.append([{"text": "Назад", "callback_data": "back_main", "style": "primary", "icon_custom_emoji_id": E_CROSS}])
    return {"inline_keyboard": kb}

def boost_menu():
    kb = []
    styles = ["success", "primary", "danger"]
    for i, (a, p) in enumerate(BOOST_PRICES):
        style = styles[i % 3]
        kb.append([{"text": f"{a} — {p}₽", "callback_data": f"boost_{a}", "style": style, "icon_custom_emoji_id": E_PRICE}])
    kb.append([{"text": "Назад", "callback_data": "back_main", "style": "primary", "icon_custom_emoji_id": E_CROSS}])
    return {"inline_keyboard": kb}

def back_button(cb="back_main"):
    return {"inline_keyboard": [[{"text": "Назад", "callback_data": cb, "style": "primary", "icon_custom_emoji_id": E_CROSS}]]}

# ---------- Меню выбора способа покупки ----------
def purchase_method_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Обычная покупка", "callback_data": f"method_normal_{pid}", "style": "primary", "icon_custom_emoji_id": E_BOX}],
        [{"text": "Приоритет в очереди (+100₽)", "callback_data": f"method_priority_{pid}", "style": "success", "icon_custom_emoji_id": E_ROCKET}],
        [{"text": "Отмена", "callback_data": f"cancel_{pid}", "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

# ---------- Меню приоритета ----------
def priority_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Оплатить приоритет (+100₽)", "url": PAY_LINK_PRIORITY, "style": "success", "icon_custom_emoji_id": E_MONEY}],
        [{"text": "Что такое приоритет в очереди?", "callback_data": f"what_priority_{pid}", "style": "primary", "icon_custom_emoji_id": E_INFO}],
        [{"text": "Отмена", "callback_data": f"cancel_{pid}", "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

# ---------- Меню обычной покупки ----------
def normal_pay_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Оплатить", "url": PAY_LINK_NORMAL, "style": "success", "icon_custom_emoji_id": E_MONEY}],
        [{"text": "Отмена", "callback_data": f"cancel_{pid}", "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

# ---------- Меню ПОСЛЕ оплаты приоритета ----------
def after_priority_pay_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Купить сопровождение", "callback_data": "menu_support", "style": "success", "icon_custom_emoji_id": E_MAP}],
        [{"text": "Посмотреть очередь", "callback_data": f"view_queue_{pid}", "style": "primary", "icon_custom_emoji_id": E_INFO}],
        [{"text": "Написать", "url": MANAGER_LINK, "style": "success", "icon_custom_emoji_id": E_LAPTOP}],
        [{"text": "Ждать", "callback_data": f"wait_{pid}", "style": "danger", "icon_custom_emoji_id": E_WAIT}],
    ]}

# ---------- Меню ПОСЛЕ обычной оплаты ----------
def after_normal_pay_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Купить «Приоритет в очереди»", "callback_data": f"method_priority_{pid}", "style": "success", "icon_custom_emoji_id": E_ROCKET}],
        [{"text": "Написать", "url": MANAGER_LINK, "style": "success", "icon_custom_emoji_id": E_LAPTOP}],
        [{"text": "Ждать", "callback_data": f"wait_{pid}", "style": "danger", "icon_custom_emoji_id": E_WAIT}],
    ]}

# ---------- Меню оплаты (старое, для совместимости) ----------
def payment_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Я оплатил", "callback_data": f"paid_{pid}", "style": "success", "icon_custom_emoji_id": E_CHECK}],
        [{"text": "Не хочу оплачивать", "callback_data": f"cancel_{pid}", "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

def owner_confirm_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Да, деньги пришли", "callback_data": f"owner_yes_{pid}", "style": "success", "icon_custom_emoji_id": E_CHECK}],
        [{"text": "Нет, отменить", "callback_data": f"owner_no_{pid}", "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

def owner_done_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Заказ выполнен — Да", "callback_data": f"done_yes_{pid}", "style": "success", "icon_custom_emoji_id": E_CHECK}],
        [{"text": "Заказ выполнен — Нет", "callback_data": f"done_no_{pid}", "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

def owner_send_qr_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Отправить QR-код", "callback_data": f"send_qr_{pid}", "style": "success", "icon_custom_emoji_id": E_INFO}],
        [{"text": "Заказ выполнен — Да", "callback_data": f"done_yes_{pid}", "style": "success", "icon_custom_emoji_id": E_CHECK}],
        [{"text": "Заказ выполнен — Нет", "callback_data": f"done_no_{pid}", "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

def group_join_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Я участвую в сопровождении", "callback_data": f"join_{pid}", "style": "success", "icon_custom_emoji_id": E_USER}]
    ]}

# ---------- Кнопка "Команда свободна" для админа ----------
def owner_team_free_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Команда свободна", "callback_data": f"team_free_{pid}", "style": "success", "icon_custom_emoji_id": E_CHECK}],
        [{"text": "Заказ выполнен — Да", "callback_data": f"done_yes_{pid}", "style": "success", "icon_custom_emoji_id": E_CHECK}],
        [{"text": "Заказ выполнен — Нет", "callback_data": f"done_no_{pid}", "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

# ============================================================
# ТЕКСТ ЗАКАЗА В ГРУППЕ
# ============================================================

def build_group_text(pid):
    o = orders.get(pid, {})
    gm = group_messages.get(pid, {})
    parts = gm.get("parts", [])
    total = len(parts)
    buyer = o.get("username", "—")
    pubg = o.get("pubg_id", "—")
    item = o.get("item_name", "—")
    price = o.get("price", "—")
    
    desc = SUPPORT_DESCRIPTIONS.get(o.get("item_key"), "") if o.get("type") == "support" else ""
    
    text = (
        f'{em(E_BOX, "📦")} <b>НОВЫЙ ЗАКАЗ В СОПРОВОЖДЕНИЕ</b>\n\n'
        f'{em(E_USER, "👤")} Купил: @{buyer}\n'
        f'{em(E_USER, "🆔")} PUBG ID: <code>{pubg}</code>\n\n'
        f'{em(E_BOX, "📦")} Товар: <b>{item}</b>\n'
        f'{em(E_PRICE, "💵")} Цена: {price}₽\n\n'
    )
    
    if desc:
        text += f'{em(E_DIAMOND, "💎")} <b>Описание:</b>\n{desc}\n\n'
    
    text += f'{em(E_USER, "👥")} Участвуют: {", ".join(parts)} ({total}/{MAX_PARTICIPANTS})'
    return text

# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================

def send_main_menu(chat_id):
    global PHOTO_FILE_ID
    clear_last_message(chat_id)
    photo = PHOTO_FILE_ID or PHOTO_URL
    r = send_photo_safe(chat_id, photo, caption=MAIN_CAPTION, reply_markup=main_menu())
    if r.get("ok"):
        if not PHOTO_FILE_ID:
            try:
                PHOTO_FILE_ID = r["result"]["photo"][-1]["file_id"]
                logger.info(f'💾 PHOTO_FILE_ID = "{PHOTO_FILE_ID}"')
            except: pass
        remember_message(chat_id, r["result"]["message_id"])
    else:
        r2 = send_safe(chat_id, MAIN_CAPTION, main_menu())
        if r2.get("ok"):
            remember_message(chat_id, r2["result"]["message_id"])
    return r

def send_replacing(chat_id, text, reply_markup=None):
    clear_last_message(chat_id)
    r = send_safe(chat_id, text, reply_markup)
    if r.get("ok"):
        remember_message(chat_id, r["result"]["message_id"])
    return r

# ============================================================
# НОВАЯ ЛОГИКА ПОКУПКИ (с выбором способа)
# ============================================================

def show_purchase_method(chat_id, itype, ikey, iname, price):
    """Показывает выбор способа покупки"""
    clear_last_message(chat_id)
    pid = gen_order_id()
    orders[pid] = {
        "user_id": chat_id,
        "type": itype,
        "item_key": ikey,
        "item_name": iname,
        "price": price,
        "status": "choosing_method",
        "priority": False,
        "base_price": price
    }
    logger.info(f"🛒 {pid}: {iname} — {price}₽ — выбор способа")
    
    text = (
        f'{em(E_BOX, "📦")} <b>ВЫБЕРИТЕ СПОСОБ ПОКУПКИ</b>\n\n'
        f'{em(E_SHOP, "🏪")} Товар: <b>{iname}</b>\n'
        f'{em(E_PRICE, "💵")} Цена: <b>{price}₽</b>\n\n'
        f'{em(E_INFO, "ℹ️")} Выберите как вы хотите купить, ниже {em(E_CHECK, "✅")}\n\n'
        f'{stars_row()}'
    )
    r = send_safe(chat_id, text, purchase_method_menu(pid))
    if r.get("ok"):
        remember_message(chat_id, r["result"]["message_id"])
    return pid

def process_method_priority(chat_id, cb_id, pid):
    """Пользователь выбрал приоритет в очереди"""
    o = orders.get(pid)
    if not o:
        answer_callback(cb_id, f'{em(E_CROSS, "❌")} Заказ не найден', True)
        return
    
    o["status"] = "choosing_priority"
    o["priority"] = True
    
    text = (
        f'{em(E_ROCKET, "🚀")} <b>ПРИОРИТЕТ В ОЧЕРЕДИ</b>\n\n'
        f'{em(E_SHOP, "🏪")} Товар: <b>{o["item_name"]}</b>\n'
        f'{em(E_PRICE, "💵")} Цена: <b>{o["base_price"]}₽</b> + <b>100₽</b> (приоритет)\n'
        f'{em(E_MONEY, "💰")} Итого: <b>{o["base_price"] + 100}₽</b>\n\n'
        f'{em(E_INFO, "ℹ️")} Выберите действие\n\n'
        f'{stars_row()}'
    )
    
    clear_last_message(chat_id)
    r = send_safe(chat_id, text, priority_menu(pid))
    if r.get("ok"):
        remember_message(chat_id, r["result"]["message_id"])
    answer_callback(cb_id, f'{em(E_ROCKET, "🚀")} Приоритет выбран')

def process_method_normal(chat_id, cb_id, pid):
    """Пользователь выбрал обычную покупку"""
    o = orders.get(pid)
    if not o:
        answer_callback(cb_id, f'{em(E_CROSS, "❌")} Заказ не найден', True)
        return
    
    o["status"] = "choosing_normal"
    o["priority"] = False
    
    text = (
        f'{em(E_BOX, "📦")} <b>ОБЫЧНАЯ ПОКУПКА</b>\n\n'
        f'{em(E_SHOP, "🏪")} Товар: <b>{o["item_name"]}</b>\n'
        f'{em(E_PRICE, "💵")} Цена: <b>{o["base_price"]}₽</b>\n\n'
        f'{stars_row()}'
    )
    
    clear_last_message(chat_id)
    r = send_safe(chat_id, text, normal_pay_menu(pid))
    if r.get("ok"):
        remember_message(chat_id, r["result"]["message_id"])
    answer_callback(cb_id, f'{em(E_BOX, "📦")} Обычная покупка')

def process_priority_paid(chat_id, pid):
    """Пользователь оплатил приоритет — показываем статистику очереди"""
    o = orders.get(pid)
    if not o:
        return
    
    o["status"] = "priority_paid"
    o["priority"] = True
    o["total_price"] = o["base_price"] + 100
    
    username = get_username(chat_id)
    add_to_priority(o["item_key"], chat_id, username)
    
    before, after, total = get_queue_info(o["item_key"], chat_id)
    
    # Сообщение 1: Спасибо за покупку
    send_safe(chat_id,
        f'{em(E_HEART, "❤️")} <b>Спасибо за покупку !!!</b>')
    
    # Сообщение 2: Информация об очереди
    text = (
        f'{em(E_SMILE, "😉")} <b>Вы оплатили «Приоритет в очереди»</b>\n\n'
        f'{em(E_INFO, "ℹ️")} Текущая очередь: перед вами — \n'
        f'<b>{before}</b> {"человек" if before != 1 else "человек"} которые первые приобрели «приоритет»\n\n'
        f'После вас — <b>{after}</b> {"человека" if after not in (1,) else "человек"}, которые после вас приобрели «приоритет»\n\n'
        f'{em(E_USER, "👤")} Вам напишет человек, когда вы станете первые в очереди {em(E_SMILE, "😉")}\n'
        f'{em(E_INFO, "‼️")} Просьба, не спамить {em(E_INFO, "‼️")}'
    )
    
    clear_last_message(chat_id)
    r = send_safe(chat_id, text, after_priority_pay_menu(pid))
    if r.get("ok"):
        remember_message(chat_id, r["result"]["message_id"])
    
    # Уведомляем админа
    send_safe(OWNER_ID,
        f'{em(E_ROCKET, "🚀")} <b>НОВЫЙ ПРИОРИТЕТ!</b>\n\n'
        f'{em(E_USER, "👤")} @{username}\n'
        f'{em(E_SHOP, "🏪")} {o["item_name"]}\n'
        f'{em(E_PRICE, "💵")} {o["total_price"]}₽ (с приоритетом)\n'
        f'{em(E_INFO, "📊")} Очередь: перед — {before}, после — {after}'
    )

def process_normal_paid(chat_id, pid):
    """Пользователь оплатил обычную покупку"""
    o = orders.get(pid)
    if not o:
        return
    
    o["status"] = "normal_paid"
    o["priority"] = False
    o["total_price"] = o["base_price"]
    
    username = get_username(chat_id)
    add_to_normal(o["item_key"], chat_id, username)
    
    before, after, total = get_queue_info(o["item_key"], chat_id)
    
    # Сообщение 1: Спасибо за покупку
    send_safe(chat_id,
        f'{em(E_HEART, "❤️")} <b>Спасибо за покупку !!!</b>')
    
    # Сообщение 2: Информация об очереди
    text = (
        f'{em(E_INFO, "ℹ️")} <b>Ваша очередь:</b>\n\n'
        f'{em(E_USER, "👤")} Перед вами — <b>{before}</b> {"человек" if before != 1 else "человек"}\n'
        f'{em(E_USER, "👤")} После вас — <b>{after}</b> {"человека" if after not in (1,) else "человек"}\n\n'
        f'{em(E_INFO, "ℹ️")} Вам напишет человек, когда вы станете первые в очереди {em(E_SMILE, "😉")}\n'
        f'{em(E_INFO, "‼️")} Просьба, не спамить {em(E_INFO, "‼️")}'
    )
    
    clear_last_message(chat_id)
    r = send_safe(chat_id, text, after_normal_pay_menu(pid))
    if r.get("ok"):
        remember_message(chat_id, r["result"]["message_id"])
    
    # Уведомляем админа
    send_safe(OWNER_ID,
        f'{em(E_BOX, "📦")} <b>НОВЫЙ ЗАКАЗ (обычный)</b>\n\n'
        f'{em(E_USER, "👤")} @{username}\n'
        f'{em(E_SHOP, "🏪")} {o["item_name"]}\n'
        f'{em(E_PRICE, "💵")} {o["total_price"]}₽'
    )

def process_view_queue(chat_id, pid):
    """Показывает очередь пользователю"""
    o = orders.get(pid)
    if not o:
        send_replacing(chat_id, f'{em(E_CROSS, "❌")} Заказ не найден', back_button())
        return
    
    username = get_username(chat_id)
    before, after, total = get_queue_info(o["item_key"], chat_id)
    
    text = (
        f'{em(E_INFO, "📊")} <b>ТЕКУЩАЯ ОЧЕРЕДЬ</b>\n\n'
        f'{em(E_SHOP, "🏪")} Товар: <b>{o["item_name"]}</b>\n\n'
        f'{em(E_USER, "👤")} Перед вами — <b>{before}</b> {"человек" if before != 1 else "человек"}\n'
        f'{em(E_USER, "👤")} После вас — <b>{after}</b> {"человека" if after not in (1,) else "человек"}\n'
        f'{em(E_INFO, "📈")} Всего в очереди: <b>{total}</b>\n\n'
        f'{em(E_USER, "👤")} Вам напишет человек, когда вы станете первые в очереди {em(E_SMILE, "😉")}\n'
        f'{em(E_INFO, "‼️")} Просьба, не спамить {em(E_INFO, "‼️")}'
    )
    
    clear_last_message(chat_id)
    r = send_safe(chat_id, text, after_priority_pay_menu(pid))
    if r.get("ok"):
        remember_message(chat_id, r["result"]["message_id"])

# ============================================================
# СТАРАЯ ЛОГИКА (payment_menu / owner_confirm)
# ============================================================

def start_purchase(chat_id, itype, ikey, iname, price):
    """Старая функция (для совместимости) — редиректит на новый выбор"""
    return show_purchase_method(chat_id, itype, ikey, iname, price)

def process_paid(chat_id, cb_id, pid):
    o = orders.get(pid)
    if not o:
        answer_callback(cb_id, f'{em(E_CROSS, "❌")} Заказ не найден', True)
        return
    if o.get("status") not in ("awaiting_payment", "choosing_method", "choosing_normal", "choosing_priority"):
        answer_callback(cb_id, f'{em(E_TIME, "⏳")} Уже обработан', True)
        return
    
    o["status"] = "awaiting_owner_confirm"
    o["username"] = get_username(chat_id)
    logger.info(f'💰 {pid}: {chat_id} нажал Я оплатил')
    
    owner_text = (
        f'{em(E_MONEY, "💰")} <b>ПОДТВЕРЖДЕНИЕ ОПЛАТЫ</b>\n\n'
        f'{em(E_USER, "👤")} Покупатель: @{o["username"]}\n'
        f'{em(E_BOX, "📦")} Товар: {o["item_name"]}\n'
        f'{em(E_PRICE, "💵")} Сумма: {o["price"]}₽\n\n'
        f'{em(E_INFO, "ℹ️")} Пришли ли вам деньги?'
    )
    send_safe(OWNER_ID, owner_text, owner_confirm_menu(pid))
    answer_callback(cb_id, f'{em(E_CHECK, "✅")} Отправлено админу')
    send_replacing(chat_id, f'{em(E_TIME, "⏳")} Ожидайте подтверждения...')

def owner_confirm(cb_id, pid, yes):
    o = orders.get(pid)
    if not o:
        answer_callback(cb_id, f'{em(E_CROSS, "❌")} Не найден', True)
        return
    if yes:
        o["status"] = "awaiting_info"
        logger.info(f'✅ {pid}: админ подтвердил')
        
        if o["type"] == "boost":
            send_safe(o["user_id"],
                f'{em(E_CHECK, "✅")} <b>Оплата подтверждена!</b>\n\n'
                f'{em(E_INFO, "ℹ️")} Ожидайте QR-код от админа.\n\n'
                f'{em(E_TIME, "⏳")} Максимум 20 минут.')
            awaiting_qr_from_admin[pid] = True
            send_safe(OWNER_ID,
                f'{em(E_INFO, "ℹ️")} <b>Отправьте QR-код</b> для заказа {pid}\n\n'
                f'{em(E_USER, "👤")} Покупатель: @{o["username"]}\n'
                f'{em(E_BOX, "📦")} {o["item_name"]}',
                owner_send_qr_menu(pid))
        else:
            send_safe(o["user_id"],
                f'{em(E_CHECK, "✅")} <b>Заказ оплачен!</b>\n\n'
                f'{em(E_USER, "🆔")} Введите ваш PUBG ID (только цифры):')
            # Ждём PUBG ID — обрабатывается в handle_message
            
            # Отправляем админу кнопку "Команда свободна" (если это сопровождение)
            send_safe(OWNER_ID,
                f'{em(E_ROCKET, "🚀")} <b>ЗАКАЗ ГОТОВ К ВЫПОЛНЕНИЮ</b>\n\n'
                f'{em(E_USER, "👤")} @{o["username"]}\n'
                f'{em(E_BOX, "📦")} {o["item_name"]}\n\n'
                f'{em(E_INFO, "ℹ️")} Нажмите «Команда свободна», когда будете готовы:',
                owner_team_free_menu(pid))
    else:
        o["status"] = "cancelled"
        send_safe(o["user_id"],
            f'{em(E_CROSS, "❌")} <b>Оплата не подтверждена</b>\n\n'
            f'{em(E_INFO, "ℹ️")} Свяжитесь с @Manager_Kranzayy')
        answer_callback(cb_id, f'{em(E_CROSS, "❌")} Отменено')

def process_team_free(chat_id, cb_id, pid):
    """Админ нажал «Команда свободна» — уведомляем покупателя"""
    o = orders.get(pid)
    if not o:
        answer_callback(cb_id, f'{em(E_CROSS, "❌")} Не найден', True)
        return
    
    send_safe(o["user_id"],
        f'{em(E_CHECK, "✅")} <b>Команда свободна и ждет вас в игре !!!</b>')
    
    answer_callback(cb_id, f'{em(E_CHECK, "✅")} Покупатель уведомлён')
    send_safe(OWNER_ID,
        f'{em(E_CHECK, "✅")} Уведомление отправлено @{o.get("username", "—")}')

# ============================================================
# ОБРАБОТКА CALLBACK
# ============================================================

def handle_callback(cb):
    cb_id = cb["id"]
    chat_id = cb["from"]["id"]
    data = cb.get("data", "")
    msg = cb.get("message", {})
    msg_id = msg.get("message_id")
    
    # ---------- ГЛАВНОЕ МЕНЮ ----------
    if data == "back_main":
        send_main_menu(chat_id)
        answer_callback(cb_id, f'{em(E_MENU, "🏠")} Главное меню')
        return
    
    if data == "menu_support":
        text = (
            f'{em(E_SHOP, "🏪")} <b>СОПРОВОЖДЕНИЯ</b>\n\n'
            f'{em(E_INFO, "ℹ️")} Выберите подходящий вариант:\n\n'
            f'{stars_row()}'
        )
        edit_safe(chat_id, msg_id, text, support_menu())
        answer_callback(cb_id, f'{em(E_SHOP, "🏪")} Сопровождения')
        return
    
    if data == "menu_kits":
        edit_safe(chat_id, msg_id, KITS_TEXT, back_button())
        answer_callback(cb_id, f'{em(E_BOX, "📦")} Комплекты')
        return
    
    if data == "menu_loot":
        edit_safe(chat_id, msg_id, LOOT_TEXT, back_button())
        answer_callback(cb_id, f'{em(E_BAG, "🎒")} Скупка лута')
        return
    
    if data == "menu_boost":
        edit_safe(chat_id, msg_id,
            f'{em(E_BOOST, "🚀")} <b>БУСТ БАЛАНСА</b>\n\n'
            f'{em(E_INFO, "ℹ️")} Выберите сумму:\n\n{stars_row()}',
            boost_menu())
        answer_callback(cb_id, f'{em(E_ROCKET, "🚀")} Буст баланса')
        return
    
    # ---------- СОПРОВОЖДЕНИЯ ----------
    if data.startswith("sup_"):
        key = data[4:]
        if key in SUPPORT_DESCRIPTIONS:
            # Показываем выбор способа покупки
            show_purchase_method(
                chat_id, "support", key,
                SUPPORT_NAMES.get(key, "Сопровождение"),
                SUPPORT_PRICES.get(key, 0)
            )
            answer_callback(cb_id, f'{em(E_CHECK, "✅")} {SUPPORT_NAMES.get(key, "")}')
        return
    
    # ---------- ВЫБОР СПОСОБА ПОКУПКИ ----------
    if data.startswith("method_normal_"):
        pid = data[14:]
        process_method_normal(chat_id, cb_id, pid)
        return
    
    if data.startswith("method_priority_"):
        pid = data[16:]
        process_method_priority(chat_id, cb_id, pid)
        return
    
    if data.startswith("what_priority_"):
        pid = data[14:]
        answer_callback(cb_id)
        text = (
            f'{em(E_INFO, "ℹ️")} <b>ЧТО ТАКОЕ ПРИОРИТЕТ В ОЧЕРЕДИ?</b>\n\n'
            f'{em(E_ROCKET, "🚀")} Это возможность получить сопровождение <b>вне очереди</b>!\n\n'
            f'{em(E_CHECK, "✅")} Вы будете одними из первых, кто получит команду.\n'
            f'{em(E_MONEY, "💰")} Дополнительная плата: <b>+100₽</b>\n\n'
            f'{em(E_INFO, "ℹ️")} Чем раньше оплатите — тем выше приоритет!\n\n'
            f'{stars_row()}'
        )
        edit_safe(chat_id, msg_id, text, priority_menu(pid))
        return
    
    # ---------- ПОЛЬЗОВАТЕЛЬ ОПЛАТИЛ ----------
    if data.startswith("priority_paid_"):
        pid = data[14:]
        process_priority_paid(chat_id, pid)
        answer_callback(cb_id, f'{em(E_HEART, "❤️")} Спасибо!')
        return
    
    if data.startswith("normal_paid_"):
        pid = data[12:]
        process_normal_paid(chat_id, pid)
        answer_callback(cb_id, f'{em(E_HEART, "❤️")} Спасибо!')
        return
    
    if data.startswith("view_queue_"):
        pid = data[11:]
        process_view_queue(chat_id, pid)
        answer_callback(cb_id, f'{em(E_INFO, "📊")} Очередь')
        return
    
    if data.startswith("wait_"):
        pid = data[5:]
        answer_callback(cb_id, f'{em(E_TIME, "⏳")} Ожидайте сообщения')
        return
    
    # ---------- БУСТ ----------
    if data.startswith("boost_"):
        amount = data[6:]
        price = None
        for a, p in BOOST_PRICES:
            if a == amount:
                price = p
                break
        if price:
            start_purchase(chat_id, "boost", amount, f"Буст на {amount}", price)
            answer_callback(cb_id, f'{em(E_ROCKET, "🚀")} Буст на {amount}')
        return
    
    # ---------- ОПЛАТА (СТАРОЕ) ----------
    if data.startswith("paid_"):
        pid = data[5:]
        process_paid(chat_id, cb_id, pid)
        return
    
    if data.startswith("cancel_"):
        pid = data[5:]
        o = orders.get(pid)
        if o:
            o["status"] = "cancelled"
            clear_last_message(chat_id)
            send_main_menu(chat_id)
        answer_callback(cb_id, f'{em(E_CROSS, "❌")} Отменено')
        return
    
    # ---------- АДМИН ----------
    if data.startswith("owner_yes_"):
        pid = data[10:]
        owner_confirm(cb_id, pid, True)
        return
    
    if data.startswith("owner_no_"):
        pid = data[9:]
        owner_confirm(cb_id, pid, False)
        return
    
    if data.startswith("done_yes_"):
        pid = data[9:]
        o = orders.get(pid)
        if o:
            o["status"] = "completed"
            send_safe(o["user_id"],
                f'{em(E_CHECK, "✅")} <b>Заказ выполнен!</b>\n\n'
                f'{em(E_HEART, "❤️")} Спасибо за покупку!')
            send_safe(OWNER_ID, f'{em(E_CHECK, "✅")} Заказ {pid} завершён')
        answer_callback(cb_id, f'{em(E_CHECK, "✅")} Завершено')
        return
    
    if data.startswith("done_no_"):
        pid = data[8:]
        send_safe(OWNER_ID, f'{em(E_INFO, "ℹ️")} Заказ {pid} ещё в работе')
        answer_callback(cb_id, f'{em(E_INFO, "ℹ️")} Ок')
        return
    
    if data.startswith("send_qr_"):
        pid = data[8:]
        awaiting_qr_from_admin[pid] = True
        answer_callback(cb_id, f'{em(E_INFO, "ℹ️")} Отправьте фото QR-кода')
        send_safe(OWNER_ID, f'{em(E_INFO, "ℹ️")} Отправьте фото QR-кода для заказа {pid}')
        return
    
    if data.startswith("team_free_"):
        pid = data[10:]
        process_team_free(chat_id, cb_id, pid)
        return
    
    # ---------- ГРУППА ----------
    if data.startswith("join_"):
        pid = data[5:]
        o = orders.get(pid)
        if o:
            gm = group_messages.get(pid, {})
            parts = gm.setdefault("parts", [])
            username = get_username(chat_id)
            if len(parts) >= MAX_PARTICIPANTS:
                answer_callback(cb_id, f'{em(E_CROSS, "❌")} Уже 4 участника', True)
                return
            if username in parts:
                answer_callback(cb_id, f'{em(E_CROSS, "❌")} Вы уже участвуете', True)
                return
            parts.append(username)
            gm["parts"] = parts
            group_messages[pid] = gm
            if msg_id:
                edit_safe(GROUP_ID, msg_id, build_group_text(pid), group_join_menu(pid))
            answer_callback(cb_id, f'{em(E_CHECK, "✅")} Вы участвуете!')
        return
    
    answer_callback(cb_id, f'{em(E_INFO, "ℹ️")} В обработке')

# ============================================================
# ОБРАБОТКА СООБЩЕНИЙ
# ============================================================

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()
    user_id = msg["from"]["id"]
    msg_id = msg["message_id"]
    
    # ---------- КОМАНДЫ ----------
    if text.startswith("/start"):
        send_main_menu(chat_id)
        return
    
    if text == "/myid" and user_id == OWNER_ID:
        send_safe(chat_id, f'{em(E_INFO, "ℹ️")} Ваш ID: <code>{chat_id}</code>')
        return
    
    # ---------- АДМИН: РАССЫЛКА ----------
    if user_id == OWNER_ID and text.startswith("/send "):
        parts = text[6:].split(" ", 1)
        if len(parts) == 2:
            try:
                send_safe(int(parts[0]), parts[1])
                send_safe(chat_id, f'{em(E_CHECK, "✅")} Отправлено')
            except Exception as e:
                send_safe(chat_id, f'{em(E_CROSS, "❌")} Ошибка: {e}')
        return
    
    # ---------- АДМИН: СТАТИСТИКА ----------
    if user_id == OWNER_ID and text == "/stats":
        total = len(orders)
        support_count = sum(1 for o in orders.values() if o.get("type") == "support")
        boost_count = sum(1 for o in orders.values() if o.get("type") == "boost")
        prio_count = sum(1 for o in orders.values() if o.get("priority"))
        send_safe(chat_id,
            f'{em(E_INFO, "📊")} <b>СТАТИСТИКА</b>\n\n'
            f'{em(E_BOX, "📦")} Всего заказов: <b>{total}</b>\n'
            f'{em(E_CHECK, "✅")} Сопровождений: <b>{support_count}</b>\n'
            f'{em(E_ROCKET, "🚀")} Бустов: <b>{boost_count}</b>\n'
            f'{em(E_STAR, "⭐")} Приоритетов: <b>{prio_count}</b>')
        return
    
    # ---------- PUBG ID ОТ ЮЗЕРА ----------
    uid = str(chat_id)
    if uid in user_data and user_data[uid].get("awaiting_pubg"):
        if re.match(r'^\d+$', text):
            pid = user_data[uid].get("order_id")
            o = orders.get(pid)
            if o:
                o["pubg_id"] = text
                user_data[uid]["awaiting_pubg"] = False
                send_safe(chat_id, f'{em(E_CHECK, "✅")} PUBG ID сохранён: <code>{text}</code>')
                
                # Отправляем в группу
                gm = {"parts": [], "users": {}}
                group_messages[pid] = gm
                r = send_safe(GROUP_ID,
                    build_group_text(pid),
                    group_join_menu(pid))
                if r.get("ok"):
                    group_messages[pid]["msg_id"] = r["result"]["message_id"]
                
                # Уведомляем админа
                send_safe(OWNER_ID,
                    f'{em(E_CHECK, "✅")} <b>НОВЫЙ ЗАКАЗ ГОТОВ</b>\n\n'
                    f'{em(E_USER, "👤")} @{o.get("username", "—")}\n'
                    f'{em(E_BOX, "📦")} {o["item_name"]}\n'
                    f'{em(E_USER, "🆔")} PUBG ID: <code>{text}</code>\n'
                    f'{em(E_PRICE, "💵")} {o.get("total_price", o["price"])}₽')
            return
        else:
            send_safe(chat_id, f'{em(E_CROSS, "❌")} Введите только цифры!')
            return

# ============================================================
# ПОЛУЧЕНИЕ ОБНОВЛЕНИЙ
# ============================================================

def get_updates(offset=0):
    try:
        r = requests.get(
            f"{BASE_URL}/getUpdates",
            params={"offset": offset, "timeout": 30, "allowed_updates": json.dumps(["message", "callback_query"])},
            timeout=35
        ).json()
        return r
    except Exception as e:
        logger.error(f"❌ getUpdates: {e}")
        return {"ok": False}

# ============================================================
# ГЛАВНЫЙ ЦИКЛ
# ============================================================

def main():
    logger.info("🚀 KRANZAYY BOT v18 — ЗАПУСК")
    
    # Настраиваем команды бота
    api_request("setMyCommands", {
        "commands": json.dumps([
            {"command": "start", "description": "🏪 Главное меню"},
        ])
    })
    
    offset = 0
    backoff = RECONNECT_MIN
    
    while True:
        try:
            r = get_updates(offset)
            if not r.get("ok"):
                time.sleep(backoff)
                backoff = min(backoff * 2, RECONNECT_MAX)
                continue
            
            backoff = RECONNECT_MIN
            
            for upd in r.get("result", []):
                offset = upd["update_id"] + 1
                
                try:
                    if "callback_query" in upd:
                        handle_callback(upd["callback_query"])
                    elif "message" in upd:
                        handle_message(upd["message"])
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки: {e}")
                    traceback.print_exc()
            
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            logger.info("🛑 Остановка...")
            break
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}")
            traceback.print_exc()
            time.sleep(backoff)
            backoff = min(backoff * 2, RECONNECT_MAX)

if __name__ == "__main__":
    main()
