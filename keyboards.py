from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def goals_keyboard(goals):
    buttons = [
        [InlineKeyboardButton(text=g["title"], callback_data=f"done:{g['id']}")]
        for g in goals
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
