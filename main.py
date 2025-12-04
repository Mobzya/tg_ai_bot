import asyncio
import logging
from openai import OpenAI 
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder  # Правильный импорт
from tokens import BOT_TOKEN, hug_url, OPENAI_API_KEY
from math import ceil

client = OpenAI(
    base_url=hug_url,
    api_key=OPENAI_API_KEY,
)

class Metrics():
    """Все наши метрики"""
    N: int = 1
    L: int = 1
    Task_number: int = 1 
    
    @property
    def D(self):
        return ceil(0.8 * self.N * 1.25 * self.L)
    
user_story_chat = {}

# Хранилище метрик по user_id
user_metrics = {}

# Состояния для FSM
class UserStates(StatesGroup):
    waiting_for_N = State()
    waiting_for_L = State()
    waiting_for_task_number = State()
    chatting_mode = State()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

# Правильная инициализация бота в aiogram 3.7.0+
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Стилизованная клавиатура главного меню
start_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
    [
        types.InlineKeyboardButton(text="📊 N - Фактическая сложность", callback_data="btn1"),
        types.InlineKeyboardButton(text="🧮 L - Логическая сложность", callback_data="btn2"),
    ],
    [
        types.InlineKeyboardButton(text="🔢 Выбрать номер задания", callback_data="btn3")
    ],
    [
        types.InlineKeyboardButton(text="🚀 Начать выполнение", callback_data="btn4")
    ]
])

# Стилизованная клавиатура для режима чата
chat_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
    [
        types.InlineKeyboardButton(text="❌ Выйти из режима чата", callback_data="exit_chat")
    ]
])

# Клавиатура для ввода чисел
input_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
    [
        types.InlineKeyboardButton(text="1", callback_data="num_1"),
        types.InlineKeyboardButton(text="2", callback_data="num_2"),
        types.InlineKeyboardButton(text="3", callback_data="num_3"),
    ],
    [
        types.InlineKeyboardButton(text="4", callback_data="num_4"),
        types.InlineKeyboardButton(text="5", callback_data="num_5"),
        types.InlineKeyboardButton(text="6", callback_data="num_6"),
    ],
    [
        types.InlineKeyboardButton(text="7", callback_data="num_7"),
        types.InlineKeyboardButton(text="8", callback_data="num_8"),
        types.InlineKeyboardButton(text="9", callback_data="num_9"),
    ],
    [
        types.InlineKeyboardButton(text="10", callback_data="num_10"),
        types.InlineKeyboardButton(text="Отмена", callback_data="cancel_input"),
    ]
])

# Клавиатура для выбора задания (1-19) используя InlineKeyboardMarkup
def create_task_keyboard():
    """Создает клавиатуру для выбора задания 1-19"""
    keyboard = []
    
    # Создаем ряды по 5 кнопок
    for i in range(0, 15, 5):
        row = []
        for j in range(1, 6):
            num = i + j
            if num <= 15:
                row.append(types.InlineKeyboardButton(text=str(num), callback_data=f"task_{num}"))
        if row:
            keyboard.append(row)
    
    # Ряд для 16-19
    row_16_19 = []
    for num in range(16, 20):
        row_16_19.append(types.InlineKeyboardButton(text=str(num), callback_data=f"task_{num}"))
    if row_16_19:
        keyboard.append(row_16_19)
    
    # Ряд с кнопкой отмены
    keyboard.append([types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_task")])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

# Создаем клавиатуру
task_keyboard = create_task_keyboard()

@dp.message(Command("start"))
async def start(message: types.Message):
    """Стилизованное приветственное сообщение"""
    user_id = message.from_user.id
    user_metrics[user_id] = Metrics()
    
    welcome_message = """
🎓 <b>Добро пожаловать в бота, генерирующего собственные задания!</b>

✨ <i>Я помогу вам подготовиться к ЕГЭ по профильной математике</i>

🚀 <b>Возможности бота:</b>
• 📊 Настройка сложности заданий
• 🧮 Генерация уникальных задач
• 🤖 Интеллектуальная помощь в решении
• 📈 Адаптация под ваш уровень

👇 <b>Используйте кнопки ниже для навигации:</b>
"""
    
    await message.answer(
        welcome_message,
        reply_markup=start_keyboard
    )
    

async def show_metrics_inline(message: types.Message, user_id: int = None):
    """Стилизованное отображение метрик"""
    if user_id is None:
        user_id = message.from_user.id
    
    if user_id not in user_metrics:
        user_metrics[user_id] = Metrics()
    
    metrics_message = f"""
📊 <b>ТЕКУЩИЕ МЕТРИКИ</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>📈 Фактическая сложность (N):</b> <code>{user_metrics[user_id].N}</code>
<b>🧮 Логическая сложность (L):</b> <code>{user_metrics[user_id].L}</code>
<b>🎯 Итоговая сложность (D):</b> <code>{user_metrics[user_id].D}</code>
<b>🔢 Номер задания:</b> <code>{user_metrics[user_id].Task_number}</code>
━━━━━━━━━━━━━━━━━━━━━━
"""
    await message.answer(metrics_message, reply_markup=start_keyboard)

@dp.message(Command("cancel"), StateFilter("*"))
async def cancel_handler(message: types.Message, state: FSMContext):
    """Стилизованный обработчик отмены"""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("❌ <b>Нечего отменять.</b>", reply_markup=start_keyboard)
        return
    
    await state.clear()
    await message.answer("✅ <b>Действие отменено.</b>\n\nВозвращаемся в главное меню...", reply_markup=start_keyboard)

@dp.callback_query(F.data == 'show_metrics')
async def show_metrics_callback(callback_query: types.CallbackQuery):
    """Обработчик кнопки показа метрик"""
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    await show_metrics_inline(callback_query.message, user_id)

@dp.callback_query(F.data == 'btn1')
async def process_callback_button1(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки N с красивым оформлением"""
    await bot.answer_callback_query(callback_query.id)
    
    user_id = callback_query.from_user.id
    if user_id not in user_metrics:
        user_metrics[user_id] = Metrics()
    
    await state.set_state(UserStates.waiting_for_N)
    await state.update_data(user_id=user_id)
    
    message_text = """
🎯 <b>Настройка фактической сложности (N)</b>

📊 <i>Фактическая сложность определяет уровень математических операций:</i>
• 1-3: Базовые операции
• 4-6: Средний уровень
• 7-10: Сложные вычисления

👇 <b>Выберите значение от 1 до 10:</b>
"""
    await bot.send_message(user_id, message_text, reply_markup=input_keyboard)

@dp.callback_query(F.data == 'btn2')
async def process_callback_button2(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки L с красивым оформлением"""
    await bot.answer_callback_query(callback_query.id)
    
    user_id = callback_query.from_user.id
    if user_id not in user_metrics:
        user_metrics[user_id] = Metrics()
    
    await state.set_state(UserStates.waiting_for_L)
    await state.update_data(user_id=user_id)
    
    message_text = """
🧠 <b>Настройка логической сложности (L)</b>

💡 <i>Логическая сложность определяет уровень мышления:</i>
• 1-3: Прямые решения
• 4-6: Комбинированные подходы
• 7-10: Нестандартные решения

👇 <b>Выберите значение от 1 до 10:</b>
"""
    await bot.send_message(user_id, message_text, reply_markup=input_keyboard)

# Обработчики для числовых кнопок
@dp.callback_query(F.data.startswith("num_"))
async def process_number_input(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик ввода чисел через кнопки"""
    await bot.answer_callback_query(callback_query.id)
    value = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id
    current_state = await state.get_state()
    
    if current_state == UserStates.waiting_for_N:
        user_metrics[user_id].N = value
        await state.clear()
        await bot.send_message(user_id, f"✅ <b>Фактическая сложность установлена:</b> <code>{value}</code>")
        await show_metrics_inline(callback_query.message, user_id)
        
    elif current_state == UserStates.waiting_for_L:
        user_metrics[user_id].L = value
        await state.clear()
        await bot.send_message(user_id, f"✅ <b>Логическая сложность установлена:</b> <code>{value}</code>")
        await show_metrics_inline(callback_query.message, user_id)

@dp.callback_query(F.data == "cancel_input")
async def cancel_input(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена ввода числа"""
    await bot.answer_callback_query(callback_query.id)
    await state.clear()
    await bot.send_message(callback_query.from_user.id, "❌ <b>Ввод отменен.</b>", reply_markup=start_keyboard)

# Обработчик для кнопки 3
@dp.callback_query(F.data == 'btn3')
async def process_callback_button3(callback_query: types.CallbackQuery, state: FSMContext):
    """Стилизованный выбор номера задания"""
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    if user_id not in user_metrics:
        user_metrics[user_id] = Metrics()
    
    message_text = """
📚 <b>Выбор номера задания</b>

🔢 <i>ЕГЭ по профильной математике содержит задания 1-19:</i>
• 1-12: Задания первой части
• 13-19: Задания второй части
👇 <b>Выберите номер задания:</b>
"""
    await bot.send_message(user_id, message_text, reply_markup=task_keyboard)

@dp.callback_query(F.data.startswith("task_"))
async def process_task_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора задания"""
    await bot.answer_callback_query(callback_query.id)
    value = int(callback_query.data.split("_")[1])
    user_id = callback_query.from_user.id
    
    user_metrics[user_id].Task_number = value
    await state.clear()
    await bot.send_message(
        user_id, 
        f"✅ <b>Задание №{value} успешно выбрано!</b>\n\n"
        f"<i>Теперь вы можете сгенерировать задание этого типа.</i>"
    )
    await show_metrics_inline(callback_query.message, user_id)

@dp.callback_query(F.data == "cancel_task")
async def cancel_task_selection(callback_query: types.CallbackQuery):
    """Отмена выбора задания"""
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "❌ <b>Выбор задания отменен.</b>", reply_markup=start_keyboard)

@dp.callback_query(F.data == 'btn4')
async def process_callback_button4(callback_query: types.CallbackQuery, state: FSMContext):
    """Стилизованный запуск генерации задания"""
    user_id = callback_query.from_user.id
    
    # Показываем анимацию загрузки
    loading_message = await bot.send_message(
        user_id,
        "⏳ <b>Генерация задания...</b>\n"
        "<i>Нейросеть создает уникальную задачу для вас...</i>"
    )
    
    user_story_chat[user_id] = [{
        "role": "user",
        "content": f"Привет, наверняка ты знаком с ЕГЭ по профильной математике. Допустим N - это фактическая сложность задачи на экзамене (величина от 1 до 10), все задания данные в прошлые года имеют некую ценность от 1 до 10, по фактической уровни сложности этой задачи, а есть I - это 'степень олимпиадности задания', то есть на экзамене, все задания прошлых лет на самом экзамене имеют степень олимпиадности 1, однако я хочу создать такие задания, который можно будет формировать по формуле D = 0.8N * 1.25I, где D конечная сложность задачи. (Олимпиадность задачи означает наличие нестандартных и необычных методов подходов к ее решению, где 1 задача, где требуются довольно обычные рассуждения, а уровень 10, такой, где нужно применить очень глубокие олимпидные рассуждения). Т.е N(от 1 до 10), и I(от 1 до 10), соответственно D(от 5 до 100). Итак у нас есть формула D = N * I, обязательно используй формат и тему задания №{user_metrics[user_id].Task_number}, которое есть в ЕГЭ по профильной математике, убедись что ты выбрал именно ту тему, по которой в этой позиции на экамене дают задания, однако не пиши об этом в сообщении. Составь задание номер {user_metrics[user_id].Task_number} со сложностью {user_metrics[user_id].D}, учитывая что I = {user_metrics[user_id].L},, N = {user_metrics[user_id].N}.(От разработчика): Я использую твой текст условия задачи в телеграмме, для передачи другом пользователям. Поэтому составь ответ по такому плану: 1.Написать итоговую D (не говоря про формулу, только само значение D) задачи и предложить ему ее решить, 2. Дать само условие задачи, 3. Дать в конце сообщения пользователю знать, что он может попросить подсказки для задания. Если же пользователь попросит подсказку, не решай всю задачу за него, дай ему пару идей для продвижения в решении, и только если он попросит решение задачи, рапспиши полностью решение этой задачи. После чего, если пользователь сам решил задание и дал ответ или воспользовался твоим решением, спроси его, хочет ли он еще решить задание, и если да, сгенерируй новый ответ. Опять же, так как я использую тебя в телеграмме, старайсся отделять записи уравнений и примеров, не используй символы для форматизации текста, которые ты используешь в основном своем чате, а постарайся записывать примеры очень понятно и досконально. Дели условия и решения на логичные и смысловые части, и конечно, не пиши в ответ, комментарии разработчику, напиши в сообщение только то, что должен увидеть пользователь, а также отвечай только на вопросы пользователя связанные с математикой."
    }]
    
    try:
        completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3.2:novita",
            messages=user_story_chat[user_id],
        )
        
        await bot.delete_message(user_id, loading_message.message_id)
        
        await state.set_state(UserStates.chatting_mode)
        responsik = completion.choices[0].message.content
        
        # Форматируем ответ нейросети для лучшего отображения
        formatted_response = f"""
🎯 <b>Задание номер {user_metrics[user_id].Task_number}</b>
━━━━━━━━━━━━━━━━━━━━━━
{responsik}
━━━━━━━━━━━━━━━━━━━━━━
"""
        
        await bot.send_message(user_id, formatted_response, reply_markup=chat_keyboard)
        user_story_chat[user_id].append({"role": "assistant", "content": completion.choices[0].message.content})
        
    except Exception as e:
        await bot.edit_message_text(
            "❌ <b>Ошибка при генерации задания!</b>\n"
            "<i>Попробуйте еще раз позже.</i>",
            user_id,
            loading_message.message_id,
            reply_markup=start_keyboard
        )
        logging.error(f"Error in generating task: {e}")

@dp.message(StateFilter(UserStates.chatting_mode))
async def chat_mode_handler(message: types.Message, state: FSMContext):
    """Стилизованный обработчик режима чата"""
    user_id = message.from_user.id
    
    # Показываем индикатор набора сообщения
    await bot.send_chat_action(user_id, "typing")
    
    user_story_chat[user_id].append({"role": "user", "content": message.text})

    try:
        loading_message = await bot.send_message(
            user_id,
            "⏳ <b>Нейросеть думает...</b>"
        )
        
        completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3.2:novita",
            messages=user_story_chat[user_id]
        )
        
        await bot.delete_message(user_id, loading_message.message_id)
        
        response = completion.choices[0].message.content
        formatted_response = f"""
🤖 <b>Подсказка</b>
━━━━━━━━━━━━━━━━━━━━━━
{response}
━━━━━━━━━━━━━━━━━━━━━━
"""
        
        await bot.send_message(user_id, formatted_response, reply_markup=chat_keyboard)
        user_story_chat[user_id].append({"role": "assistant", "content": completion.choices[0].message.content})

    except Exception as e:
        await bot.send_message(
            user_id, 
            "❌ <b>Упс, произошла ошибка!</b>\n"
            "<i>Попробуйте еще раз или вернитесь в меню.</i>",
            reply_markup=chat_keyboard
        )
        logging.error(f"Error in chat mode: {e}")



@dp.callback_query(F.data == 'exit_chat', StateFilter(UserStates.chatting_mode))
async def exit_chat_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Выход из режима чата с красивым оформлением"""
    await bot.answer_callback_query(callback_query.id)
    
    await state.clear()
    
    await bot.send_message(
        callback_query.from_user.id,
        "👋 <b>Вы вышли из режима решения.</b>\n\n"
        "<i>Возвращаемся в главное меню...</i>",
        reply_markup=start_keyboard
    )

@dp.message(Command("metrics"))
async def show_metrics_command(message: types.Message):
    """Команда для показа метрик"""
    await show_metrics_inline(message)

@dp.message()
async def handle_other_messages(message: types.Message, state: FSMContext):
    """Обработчик прочих сообщений"""
    current_state = await state.get_state()
    if current_state == UserStates.chatting_mode:
        return
    
    user_id = message.from_user.id
    if user_id not in user_metrics:
        user_metrics[user_id] = Metrics()
    
    # Если это не команда, показываем помощь
    if not message.text.startswith('/'):
        help_message = """
ℹ️ <b>Помощь по использованию бота</b>

👇 <b>Основные команды:</b>
• /start - Главное меню
• /cancel - Отмена текущего действия
• /metrics - Показать текущие метрики

<b>Используйте кнопки для навигации:</b>
"""
        await message.answer(help_message, reply_markup=start_keyboard)
    else:
        await show_metrics_inline(message, user_id)

async def main():
    """Запуск бота"""
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())