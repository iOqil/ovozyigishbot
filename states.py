from aiogram.fsm.state import State, StatesGroup

class SurveyCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_image = State()
    waiting_for_candidates = State()

class ChannelManagement(StatesGroup):
    waiting_for_forward = State()

class SurveyPosting(StatesGroup):
    waiting_for_channel = State()

class PhoneNumbersExport(StatesGroup):
    waiting_for_survey = State()
