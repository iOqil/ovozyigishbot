import logging
import os
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile, LinkPreviewOptions
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID
from states import SurveyCreation, ChannelManagement, SurveyPosting
from database import (
    get_active_surveys, delete_survey, get_all_channels, 
    add_channel, channel_exists, delete_channel, 
    get_survey_details, get_survey_candidates, close_survey,
    create_survey, add_candidate, toggle_survey_channel,
    get_survey_linked_channel_ids, get_survey_participants_report
)

router = Router()
logger = logging.getLogger(__name__)

# Middleware-like check for admin
async def is_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        logger.warning(f"Unauthorized admin access attempt by {message.from_user.id}")
        return False
    return True

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await is_admin(message): return
    await message.answer("Admin panelga xush kelibsiz.\n\n/create_survey - Yangi so'rovnoma\n/delete_survey - So'rovnomani o'chirish\n/channels - Kanallar va guruhlar\n/survey_channels - 🔗 So'rovnoma Kanallari\n/finish_survey - Yakunlash\n/post_survey - Kanal/Guruhga post\n/post_results - Natijani kanal/guruhga yuborish\n/phone_numbers - 📱 Telefon raqamlar ro'yxati")

@router.message(Command("delete_survey"))
async def cmd_delete_survey(message: Message):
    if not await is_admin(message): return
    try:
        surveys = await get_active_surveys()
        if not surveys:
            await message.answer("O'chirish uchun faol so'rovnomalar yo'q.")
            return

        keyboard = []
        for s in surveys:
            keyboard.append([InlineKeyboardButton(text=f"❌ {s['title']}", callback_data=f"del_survey_{s['id']}")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer("O'chirmoqchi bo'lgan so'rovnomangizni tanlang:", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error in cmd_delete_survey: {e}")
        await message.answer("Xatolik yuz berdi.")

@router.callback_query(F.data.startswith("del_survey_"))
async def process_delete_survey(callback: CallbackQuery):
    try:
        survey_id = int(callback.data.split("_")[2])
        await delete_survey(survey_id)
        await callback.answer("So'rovnoma o'chirildi!", show_alert=True)
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Error in process_delete_survey: {e}")
        await callback.answer("O'chirishda xatolik.", show_alert=True)

# --- Channel Management ---

@router.message(Command("channels"))
async def cmd_channels(message: Message):
    if not await is_admin(message): return
    try:
        channels = await get_all_channels()
        text = "📢 **Ulangan kanallar va guruhlar:**\n\n"
        keyboard = []
        
        if channels:
            for c in channels:
                text += f"{c['name']} - {c['url']}\n"
                keyboard.append([InlineKeyboardButton(text=f"❌ {c['name']} ni o'chirish", callback_data=f"del_channel_{c['id']}")])
        else:
            text += "Hozircha kanallar yoki guruhlar yo'q."
            
        keyboard.append([InlineKeyboardButton(text="➕ Qo'shish", callback_data="add_channel")])
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await message.answer(text, reply_markup=markup, link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception as e:
        logger.error(f"Error in cmd_channels: {e}")
        await message.answer("Kanal ro'yxatini yuklashda xatolik.")

@router.callback_query(F.data == "add_channel")
async def ask_channel(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Yangi kanal yoki guruh qo'shish uchun:\n\n"
        "1. O'sha kanaldan/guruhdan birorta xabarni shu yerga **Forward** qiling.\n"
        "2. Yoki uning **ID**sini (masalan: -100...) yoki **Username**ini (@...) yozib yuboring.\n\n"
        "Eslatma: Bot o'sha chatda ADMIN bo'lishi shart!"
    )
    await state.set_state(ChannelManagement.waiting_for_forward)
    await callback.answer()

@router.message(ChannelManagement.waiting_for_forward)
async def process_channel_input(message: Message, state: FSMContext, bot):
    try:
        chat_id = None
        chat_title = None

        if message.forward_from_chat:
            chat_id = message.forward_from_chat.id
            chat_title = message.forward_from_chat.title
        else:
            input_text = message.text.strip()
            try:
                chat = await bot.get_chat(input_text)
                chat_id = chat.id
                chat_title = chat.title
            except Exception as e:
                await message.answer(f"Xatolik: Kanal yoki guruhni topib bo'lmadi. Username yoki ID to'g'riligini tekshiring.\nError: {e}")
                return
            
        try:
            bot_user = await bot.get_me()
            member = await bot.get_chat_member(chat_id, bot_user.id)
            if member.status not in ["administrator", "creator"]:
                 await message.answer("Bot bu chatda admin emas! Iltimos avval botni admin qiling.")
                 return
        except Exception as e:
            await message.answer(f"Xatolik: Bot chatni ko'ra olmayapti. Botni admin qilganingizga ishonch hosil qiling.\nError: {e}")
            return

        invite_link = None
        try:
            chat = await bot.get_chat(chat_id)
            invite_link = chat.invite_link
            if not invite_link:
                 if chat.username:
                     invite_link = f"https://t.me/{chat.username}"
                 else:
                     invite_link = await bot.export_chat_invite_link(chat_id)
        except Exception:
             invite_link = "Noma'lum havola"

        if await channel_exists(str(chat_id)):
            await message.answer("Bu kanal/guruh allaqachon qo'shilgan!")
            await state.clear()
            return

        await add_channel(str(chat_id), chat_title, invite_link)
        await message.answer(f"✅ Qo'shildi:\nNom: {chat_title}\nID: {chat_id}\nHavola: {invite_link}")
        await state.clear()
    except Exception as e:
        logger.error(f"Error in process_channel_input: {e}")
        await message.answer("Kanal qo'shishda kutilmagan xatolik.")
        await state.clear()

@router.callback_query(F.data.startswith("del_channel_"))
async def delete_channel_handler(callback: CallbackQuery):
    try:
        c_id = int(callback.data.split("_")[2])
        await delete_channel(c_id)
        await callback.answer("O'chirildi!", show_alert=True)
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Error in delete_channel_handler: {e}")
        await callback.answer("O'chirishda xatolik.", show_alert=True)

# --- Post Survey ---

@router.message(Command("post_survey"))
async def cmd_post_survey(message: Message):
    if not await is_admin(message): return
    try:
        surveys = await get_active_surveys()
        if not surveys:
            await message.answer("Yuborish uchun faol so'rovnomalar yo'q.")
            return

        keyboard = []
        for s in surveys:
            keyboard.append([InlineKeyboardButton(text=f"📤 {s['title']}", callback_data=f"post_select_{s['id']}")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer("📢 **Qaysi so'rovnomani kanalga chiqarmoqchisiz?**", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error in cmd_post_survey: {e}")
        await message.answer("Xatolik.")

@router.callback_query(F.data.startswith("post_select_"))
async def ask_target_channel(callback: CallbackQuery, state: FSMContext):
    survey_id = int(callback.data.split("_")[2])
    await state.update_data(post_survey_id=survey_id)
    await callback.message.answer(
        "So'rovnomani qaysi kanal yoki guruhga yubormoqchisiz?\n\nUsername (@...) yoki ID kiriting.\nBot admin bo'lishi shart!"
    )
    await state.set_state(SurveyPosting.waiting_for_channel)
    await callback.answer()

@router.message(SurveyPosting.waiting_for_channel)
async def perform_post_survey(message: Message, state: FSMContext, bot):
    try:
        channel_id = message.text.strip()
        data = await state.get_data()
        survey_id = data.get('post_survey_id')
        is_result = data.get('is_result_post', False)
        
        survey = await get_survey_details(survey_id)
        candidates = await get_survey_candidates(survey_id)

        if not survey:
            await message.answer("Xatolik: So'rovnoma topilmadi.")
            await state.clear()
            return

        if is_result:
            text = f"🏁 <b>SO'ROVNOMA NATIJALARI</b>\n\n📌 <b>{survey['title']}</b>\n\n"
            medals = ["🥇", "🥈", "🥉"]
            total_votes = sum(c['votes_count'] for c in candidates)
            
            for i, c in enumerate(candidates):
                icon = medals[i] if i < 3 else "▪️"
                percent = (c['votes_count'] / total_votes * 100) if total_votes > 0 else 0
                text += f"{icon} <b>{c['votes_count']} ovoz</b> ({percent:.1f}%) — {c['full_name']}\n"
            text += f"\n🗳 Jami ovozlar: {total_votes}"
            
            try:
                if survey['image_file_id']:
                    if len(text) > 1000:
                        await bot.send_photo(chat_id=channel_id, photo=survey['image_file_id'])
                        await bot.send_message(chat_id=channel_id, text=text, parse_mode="HTML")
                    else:
                        await bot.send_photo(chat_id=channel_id, photo=survey['image_file_id'], caption=text, parse_mode="HTML")
                else:
                    await bot.send_message(chat_id=channel_id, text=text, parse_mode="HTML")
                await message.answer(f"✅ Natijalar {channel_id} ga yuborildi!")
            except Exception as e:
                await message.answer(f"❌ Xatolik: {e}")
        else:
            text = f"{survey['description']}"
            builder = InlineKeyboardBuilder()
            for c in candidates:
                builder.button(text=f"{c['full_name']} ({c['votes_count']})", callback_data=f"vote_{survey_id}_{c['id']}")
            builder.adjust(1)

            try:
                if survey['image_file_id']:
                    await bot.send_photo(chat_id=channel_id, photo=survey['image_file_id'], caption=text, reply_markup=builder.as_markup(), parse_mode="HTML")
                else:
                    await bot.send_message(chat_id=channel_id, text=text, reply_markup=builder.as_markup(), parse_mode="HTML")
                await message.answer(f"✅ So'rovnoma {channel_id} ga yuborildi!")
            except Exception as e:
                await message.answer(f"❌ Xatolik yuz berdi: {e}")
    except Exception as e:
        logger.error(f"Error in perform_post_survey: {e}")
        await message.answer("Yuborishda kutilmagan xatolik.")
    finally:
        await state.clear()

# --- Survey Management ---

@router.message(Command("finish_survey"))
async def cmd_finish_survey(message: Message):
    if not await is_admin(message): return
    try:
        # Get surveys that are active but not closed
        surveys = [s for s in await get_active_surveys() if not s['is_closed']]
        if not surveys:
            await message.answer("Tugatish uchun faol so'rovnomalar yo'q.")
            return

        keyboard = []
        for s in surveys:
            keyboard.append([InlineKeyboardButton(text=f"🛑 {s['title']}", callback_data=f"finish_survey_{s['id']}")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer("🏁 **Qaysi so'rovnomani yakunlamoqchisiz?**", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error in cmd_finish_survey: {e}")
        await message.answer("Xatolik.")

@router.callback_query(F.data.startswith("finish_survey_"))
async def process_finish_survey_handler(callback: CallbackQuery):
    try:
        survey_id = int(callback.data.split("_")[2])
        await close_survey(survey_id)
        await callback.answer("So'rovnoma yakunlandi!", show_alert=True)
        await callback.message.edit_text("✅ So'rovnoma muvaffaqiyatli yakunlandi.")
    except Exception as e:
        logger.error(f"Error in process_finish_survey: {e}")
        await callback.answer("Yakunlashda xatolik.", show_alert=True)

@router.message(Command("post_results"))
async def cmd_post_results(message: Message):
    if not await is_admin(message): return
    try:
        surveys = [s for s in await get_active_surveys() if s['is_closed']]
        if not surveys:
            await message.answer("Natijasini chiqarish uchun yakunlangan so'rovnomalar yo'q.")
            return

        keyboard = []
        for s in surveys:
            keyboard.append([InlineKeyboardButton(text=f"📈 {s['title']}", callback_data=f"res_select_{s['id']}")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer("📊 **Qaysi so'rovnoma natijasini kanal/guruhga chiqarmoqchisiz?**", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error in cmd_post_results: {e}")
        await message.answer("Xatolik.")

@router.callback_query(F.data.startswith("res_select_"))
async def ask_target_channel_results(callback: CallbackQuery, state: FSMContext):
    survey_id = int(callback.data.split("_")[2])
    await state.update_data(post_survey_id=survey_id, is_result_post=True)
    await callback.message.answer("Natijani qaysi kanal yoki guruhga yubormoqchisiz?\nUsername (@...) yoki ID kiriting.")
    await state.set_state(SurveyPosting.waiting_for_channel)
    await callback.answer()

@router.message(Command("create_survey"))
async def start_survey_creation(message: Message, state: FSMContext):
    if not await is_admin(message): return
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
    await state.update_data(image_file_id=image_file_id, candidates=[])
    await message.answer("Endi nomzodlarni kiriting.\nHar bir nomzodni alohida xabar sifatida yuboring.\nTugatish uchun /done deb yozing.")
    await state.set_state(SurveyCreation.waiting_for_candidates)

@router.message(SurveyCreation.waiting_for_image, Command("skip"))
async def skip_image(message: Message, state: FSMContext):
    await state.update_data(image_file_id=None, candidates=[])
    await message.answer("Rasm o'tkazib yuborildi.\nEndi nomzodlarni kiriting.\nHar bir nomzodni alohida xabar sifatida yuboring.\nTugatish uchun /done deb yozing.")
    await state.set_state(SurveyCreation.waiting_for_candidates)

@router.message(SurveyCreation.waiting_for_candidates, Command("done"))
async def finish_candidates(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        candidates = data.get("candidates", [])
        if not candidates:
            await message.answer("Kamida bitta nomzod kiritish kerak! Davom eting.")
            return

        survey_id = await create_survey(data['title'], data['description'], data['image_file_id'])
        for c in candidates:
            await add_candidate(survey_id, c)
        
        await message.answer(f"So'rovnoma yaratildi!\nID: {survey_id}\nNomzodlar soni: {len(candidates)}")
    except Exception as e:
        logger.error(f"Error in finish_candidates: {e}")
        await message.answer("Yaratishda xatolik yuz berdi.")
    finally:
        await state.clear()

@router.message(SurveyCreation.waiting_for_candidates)
async def process_candidate(message: Message, state: FSMContext):
    data = await state.get_data()
    candidates = data.get("candidates", [])
    candidates.append(message.text)
    await state.update_data(candidates=candidates)
    await message.answer(f"Nomzod qo'shildi: {message.text}\nYana yuboring yoki /done ni bosing.")

# --- Survey Channel Linking ---

@router.message(Command("survey_channels"))
async def cmd_survey_channels(message: Message):
    if not await is_admin(message): return
    try:
        surveys = await get_active_surveys()
        if not surveys:
            await message.answer("Sozlash uchun faol so'rovnomalar yo'q.")
            return

        keyboard = []
        for s in surveys:
            keyboard.append([InlineKeyboardButton(text=f"⚙️ {s['title']}", callback_data=f"sc_list_{s['id']}")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer("🔗 **Qaysi so'rovnoma uchun kanal/guruhlarni sozlamoqchisiz?**", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error in cmd_survey_channels: {e}")
        await message.answer("Xatolik.")

@router.callback_query(F.data.startswith("sc_list_"))
async def show_survey_channels_handler(callback: CallbackQuery):
    try:
        survey_id = int(callback.data.split("_")[2])
        survey = await get_survey_details(survey_id)
        all_channels = await get_all_channels()
        linked_ids = await get_survey_linked_channel_ids(survey_id)
                
        if not all_channels:
            await callback.answer("Hozircha hech qanday kanal qo'shilmagan (/channels).", show_alert=True)
            return

        text = f"⚙️ **{survey['title'] if survey else '?' }** uchun majburiy obunalar:\nUstiga bosib yoqing/o'chiring."
        keyboard = []
        for c in all_channels:
            status_icon = "✅" if c['id'] in linked_ids else "❌"
            keyboard.append([InlineKeyboardButton(text=f"{status_icon} {c['name']}", callback_data=f"sc_toggle_{survey_id}_{c['id']}")])
            
        keyboard.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_sc_surveys")])
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        try:
            await callback.message.edit_text(text, reply_markup=markup)
        except Exception:
            await callback.message.answer(text, reply_markup=markup)
            await callback.message.delete()
    except Exception as e:
        logger.error(f"Error in show_survey_channels: {e}")
        await callback.answer("Yuklashda xatolik.", show_alert=True)

@router.callback_query(F.data == "back_to_sc_surveys")
async def back_to_surveys_list(callback: CallbackQuery):
    try:
        surveys = await get_active_surveys()
        keyboard = []
        for s in surveys:
            keyboard.append([InlineKeyboardButton(text=f"⚙️ {s['title']}", callback_data=f"sc_list_{s['id']}")])
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback.message.edit_text("🔗 **Qaysi so'rovnoma uchun kanallarni sozlamoqchisiz?**", reply_markup=markup)
    except Exception:
        pass

@router.callback_query(F.data.startswith("sc_toggle_"))
async def toggle_survey_channel_handler(callback: CallbackQuery):
    try:
        _, _, survey_id, channel_id = callback.data.split("_")
        action = await toggle_survey_channel(int(survey_id), int(channel_id))
        await callback.answer(f"Kanal {action}!")
        await show_survey_channels_handler(callback)
    except Exception as e:
        logger.error(f"Error in toggle_survey_channel: {e}")
        await callback.answer("O'zgartirishda xatolik.", show_alert=True)

@router.message(Command("phone_numbers"))
async def cmd_phone_numbers(message: Message, state: FSMContext):
    if not await is_admin(message): return
    try:
        surveys = await get_active_surveys()
        if not surveys:
            await message.answer("Ro'yxatni olish uchun faol so'rovnomalar yo'q.")
            return

        keyboard = []
        for s in surveys:
            keyboard.append([InlineKeyboardButton(text=f"📊 {s['title']}", callback_data=f"exp_phone_{s['id']}")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer("Qaysi so'rovnoma qatnashchilarini ro'yxatini olmoqchisiz?", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error in cmd_phone_numbers: {e}")
        await message.answer("Xatolik.")

@router.callback_query(F.data.startswith("exp_phone_"))
async def process_survey_phone_numbers(callback: CallbackQuery):
    file_path = None
    try:
        survey_id = int(callback.data.split("_")[2])
        survey = await get_survey_details(survey_id)
        rows = await get_survey_participants_report(survey_id)
                
        if not rows:
            await callback.answer("Foydalanuvchilar topilmadi.")
            return
            
        file_path = f"users_data_{survey_id}.txt"
        survey_title = survey['title'] if survey else "Noma'lum"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"SO'ROVNOMA: {survey_title}\n" + "-" * 80 + "\n")
            f.write(f"{'№':<4} | {'Telefon':<15} | {'Ism':<25} | {'Tanlangan nomzod':<30}\n" + "-" * 80 + "\n")
            for i, r in enumerate(rows, 1):
                f.write(f"{i:<4} | {r['phone_number']:<15} | {str(r['full_name'])[:25]:<25} | {str(r['candidate_name'] or 'Ovoz bermagan')[:30]:<30}\n")
                
        await callback.message.answer_document(
            document=FSInputFile(file_path),
            caption=f"✅ {survey_title}\nJami ro'yxat: {len(rows)} ta"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in process_survey_phone_numbers: {e}")
        await callback.message.answer("Xabar tayyorlashda xatolik yuz berdi.")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
