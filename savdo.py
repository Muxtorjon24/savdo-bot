import os
import asyncio
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================== ENV ==================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not BOT_TOKEN or not CHANNEL_ID or not ADMIN_ID:
    raise RuntimeError("❌ .env faylda BOT_TOKEN / CHANNEL_ID / ADMIN_ID yo‘q!")

PAYMENT_CARD = "9860 1701 0904 2573"

# ================== PRODUCTS ==================
PRODUCTS = {
    "MF1": {"name": "Daraxt", "price": 6000, "max_quantity": 20, "post_id": 454},
    "MF2": {"name": "Daraxt", "price": 4000, "max_quantity": 10, "post_id": 455},
    "MF3": {"name": "Daraxt", "price": 4000, "max_quantity": 15, "post_id": 456},
    "MF4": {"name": "Daraxt", "price": 5000, "max_quantity": 10, "post_id": 457},
}

# ================== BOT ==================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# ================== STATES ==================
class OrderStates(StatesGroup):
    waiting_for_product_id = State()
    waiting_for_quantity = State()
    waiting_for_payment_proof = State()
    admin_adding_product = State()

# ================== START ==================
@router.message(Command("start", "neworder"))
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Assalomu alaykum 😊\n\n"
        "Buyurtma berish uchun tovar ID sini kiriting.\n"
        "Misol: <b>MF1</b>",
        parse_mode="HTML"
    )
    await state.set_state(OrderStates.waiting_for_product_id)

# ================== PRODUCT ID ==================
@router.message(OrderStates.waiting_for_product_id)
async def product_id_received(message: types.Message, state: FSMContext):
    product_id = message.text.strip().upper()

    if product_id not in PRODUCTS:
        await message.answer("❌ Bunday tovar yo‘q. Qayta urinib ko‘ring:")
        return

    product = PRODUCTS[product_id]

    try:
        await bot.forward_message(
            chat_id=message.from_user.id,
            from_chat_id=CHANNEL_ID,
            message_id=product["post_id"]
        )
    except Exception:
        await message.answer(
            f"<b>{product['name']}</b>\nNarxi: {product['price']:,} UZS",
            parse_mode="HTML"
        )

    await message.answer(
        f"Nechta buyurtma qilasiz?\nMaksimal: <b>{product['max_quantity']}</b>",
        parse_mode="HTML"
    )

    await state.update_data(product_id=product_id, product=product)
    await state.set_state(OrderStates.waiting_for_quantity)

# ================== QUANTITY ==================
@router.message(OrderStates.waiting_for_quantity)
async def quantity_received(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat son kiriting:")
        return

    quantity = int(message.text)
    data = await state.get_data()
    product = data["product"]

    if not 1 <= quantity <= product["max_quantity"]:
        await message.answer(f"1–{product['max_quantity']} oralig‘ida kiriting:")
        return

    total_price = quantity * product["price"]

    await message.answer(
        f"💳 To‘lov qiling:\n<code>{PAYMENT_CARD}</code>\n\n"
        f"Jami: <b>{total_price:,} UZS</b>\n\n"
        f"Chekni rasm qilib yuboring.",
        parse_mode="HTML"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Tasdiqlash",
            callback_data=f"confirm_{message.from_user.id}_{data['product_id']}_{quantity}"
        )],
        [InlineKeyboardButton(
            text="❌ Rad etish",
            callback_data=f"reject_{message.from_user.id}"
        )]
    ])

    admin_msg = await bot.send_message(
        ADMIN_ID,
        f"🆕 BUYURTMA\n\n"
        f"👤 {message.from_user.full_name}\n"
        f"🆔 {data['product_id']}\n"
        f"📦 {quantity} dona\n"
        f"💰 {total_price:,} UZS\n\n"
        f"⏳ Chek kutilmoqda...",
        reply_markup=kb
    )

    await state.update_data(
        admin_msg_id=admin_msg.message_id,
        quantity=quantity,
        total_price=total_price,
        user_id=message.from_user.id
    )
    await state.set_state(OrderStates.waiting_for_payment_proof)

# ================== PAYMENT PROOF ==================
@router.message(OrderStates.waiting_for_payment_proof, lambda m: m.content_type == ContentType.PHOTO)
async def payment_proof_received(message: types.Message, state: FSMContext):
    data = await state.get_data()

    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

    await message.answer("✅ Chek qabul qilindi. Tekshirilmoqda...")
    await state.clear()

# ================== CALLBACKS ==================
@router.callback_query(lambda c: c.data.startswith("confirm_"))
async def confirm_order(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Ruxsat yo‘q", show_alert=True)

    _, user_id, product_id, qty = callback.data.split("_")
    product = PRODUCTS[product_id]
    total = int(qty) * product["price"]

    await bot.send_message(
        int(user_id),
        f"🎉 Buyurtma tasdiqlandi!\n"
        f"{product['name']} — {qty} dona\n"
        f"Jami: {total:,} UZS"
    )

    await callback.message.edit_reply_markup(None)
    await callback.message.edit_text(callback.message.text + "\n\n✅ TASDIQLANDI")
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_order(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Ruxsat yo‘q", show_alert=True)

    user_id = callback.data.split("_")[1]
    await bot.send_message(int(user_id), "❌ Buyurtma rad etildi.")
    await callback.message.edit_reply_markup(None)
    await callback.message.edit_text(callback.message.text + "\n\n❌ RAD ETILDI")
    await callback.answer()

# ================== RUN ==================
dp.include_router(router)

async def main():
    print("🤖 Bot ishga tushdi")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
