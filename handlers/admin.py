import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import ADMIN_ID, DB_NAME
from states import SurveyCreation, ChannelManagement, SurveyPosting

router = Router()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Admin panelga xush kelibsiz.\n\n/create_survey - Yangi so'rovnoma\n/delete_survey - So'rovnomani o'chirish\n/channels - Kanallar\n/survey_channels - 🔗 So'rovnoma Kanallari\n/finish_survey - Yakunlash\n/post_survey - Kanalga post\n/post_results - Natijani kanalga yuborish")

@router.message(Command("delete_survey"))
async def cmd_delete_survey(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, title FROM surveys WHERE is_active = 1") as cursor:
            surveys = await cursor.fetchall()

    if not surveys:
        await message.answer("O'chirish uchun faol so'rovnomalar yo'q.")
        return

    # Build keyboard
    keyboard = []
    for s_id, title in surveys:
        keyboard.append([InlineKeyboardButton(text=f"❌ {title}", callback_data=f"del_survey_{s_id}")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("O'chirmoqchi bo'lgan so'rovnomangizni tanlang:", reply_markup=markup)

@router.callback_query(F.data.startswith("del_survey_"))
async def process_delete_survey(callback: CallbackQuery):
    survey_id = int(callback.data.split("_")[2])
    
    async with aiosqlite.connect(DB_NAME) as db:
        # We can either delete or set is_active = 0. Setting is_active = 0 is safer.
        await db.execute("UPDATE surveys SET is_active = 0 WHERE id = ?", (survey_id,))
        await db.commit()
    
    await callback.answer("So'rovnoma o'chirildi!", show_alert=True)
    await callback.message.delete()

# --- Channel Management ---

@router.message(Command("channels"))
async def cmd_channels(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, name, url FROM channels") as cursor:
            channels = await cursor.fetchall()
            
    text = "📢 **Ulangan kanallar:**\n\n"
    keyboard = []
    
    if channels:
        for c_id, name, url in channels:
            text += f"{name} - {url}\n"
            keyboard.append([InlineKeyboardButton(text=f"❌ {name} ni o'chirish", callback_data=f"del_channel_{c_id}")])
    else:
        text += "Hozircha kanallar yo'q."
        
    keyboard.append([InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")])
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(text, reply_markup=markup)

@router.callback_query(F.data == "add_channel")
async def ask_channel(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Yangi kanal qo'shish uchun, o'sha kanaldan birorta xabarni shu yerga **Forward** (uzatish) qiling.\n\nEslatma: Bot o'sha kanalda ADMIN bo'lishi shart!")
    await state.set_state(ChannelManagement.waiting_for_forward)
    await callback.answer()

@router.message(ChannelManagement.waiting_for_forward)
async def process_channel_forward(message: Message, state: FSMContext, bot):
    if not message.forward_from_chat:
        await message.answer("Iltimos, kanaldan xabar forward qiling yoki bekor qilish uchun /cancel deb yozing.")
        return
        
    chat_id = message.forward_from_chat.id
    chat_title = message.forward_from_chat.title
    
    # Check if bot is admin
    try:
        member = await bot.get_chat_member(chat_id, bot.id)
        if member.status not in ["administrator", "creator"]:
             await message.answer("Bot bu kanalda admin emas! Iltimos avval botni kanalga admin qiling.")
             return
    except Exception as e:
        await message.answer(f"Xatolik: Bot kanalni ko'ra olmayapti. Botni admin qilganingizga ishonch hosil qiling.\nError: {e}")
        return

    # Get invite link
    try:
        chat = await bot.get_chat(chat_id)
        invite_link = chat.invite_link
        if not invite_link:
             # Try to export/generate one if not public?
             # Or just use username if public
             if chat.username:
                 invite_link = f"https://t.me/{chat.username}"
             else:
                 await message.answer("Kanal havolasini aniqlab bo'lmadi. Iltimos kanal ochiq (public) ekanligiga ishonch hosil qiling yoki botga havola yaratish huquqini bering.")
                 return
    except Exception:
         invite_link = "Noma'lum havola"

    # Save to DB
    async with aiosqlite.connect(DB_NAME) as db:
        # Check duplicate
        async with db.execute("SELECT 1 FROM channels WHERE channel_id = ?", (str(chat_id),)) as cursor:
            if await cursor.fetchone():
                await message.answer("Bu kanal allaqachon qo'shilgan!")
                await state.clear()
                return

        await db.execute("INSERT INTO channels (channel_id, name, url) VALUES (?, ?, ?)", (str(chat_id), chat_title, invite_link))
        await db.commit()
        
    await message.answer(f"✅ Kanal qo'shildi:\nNom: {chat_title}\nID: {chat_id}\nHavola: {invite_link}")
    await state.clear()

@router.callback_query(F.data.startswith("del_channel_"))
async def delete_channel(callback: CallbackQuery):
    c_id = int(callback.data.split("_")[2])
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM channels WHERE id = ?", (c_id,))
        await db.commit()
        
    await callback.answer("Kanal o'chirildi!", show_alert=True)
    await callback.message.delete()
    # Optionally refresh the list
    # await cmd_channels(callback.message) # message object might be different, simpler to just delete.

# --- End Channel Management ---


    await callback.message.delete()
    # Optionally refresh the list
    # await cmd_channels(callback.message) # message object might be different, simpler to just delete.

# --- End Channel Management ---

# --- Post Survey to Channel ---

@router.message(Command("post_survey"))
async def cmd_post_survey(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, title FROM surveys WHERE is_active = 1") as cursor:
            surveys = await cursor.fetchall()
            
    if not surveys:
        await message.answer("Yuborish uchun faol so'rovnomalar yo'q.")
        return

    text = "📢 **Qaysi so'rovnomani kanalga chiqarmoqchisiz?**"
    keyboard = []
    for s_id, title in surveys:
        keyboard.append([InlineKeyboardButton(text=f"📤 {title}", callback_data=f"post_select_{s_id}")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup)

@router.callback_query(F.data.startswith("post_select_"))
async def ask_target_channel(callback: CallbackQuery, state: FSMContext):
    survey_id = int(callback.data.split("_")[2])
    await state.update_data(post_survey_id=survey_id)
    
    await callback.message.answer(
        "So'rovnomani qaysi kanalga yubormoqchisiz?\n\n"
        "Kanalning **Username**ini (masalan: @mening_kanalim) yoki **ID**sini kiriting.\n"
        "__Eslatma: Bot o'sha kanalda ADMIN bo'lishi shart!__"
    )
    await state.set_state(SurveyPosting.waiting_for_channel)
    await callback.answer()

@router.message(SurveyPosting.waiting_for_channel)
async def perform_post_survey(message: Message, state: FSMContext, bot):
    channel_id = message.text.strip()
    data = await state.get_data()
    survey_id = data.get('post_survey_id')
    is_result = data.get('is_result_post', False)
    
    # Get survey details
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT title, description, image_file_id FROM surveys WHERE id = ?", (survey_id,)) as cursor:
             survey = await cursor.fetchone()
        
        async with db.execute("SELECT id, full_name, votes_count FROM candidates WHERE survey_id = ? ORDER BY votes_count DESC", (survey_id,)) as cursor:
             candidates = await cursor.fetchall()

    if not survey:
        await message.answer("Xatolik: So'rovnoma topilmadi.")
        await state.clear()
        return

    title, description, image_file_id = survey

    if is_result:
        # Format results message
        text = f"🏁 <b>SO'ROVNOMA NATIJALARI</b>\n\n📌 <b>{title}</b>\n\n"
        
        # Medal emojis for top 3
        medals = ["🥇", "🥈", "🥉"]
        
        total_votes = sum(c[2] for c in candidates)
        
        for i, (c_id, name, votes) in enumerate(candidates):
            icon = medals[i] if i < 3 else "▪️"
            percent = (votes / total_votes * 100) if total_votes > 0 else 0
            text += f"{icon} <b>{votes} ovoz</b> ({percent:.1f}%) — {name}\n"
            
        text += f"\n🗳 Jami ovozlar: {total_votes}"
        
        try:
            if image_file_id:
                # Results with image? Maybe separate message or caption. Caption limit 1024 chars.
                if len(text) > 1000:
                    await bot.send_photo(chat_id=channel_id, photo=image_file_id)
                    await bot.send_message(chat_id=channel_id, text=text, parse_mode="HTML")
                else:
                    await bot.send_photo(chat_id=channel_id, photo=image_file_id, caption=text, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=channel_id, text=text, parse_mode="HTML")
            
            await message.answer(f"✅ Natijalar {channel_id} kanaliga yuborildi!")
        except Exception as e:
            await message.answer(f"❌ Xatolik: {e}")

    else:
        # Standard Survey Post
        text = f"{description}" # Title removed as per request
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for c_id, name, votes in candidates:
            builder.button(text=f"{name} ({votes})", callback_data=f"vote_{survey_id}_{c_id}")
        builder.adjust(1)
        kb = builder.as_markup()

        try:
            if image_file_id:
                await bot.send_photo(chat_id=channel_id, photo=image_file_id, caption=text, reply_markup=kb)
            else:
                await bot.send_message(chat_id=channel_id, text=text, reply_markup=kb)
            
            await message.answer(f"✅ So'rovnoma {channel_id} kanaliga muvaffaqiyatli yuborildi!")
        except Exception as e:
            await message.answer(f"❌ Xatolik yuz berdi: {e}\n\nBotni kanalga admin qilganingizni tekshiring.")
        
    await state.clear()


    await state.clear()


# --- Finish Survey & Post Results ---

@router.message(Command("finish_survey"))
async def cmd_finish_survey(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    async with aiosqlite.connect(DB_NAME) as db:
        # Get active and NOT closed surveys. Or just active ones.
        # If is_active=1 and is_closed=0 -> Running
        async with db.execute("SELECT id, title FROM surveys WHERE is_active = 1 AND is_closed = 0") as cursor:
            surveys = await cursor.fetchall()
            
    if not surveys:
        await message.answer("Tugatish uchun faol so'rovnomalar yo'q.")
        return

    text = "🏁 **Qaysi so'rovnomani yakunlamoqchisiz?**\n(Yakunlangach ovoz berish to'xtatiladi)"
    keyboard = []
    for s_id, title in surveys:
        keyboard.append([InlineKeyboardButton(text=f"🛑 {title}", callback_data=f"finish_survey_{s_id}")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup)

@router.callback_query(F.data.startswith("finish_survey_"))
async def process_finish_survey(callback: CallbackQuery):
    survey_id = int(callback.data.split("_")[2])
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE surveys SET is_closed = 1 WHERE id = ?", (survey_id,))
        await db.commit()
    
    await callback.answer("So'rovnoma yakunlandi!", show_alert=True)
    await callback.message.edit_text("✅ So'rovnoma muvaffaqiyatli yakunlandi.")

@router.message(Command("post_results"))
async def cmd_post_results(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    async with aiosqlite.connect(DB_NAME) as db:
        # Get finished surveys logic? Or any survey? 
        # Usually we post results of closed surveys.
        # Let's show all active (visible) surveys.
        async with db.execute("SELECT id, title FROM surveys WHERE is_active = 1 AND is_closed = 1") as cursor:
            surveys = await cursor.fetchall()
            
    if not surveys:
        await message.answer("Natijasini chiqarish uchun yakunlangan so'rovnomalar yo'q.")
        return

    text = "📊 **Qaysi so'rovnoma natijasini kanalga chiqarmoqchisiz?**"
    keyboard = []
    for s_id, title in surveys:
        keyboard.append([InlineKeyboardButton(text=f"📈 {title}", callback_data=f"res_select_{s_id}")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup)

@router.callback_query(F.data.startswith("res_select_"))
async def ask_target_channel_results(callback: CallbackQuery, state: FSMContext):
    survey_id = int(callback.data.split("_")[2])
    await state.update_data(post_survey_id=survey_id)
    # We can reuse SurveyPosting state
    await callback.message.answer(
        "Natijani qaysi kanalga yubormoqchisiz?\nUsername (@kanal) yoki ID kiriting.\nBot admin bo'lishi shart."
    )
    # Reuse handling logic? 
    # The existing SurveyPosting.waiting_for_channel logic posts the survey itself (with vote buttons).
    # We need a DIFFERENT logic for results (text list). 
    # So we need a status to differentiate, OR a different state.
    # Let's make a new state or just check a flag in data.
    await state.update_data(is_result_post=True) 
    await state.set_state(SurveyPosting.waiting_for_channel)
    await callback.answer()

@router.message(Command("create_survey"))
async def start_survey_creation(message: Message, state: FSMContext):
# ... existing code ... (This is just context, I will append new handlers)

# ... (Actually I'll append to the end of file for cleanliness or insert before create_survey if it makes sense. 
# Let's insert before create_survey for grouping commands).

# Let's stick to appending new logic or finding a good insertion point.
# I will append the close logic after post_survey logic and before create_survey.

    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("So'rovnoma sarlavhasini kiriting:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(SurveyCreation.waiting_for_title)

@router.message(SurveyCreation.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Endi so'rovnoma matni/tavsifini kiriting:")
    await state.set_state(SurveyCreation.waiting_for_description)

@router.message(SurveyCreation.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("So'rovnoma uchun rasm yuboring (yoki /skip deb yozing):")
    await state.set_state(SurveyCreation.waiting_for_image)

@router.message(SurveyCreation.waiting_for_image, F.photo)
async def process_image(message: Message, state: FSMContext):
    image_file_id = message.photo[-1].file_id
    await state.update_data(image_file_id=image_file_id)
    await message.answer("Endi nomzodlarni kiriting.\nHar bir nomzodni alohida xabar sifatida yuboring.\nTugatish uchun /done deb yozing.")
    await state.update_data(candidates=[])
    await state.set_state(SurveyCreation.waiting_for_candidates)

@router.message(SurveyCreation.waiting_for_image, Command("skip"))
async def skip_image(message: Message, state: FSMContext):
    await state.update_data(image_file_id=None)
    await message.answer("Rasm o'tkazib yuborildi.\nEndi nomzodlarni kiriting.\nHar bir nomzodni alohida xabar sifatida yuboring.\nTugatish uchun /done deb yozing.")
    await state.update_data(candidates=[])
    await state.set_state(SurveyCreation.waiting_for_candidates)

@router.message(SurveyCreation.waiting_for_candidates, Command("done"))
async def finish_candidates(message: Message, state: FSMContext):
    data = await state.get_data()
    candidates = data.get("candidates", [])
    
    if not candidates:
        await message.answer("Kamida bitta nomzod kiritish kerak! Davom eting.")
        return

    # Save to DB
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO surveys (title, description, image_file_id, is_active, deadline) VALUES (?, ?, ?, 1, ?)",
            (data['title'], data['description'], data['image_file_id'], "2025-01-25 21:00") # Hardcoded deadline based on prompt or add step
        )
        survey_id = cursor.lastrowid
        
        for candidate in candidates:
            await db.execute("INSERT INTO candidates (survey_id, full_name) VALUES (?, ?)", (survey_id, candidate))
        
        await db.commit()
    
    await message.answer(f"So'rovnoma yaratildi!\nID: {survey_id}\nNomzodlar soni: {len(candidates)}")
    await state.clear()

@router.message(SurveyCreation.waiting_for_candidates)
async def process_candidate(message: Message, state: FSMContext):
    data = await state.get_data()
    candidates = data.get("candidates", [])
    candidates.append(message.text)
    await state.update_data(candidates=candidates)
    await message.answer(f"Nomzod qo'shildi: {message.text}\nYana yuboring yoki /done ni bosing.")
