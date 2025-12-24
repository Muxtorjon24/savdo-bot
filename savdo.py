import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
raw_admin = os.getenv("ADMIN_ID", "6269872662")
raw_channel = os.getenv("CHANNEL_ID", "-1002022910644")
ADMIN_ID = int(raw_admin)
CHANNEL_ID = int(raw_channel)
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "9860 1701 0904 2573")
PRODUCTS = {
    "MF1": {"name": "Daraxt", "price": 6000, "max_quantity": 20, "post_id": 454},
    "MF2": {"name": "Daraxt", "price": 4000, "max_quantity": 10, "post_id": 455},
    "MF3": {"name": "Daraxt", "price": 4000, "max_quantity": 15, "post_id": 456},
    "MF4": {"name": "Daraxt", "price": 5000, "max_quantity": 10, "post_id": 457},
    "MF5": {"name": "Daraxt", "price": 4000, "max_quantity": 10, "post_id": 458},
    "MF6": {"name": "Daraxt", "price": 3000, "max_quantity": 10, "post_id": 459},
    "MF7": {"name": "Daraxt", "price": 2000, "max_quantity": 20, "post_id": 460},
}
USER_ORDERS = {}
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
class OrderStates(StatesGroup):
    waiting_for_product_id = State()
    waiting_for_quantity = State()
    waiting_for_payment_proof = State()
def get_main_menu():
    buttons = [
        [
            InlineKeyboardButton(text="👤 Mening holatim", callback_data="my_status"),
            InlineKeyboardButton(text="❓ Yordam", callback_data="help")
        ],
        [InlineKeyboardButton(text="🛍️ Yangi buyurtma berish", callback_data="new_order")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Assalomu alaykum! Kerakli bo'limni tanlang:", reply_markup=get_main_menu())
@router.callback_query(F.data == "new_order")
async def start_new_order(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.waiting_for_product_id)
    await call.message.edit_text("Mahsulot ID sini kiriting (Masalan: MF1):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back")]]))
@router.message(OrderStates.waiting_for_product_id)
async def id_received(message: types.Message, state: FSMContext):
    p_id = message.text.strip().upper()
    if p_id not in PRODUCTS:
        await message.answer("Xato ID! Qayta kiriting (MF1-MF7):")
        return
    product = PRODUCTS[p_id]
    await state.update_data(p_id=p_id, p_name=product['name'], p_price=product['price'], max_qty=product['max_quantity'])
    try:
        await bot.forward_message(message.chat.id, CHANNEL_ID, product["post_id"])
    except Exception as e:
        print(f"Forward xatosi: {e}")
        await message.answer(f"📦 {product['name']}\nNarxi: {product['price']:,} UZS")
    await message.answer(f"Nechta buyurtma qilasiz? (Maks: {product['max_quantity']})")
    await state.set_state(OrderStates.waiting_for_quantity)
@router.message(OrderStates.waiting_for_quantity)
async def qty_received(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat raqam kiriting:")
        return
    qty = int(message.text)
    data = await state.get_data()
    if qty > data['max_qty']:
        await message.answer("Maksimum sonidan ko'p!")
        return
    total = qty * data['p_price']
    await state.update_data(qty=qty, total=total)
    await message.answer(f"Jami summa: {total:,} UZS\n💳 Karta: `{PAYMENT_CARD}`\nTo'lov qilib, chek rasmida yuboring.", parse_mode="Markdown")
    await state.set_state(OrderStates.waiting_for_payment_proof)
@router.message(OrderStates.waiting_for_payment_proof, F.photo)
async def payment_sent(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    if user_id not in USER_ORDERS: USER_ORDERS[user_id] = []
    order_idx = len(USER_ORDERS[user_id])
    USER_ORDERS[user_id].append({"name": data['p_name'], "qty": data['qty'], "status": "⏳ Kutilmoqda"})
    try:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"done_{user_id}_{order_idx}")]])
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🆕 Buyurtma!\nUser: {message.from_user.full_name}\nMahsulot: {data['p_name']}\nSumma: {data['total']:,} UZS", reply_markup=admin_kb)
    except Exception as e:
        print(f"Admin ga yuborish xatosi: {e}")
    await message.answer("✅ Chek adminga yuborildi.", reply_markup=get_main_menu())
    await state.clear()
@router.callback_query(F.data.startswith("done_"))
async def confirm_order(call: types.CallbackQuery):
    _, uid, idx = call.data.split("_")
    uid, idx = int(uid), int(idx)
    if uid in USER_ORDERS:
        USER_ORDERS[uid][idx]["status"] = "✅ Tasdiqlandi"
        try: await bot.send_message(uid, f"Sizning buyurtmangiz tasdiqlandi! ✅")
        except: pass
    await call.message.edit_caption(caption=call.message.caption + "\n\n✅ TASDIQLANDI")
@router.callback_query(F.data == "back")
async def back(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Asosiy menyu:", reply_markup=get_main_menu())
@router.callback_query(F.data == "my_status")
async def my_status(call: types.CallbackQuery):
    user_id = call.from_user.id
    if user_id not in USER_ORDERS or not USER_ORDERS[user_id]:
        await call.message.edit_text("Sizning buyurtmalaringiz yoʻq.\nYangi buyurtma berish uchun tugmani bosing.", reply_markup=get_main_menu())
        return
    orders_list = "\n".join([f"{i+1}. {order['name']} - {order['qty']} dona - {order['status']}" for i, order in enumerate(USER_ORDERS[user_id])])
    await call.message.edit_text(f"Sizning buyurtmalaringiz:\n{orders_list}", reply_markup=get_main_menu())
@router.callback_query(F.data == "help")
async def help_command(call: types.CallbackQuery):
    await call.message.edit_text("Yordam:\n- Yangi buyurtma berish uchun tugmani bosing.\n- Buyurtma jarayoni: ID → Son → Toʻlov cheki.\n- Savollar boʻlsa admin ga yozing.", reply_markup=get_main_menu())
dp.include_router(router)
async def main():
    print("Bot ishga tushmoqda...")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())
