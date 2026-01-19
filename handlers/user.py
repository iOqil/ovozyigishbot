import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import DB_NAME
from keyboards.default import main_menu
from keyboards.inline import surveys_list_keyboard, candidates_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Assalomu alaykum! Xush kelibsiz.", reply_markup=main_menu())

@router.message(F.text == "🗳 Ovoz berish")
async def show_surveys(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        # Get active surveys (both open and closed, as long as is_active=1)
        async with db.execute("SELECT id, title, is_closed FROM surveys WHERE is_active = 1") as cursor:
            surveys = await cursor.fetchall()
            
    if not surveys:
        await message.answer("Hozircha faol so'rovnomalar yo'q.")
        return
    
    # Custom keyboard to show status
    builder = InlineKeyboardBuilder()
    for s_id, title, is_closed in surveys:
        status_icon = "🏁" if is_closed else "🗳"
        builder.button(text=f"{status_icon} {title}", callback_data=f"survey_{s_id}")
    builder.adjust(1)

    await message.answer("Mavjud so'rovnomalar:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("survey_"))
async def show_survey_details(callback: CallbackQuery, bot):
    survey_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    # Check subscriptions
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT channel_id, name, url FROM channels") as cursor:
            channels = await cursor.fetchall()
            
    not_subscribed = []
    if channels:
        for ch_id, ch_name, ch_url in channels:
            try:
                member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
                if member.status not in ["creator", "administrator", "member"]:
                    not_subscribed.append((ch_name, ch_url))
            except Exception:
                 # If bot can't check, assume subscribed or ignore
                 pass
    
    if not_subscribed:
        text = "❌ <b>Ovoz berish uchun quyidagi kanallarga obuna bo'lishingiz shart:</b>\n\n"
        kb_builder = InlineKeyboardBuilder()
        for name, url in not_subscribed:
            kb_builder.button(text=f"➕ {name}", url=url)
            text += f"• {name}\n"
        
        kb_builder.button(text="✅ Obuna bo'ldim", callback_data=f"survey_{survey_id}")
        kb_builder.adjust(1)
        
        if callback.message.reply_markup:
             await callback.answer("Siz ko'rsatilgan kanallarga obuna bo'lmagansiz, so'rovnomada qatnashish uchun iltimos shu kanallarga obuna bo'ling", show_alert=True)
        else:
             await callback.answer()

        try:
            await callback.message.edit_text(text, reply_markup=kb_builder.as_markup())
        except Exception:
            pass
        return

    async with aiosqlite.connect(DB_NAME) as db:
        # Get survey details
        async with db.execute("SELECT title, description, image_file_id, is_closed FROM surveys WHERE id = ?", (survey_id,)) as cursor:
            survey = await cursor.fetchone()
            
        if not survey:
            await callback.answer("So'rovnoma topilmadi.")
            return

        title, description, image_file_id, is_closed = survey

        # Get candidates
        async with db.execute("SELECT id, full_name, votes_count FROM candidates WHERE survey_id = ? ORDER BY votes_count DESC", (survey_id,)) as cursor:
            candidates = await cursor.fetchall()

    text = f"{description}" # No title as requested
    
    if is_closed:
        text = f"🏁 <b>SO'ROVNOMA YAKUNLANGAN</b>\n\n{text}\n\nNatijalarni ko'rish uchun quyidagi tugmani bosing."
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text="📊 Natijalarni ko'rish", callback_data=f"results_{survey_id}")
        kb = kb_builder.as_markup()
    else:
        kb = candidates_keyboard(survey_id, candidates)
    
    # Try to send image if available, else text only
    if image_file_id:
        try:
            await callback.message.answer_photo(photo=image_file_id, caption=text, reply_markup=kb, parse_mode="HTML")
            await callback.message.delete()
        except Exception:
            try:
                 await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except:
                 await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
                 await callback.message.delete()
    else:
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except:
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
            await callback.message.delete()

@router.callback_query(F.data.startswith("results_"))
async def show_results(callback: CallbackQuery):
    survey_id = int(callback.data.split("_")[1])
    
    async with aiosqlite.connect(DB_NAME) as db:
         async with db.execute("SELECT title FROM surveys WHERE id = ?", (survey_id,)) as cursor:
            res = await cursor.fetchone()
            title = res[0] if res else "Results"

         async with db.execute("SELECT full_name, votes_count FROM candidates WHERE survey_id = ? ORDER BY votes_count DESC", (survey_id,)) as cursor:
            candidates = await cursor.fetchall()
            
    text = f"🏁 <b>SO'ROVNOMA NATIJALARI</b>\n\n📌 <b>{title}</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    total_votes = sum(c[1] for c in candidates)
    
    for i, (name, votes) in enumerate(candidates):
        icon = medals[i] if i < 3 else "▪️"
        percent = (votes / total_votes * 100) if total_votes > 0 else 0
        text += f"{icon} <b>{votes}</b> ({percent:.1f}%) — {name}\n"
        
    text += f"\n🗳 Jami ovozlar: {total_votes}"
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("vote_"))
async def register_vote(callback: CallbackQuery):
    _, survey_id, candidate_id = callback.data.split("_")
    survey_id = int(survey_id)
    candidate_id = int(candidate_id)
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        # Check if already voted
        async with db.execute("SELECT 1 FROM votes WHERE user_id = ? AND survey_id = ?", (user_id, survey_id)) as cursor:
            if await cursor.fetchone():
                await callback.answer("Siz allaqachon ovoz bergansiz!", show_alert=True)
                return

        # Register vote
        await db.execute("INSERT INTO votes (user_id, survey_id, candidate_id) VALUES (?, ?, ?)", (user_id, survey_id, candidate_id))
        await db.execute("UPDATE candidates SET votes_count = votes_count + 1 WHERE id = ?", (candidate_id,))
        await db.commit()
        
        # Refresh the view to show updated counts
        # Get survey details (we need text again to edit)
        # Actually easiest is just to edit reply_markup? But message caption might not change. 
        # But we want to show updated counts.
        
        # Get candidates again
        async with db.execute("SELECT id, full_name, votes_count FROM candidates WHERE survey_id = ?", (survey_id,)) as cursor:
            candidates = await cursor.fetchall()
            
    await callback.answer("Sizning ovozingiz qabul qilindi!", show_alert=True)
    
    # Update the keyboard with new counts
    await callback.message.edit_reply_markup(reply_markup=candidates_keyboard(survey_id, candidates))
