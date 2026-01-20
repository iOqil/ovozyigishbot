from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def surveys_list_keyboard(surveys):
    builder = InlineKeyboardBuilder()
    for survey_id, title in surveys:
        builder.button(text=title, callback_data=f"survey_{survey_id}")
    builder.adjust(1)
    return builder.as_markup()

def candidates_keyboard(survey_id, candidates):
    builder = InlineKeyboardBuilder()
    for c_id, name, votes in candidates:
        builder.button(text=f"{name} ({votes})", callback_data=f"vote_{survey_id}_{c_id}")
    builder.adjust(1)
    # Add a back button? Maybe later.
    return builder.as_markup()
