import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
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
    admin_add_id = State()
    admin_add_name = State()
    admin_add_price = State()
    admin_add_max = State()
    admin_add_post = State()
    admin_delete_product = State()
def get_main_menu():
    buttons = [
        [
            InlineKeyboardButton(text="👤 Mening holatim", callback_data="my_status"),
            InlineKeyboardButton(text="❓ Yordam", callback_data="help")
        ],
        [InlineKeyboardButton(text="🛍️ Yangi buyurtma berish", callback_data="new_order")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
@router.message(Command("start", "neworder"))
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
# Admin panel
@router.message(Command("admin"))
async def admin_panel(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Siz admin emassiz!")
        return
    products_list = "\n".join([f"{id}: {p['name']} - {p['price']:,} UZS (post_id: {p['post_id']})" for id, p in PRODUCTS.items()])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi mahsulot qo'shish", callback_data="add_product")],
        [InlineKeyboardButton(text="🗑️ Mahsulot o'chirish", callback_data="delete_product")]
    ])
    await message.answer(f"Admin panel:\n\nMavjud mahsulotlar:\n{products_list}\n\nNima qilmoqchisiz?", reply_markup=kb)
@router.callback_query(F.data == "add_product")
async def start_add_product(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(OrderStates.admin_add_id)
    await call.message.edit_text("Yangi mahsulot ID sini kiriting (masalan: MF8):")
@router.message(OrderStates.admin_add_id)
async def add_id(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    p_id = message.text.strip().upper()
    if p_id in PRODUCTS:
        await message.answer("Bunday ID allaqachon mavjud!")
        return
    await state.update_data(new_id=p_id)
    await state.set_state(OrderStates.admin_add_name)
    await message.answer("Mahsulot nomini kiriting:")
@router.message(OrderStates.admin_add_name)
async def add_name(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(name=message.text)
    await state.set_state(OrderStates.admin_add_price)
    await message.answer("Narxini kiriting (raqam):")
@router.message(OrderStates.admin_add_price)
async def add_price(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.text.isdigit():
        await message.answer("Faqat raqam kiriting!")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(OrderStates.admin_add_max)
    await message.answer("Maksimal sonini kiriting:")
@router.message(OrderStates.admin_add_max)
async def add_max(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.text.isdigit():
        await message.answer("Faqat raqam kiriting!")
        return
    await state.update_data(max_quantity=int(message.text))
    await state.set_state(OrderStates.admin_add_post)
    await message.answer("Kanal post ID sini kiriting (raqam):")
@router.message(OrderStates.admin_add_post)
async def add_post(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.text.isdigit():
        await message.answer("Faqat raqam kiriting!")
        return
    data = await state.get_data()
    PRODUCTS[data['new_id']] = {
        "name": data['name'],
        "price": data['price'],
        "max_quantity": data['max_quantity'],
        "post_id": int(message.text)
    }
    await message.answer(f"✅ Yangi mahsulot qo'shildi: {data['new_id']}")
    await state.clear()
@router.callback_query(F.data == "delete_product")
async def start_delete_product(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p_id in PRODUCTS:
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{p_id} - {PRODUCTS[p_id]['name']}", callback_data=f"del_{p_id}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")])
    await call.message.edit_text("O'chirmoqchi bo'lgan mahsulotni tanlang:", reply_markup=kb)
@router.callback_query(F.data.startswith("del_"))
async def delete_product(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return
    p_id = call.data.split("_")[1]
    if p_id in PRODUCTS:
        del PRODUCTS[p_id]
        await call.message.edit_text(f"✅ {p_id} mahsuloti o'chirildi!", reply_markup=get_main_menu())
    await state.clear()
@router.callback_query(F.data == "admin_back")
async def admin_back(call: types.CallbackQuery, state: FSMContext):
    await admin_panel(call.message, state)
dp.include_router(router)
async def main():
    print("Bot ishga tushmoqda...")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())
