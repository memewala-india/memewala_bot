import asyncio
import os
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    LabeledPrice, PreCheckoutQuery, SuccessfulPayment,
    FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from meme_generator import generate_meme
from keyboards import (
    main_menu, templates_menu, after_meme,
    limit_reached, premium_menu, back_to_main,
)
from templates_manager import fetch_templates, get_random_template
from database import (
    init_db, get_user, create_user,
    can_create_meme, register_meme, set_premium,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "MemeWalaIndiaBot")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

TEMPLATES = []
TEMPLATES_BY_ID = {}


class MemeStates(StatesGroup):
    choosing_template = State()
    waiting_top = State()
    waiting_bottom = State()


# === START ===
@dp.message(CommandStart(deep_link=True))
async def cmd_start_ref(message: Message, state: FSMContext):
    args = message.text.split()
    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1].replace("ref_", ""))
            if referred_by == message.from_user.id:
                referred_by = None
        except ValueError:
            pass
    await _register_and_greet(message, state, referred_by)


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await _register_and_greet(message, state)


async def _register_and_greet(message: Message, state: FSMContext, referred_by=None):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        create_user(
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name or "Dost",
            referred_by=referred_by,
        )
        if referred_by:
            await message.answer(
                "🎉 <b>Referral bonus mil gaya!</b>\n"
                "Aapke dost ko 1 free meme mila.",
                parse_mode="HTML"
            )
    
    await state.clear()
    
    text = (
        f"🎭 <b>MemeWala India</b> mein aapka swagat hai, "
        f"{message.from_user.first_name or 'Dost'}!\n\n"
        "Meme banao — Hinglish captions ke saath!\n\n"
        "✅ <b>Free:</b> 3 memes roz\n"
        "✅ <b>Dost bulao:</b> har dost pe 1 free meme\n"
        "✅ <b>Premium:</b> watermark hatayein\n\n"
        "Kya karna hai? Neeche se choose karo:"
    )
    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


# === BACK ===
@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(
            "🎭 <b>MemeWala India</b>\n\nKya karna hai?",
            reply_markup=main_menu(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            "🎭 <b>MemeWala India</b>\n\nKya karna hai?",
            reply_markup=main_menu(),
            parse_mode="HTML",
        )
    await callback.answer()


# === ВЫБОР ШАБЛОНА ===
@dp.callback_query(F.data == "choose_template")
async def choose_template(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📸 <b>Kaunsa template?</b>\n\n"
        "Neeche se choose karo:",
        reply_markup=templates_menu(TEMPLATES, page=0),
        parse_mode="HTML",
    )
    await state.set_state(MemeStates.choosing_template)
    await callback.answer()


@dp.callback_query(F.data.startswith("page_"))
async def change_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])
    await callback.message.edit_reply_markup(
        reply_markup=templates_menu(TEMPLATES, page=page)
    )
    await callback.answer()


@dp.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


# === ВЫБРАН ШАБЛОН ===
@dp.callback_query(F.data.startswith("tmpl_"))
async def template_chosen(callback: CallbackQuery, state: FSMContext):
    tmpl_id = callback.data.replace("tmpl_", "")
    template = TEMPLATES_BY_ID.get(tmpl_id)
    
    if not template:
        await callback.answer("Template nahi mila 😔")
        return
    
    can_do, reason = can_create_meme(callback.from_user.id)
    if not can_do:
        await callback.message.edit_text(
            "😔 <b>Aaj ke 3 free memes khatam ho gaye!</b>\n\n"
            "Kal wapas aao, ya:\n"
            "👥 Dost bulao — 1 free meme per dost\n"
            "⭐ Premium lo — unlimited memes",
            reply_markup=limit_reached(),
            parse_mode="HTML",
        )
        await callback.answer()
        return
    
    await state.update_data(template_id=tmpl_id)
    
    await callback.message.edit_text(
        f"🎨 Template: <b>{template['name']}</b>\n\n"
        "✏️ <b>Top text</b> likho (ya /skip bhejo):\n\n"
        "<i>Example: Jab boss salary badhane se mana kare</i>",
        parse_mode="HTML",
    )
    await state.set_state(MemeStates.waiting_top)
    await callback.answer()


# === RANDOM ===
@dp.callback_query(F.data == "random_template")
async def random_template(callback: CallbackQuery, state: FSMContext):
    can_do, reason = can_create_meme(callback.from_user.id)
    if not can_do:
        await callback.message.edit_text(
            "😔 Aaj ke free memes khatam!",
            reply_markup=limit_reached(),
            parse_mode="HTML",
        )
        await callback.answer()
        return
    
    template = get_random_template(TEMPLATES)
    if not template:
        await callback.answer("Templates load nahi hue 😔")
        return
    
    await state.update_data(template_id=template["id"])
    
    await callback.message.edit_text(
        f"🎲 Random template: <b>{template['name']}</b>\n\n"
        "✏️ <b>Top text</b> likho (ya /skip):",
        parse_mode="HTML",
    )
    await state.set_state(MemeStates.waiting_top)
    await callback.answer()


# === TOP TEXT ===
@dp.message(MemeStates.waiting_top)
async def handle_top(message: Message, state: FSMContext):
    top_text = "" if message.text == "/skip" else message.text.strip()
    await state.update_data(top=top_text)
    
    await message.answer(
        "✅ <b>Top text mil gaya!</b>\n\n"
        "✏️ Ab <b>bottom text</b> likho (ya /skip):\n\n"
        "<i>Example: Moye Moye</i>",
        parse_mode="HTML",
    )
    await state.set_state(MemeStates.waiting_bottom)


# === BOTTOM TEXT + ГЕНЕРАЦИЯ ===
@dp.message(MemeStates.waiting_bottom)
async def handle_bottom(message: Message, state: FSMContext):
    bottom_text = "" if message.text == "/skip" else message.text.strip()
    
    data = await state.get_data()
    tmpl_id = data.get("template_id")
    top_text = data.get("top", "")
    
    template = TEMPLATES_BY_ID.get(tmpl_id)
    if not template:
        await message.answer("😔 Kuch galat ho gaya. /start se phir try karo.")
        await state.clear()
        return
    
    user = get_user(message.from_user.id)
    is_premium = user and user["premium"]
    
    msg = await message.answer("🎨 <b>Meme ban raha hai...</b> ⏳", parse_mode="HTML")
    
    try:
        output_path = generate_meme(
            template_path=template["file_path"],
            top_text=top_text,
            bottom_text=bottom_text,
            user_id=message.from_user.id,
            watermark=not is_premium,
        )
        
        register_meme(message.from_user.id)
        
        photo = FSInputFile(output_path)
        
        if is_premium:
            caption = (
                "✅ <b>Meme ready!</b> (Premium — bina watermark)\n\n"
                "Share karo aur doston ko dikhao! 🔥"
            )
        else:
            caption = (
                "✅ <b>Meme ready!</b>\n\n"
                "⭐ Watermark hatao — sirf 5 Stars\n"
                "👥 Ya dost bulao — free meme pao!"
            )
        
        await msg.delete()
        await message.answer_photo(
            photo,
            caption=caption,
            reply_markup=after_meme(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Ошибка генерации мема: {e}")
        await msg.edit_text("😔 Meme nahi ban paya. Phir try karo.")
    
    await state.clear()


# === INVITE ===
@dp.callback_query(F.data == "invite")
async def invite(callback: CallbackQuery):
    user_id = callback.from_user.id
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    
    user = get_user(user_id)
    referrals = user["referrals"] if user else 0
    free = user["free_memes"] if user else 0
    
    text = (
        "👥 <b>Dost bulao — free meme pao!</b>\n\n"
        "Aapka invite link:\n"
        f"<code>{link}</code>\n\n"
        f"📊 Aapne ab tak <b>{referrals}</b> dost bulaaye\n"
        f"🎁 Free memes: <b>{free}</b>\n\n"
        "Har dost pe 1 free meme milega!"
    )
    
    share_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 WhatsApp pe share",
            url=f"https://wa.me/?text=Best%20meme%20bot!%20{link}"
        )],
        [InlineKeyboardButton(
            text="📤 Telegram pe share",
            url=f"https://t.me/share/url?url={link}&text=Meme%20banao%20free%20mein!"
        )],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_main")],
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=share_kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=share_kb, parse_mode="HTML")
    await callback.answer()


# === STATS ===
@dp.callback_query(F.data == "my_stats")
async def my_stats(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("User nahi mila")
        return
    
    premium = "✅ Haan" if user["premium"] else "❌ Nahi"
    
    text = (
        "📊 <b>Aapki stats</b>\n\n"
        f"🎨 Total memes banaye: <b>{user['total_memes']}</b>\n"
        f"📅 Aaj ke memes: <b>{user['memes_today']}/3</b>\n"
        f"👥 Doston ko bulaya: <b>{user['referrals']}</b>\n"
        f"🎁 Free memes bache: <b>{user['free_memes']}</b>\n"
        f"⭐ Premium: <b>{premium}</b>"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=back_to_main(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=back_to_main(), parse_mode="HTML")
    await callback.answer()


# === PREMIUM INFO ===
@dp.callback_query(F.data == "premium_info")
async def premium_info(callback: CallbackQuery):
    text = (
        "⭐ <b>MemeWala Premium</b>\n\n"
        "🎁 <b>Kya milega:</b>\n"
        "✅ Bina watermark wale memes\n"
        "✅ Unlimited memes\n"
        "✅ Priority support\n\n"
        "💰 <b>Prices:</b>\n"
        "• 30 din — 150 Stars (~₹210)\n"
        "• Lifetime — 300 Stars (~₹420)\n\n"
        "Telegram Stars se pay karo!"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=premium_menu(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=premium_menu(), parse_mode="HTML")
    await callback.answer()


# === ПОКУПКИ ===
@dp.callback_query(F.data == "buy_no_watermark")
async def buy_no_watermark(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass
    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Watermark Hatao",
            description="Agla meme bina watermark ke banega",
            payload="remove_watermark_1",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="No Watermark", amount=5)],
        )
    except Exception as e:
        logger.error(f"Invoice error: {e}")
        try:
            await callback.message.answer("Payment error. Try again.")
        except Exception:
            pass


@dp.callback_query(F.data == "buy_unlimited")
async def buy_unlimited(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass
    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="MemeWala Premium — 30 din",
            description="Unlimited memes + bina watermark",
            payload="premium_30",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="30 din Unlimited", amount=150)],
        )
    except Exception as e:
        logger.error(f"Invoice error: {e}")
        try:
            await callback.message.answer("Payment error. Try again.")
        except Exception:
            pass


@dp.callback_query(F.data == "buy_lifetime")
async def buy_lifetime(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass
    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="MemeWala Lifetime",
            description="Hamesha ke liye unlimited memes",
            payload="premium_lifetime",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Lifetime Access", amount=300)],
        )
    except Exception as e:
        logger.error(f"Invoice error: {e}")
        try:
            await callback.message.answer("Payment error. Try again.")
        except Exception:
            pass


# === PLATYON ===
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def payment_success(message: Message):
    payment: SuccessfulPayment = message.successful_payment
    payload = payment.invoice_payload
    user_id = message.from_user.id
    
    if payload == "remove_watermark_1":
        await message.answer(
            "🎉 <b>Watermark hat gaya!</b>\n\n"
            "Agla meme bina watermark ke banega.",
            parse_mode="HTML",
            reply_markup=back_to_main(),
        )
    elif payload in ("premium_30", "premium_lifetime"):
        set_premium(user_id)
        await message.answer(
            "🌟 <b>Premium activate ho gaya!</b>\n\n"
            "Ab aap unlimited memes bina watermark ke bana sakte ho!\n\n"
            "Dhanyavaad! 🙏",
            parse_mode="HTML",
            reply_markup=back_to_main(),
        )


# === SHARE ===
@dp.callback_query(F.data == "share")
async def share(callback: CallbackQuery):
    link = f"https://t.me/{BOT_USERNAME}"
    share_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 WhatsApp",
            url=f"https://wa.me/?text=Best%20meme%20bot!%20{link}"
        )],
        [InlineKeyboardButton(
            text="📤 Telegram",
            url=f"https://t.me/share/url?url={link}&text=Meme%20banao%20free!"
        )],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_main")],
    ])
    await callback.message.answer("Kahan share karna hai?", reply_markup=share_kb)
    await callback.answer()


# === HELP ===
@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📖 <b>MemeWala India — Help</b>\n\n"
        "/start — Главное меню\n"
        "/help — Эта помощь\n"
        "/skip — Пропустить текст\n\n"
        "<b>Как сделать мем:</b>\n"
        "1. Нажми «Meme banao»\n"
        "2. Выбери шаблон\n"
        "3. Напиши top и bottom текст\n"
        "4. Получи мем!\n\n"
        "<b>Free:</b> 3 мема в день\n"
        "<b>Dost bulao:</b> +1 мем за друга\n"
        "<b>Premium:</b> безлимит без watermark"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())


# === ЗАПУСК ===
async def main():
    global TEMPLATES, TEMPLATES_BY_ID
    
    print("🔧 Инициализация базы данных...")
    init_db()
    
    print("📥 Загрузка шаблонов...")
    TEMPLATES = await fetch_templates()
    TEMPLATES_BY_ID = {t["id"]: t for t in TEMPLATES}
    print(f"✅ Шаблонов в памяти: {len(TEMPLATES)}")
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("🚀 Бот запущен! Нажми Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())