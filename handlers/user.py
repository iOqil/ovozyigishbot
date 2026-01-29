import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import (
    get_user_by_id, add_or_update_user, get_active_surveys, 
    get_survey_details, get_survey_candidates, has_user_voted, 
    register_vote, get_linked_channels
)
from keyboards.default import main_menu
from keyboards.inline import candidates_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: Message):
    try:
        user_id = message.from_user.id
        user_data = await get_user_by_id(user_id)
                
        if not user_data:
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await message.answer(
                "Assalomu alaykum! Botdan foydalanish uchun telefon raqamingizni tasdiqlashingiz kerak.", 
                reply_markup=kb
            )
            return

        await message.answer(
            "So'rovnomalar botiga xush kelibsiz, so'rovnomalarda ishtirok etish uchun \"Ovoz berish\" tugmasini bosing.", 
            reply_markup=main_menu()
        )
    except Exception as e:
        logger.error(f"Error in cmd_start: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos keyinroq qayta urinib ko'ring.")

@router.message(F.contact)
async def handle_contact(message: Message):
    try:
        contact = message.contact
        user_id = message.from_user.id
        
        if contact.user_id != user_id:
            await message.answer("Iltimos, o'zingizning telefon raqamingizni yuboring!")
            return
            
        await add_or_update_user(
            user_id, 
            contact.phone_number, 
            message.from_user.username, 
            message.from_user.full_name
        )
        
        await message.answer("Rahmat! Siz muvaffaqiyatli ro'yxatdan o'tdingiz.", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Error in handle_contact: {e}")
        await message.answer("Ro'yxatdan o'tishda xatolik yuz berdi.")

@router.message(F.text == "🗳 Ovoz berish")
async def show_surveys(message: Message):
    try:
        surveys = await get_active_surveys()
                
        if not surveys:
            await message.answer("Hozircha faol so'rovnomalar yo'q.")
            return
        
        builder = InlineKeyboardBuilder()
        for s in surveys:
            status_icon = "🏁" if s['is_closed'] else "🗳"
            builder.button(text=f"{status_icon} {s['title']}", callback_data=f"survey_{s['id']}")
        builder.adjust(1)

        await message.answer("Mavjud so'rovnomalar:", reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in show_surveys: {e}")
        await message.answer("So'rovnomalarni yuklashda xatolik yuz berdi.")

@router.callback_query(F.data.startswith("survey_"))
async def show_survey_details(callback: CallbackQuery, bot):
    try:
        survey_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        channels_to_check = await get_linked_channels(survey_id)
            
        not_subscribed = []
        if channels_to_check:
            for ch in channels_to_check:
                try:
                    member = await bot.get_chat_member(chat_id=ch['channel_id'], user_id=user_id)
                    if member.status not in ["creator", "administrator", "member"]:
                        not_subscribed.append((ch['name'], ch['url']))
                except Exception as e:
                     logger.warning(f"Could not check subscription for user {user_id} in {ch['channel_id']}: {e}")
        
        if not_subscribed:
            text = "❌ <b>Ovoz berish uchun quyidagi kanallar va guruhlarga obuna bo'lishingiz shart:</b>\n\n"
            kb_builder = InlineKeyboardBuilder()
            for name, url in not_subscribed:
                kb_builder.button(text=f"➕ {name}", url=url)
                text += f"• {name}\n"
            
            kb_builder.button(text="✅ Obuna bo'ldim", callback_data=f"survey_{survey_id}")
            kb_builder.adjust(1)
            
            if callback.message.reply_markup:
                 await callback.answer("Siz ko'rsatilgan kanallarga obuna bo'lmagansiz!", show_alert=True)
            else:
                 await callback.answer()

            try:
                await callback.message.edit_text(text, reply_markup=kb_builder.as_markup(), parse_mode="HTML")
            except Exception:
                pass
            return

        survey = await get_survey_details(survey_id)
        if not survey:
            await callback.answer("So'rovnoma topilmadi.")
            return

        candidates = await get_survey_candidates(survey_id)

        text = f"{survey['description']}"
        
        if survey['is_closed']:
            text = f"🏁 <b>SO'ROVNOMA YAKUNLANGAN</b>\n\n{text}\n\nNatijalarni ko'rish uchun quyidagi tugmani bosing."
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(text="📊 Natijalarni ko'rish", callback_data=f"results_{survey_id}")
            kb = kb_builder.as_markup()
        else:
            kb = candidates_keyboard(survey_id, candidates)
        
        image_file_id = survey['image_file_id']
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
                
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_survey_details: {e}")
        await callback.answer("Ma'lumotlarni yuklashda xatolik.", show_alert=True)

@router.callback_query(F.data.startswith("results_"))
async def show_results(callback: CallbackQuery):
    try:
        survey_id = int(callback.data.split("_")[1])
        survey = await get_survey_details(survey_id)
        title = survey['title'] if survey else "Natijalar"
        candidates = await get_survey_candidates(survey_id)
                
        text = f"🏁 <b>SO'ROVNOMA NATIJALARI</b>\n\n📌 <b>{title}</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]
        total_votes = sum(c['votes_count'] for c in candidates)
        
        for i, c in enumerate(candidates):
            icon = medals[i] if i < 3 else "▪️"
            percent = (c['votes_count'] / total_votes * 100) if total_votes > 0 else 0
            text += f"{icon} <b>{c['votes_count']}</b> ({percent:.1f}%) — {c['full_name']}\n"
            
        text += f"\n🗳 Jami ovozlar: {total_votes}"
        
        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_results: {e}")
        await callback.answer("Natijalarni yuklashda xatolik.", show_alert=True)

@router.callback_query(F.data.startswith("vote_"))
async def register_vote_handler(callback: CallbackQuery):
    try:
        _, survey_id, candidate_id = callback.data.split("_")
        survey_id = int(survey_id)
        candidate_id = int(candidate_id)
        user_id = callback.from_user.id
        
        if await has_user_voted(user_id, survey_id):
            await callback.answer("Siz allaqachon ovoz bergansiz!", show_alert=True)
            return

        success = await register_vote(user_id, survey_id, candidate_id)
        if not success:
            await callback.answer("Ovoz berishda xatolik yuz berdi.", show_alert=True)
            return
            
        candidates = await get_survey_candidates(survey_id)
        await callback.answer("Sizning ovozingiz qabul qilindi!", show_alert=True)
        
        try:
            await callback.message.edit_reply_markup(reply_markup=candidates_keyboard(survey_id, candidates))
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Error in register_vote_handler: {e}")
        await callback.answer("Ovoz berishda texnik xatolik.", show_alert=True)
