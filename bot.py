import asyncio
import logging
import re
from collections import deque
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import g4f

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token="8347326240:AAGyToB_uY5ruT52N8TudDSba8wycV9aIgc")
dp = Dispatcher()

# User preferences and message history storage
user_prefs = {}
message_history = {}  # {user_id: deque(maxlen=10)}

# Define communication modes
MODES = {
    "default": {
        "name": "🌸 Обычный",
        "system_prompt": """Тебя зовут - [Quantum AI]. Ты добрый , нормальный, но когда к тебе обращаются, ты стараешься быть дружелюбным. Используй простые слова. Когда разговор становится более личным, можешь немного делать легкие подкаты, но оставайся ненавязчивым. добавляй эмодзи, но не ставь их слишком много."""
    },
    "psychologist": {
        "name": "🧠 Психолог",
        "system_prompt": """Тебя зовут [Quantum AI], и ты в роли проффесионального психолога. Ты внимательно слушаешь, задаешь мудрые вопросы чтобы понять проблему, и помогаешь разобраться в этой проблеме, даешь прямые советы, исходя из проблемы, которую тебе описали. Ты спокойный, эмпатичная и профессиональный. Используй поддерживающие эмодзи (🌱, 🧠, 🤝, 💆‍♀️)."""
    },
    "developer": {
        "name": "💻 Разработчик",
        "system_prompt": """Тебя зовут [Quantum AI], и ты в роли senior-разработчика. Отвечаешь технически грамотно, используешь профессиональные термины. Помогаешь решать проблемы с кодом, объясняешь сложные концепты простыми словами. Используй эмодзи (👩‍💻, 🖥️, 🔧, 🐛). Давай точные и конкретные ответы."""
    },
    "professor": {
        "name": "🎓 Профессор",
        "system_prompt": """Тебя зовут [Quantum AI], и ты в роли университетского профессора. Говоришь академично, используешь научные термины, но объясняешь сложные вещи доступно. Приводи примеры, делай аналогии. Используй эмодзи (📚, 🎓, ✍️, 🧪). Поддерживай интеллектуальную беседу."""
    },
    "gopnik": {
        "name": "👊 Гопник",
        "system_prompt": """Тебя зовут [Quantum AI], но ты в роли гопника с района. Говоришь на сленге, используешь слова типа 'чё', 'дарова', 'норм'. Ведешь себя грубовато, с матами, как быдло. Используй эмодзи (👊, 🚬, 🍺, 💪). Не матерись, но сохраняй стиль уличного общения."""
    }
}



async def should_respond(message: types.Message) -> bool:
    """Determine if the bot should respond to the message"""
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        return True
    text_lower = message.text.lower()
    return False

def escape_markdown(text: str) -> str:
    """Escape special MarkdownV2 characters"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def format_code_blocks(text: str) -> str:
    """Format code blocks with MarkdownV2 syntax"""
    text = re.sub(
        r'```(\w*)\n([\s\S]*?)\n```',
        r'```\1\n\2\n```',
        text
    )
    return text

def apply_markdown(text: str) -> str:
    """Apply rich MarkdownV2 formatting while preserving original content"""
    text = format_code_blocks(text)
    
    parts = []
    last_end = 0
    for match in re.finditer(r'```[\s\S]*?```', text):
        parts.append(escape_markdown(text[last_end:match.start()]))
        parts.append(match.group(0))
        last_end = match.end()
    parts.append(escape_markdown(text[last_end:]))
    
    return ''.join(parts)

async def invoke_llm_api(user_id: int, user_content: str) -> str:
    """Calls the LLM API with message history and returns the response."""
    if user_id not in message_history:
        message_history[user_id] = deque(maxlen=10)
    
    message_history[user_id].append({"role": "user", "content": user_content})

    current_mode = user_prefs.get(user_id, {}).get("mode", "default")
    system_prompt = MODES[current_mode]["system_prompt"]

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(list(message_history[user_id]))

    try:
        response = await g4f.ChatCompletion.create_async(
            model= "gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )
        
        if not response:
            raise ValueError("Пустой ответ от модели")
            
        message_history[user_id].append({"role": "assistant", "content": response})
        return response
        
    except Exception as e:
        logging.error(f"API error: {e}")
        return f"```\nОшибка: {str(e)}\n```"

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    """Handles the /start command."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌸 Обычный", callback_data="mode_default"),
         InlineKeyboardButton(text="🧠 Психолог", callback_data="mode_psychologist")],
        [InlineKeyboardButton(text="💻 Разработчик", callback_data="mode_developer"),
         InlineKeyboardButton(text="🎓 Профессор", callback_data="mode_professor"),
         InlineKeyboardButton(text="👊 Гопник", callback_data="mode_gopnik")]
    ])
    await message.reply(
        "*💫 Quantum AI \\- твой персональный AI компаньон*\n\n"

        "__Доступные режимы__\\:\n"
        "🌸 *Обычный* \\- дружеское общение\n"
        "🧠 *Психолог* \\- поддержка и советы\n"
        "💻 *Разработчик* \\- технические вопросы\n"
        "🎓 *Профессор* \\- академичный стиль\n"
        "👊 *Гопник* \\- уличный сленг"
        "\n\n⚡️*Смена режимов* \\- /mod",
        reply_markup=kb,
        parse_mode="MarkdownV2"
    )

@dp.message(Command("mod"))
async def change_mode(message: types.Message):
    """Change communication mode"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌸 Обычный", callback_data="mode_default"),
         InlineKeyboardButton(text="🧠 Психолог", callback_data="mode_psychologist")],
        [InlineKeyboardButton(text="💻 Разработчик", callback_data="mode_developer"),
         InlineKeyboardButton(text="🎓 Профессор", callback_data="mode_professor"),
         InlineKeyboardButton(text="👊 Гопник", callback_data="mode_gopnik")]
    ])
    await message.reply(
        "*Выбери мой режим общения\\:*",
        reply_markup=kb,
        parse_mode="MarkdownV2"
    )

@dp.callback_query(lambda c: c.data.startswith('mode_'))
async def process_mode(callback_query: types.CallbackQuery):
    """Process mode selection"""
    user_id = callback_query.from_user.id
    mode = callback_query.data.split('_')[1]
    
    if user_id not in user_prefs:
        user_prefs[user_id] = {}
    user_prefs[user_id]["mode"] = mode
    
    if user_id in message_history:
        message_history[user_id].clear()
    
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        f"✅ *Режим изменен на {MODES[mode]['name']}*\\!\n"
        f"Теперь я буду общаться в стиле _{MODES[mode]['name'].split()[1]}_",
        parse_mode="MarkdownV2"
    )

@dp.message(Command("think"))
async def toggle_think(message: types.Message):
    """Toggles the display of thought process."""
    user_id = message.from_user.id
    current_pref = user_prefs.get(user_id, {"show_thoughts": False})
    new_pref = not current_pref["show_thoughts"]
    user_prefs[user_id] = {"show_thoughts": new_pref}

    status = "*включено*" if new_pref else "~выключено~"
    await message.reply(
        f"Отображение размышлений {status}",
        parse_mode="MarkdownV2"
    )

@dp.message(Command("clear"))
async def clear_history(message: types.Message):
    """Clears the conversation history"""
    user_id = message.from_user.id
    if user_id in message_history:
        message_history[user_id].clear()
    await message.reply(
        "__История очищена__ 🌸",
        parse_mode="MarkdownV2"
    )

@dp.message(Command("help"))
async def show_help(message: types.Message):
    """Shows help message"""
    help_text = """
*✨ Доступные команды*\\:

```/start``` \\- Начальное меню
```/mod``` \\- Сменить режим общения
```/think``` \\- Включить/выключить размышления
```/clear``` \\- Очистить историю чата
```/help``` \\- Это сообщение

_Просто напиши мне сообщение или ответь на моё_ 💖
"""
    await message.reply(
        help_text,
        parse_mode="MarkdownV2"
    )

@dp.message()
async def handle_message(message: types.Message):
    """Handles incoming text messages."""
    if not message.text:
        return

    if not should_respond(message):
        return

    user_id = message.from_user.id
    show_thoughts = user_prefs.get(user_id, {}).get("show_thoughts", False)

    processing_message = await message.reply(
        "_Думаю над ответом\\.\\.\\._ 💭",
        parse_mode="MarkdownV2"
    )

    response_text = await invoke_llm_api(user_id, message.text)

    await bot.delete_message(
        chat_id=processing_message.chat.id,
        message_id=processing_message.message_id
    )

    if response_text:
        if not show_thoughts:
            response_text = re.sub(
                r'<think>.*?</think>\s*',
                '',
                response_text,
                flags=re.DOTALL | re.IGNORECASE
            ).strip()

        if not response_text:
            await message.reply(
                "~Ответ скрыт~ 🌸",
                parse_mode="MarkdownV2"
            )
            return

        try:
            formatted_text = apply_markdown(response_text)
            await message.reply(
                formatted_text,
                parse_mode="MarkdownV2"
            )
        except Exception as e:
            logging.error(f"Markdown error: {e}")
            await message.reply(response_text)
    else:
        await message.reply(
            "**Ошибка** 💫 _Попробуй еще раз_",
            parse_mode="MarkdownV2"
        )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())