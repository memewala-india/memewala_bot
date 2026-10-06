from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Meme banao", callback_data="choose_template")],
        [InlineKeyboardButton(text="🎲 Random meme", callback_data="random_template")],
        [InlineKeyboardButton(text="👥 Dost ko bulao", callback_data="invite")],
        [InlineKeyboardButton(text="⭐ Premium", callback_data="premium_info")],
        [InlineKeyboardButton(text="📊 Meri stats", callback_data="my_stats")],
    ])


def templates_menu(templates, page=0):
    per_page = 5
    start = page * per_page
    end = start + per_page
    page_items = templates[start:end]
    total_pages = (len(templates) + per_page - 1) // per_page
    
    buttons = []
    for i, t in enumerate(page_items, start=1):
        buttons.append([
            InlineKeyboardButton(
                text=f"{start + i}. {t['name'][:35]}",
                callback_data=f"tmpl_{t['id']}"
            )
        ])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if end < len(templates):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page_{page+1}"))
    
    if nav:
        buttons.append(nav)
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def after_meme():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Watermark hatao — 5 Stars", callback_data="buy_no_watermark")],
        [InlineKeyboardButton(text="📤 Share", callback_data="share")],
        [InlineKeyboardButton(text="🎨 Naya meme", callback_data="back_main")],
    ])


def limit_reached():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Dost bulao — 1 free meme", callback_data="invite")],
        [InlineKeyboardButton(text="⭐ Unlimited — 150 Stars", callback_data="buy_unlimited")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_main")],
    ])


def premium_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 30 din unlimited — 150 Stars", callback_data="buy_unlimited")],
        [InlineKeyboardButton(text="⭐ Lifetime — 300 Stars", callback_data="buy_lifetime")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_main")],
    ])


def back_to_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_main")]
    ])