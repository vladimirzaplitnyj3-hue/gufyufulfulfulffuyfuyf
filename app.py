# ============================================================
# KRANZAYY | METRO SHOP BOT — v20 (FINAL, с premium emoji в кнопках)
# ============================================================

import requests, json, time, logging, sys, traceback, re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot.log', encoding='utf-8'),
              logging.StreamHandler(sys.stdout)]
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
PHOTO_URL = "https://i.ibb.co/kVCDv7Rg/IMG-3261.jpg"
PHOTO_FILE_ID = None

PAY_LINK_PRIORITY = "https://t.me/Manager_Kranzayy"
PAY_LINK_NORMAL = "https://t.me/Manager_Kranzayy"
MAX_PARTICIPANTS = 4

# ============================================================
# ПРЕМИУМ-ЭМОДЗИ (ID для текста через <tg-emoji> И для кнопок icon_custom_emoji_id)
# ============================================================
E_MENU    = "5231235536206730707"
E_SHOP    = "5278702045883292456"
E_STAR    = "5330051403563943171"
E_STAR2   = "5330245862503236304"
E_STAR3   = "5327866716909229540"
E_ARROW   = "5219793421207629443"
E_CHECK   = "5219809810802829750"
E_CROSS   = "5219835361563275589"
E_INFO    = "5285430309720966085"
E_TIME    = "5310169226856644648"
E_USER    = "5316970857325687050"
E_MONEY   = "5219714093161671306"
E_PRICE   = "5219919637411556483"
E_HEART   = "5346301287774323405"
E_DIAMOND = "5465556444931718975"
E_BAG     = "5431406343917414987"
E_BOX     = "5429424809215797643"
E_ROCKET  = "5474525938668550110"
E_CROWN   = "5465556444931718975"
E_LOCK    = "5316970857325687050"

# ============================================================
# ХРАНИЛИЩА
# ============================================================
user_data, orders, group_messages, awaiting_qr = {}, {}, {}, {}
orders_counter = [0]
priority_queue, normal_queue = {}, {}

# ============================================================
# ХЕЛПЕРЫ
# ============================================================
def em(eid, fallback="⭐"):
    return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'

def stars_row():
    return f'{em(E_STAR)}{em(E_STAR2)}{em(E_STAR2)}{em(E_STAR3)}'

def arrows_row(n=6):
    return em(E_ARROW) * n

def strip_html(t):
    return re.sub(r'<[^>]+>', '', t)

# ============================================================
# API
# ============================================================
def api(method, payload, retries=2):
    url = f"{BASE_URL}/{method}"
    for i in range(retries):
        try:
            r = requests.post(url, json=payload, timeout=30).json()
            if not r.get("ok"):
                logger.error(f"[{method}] {r.get('description')}")
            return r
        except Exception as e:
            if i < retries - 1:
                time.sleep(2)
            else:
                logger.error(f"[{method}] {e}")
                return {"ok": False, "error": str(e)}
    return {"ok": False}

def send(chat_id, text, kb=None):
    p = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if kb: p["reply_markup"] = json.dumps(kb)
    r = api("sendMessage", p)
    if r.get("ok"): return r
    p2 = {"chat_id": chat_id, "text": strip_html(text)}
    if kb: p2["reply_markup"] = json.dumps(kb)
    return api("sendMessage", p2)

def send_photo(chat_id, photo, caption=None, kb=None):
    p = {"chat_id": chat_id, "photo": photo, "parse_mode": "HTML"}
    if caption: p["caption"] = caption
    if kb: p["reply_markup"] = json.dumps(kb)
    r = api("sendPhoto", p)
    if r.get("ok"): return r
    if caption:
        p2 = {"chat_id": chat_id, "photo": photo, "caption": strip_html(caption)}
        if kb: p2["reply_markup"] = json.dumps(kb)
        return api("sendPhoto", p2)
    return r

def edit(chat_id, msg_id, text, kb=None):
    p = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    if kb: p["reply_markup"] = json.dumps(kb)
    r = api("editMessageText", p)
    if r.get("ok"): return r
    p2 = {"chat_id": chat_id, "message_id": msg_id, "text": strip_html(text)}
    if kb: p2["reply_markup"] = json.dumps(kb)
    return api("editMessageText", p2)

def answer_cb(cb_id, text=None, alert=False):
    p = {"callback_query_id": cb_id}
    if text: p["text"] = text
    if alert: p["show_alert"] = True
    return api("answerCallbackQuery", p)

def del_msg(chat_id, msg_id):
    return api("deleteMessage", {"chat_id": chat_id, "message_id": msg_id})

def get_username(chat_id):
    try:
        r = api("getChat", {"chat_id": chat_id})
        if r.get("ok"):
            u = r["result"]
            return u.get("username") or u.get("first_name", "Пользователь")
    except: pass
    return "Пользователь"

def gen_pid():
    orders_counter[0] += 1
    return f"ORD{int(time.time())}_{orders_counter[0]}"

def remember(uid, mid):
    s = str(uid)
    user_data.setdefault(s, {})["last_msg_id"] = mid

def clear_last(uid):
    s = str(uid)
    lid = user_data.get(s, {}).get("last_msg_id")
    if lid: del_msg(uid, lid)
    if s in user_data: user_data[s]["last_msg_id"] = None

# ============================================================
# ОЧЕРЕДЬ
# ============================================================
def add_prio(k, uid, uname):
    priority_queue.setdefault(k, [])
    if not any(u["id"] == uid for u in priority_queue[k]):
        priority_queue[k].append({"id": uid, "username": uname})

def add_norm(k, uid, uname):
    normal_queue.setdefault(k, [])
    if not any(u["id"] == uid for u in normal_queue[k]):
        normal_queue[k].append({"id": uid, "username": uname})

def queue_info(k, uid):
    p, n = priority_queue.get(k, []), normal_queue.get(k, [])
    pi = next((i for i, u in enumerate(p) if u["id"] == uid), None)
    if pi is not None:
        return pi, (len(p) - pi - 1) + len(n), len(p) + len(n)
    ni = next((i for i, u in enumerate(n) if u["id"] == uid), None)
    if ni is not None:
        return len(p) + ni, len(n) - ni - 1, len(p) + len(n)
    return 0, 0, len(p) + len(n)

# ============================================================
# КЛАВИАТУРЫ С ПРЕМИУМ-ЭМОДЗИ В КНОПКАХ
# Используем icon_custom_emoji_id + style
# ============================================================

def main_menu():
    return {"inline_keyboard": [
        [{"text": "СОПРОВОЖДЕНИЯ", "callback_data": "menu_support",
          "style": "success", "icon_custom_emoji_id": E_CHECK}],
        [{"text": "КОМПЛЕКТЫ", "callback_data": "menu_kits",
          "style": "primary", "icon_custom_emoji_id": E_BOX},
         {"text": "СКУПКА ЛУТА", "callback_data": "menu_loot",
          "style": "primary", "icon_custom_emoji_id": E_BAG}],
        [{"text": "БУСТ БАЛАНСА", "callback_data": "menu_boost",
          "style": "success", "icon_custom_emoji_id": E_ROCKET}],
        [{"text": "РЕГЛАМЕНТ", "url": "https://t.me/+MU3bQoEK9rUxYTIy",
          "style": "danger", "icon_custom_emoji_id": E_LOCK},
         {"text": "НИШТЯКИ", "url": "https://t.me/kranzayy_nustaku",
          "style": "success", "icon_custom_emoji_id": E_DIAMOND}],
        [{"text": "Отзывы", "url": "https://t.me/kranzayy_OTZ",
          "style": "primary", "icon_custom_emoji_id": E_HEART}],
    ]}

SUPPORT_LIST = [
    ("default",       "10кк | Дефолт (7 карта) — 100₽",  "success", E_CHECK),
    ("vip",           "15кк | Вип (7 карта) — 150₽",      "success", E_CHECK),
    ("elite",         "21кк | Элит (7 карта) — 290₽",     "success", E_CROWN),
    ("oligarch",      "35кк | Олигарх (7 карта) — 359₽",  "success", E_CROWN),
    ("default_plus",  "10кк | Дефолт+ (7 карта) — 150₽",  "primary", E_STAR),
    ("vip_plus",      "15кк | Вип+ (7 карта) — 210₽",     "primary", E_STAR),
    ("elite_plus",    "21кк | Элит+ (7 карта) — 290₽",    "primary", E_STAR2),
    ("oligarch_plus", "35кк | Олигарх+ (7 карта) — 425₽", "primary", E_STAR3),
    ("default_pro",   "10кк | Дефолт ПРО (7 карта) — 225₽","danger", E_ROCKET),
    ("vip_pro",       "15кк | Вип ПРО (7 карта) — 289₽",   "danger", E_ROCKET),
    ("elite_pro",     "21кк | Элит ПРО (7 карта) — 369₽",  "danger", E_ROCKET),
    ("oligarch_pro",  "35кк | Олигарх ПРО (7 карта) — 529₽","danger", E_CROWN),
]

def support_menu():
    kb = [[{"text": t, "callback_data": f"sup_{k}",
            "style": s, "icon_custom_emoji_id": ic}] for k, t, s, ic in SUPPORT_LIST]
    kb.append([{"text": "Назад", "callback_data": "back_main",
                "style": "danger", "icon_custom_emoji_id": E_CROSS}])
    return {"inline_keyboard": kb}

BOOST_LIST = [
    ("5.000.000", 85, "success", E_MONEY),
    ("10.000.000", 145, "success", E_MONEY),
    ("15.000.000", 250, "primary", E_PRICE),
    ("20.000.000", 310, "primary", E_PRICE),
    ("25.000.000", 390, "primary", E_PRICE),
    ("35.000.000", 560, "danger", E_DIAMOND),
    ("50.000.000", 790, "danger", E_DIAMOND),
    ("75.000.000", 1190, "danger", E_CROWN),
    ("100.000.000", 1590, "danger", E_CROWN),
]

def boost_menu():
    kb = [[{"text": f"{a} — {p}₽", "callback_data": f"boost_{a}",
            "style": s, "icon_custom_emoji_id": ic}] for a, p, s, ic in BOOST_LIST]
    kb.append([{"text": "Назад", "callback_data": "back_main",
                "style": "danger", "icon_custom_emoji_id": E_CROSS}])
    return {"inline_keyboard": kb}

def back_btn(cb="back_main"):
    return {"inline_keyboard": [[{"text": "Назад", "callback_data": cb,
                                   "style": "danger", "icon_custom_emoji_id": E_CROSS}]]}

def method_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Обычная покупка", "callback_data": f"method_normal_{pid}",
          "style": "primary", "icon_custom_emoji_id": E_BOX}],
        [{"text": "Приоритет в очереди (+100₽)", "callback_data": f"method_priority_{pid}",
          "style": "success", "icon_custom_emoji_id": E_ROCKET}],
        [{"text": "Отмена", "callback_data": f"cancel_{pid}",
          "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

def priority_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Оплатить приоритет (+100₽)", "url": PAY_LINK_PRIORITY,
          "style": "success", "icon_custom_emoji_id": E_MONEY}],
        [{"text": "Что такое приоритет в очереди?", "callback_data": f"what_priority_{pid}",
          "style": "primary", "icon_custom_emoji_id": E_INFO}],
        [{"text": "Отмена", "callback_data": f"cancel_{pid}",
          "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

def normal_pay_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Оплатить", "url": PAY_LINK_NORMAL,
          "style": "success", "icon_custom_emoji_id": E_MONEY}],
        [{"text": "Отмена", "callback_data": f"cancel_{pid}",
          "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

def after_prio_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Купить сопровождение", "callback_data": "menu_support",
          "style": "success", "icon_custom_emoji_id": E_SHOP}],
        [{"text": "Посмотреть очередь", "callback_data": f"view_queue_{pid}",
          "style": "primary", "icon_custom_emoji_id": E_INFO}],
        [{"text": "Написать", "url": MANAGER_LINK,
          "style": "success", "icon_custom_emoji_id": E_USER}],
        [{"text": "Ждать", "callback_data": f"wait_{pid}",
          "style": "danger", "icon_custom_emoji_id": E_TIME}],
    ]}

def after_norm_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Купить Приоритет (+100₽)", "callback_data": f"method_priority_{pid}",
          "style": "success", "icon_custom_emoji_id": E_ROCKET}],
        [{"text": "Написать", "url": MANAGER_LINK,
          "style": "success", "icon_custom_emoji_id": E_USER}],
        [{"text": "Ждать", "callback_data": f"wait_{pid}",
          "style": "danger", "icon_custom_emoji_id": E_TIME}],
    ]}

def owner_confirm_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Да, деньги пришли", "callback_data": f"owner_yes_{pid}",
          "style": "success", "icon_custom_emoji_id": E_CHECK}],
        [{"text": "Нет, отменить", "callback_data": f"owner_no_{pid}",
          "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

def owner_qr_menu(pid):
    return {"inline_keyboard": [
        [{"text": "Отправить QR-код", "callback_data": f"send_qr_{pid}",
          "style": "success", "icon_custom_emoji_id": E_INFO}],
        [{"text": "Заказ выполнен", "callback_data": f"done_yes_{pid}",
          "style": "success", "icon_custom_emoji_id": E_CHECK}],
        [{"text": "Не выполнен", "callback_data": f"done_no_{pid}",
          "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

def owner_team_free(pid):
    return {"inline_keyboard": [
        [{"text": "Команда свободна", "callback_data": f"team_free_{pid}",
          "style": "success", "icon_custom_emoji_id": E_CHECK}],
        [{"text": "Заказ выполнен", "callback_data": f"done_yes_{pid}",
          "style": "success", "icon_custom_emoji_id": E_CHECK}],
        [{"text": "Не выполнен", "callback_data": f"done_no_{pid}",
          "style": "danger", "icon_custom_emoji_id": E_CROSS}],
    ]}

def group_join(pid):
    return {"inline_keyboard": [
        [{"text": "Я участвую в сопровождении", "callback_data": f"join_{pid}",
          "style": "success", "icon_custom_emoji_id": E_USER}]
    ]}

# ============================================================
# ТЕКСТЫ
# ============================================================
MAIN_CAPTION = (
    f'{em(E_MENU)} <b>Добро пожаловать в бота !!!</b>\n'
    f'{em(E_SHOP)} • <b>Kranzayy | Metro Shop</b>\n\n'
    f'{stars_row()}\n\n'
    f'<b>Можете пользоваться навигацией ниже</b>\n\n'
    f'{arrows_row()}'
)

KITS_TEXT = (
    f'{em(E_BOX)} <b>КОМПЛЕКТЫ</b>\n\n'
    f'{em(E_STAR)} 1 день — 1 шестая шмотка — 7₽\n'
    f'{em(E_STAR)} 2 день — 1 шестая шмотка — 5₽\n'
    f'{em(E_STAR)} 3-7 день — 1 шестая шмотка — 4₽\n'
    f'{em(E_STAR)} 2-3 неделя — 1 шестая шмотка — 3₽\n\n'
    f'{em(E_INFO)} В шестую шмотку входит:\n'
    f'{em(E_INFO)} хотите купить — @Manager_Kranzayy'
)

LOOT_TEXT = (
    f'{em(E_BAG)} <b>СКУПКА ЛУТА</b>\n\n'
    f'{em(E_STAR)} 1 день — 1 шестая шмотка — 7₽\n'
    f'{em(E_STAR)} 2 день — 1 шестая шмотка — 5₽\n'
    f'{em(E_STAR)} 3-7 день — 1 шестая шмотка — 4₽\n'
    f'{em(E_STAR)} 2-3 неделя — 1 шестая шмотка — 3₽\n\n'
    f'{em(E_INFO)} Если хотите купить — @Manager_Kranzayy'
)

SUP_PRICES = {
    "default":100,"vip":150,"elite":290,"oligarch":359,
    "default_plus":150,"vip_plus":210,"elite_plus":290,"oligarch_plus":425,
    "default_pro":225,"vip_pro":289,"elite_pro":369,"oligarch_pro":529,
}

SUP_NAMES = {
    "default":"ДЕФОЛТ СОПРОВОЖДЕНИЕ","vip":"ВИП СОПРОВОЖДЕНИЕ",
    "elite":"ЭЛИТ СОПРОВОЖДЕНИЕ","oligarch":"ОЛИГАРХ СОПРОВОЖДЕНИЕ",
    "default_plus":"ДЕФОЛТ+ СОПРОВОЖДЕНИЕ","vip_plus":"ВИП+ СОПРОВОЖДЕНИЕ",
    "elite_plus":"ЭЛИТ+ СОПРОВОЖДЕНИЕ","oligarch_plus":"ОЛИГАРХ+ СОПРОВОЖДЕНИЕ",
    "default_pro":"ДЕФОЛТ ПРО СОПРОВОЖДЕНИЕ","vip_pro":"ВИП ПРО СОПРОВОЖДЕНИЕ",
    "elite_pro":"ЭЛИТ ПРО СОПРОВОЖДЕНИЕ","oligarch_pro":"ОЛИГАРХ ПРО СОПРОВОЖДЕНИЕ",
}

# ============================================================
# ЛОГИКА ПОКУПКИ
# ============================================================
def show_method(chat_id, itype, ikey, iname, price):
    clear_last(chat_id)
    pid = gen_pid()
    orders[pid] = {"user_id": chat_id, "type": itype, "item_key": ikey,
                   "item_name": iname, "price": price, "base_price": price,
                   "status": "choosing_method", "priority": False}
    text = (
        f'{em(E_BOX)} <b>ВЫБЕРИТЕ СПОСОБ ПОКУПКИ</b>\n\n'
        f'{em(E_SHOP)} Товар: <b>{iname}</b>\n'
        f'{em(E_PRICE)} Цена: <b>{price}₽</b>\n\n'
        f'{em(E_INFO)} Выберите как вы хотите купить, ниже {em(E_CHECK)}\n\n'
        f'{stars_row()}'
    )
    r = send(chat_id, text, method_menu(pid))
    if r.get("ok"): remember(chat_id, r["result"]["message_id"])
    return pid

def on_priority_choice(chat_id, cb_id, pid):
    o = orders.get(pid)
    if not o: return answer_cb(cb_id, "❌ Заказ не найден", True)
    o["status"] = "choosing_priority"
    o["priority"] = True
    text = (
        f'{em(E_ROCKET)} <b>ПРИОРИТЕТ В ОЧЕРЕДИ</b>\n\n'
        f'{em(E_SHOP)} Товар: <b>{o["item_name"]}</b>\n'
        f'{em(E_PRICE)} Цена: <b>{o["base_price"]}₽</b> + <b>100₽</b>\n'
        f'{em(E_MONEY)} Итого: <b>{o["base_price"] + 100}₽</b>\n\n'
        f'{em(E_INFO)} Выберите действие\n\n'
        f'{stars_row()}'
    )
    clear_last(chat_id)
    r = send(chat_id, text, priority_menu(pid))
    if r.get("ok"): remember(chat_id, r["result"]["message_id"])
    answer_cb(cb_id, "🚀 Приоритет выбран")

def on_normal_choice(chat_id, cb_id, pid):
    o = orders.get(pid)
    if not o: return answer_cb(cb_id, "❌ Заказ не найден", True)
    o["status"] = "choosing_normal"
    o["priority"] = False
    text = (
        f'{em(E_BOX)} <b>ОБЫЧНАЯ ПОКУПКА</b>\n\n'
        f'{em(E_SHOP)} Товар: <b>{o["item_name"]}</b>\n'
        f'{em(E_PRICE)} Цена: <b>{o["base_price"]}₽</b>\n\n'
        f'{stars_row()}'
    )
    clear_last(chat_id)
    r = send(chat_id, text, normal_pay_menu(pid))
    if r.get("ok"): remember(chat_id, r["result"]["message_id"])
    answer_cb(cb_id, "📦 Обычная покупка")

def on_priority_paid(chat_id, pid):
    o = orders.get(pid)
    if not o: return
    o["status"] = "priority_paid"
    o["priority"] = True
    o["total_price"] = o["base_price"] + 100
    uname = get_username(chat_id)
    add_prio(o["item_key"], chat_id, uname)
    before, after, total = queue_info(o["item_key"], chat_id)

    send(chat_id, f'{em(E_HEART)} <b>Спасибо за покупку !!!</b>')
    text = (
        f'{em(E_STAR2)} <b>Вы оплатили «Приоритет в очереди»</b>\n\n'
        f'{em(E_INFO)} Текущая очередь: перед вами — \n'
        f'<b>{before}</b> {"человек" if before != 1 else "человек"} которые первые приобрели «приоритет»\n\n'
        f'После вас — <b>{after}</b> {"человека" if after not in (1,) else "человек"}, которые после вас приобрели «приоритет»\n\n'
        f'{em(E_USER)} Вам напишет человек, когда вы станете первые в очереди {em(E_STAR2)}\n'
        f'{em(E_INFO)} Просьба, не спамить {em(E_INFO)}'
    )
    clear_last(chat_id)
    r = send(chat_id, text, after_prio_menu(pid))
    if r.get("ok"): remember(chat_id, r["result"]["message_id"])

    send(OWNER_ID,
        f'{em(E_ROCKET)} <b>НОВЫЙ ПРИОРИТЕТ!</b>\n\n'
        f'{em(E_USER)} @{uname}\n'
        f'{em(E_SHOP)} {o["item_name"]}\n'
        f'{em(E_PRICE)} {o["total_price"]}₽\n'
        f'{em(E_INFO)} Перед — {before}, после — {after}')

def on_normal_paid(chat_id, pid):
    o = orders.get(pid)
    if not o: return
    o["status"] = "normal_paid"
    o["priority"] = False
    o["total_price"] = o["base_price"]
    uname = get_username(chat_id)
    add_norm(o["item_key"], chat_id, uname)
    before, after, total = queue_info(o["item_key"], chat_id)

    send(chat_id, f'{em(E_HEART)} <b>Спасибо за покупку !!!</b>')
    text = (
        f'{em(E_INFO)} <b>Ваша очередь:</b>\n\n'
        f'{em(E_USER)} Перед вами — <b>{before}</b>\n'
        f'{em(E_USER)} После вас — <b>{after}</b>\n\n'
        f'{em(E_INFO)} Вам напишет человек, когда вы станете первые в очереди {em(E_STAR2)}\n'
        f'{em(E_INFO)} Просьба, не спамить {em(E_INFO)}'
    )
    clear_last(chat_id)
    r = send(chat_id, text, after_norm_menu(pid))
    if r.get("ok"): remember(chat_id, r["result"]["message_id"])

    send(OWNER_ID,
        f'{em(E_BOX)} <b>НОВЫЙ ЗАКАЗ</b>\n\n'
        f'{em(E_USER)} @{uname}\n'
        f'{em(E_SHOP)} {o["item_name"]}\n'
        f'{em(E_PRICE)} {o["total_price"]}₽')

def on_view_queue(chat_id, pid):
    o = orders.get(pid)
    if not o: return
    before, after, total = queue_info(o["item_key"], chat_id)
    text = (
        f'{em(E_INFO)} <b>ТЕКУЩАЯ ОЧЕРЕДЬ</b>\n\n'
        f'{em(E_SHOP)} Товар: <b>{o["item_name"]}</b>\n\n'
        f'{em(E_USER)} Перед вами — <b>{before}</b>\n'
        f'{em(E_USER)} После вас — <b>{after}</b>\n'
        f'{em(E_INFO)} Всего: <b>{total}</b>\n\n'
        f'{em(E_USER)} Вам напишет человек, когда вы станете первые {em(E_STAR2)}\n'
        f'{em(E_INFO)} Просьба, не спамить {em(E_INFO)}'
    )
    clear_last(chat_id)
    r = send(chat_id, text, after_prio_menu(pid))
    if r.get("ok"): remember(chat_id, r["result"]["message_id"])

# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================
def send_main(chat_id):
    global PHOTO_FILE_ID
    clear_last(chat_id)
    r = send_photo(chat_id, PHOTO_FILE_ID or PHOTO_URL, caption=MAIN_CAPTION, kb=main_menu())
    if r.get("ok"):
        if not PHOTO_FILE_ID:
            try: PHOTO_FILE_ID = r["result"]["photo"][-1]["file_id"]
            except: pass
        remember(chat_id, r["result"]["message_id"])
    else:
        r2 = send(chat_id, MAIN_CAPTION, main_menu())
        if r2.get("ok"): remember(chat_id, r2["result"]["message_id"])

# ============================================================
# CALLBACK РОУТЕР
# ============================================================
def handle_cb(cb):
    cb_id = cb["id"]
    chat_id = cb["from"]["id"]
    data = cb.get("data", "")
    msg_id = cb.get("message", {}).get("message_id")
    uid = str(chat_id)

    if data == "back_main":
        send_main(chat_id); return answer_cb(cb_id, "🏠 Меню")

    if data == "menu_support":
        edit(chat_id, msg_id,
             f'{em(E_SHOP)} <b>СОПРОВОЖДЕНИЯ</b>\n\n{em(E_INFO)} Выберите вариант:\n\n{stars_row()}',
             support_menu())
        return answer_cb(cb_id, "🔥 Сопровождения")

    if data == "menu_kits":
        edit(chat_id, msg_id, KITS_TEXT, back_btn()); return answer_cb(cb_id, "📦")
    if data == "menu_loot":
        edit(chat_id, msg_id, LOOT_TEXT, back_btn()); return answer_cb(cb_id, "🎒")
    if data == "menu_boost":
        edit(chat_id, msg_id,
             f'{em(E_ROCKET)} <b>БУСТ БАЛАНСА</b>\n\n{em(E_INFO)} Выберите сумму:\n\n{stars_row()}',
             boost_menu())
        return answer_cb(cb_id, "🚀")

    if data.startswith("sup_"):
        k = data[4:]
        if k in SUP_PRICES:
            show_method(chat_id, "support", k, SUP_NAMES.get(k, ""), SUP_PRICES[k])
            answer_cb(cb_id, f"✅ {SUP_NAMES.get(k, '')}")
        return

    if data.startswith("method_normal_"):
        on_normal_choice(chat_id, cb_id, data[14:]); return
    if data.startswith("method_priority_"):
        on_priority_choice(chat_id, cb_id, data[16:]); return

    if data.startswith("what_priority_"):
        pid = data[14:]
        answer_cb(cb_id)
        edit(chat_id, msg_id,
             f'{em(E_INFO)} <b>ЧТО ТАКОЕ ПРИОРИТЕТ?</b>\n\n'
             f'{em(E_ROCKET)} Возможность получить сопровождение <b>вне очереди</b>!\n\n'
             f'{em(E_CHECK)} Вы будете одними из первых.\n'
             f'{em(E_MONEY)} Доп. плата: <b>+100₽</b>\n\n'
             f'{stars_row()}', priority_menu(pid))
        return

    if data.startswith("priority_paid_"):
        on_priority_paid(chat_id, data[14:]); return answer_cb(cb_id, "❤️")
    if data.startswith("normal_paid_"):
        on_normal_paid(chat_id, data[12:]); return answer_cb(cb_id, "❤️")
    if data.startswith("view_queue_"):
        on_view_queue(chat_id, data[11:]); return answer_cb(cb_id, "📊")
    if data.startswith("wait_"):
        return answer_cb(cb_id, "⏳ Ожидайте")

    if data.startswith("boost_"):
        amt = data[6:]
        for a, p, _, _ in BOOST_LIST:
            if a == amt:
                show_method(chat_id, "boost", amt, f"Буст на {amt}", p)
                answer_cb(cb_id, f"🚀 {amt}")
                return
        return

    if data.startswith("cancel_"):
        pid = data[7:]
        if pid in orders: orders[pid]["status"] = "cancelled"
        send_main(chat_id); return answer_cb(cb_id, "❌ Отменено")

    # Админ
    if data.startswith("owner_yes_"):
        pid = data[10:]; o = orders.get(pid)
        if not o: return answer_cb(cb_id, "❌", True)
        o["status"] = "awaiting_info"
        send(o["user_id"],
             f'{em(E_CHECK)} <b>Оплата подтверждена!</b>\n\n'
             f'{em(E_USER)} Введите ваш PUBG ID (только цифры):')
        user_data.setdefault(str(o["user_id"]), {})["awaiting_pubg"] = True
        user_data[str(o["user_id"])]["order_id"] = pid
        send(OWNER_ID,
             f'{em(E_ROCKET)} <b>ЗАКАЗ ПОДТВЕРЖДЁН</b>\n\n'
             f'{em(E_USER)} @{o.get("username", "—")}\n'
             f'{em(E_BOX)} {o["item_name"]}\n\n'
             f'{em(E_INFO)} Ждём PUBG ID от покупателя…',
             owner_team_free(pid))
        return answer_cb(cb_id, "✅ Подтверждено")

    if data.startswith("owner_no_"):
        pid = data[9:]; o = orders.get(pid)
        if o:
            o["status"] = "cancelled"
            send(o["user_id"], f'{em(E_CROSS)} <b>Оплата не подтверждена</b>\n\n{em(E_INFO)} @Manager_Kranzayy')
        return answer_cb(cb_id, "❌ Отменено")

    if data.startswith("done_yes_"):
        pid = data[9:]; o = orders.get(pid)
        if o:
            o["status"] = "completed"
            send(o["user_id"], f'{em(E_CHECK)} <b>Заказ выполнен!</b>\n\n{em(E_HEART)} Спасибо за покупку!')
        return answer_cb(cb_id, "✅")

    if data.startswith("done_no_"):
        return answer_cb(cb_id, "ℹ️")

    if data.startswith("send_qr_"):
        pid = data[8:]
        awaiting_qr[pid] = True
        send(OWNER_ID, f'{em(E_INFO)} Отправьте фото QR-кода для {pid}')
        return answer_cb(cb_id, "ℹ️ Отправьте фото")

    if data.startswith("team_free_"):
        pid = data[10:]; o = orders.get(pid)
        if o:
            send(o["user_id"], f'{em(E_CHECK)} <b>Команда свободна и ждет вас в игре !!!</b>')
            send(OWNER_ID, f'{em(E_CHECK)} Уведомление отправлено @{o.get("username", "—")}')
        return answer_cb(cb_id, "✅ Отправлено")

    if data.startswith("join_"):
        pid = data[5:]; o = orders.get(pid)
        if not o: return answer_cb(cb_id, "❌", True)
        gm = group_messages.setdefault(pid, {"parts": []})
        parts = gm["parts"]
        uname = get_username(chat_id)
        if len(parts) >= MAX_PARTICIPANTS:
            return answer_cb(cb_id, "❌ Уже 4 участника", True)
        if uname in parts:
            return answer_cb(cb_id, "❌ Вы уже участвуете", True)
        parts.append(uname)
        if msg_id:
            edit(GROUP_ID, msg_id, group_text(pid), group_join(pid))
        return answer_cb(cb_id, "✅ Вы участвуете!")

    answer_cb(cb_id, "ℹ️")

# ============================================================
# ГРУППА
# ============================================================
def group_text(pid):
    o = orders.get(pid, {})
    parts = group_messages.get(pid, {}).get("parts", [])
    return (
        f'{em(E_BOX)} <b>НОВЫЙ ЗАКАЗ В СОПРОВОЖДЕНИЕ</b>\n\n'
        f'{em(E_USER)} Купил: @{o.get("username", "—")}\n'
        f'{em(E_USER)} PUBG ID: <code>{o.get("pubg_id", "—")}</code>\n\n'
        f'{em(E_BOX)} Товар: <b>{o.get("item_name", "—")}</b>\n'
        f'{em(E_PRICE)} Цена: {o.get("price", "—")}₽\n\n'
        f'{em(E_USER)} Участвуют: {", ".join(parts) if parts else "—"} ({len(parts)}/{MAX_PARTICIPANTS})'
    )

# ============================================================
# СООБЩЕНИЯ
# ============================================================
def handle_msg(msg):
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()
    uid = msg["from"]["id"]

    if text.startswith("/start"):
        send_main(chat_id); return
    if text == "/myid" and uid == OWNER_ID:
        send(chat_id, f'<code>{chat_id}</code>'); return
    if text == "/stats" and uid == OWNER_ID:
        total = len(orders)
        prio = sum(1 for o in orders.values() if o.get("priority"))
        send(chat_id,
             f'{em(E_INFO)} <b>СТАТИСТИКА</b>\n\n'
             f'{em(E_BOX)} Всего: <b>{total}</b>\n'
             f'{em(E_ROCKET)} Приоритетов: <b>{prio}</b>')
        return

    # PUBG ID
    s = str(chat_id)
    if user_data.get(s, {}).get("awaiting_pubg"):
        if re.match(r'^\d+$', text):
            pid = user_data[s].get("order_id")
            o = orders.get(pid)
            if o:
                o["pubg_id"] = text
                user_data[s]["awaiting_pubg"] = False
                send(chat_id, f'{em(E_CHECK)} PUBG ID: <code>{text}</code>')
                gm = {"parts": []}
                group_messages[pid] = gm
                r = send(GROUP_ID, group_text(pid), group_join(pid))
                if r.get("ok"): gm["msg_id"] = r["result"]["message_id"]
                send(OWNER_ID,
                     f'{em(E_CHECK)} <b>ЗАКАЗ ГОТОВ</b>\n\n'
                     f'{em(E_USER)} @{o.get("username", "—")}\n'
                     f'{em(E_BOX)} {o["item_name"]}\n'
                     f'{em(E_USER)} PUBG ID: <code>{text}</code>\n'
                     f'{em(E_PRICE)} {o.get("total_price", o["price"])}₽')
        else:
            send(chat_id, f'{em(E_CROSS)} Введите только цифры!')
        return

# ============================================================
# MAIN LOOP
# ============================================================
def main():
    logger.info("🚀 BOT v20 ЗАПУЩЕН")
    offset = 0
    while True:
        try:
            r = requests.get(f"{BASE_URL}/getUpdates",
                             params={"offset": offset, "timeout": 30,
                                     "allowed_updates": json.dumps(["message", "callback_query"])},
                             timeout=35).json()
            if not r.get("ok"):
                time.sleep(5); continue
            for upd in r.get("result", []):
                offset = upd["update_id"] + 1
                try:
                    if "callback_query" in upd: handle_cb(upd["callback_query"])
                    elif "message" in upd: handle_msg(upd["message"])
                except Exception as e:
                    logger.error(f"Ошибка: {e}"); traceback.print_exc()
            time.sleep(0.5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Критическая: {e}"); time.sleep(5)

if __name__ == "__main__":
    main()
