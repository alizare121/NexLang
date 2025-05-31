import os
import logging
import json
import re
import tempfile
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import openai

# Import the translation cache
from translation_cache import TranslationCache

# تلاش برای import کردن dotenv، اگر نصب نبود از آن صرف نظر کن
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# تنظیم کلیدهای API
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7731221586:AAF0uDfEW-CkQ8C_zs5Wfmrf4oGPo_ZffKc')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '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')

# تنظیم OpenAI API key
openai.api_key = OPENAI_API_KEY

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize translation cache
translation_cache = TranslationCache()

# لیست کامل‌تر زبان‌های جهان
LANGUAGES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Japanese": "ja",
    "Chinese": "zh",
    "Korean": "ko",
    "Arabic": "ar",
    "Hindi": "hi",
    "Persian": "fa",
    "Turkish": "tr",
    "Dutch": "nl",
    "Swedish": "sv",
    "Norwegian": "no",
    "Danish": "da",
    "Finnish": "fi",
    "Polish": "pl",
    "Ukrainian": "uk",
    "Czech": "cs",
    "Hungarian": "hu",
    "Greek": "el",
    "Hebrew": "he",
    "Thai": "th",
    "Vietnamese": "vi",
    "Indonesian": "id",
    "Malay": "ms",
    "Tagalog": "tl",
    "Bengali": "bn",
    "Urdu": "ur",
    "Punjabi": "pa",
    "Tamil": "ta",
    "Telugu": "te",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Swahili": "sw",
    "Afrikaans": "af",
    "Albanian": "sq",
    "Armenian": "hy",
    "Azerbaijani": "az",
    "Basque": "eu",
    "Belarusian": "be",
    "Bulgarian": "bg",
    "Catalan": "ca",
    "Croatian": "hr",
    "Estonian": "et",
    "Filipino": "fil",
    "Galician": "gl",
    "Georgian": "ka",
    "Gujarati": "gu",
    "Haitian Creole": "ht",
    "Icelandic": "is",
    "Irish": "ga",
    "Kazakh": "kk",
    "Khmer": "km",
    "Lao": "lo",
    "Latvian": "lv",
    "Lithuanian": "lt",
    "Macedonian": "mk",
    "Marathi": "mr",
    "Mongolian": "mn",
    "Nepali": "ne",
    "Romanian": "ro",
    "Serbian": "sr",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Somali": "so",
    "Welsh": "cy",
    "Yiddish": "yi",
    "Zulu": "zu"
}

# تعداد سوالات ارزیابی
ASSESSMENT_QUESTIONS_COUNT = 10

# تعداد روزهای برنامه درسی
CURRICULUM_DAYS = 5

# User data storage
user_data = {}

async def save_user_data(user_id):
    """Save user data to a file."""
    try:
        filename = f"user_data_{user_id}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(user_data[user_id], f, ensure_ascii=False, indent=2)
        logger.info(f"User data saved for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving user data for user {user_id}: {e}")

async def load_user_data(user_id):
    """Load user data from a file."""
    try:
        filename = f"user_data_{user_id}.json"
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                user_data[user_id] = json.load(f)
            logger.info(f"User data loaded for user {user_id}")
            return True
    except Exception as e:
        logger.error(f"Error loading user data for user {user_id}: {e}")
    return False

async def translate_text(text, source_lang, target_lang):
    """Translate text using cache first, then OpenAI."""
    if source_lang == target_lang:
        return text

    # Check cache first
    cached_translation = translation_cache.get_translation(text, source_lang, target_lang)
    if cached_translation:
        logger.info(f"Using cached translation for {source_lang} -> {target_lang}")
        return cached_translation

    try:
        # Language name mapping
        language_names = {
            "en": "English", "fa": "Persian", "es": "Spanish", "fr": "French",
            "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian",
            "ja": "Japanese", "zh": "Chinese", "ar": "Arabic", "hi": "Hindi",
            "tr": "Turkish", "ko": "Korean", "nl": "Dutch", "sv": "Swedish",
            "no": "Norwegian", "da": "Danish", "fi": "Finnish", "pl": "Polish",
            "uk": "Ukrainian", "cs": "Czech", "hu": "Hungarian", "el": "Greek",
            "he": "Hebrew", "th": "Thai", "vi": "Vietnamese", "id": "Indonesian"
        }
        
        source_lang_name = language_names.get(source_lang, source_lang)
        target_lang_name = language_names.get(target_lang, target_lang)
        
        prompt = f"Translate the following text from {source_lang_name} to {target_lang_name}. Return ONLY the translated text, nothing else.\n\nText to translate: {text}"
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translator. Provide only the translation, no explanations or additional text."},
                {"role": "user", "content": prompt}
            ]
        )
        
        translated_text = response.choices[0].message['content'].strip()
        logger.info(f"Translated from {source_lang} to {target_lang}: {text} -> {translated_text}")
        
        # Add to cache
        translation_cache.add_translation(text, translated_text, source_lang, target_lang)
        
        return translated_text
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text

async def create_main_menu(user_id):
    """Create the main menu."""
    if user_id not in user_data:
        return None

    native_lang_code = user_data[user_id].get("native_language", {}).get("code", "en")

    menu_options = [
        ("🏠 Main Menu", "main_menu"),
        ("🌍 Change Languages", "change_languages"),
        ("📊 Retake Assessment", "retake_assessment"),
        ("📚 Learning Modes", "learning_modes"),
        ("📈 My Progress", "my_progress"),
        ("❓ Help", "help_menu")
    ]

    translated_options = []
    for text, callback in menu_options:
        emoji = text.split()[0] if text.split() else ""
        text_part = " ".join(text.split()[1:]) if len(text.split()) > 1 else text
        
        translated_text = await translate_text(text_part, "en", native_lang_code)
        translated_options.append((f"{emoji} {translated_text}", callback))

    keyboard = []
    for i in range(0, len(translated_options), 2):
        row = []
        row.append(InlineKeyboardButton(translated_options[i][0], callback_data=translated_options[i][1]))
        if i + 1 < len(translated_options):
            row.append(InlineKeyboardButton(translated_options[i+1][0], callback_data=translated_options[i+1][1]))
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)

async def create_learning_modes_menu(user_id):
    """Create learning modes menu."""
    if user_id not in user_data:
        return None

    native_lang_code = user_data[user_id].get("native_language", {}).get("code", "en")

    mode_options = [
        ("📚 Curriculum", "mode_curriculum"),
        ("📝 Vocabulary Practice", "mode_vocabulary"),
        ("💬 Useful Phrases", "mode_phrases"),
        ("🗣️ Conversation Practice", "mode_conversation"),
        ("🎤 Pronunciation Practice", "mode_pronunciation")
    ]

    translated_options = []
    for text, callback in mode_options:
        emoji = text.split()[0] if text.split() else ""
        text_part = " ".join(text.split()[1:]) if len(text.split()) > 1 else text
        
        translated_text = await translate_text(text_part, "en", native_lang_code)
        translated_options.append((f"{emoji} {translated_text}", callback))

    keyboard = []
    for text, callback in translated_options:
        keyboard.append([InlineKeyboardButton(text, callback_data=callback)])

    back_text = await translate_text("🔙 Back to Main Menu", "en", native_lang_code)
    keyboard.append([InlineKeyboardButton(back_text, callback_data="main_menu")])

    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when /start is issued."""
    user_id = update.effective_user.id

    data_loaded = await load_user_data(user_id)

    if not data_loaded:
        user_data[user_id] = {
            "native_language": None,
            "target_language": None,
            "proficiency_level": None,
            "current_state": "selecting_native_language",
            "learning_mode": None,
            "assessment": {
                "questions": [],
                "answers": [],
                "current_question": 0,
                "completed": False
            },
            "curriculum": {
                "overview": "",
                "days": {},
                "current_day": 0,
                "completed_days": []
            },
            "learning_history": [],
            "preferences": {},
            "voice_interactions": []
        }

    if (user_data[user_id].get("native_language") and user_data[user_id].get("target_language")):
        native_lang_code = user_data[user_id]["native_language"]["code"]
        target_lang_name = user_data[user_id]["target_language"]["name"]
        
        welcome_back_msg = f"Welcome back! 🎉\n\nYou're learning {target_lang_name}.\n\nYou can ask me any question about language learning, or use the menu below to navigate:"
        translated_welcome = await translate_text(welcome_back_msg, "en", native_lang_code)
        
        question_instruction = "\n\n💡 Feel free to ask me any question about language learning, grammar, vocabulary, or anything related to your studies!"
        voice_instruction = "\n\n🎤 You can also send voice messages to practice your pronunciation and speaking skills!"
        translated_instruction = await translate_text(question_instruction + voice_instruction, "en", native_lang_code)
        
        main_menu = await create_main_menu(user_id)
        
        await update.message.reply_text(
            translated_welcome + translated_instruction,
            reply_markup=main_menu
        )
        return

    # Create language selection keyboard
    languages_list = list(LANGUAGES.keys())
    keyboards = []
    current_keyboard = []
    row = []

    for i, lang in enumerate(languages_list):
        row.append(InlineKeyboardButton(lang, callback_data=f"native_{LANGUAGES[lang]}_{lang}"))
        if (i + 1) % 3 == 0:
            current_keyboard.append(row)
            row = []
        
        if (i + 1) % 15 == 0 and i != 0:
            if row:
                current_keyboard.append(row)
                row = []
            keyboards.append(current_keyboard)
            current_keyboard = []

    if row:
        current_keyboard.append(row)
    if current_keyboard:
        keyboards.append(current_keyboard)

    if len(keyboards) > 1:
        for i, keyboard in enumerate(keyboards):
            nav_row = []
            if i > 0:
                nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data=f"page_{i-1}"))
            if i < len(keyboards) - 1:
                nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"page_{i+1}"))
            keyboard.append(nav_row)

    user_data[user_id]["language_keyboards"] = keyboards
    user_data[user_id]["current_page"] = 0

    reply_markup = InlineKeyboardMarkup(keyboards[0])

    welcome_message = "Welcome to the Language Learning Bot! 🌍\n\nPlease select your native language:"

    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    if user_id not in user_data:
        await load_user_data(user_id)

    if callback_data == "main_menu":
        native_lang_code = user_data[user_id]["native_language"]["code"]
        target_lang_name = user_data[user_id]["target_language"]["name"]
        
        welcome_msg = f"Main Menu 🏠\n\nYou're learning {target_lang_name}.\n\nYou can ask me any question about language learning, or use the menu below:"
        translated_welcome = await translate_text(welcome_msg, "en", native_lang_code)
        
        question_instruction = "\n\n💡 Feel free to ask me any question!"
        voice_instruction = "\n\n🎤 You can also send voice messages to practice your pronunciation and speaking skills!"
        translated_instruction = await translate_text(question_instruction + voice_instruction, "en", native_lang_code)
        
        main_menu = await create_main_menu(user_id)
        
        await query.edit_message_text(
            translated_welcome + translated_instruction,
            reply_markup=main_menu
        )
        return

    elif callback_data == "learning_modes":
        native_lang_code = user_data[user_id]["native_language"]["code"]
        
        modes_msg = "Learning Modes 📚\n\nChoose how you want to learn today:"
        translated_msg = await translate_text(modes_msg, "en", native_lang_code)
        
        learning_menu = await create_learning_modes_menu(user_id)
        
        await query.edit_message_text(translated_msg, reply_markup=learning_menu)
        return

    elif callback_data == "change_languages":
        # Reset language selection
        user_data[user_id]["current_state"] = "selecting_native_language"
        
        # Create language selection keyboard
        languages_list = list(LANGUAGES.keys())
        keyboards = []
        current_keyboard = []
        row = []
        
        for i, lang in enumerate(languages_list):
            row.append(InlineKeyboardButton(lang, callback_data=f"native_{LANGUAGES[lang]}_{lang}"))
            if (i + 1) % 3 == 0:
                current_keyboard.append(row)
                row = []
            
            if (i + 1) % 15 == 0 and i != 0:
                if row:
                    current_keyboard.append(row)
                    row = []
                keyboards.append(current_keyboard)
                current_keyboard = []
        
        if row:
            current_keyboard.append(row)
        if current_keyboard:
            keyboards.append(current_keyboard)
        
        if len(keyboards) > 1:
            for i, keyboard in enumerate(keyboards):
                nav_row = []
                if i > 0:
                    nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data=f"page_{i-1}"))
                if i < len(keyboards) - 1:
                    nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"page_{i+1}"))
                keyboard.append(nav_row)
        
        user_data[user_id]["language_keyboards"] = keyboards
        user_data[user_id]["current_page"] = 0
        
        reply_markup = InlineKeyboardMarkup(keyboards[0])
        
        await query.edit_message_text(
            "Please select your native language:",
            reply_markup=reply_markup
        )
        return

    elif callback_data == "retake_assessment":
        # Reset assessment data
        user_data[user_id]["assessment"] = {
            "questions": [],
            "answers": [],
            "current_question": 0,
            "completed": False
        }
        user_data[user_id]["proficiency_level"] = None
        user_data[user_id]["current_state"] = "assessment_intro"
        
        native_lang_code = user_data[user_id]["native_language"]["code"]
        target_lang_name = user_data[user_id]["target_language"]["name"]
        
        assessment_msg = f"Let's retake your proficiency assessment for {target_lang_name}.\n\nI'll ask you {ASSESSMENT_QUESTIONS_COUNT} questions to determine your current level.\n\nAre you ready?"
        translated_msg = await translate_text(assessment_msg, "en", native_lang_code)
        
        yes_text = await translate_text("✅ Yes, I'm ready", "en", native_lang_code)
        back_text = await translate_text("🔙 Back to Menu", "en", native_lang_code)
        
        keyboard = [
            [InlineKeyboardButton(yes_text, callback_data="assessment_start")],
            [InlineKeyboardButton(back_text, callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            translated_msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif callback_data == "my_progress":
        native_lang_code = user_data[user_id]["native_language"]["code"]
        
        # Create progress summary
        progress_info = await create_progress_summary(user_id)
        
        back_text = await translate_text("🔙 Back to Menu", "en", native_lang_code)
        keyboard = [[InlineKeyboardButton(back_text, callback_data="main_menu")]]
        
        await query.edit_message_text(
            progress_info,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif callback_data == "help_menu":
        native_lang_code = user_data[user_id]["native_language"]["code"]
        
        help_text = "Help & Instructions 📖\n\n🤖 You can ask me any question about:\n• Grammar explanations\n• Vocabulary meanings\n• Language learning tips\n• Cultural information\n• Practice exercises\n\n🎤 Voice Messages:\n• Send voice messages to practice pronunciation\n• Get feedback on your speaking\n• Practice conversations\n\n📱 Commands:\n/start - Show main menu\n/help - Show this help message\n/reset - Reset all progress\n\n🎯 Use the menu buttons to navigate between different learning modes and features.\n\n💡 Tip: The more you practice, the better you'll become!"
        
        translated_help = await translate_text(help_text, "en", native_lang_code)
        
        back_text = await translate_text("🔙 Back to Menu", "en", native_lang_code)
        keyboard = [[InlineKeyboardButton(back_text, callback_data="main_menu")]]
        
        await query.edit_message_text(
            translated_help,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Handle pagination
    if callback_data.startswith("page_"):
        page = int(callback_data.split("_")[1])
        user_data[user_id]["current_page"] = page
        keyboards = user_data[user_id]["language_keyboards"]
        
        message = "Please select your native language:"
        
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboards[page])
        )
        return

    if callback_data.startswith("native_"):
        # Handle native language selection
        _, lang_code, lang_name = callback_data.split("_", 2)
        user_data[user_id]["native_language"] = {"code": lang_code, "name": lang_name}
        user_data[user_id]["current_state"] = "selecting_target_language"
        
        # Save user data
        await save_user_data(user_id)
        
        logger.info(f"User {user_id} selected native language: {lang_name} ({lang_code})")
        
        # پیام اصلی به انگلیسی
        original_message = f"Great! You've selected {lang_name} as your native language. Now, please select the language you want to learn:"
        
        # ترجمه پیام به زبان کاربر
        translated_message = await translate_text(original_message, "en", lang_code)
        
        logger.info(f"Original: {original_message}")
        logger.info(f"Translated: {translated_message}")
        
        # Create target language selection keyboard with pagination
        languages_list = list(LANGUAGES.keys())
        keyboards = []
        current_keyboard = []
        row = []
        
        # Create rows with 3 languages each (excluding native language)
        counter = 0
        for i, lang in enumerate(languages_list):
            # Skip the native language
            if LANGUAGES[lang] == lang_code:
                continue
                
            row.append(InlineKeyboardButton(lang, callback_data=f"target_{LANGUAGES[lang]}_{lang}"))
            counter += 1
            
            if counter % 3 == 0:
                current_keyboard.append(row)
                row = []
            
            # Create new keyboard after 15 languages (5 rows)
            if counter % 15 == 0 and counter != 0:
                if row:  # Add any remaining buttons in the row
                    current_keyboard.append(row)
                    row = []
                keyboards.append(current_keyboard)
                current_keyboard = []
        
        # Add any remaining rows and keyboards
        if row:
            current_keyboard.append(row)
        if current_keyboard:
            keyboards.append(current_keyboard)
        
        # Add navigation buttons for pagination
        if len(keyboards) > 1:
            for i, keyboard in enumerate(keyboards):
                nav_row = []
                
                # ترجمه دکمه‌های ناوبری
                prev_text = await translate_text("Previous", "en", lang_code)
                next_text = await translate_text("Next", "en", lang_code)
                
                if i > 0:
                    nav_row.append(InlineKeyboardButton(f"◀️ {prev_text}", callback_data=f"target_page_{i-1}"))
                if i < len(keyboards) - 1:
                    nav_row.append(InlineKeyboardButton(f"{next_text} ▶️", callback_data=f"target_page_{i+1}"))
                keyboard.append(nav_row)
        
        # Store keyboards in user data for pagination
        user_data[user_id]["target_keyboards"] = keyboards
        user_data[user_id]["current_target_page"] = 0
        
        reply_markup = InlineKeyboardMarkup(keyboards[0])
        
        await query.edit_message_text(
            text=translated_message,
            reply_markup=reply_markup
        )

    elif callback_data.startswith("target_page_"):
        # Handle target language pagination
        page = int(callback_data.split("_")[2])
        user_data[user_id]["current_target_page"] = page
        keyboards = user_data[user_id]["target_keyboards"]
        
        # Get native language for translation
        native_lang = user_data[user_id]["native_language"]["code"]
        
        # Translate the message
        original_message = "Please select the language you want to learn:"
        translated_message = await translate_text(original_message, "en", native_lang)
        
        await query.edit_message_text(
            text=translated_message,
            reply_markup=InlineKeyboardMarkup(keyboards[page])
        )
        
    elif callback_data.startswith("target_"):
        # Handle target language selection
        _, lang_code, lang_name = callback_data.split("_", 2)
        user_data[user_id]["target_language"] = {"code": lang_code, "name": lang_name}
        
        # Save user data
        await save_user_data(user_id)
        
        # تغییر حالت به مرحله اول ارزیابی
        user_data[user_id]["current_state"] = "assessment_intro"
        
        native_lang = user_data[user_id]["native_language"]["code"]
        
        # پیام اصلی به انگلیسی
        original_message = f"""
Excellent! You've chosen to learn {lang_name}.

Now I'm going to ask you {ASSESSMENT_QUESTIONS_COUNT} questions to assess your current proficiency level in {lang_name}. 
Try to answer in {lang_name} as best as you can. If you don't know the answer, you can say "I don't know" in {lang_name}.

You can also send voice messages to practice your speaking skills!

Are you ready to start the assessment?
"""
        
        # ترجمه پیام به زبان کاربر
        translated_message = await translate_text(original_message, "en", native_lang)
        
        # Create buttons for yes/no
        yes_text = await translate_text("Yes, I'm ready", "en", native_lang)
        no_text = await translate_text("No, later", "en", native_lang)
        
        keyboard = [
            [InlineKeyboardButton(yes_text, callback_data="assessment_start")],
            [InlineKeyboardButton(no_text, callback_data="assessment_cancel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=translated_message,
            reply_markup=reply_markup
        )

    elif callback_data == "assessment_start":
        # Start the assessment
        user_data[user_id]["current_state"] = "assessment_in_progress"
        target_lang = user_data[user_id]["target_language"]["name"]
        native_lang = user_data[user_id]["native_language"]["code"]
        
        # Generate assessment questions
        questions = await generate_assessment_questions(target_lang, native_lang)
        user_data[user_id]["assessment"]["questions"] = questions
        user_data[user_id]["assessment"]["current_question"] = 0
        user_data[user_id]["assessment"]["answers"] = []
        
        # Save user data
        await save_user_data(user_id)
        
        # Ask the first question
        await ask_next_assessment_question(update, context, user_id)

    elif callback_data == "assessment_cancel":
        # Cancel the assessment and go to main menu
        native_lang = user_data[user_id]["native_language"]["code"]
        target_lang = user_data[user_id]["target_language"]["name"]
        
        original_message = f"No problem. You can take the assessment anytime from the main menu. For now, I'll assume you're a beginner in {target_lang}."
        translated_message = await translate_text(original_message, "en", native_lang)
        
        # Set the proficiency level to beginner by default
        user_data[user_id]["proficiency_level"] = "Beginner"
        user_data[user_id]["current_state"] = "main_menu"
        
        # Save user data
        await save_user_data(user_id)
        
        # Show main menu
        main_menu = await create_main_menu(user_id)
        
        await query.edit_message_text(
            text=translated_message,
            reply_markup=main_menu
        )
        
    elif callback_data.startswith("mode_"):
        # Handle learning mode selection
        _, mode = callback_data.split("_", 1)
        user_data[user_id]["learning_mode"] = mode
        user_data[user_id]["current_state"] = "learning"
        
        # Save user data
        await save_user_data(user_id)
        
        native_lang_code = user_data[user_id]["native_language"]["code"]
        target_lang_name = user_data[user_id]["target_language"]["name"]
        proficiency = user_data[user_id]["proficiency_level"]
        
        # Prepare response based on selected mode
        if mode == "curriculum":
            original_response = f"Here's a personalized curriculum for your {proficiency} level in {target_lang_name}."
            
            # ترجمه پاسخ به زبان کاربر
            translated_response = await translate_text(original_response, "en", native_lang_code)
            
            # Generate curriculum overview
            curriculum_overview = await generate_curriculum_overview(
                target_lang_name,
                user_data[user_id]["native_language"]["name"],
                proficiency,
                native_lang_code
            )
            
            # Store the curriculum overview
            user_data[user_id]["curriculum"]["overview"] = curriculum_overview
            user_data[user_id]["current_state"] = "curriculum_overview"
            
            # Save user data
            await save_user_data(user_id)
            
            # Create buttons for starting day 1
            start_day_text = await translate_text("Start Day 1", "en", native_lang_code)
            back_text = await translate_text("Back to Learning Modes", "en", native_lang_code)
            main_menu_text = await translate_text("Main Menu", "en", native_lang_code)
            
            keyboard = [
                [InlineKeyboardButton(start_day_text, callback_data="curriculum_day_1")],
                [InlineKeyboardButton(back_text, callback_data="learning_modes")],
                [InlineKeyboardButton(main_menu_text, callback_data="main_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=f"{translated_response}\n\n{curriculum_overview}",
                reply_markup=reply_markup
            )
        
        elif mode == "pronunciation":
            # Handle pronunciation practice mode
            original_response = f"Let's practice pronunciation for your {proficiency} level in {target_lang_name}."
            translated_response = await translate_text(original_response, "en", native_lang_code)
            
            # Generate pronunciation instructions
            pronunciation_instructions = await generate_pronunciation_instructions(
                target_lang_name,
                user_data[user_id]["native_language"]["name"],
                proficiency,
                native_lang_code
            )
            
            # Create back buttons
            back_text = await translate_text("Back to Learning Modes", "en", native_lang_code)
            main_menu_text = await translate_text("Main Menu", "en", native_lang_code)
            
            keyboard = [
                [InlineKeyboardButton(back_text, callback_data="learning_modes")],
                [InlineKeyboardButton(main_menu_text, callback_data="main_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=f"{translated_response}\n\n{pronunciation_instructions}",
                reply_markup=reply_markup
            )
            
        else:
            # Handle other learning modes
            original_response = f"Let's practice {mode.replace('_', ' ')} for your {proficiency} level in {target_lang_name}."
            translated_response = await translate_text(original_response, "en", native_lang_code)
            
            # Generate learning content based on mode
            learning_content = await generate_learning_content(
                mode, 
                target_lang_name,
                user_data[user_id]["native_language"]["name"],
                proficiency,
                native_lang_code
            )
            
            # Create back buttons
            back_text = await translate_text("Back to Learning Modes", "en", native_lang_code)
            main_menu_text = await translate_text("Main Menu", "en", native_lang_code)
            
            keyboard = [
                [InlineKeyboardButton(back_text, callback_data="learning_modes")],
                [InlineKeyboardButton(main_menu_text, callback_data="main_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=f"{translated_response}\n\n{learning_content}",
                reply_markup=reply_markup
            )

    elif callback_data.startswith("curriculum_day_"):
        # Handle curriculum day selection
        day_number = int(callback_data.split("_")[-1])
        
        if day_number > CURRICULUM_DAYS:
            # If we've gone beyond the curriculum days, show completion menu
            await show_curriculum_completion_menu(update, context, user_id)
            return
        
        user_data[user_id]["curriculum"]["current_day"] = day_number
        native_lang_code = user_data[user_id]["native_language"]["code"]
        target_lang_name = user_data[user_id]["target_language"]["name"]
        proficiency = user_data[user_id]["proficiency_level"]
        
        # Save user data
        await save_user_data(user_id)
        
        if day_number == 0:
            # Show curriculum overview
            original_response = f"Here's a personalized curriculum for your {proficiency} level in {target_lang_name}."
            translated_response = await translate_text(original_response, "en", native_lang_code)
            
            curriculum_overview = user_data[user_id]["curriculum"]["overview"]
            
            # Create buttons for starting day 1
            start_day_text = await translate_text("Start Day 1", "en", native_lang_code)
            back_text = await translate_text("Back to Learning Modes", "en", native_lang_code)
            main_menu_text = await translate_text("Main Menu", "en", native_lang_code)
            
            keyboard = [
                [InlineKeyboardButton(start_day_text, callback_data="curriculum_day_1")],
                [InlineKeyboardButton(back_text, callback_data="learning_modes")],
                [InlineKeyboardButton(main_menu_text, callback_data="main_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=f"{translated_response}\n\n{curriculum_overview}",
                reply_markup=reply_markup
            )
            
        else:
            # Show specific day content
            user_data[user_id]["current_state"] = f"curriculum_day_{day_number}"
            
            # Check if we already have content for this day
            if day_number in user_data[user_id]["curriculum"]["days"]:
                day_content = user_data[user_id]["curriculum"]["days"][day_number]
            else:
                # Generate content for this day
                day_content = await generate_curriculum_day(
                    day_number,
                    target_lang_name,
                    user_data[user_id]["native_language"]["name"],
                    proficiency,
                    native_lang_code
                )
                # Store the day content
                user_data[user_id]["curriculum"]["days"][day_number] = day_content
                
                # Save user data
                await save_user_data(user_id)
            
            # Create navigation buttons
            button_texts = []
            
            if day_number > 1:
                prev_day_text = await translate_text(f"← Day {day_number-1}", "en", native_lang_code)
                button_texts.append((prev_day_text, f"curriculum_day_{day_number-1}"))
            
            overview_text = await translate_text("📋 Overview", "en", native_lang_code)
            button_texts.append((overview_text, "curriculum_day_0"))
            
            if day_number < CURRICULUM_DAYS:
                next_day_text = await translate_text(f"Day {day_number+1} →", "en", native_lang_code)
                button_texts.append((next_day_text, f"curriculum_day_{day_number+1}"))
            else:
                # Last day - show completion option
                complete_text = await translate_text("🎉 Complete Curriculum", "en", native_lang_code)
                button_texts.append((complete_text, "curriculum_complete"))
            
            # Create keyboard with navigation buttons
            keyboard = []
            row = []
            
            for text, callback in button_texts:
                row.append(InlineKeyboardButton(text, callback_data=callback))
                
                # Create a new row after 2 buttons
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            
            # Add any remaining buttons
            if row:
                keyboard.append(row)
            
            # Add menu buttons
            learning_modes_text = await translate_text("📚 Learning Modes", "en", native_lang_code)
            main_menu_text = await translate_text("🏠 Main Menu", "en", native_lang_code)
            keyboard.append([InlineKeyboardButton(learning_modes_text, callback_data="learning_modes")])
            keyboard.append([InlineKeyboardButton(main_menu_text, callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Create day header
            day_header = f"Day {day_number} of {CURRICULUM_DAYS}"
            translated_day_header = await translate_text(day_header, "en", native_lang_code)
            
            await query.edit_message_text(
                text=f"📚 {translated_day_header} 📚\n\n{day_content}",
                reply_markup=reply_markup
            )

    elif callback_data == "curriculum_complete":
        # Handle curriculum completion
        await show_curriculum_completion_menu(update, context, user_id)

async def show_curriculum_completion_menu(update, context, user_id):
    """Show menu after curriculum completion."""
    native_lang_code = user_data[user_id]["native_language"]["code"]

    # Mark curriculum as completed
    if user_data[user_id]["curriculum"]["current_day"] not in user_data[user_id]["curriculum"]["completed_days"]:
        user_data[user_id]["curriculum"]["completed_days"].append(user_data[user_id]["curriculum"]["current_day"])

    # Save user data
    await save_user_data(user_id)

    completion_msg = """
🎉 Congratulations! You've completed the curriculum! 🎉

What would you like to do next?

You can:
• Continue with other learning modes
• Retake the assessment to see your progress
• Practice more with vocabulary or conversation
• Ask me any questions about what you've learned
• Send voice messages to practice your pronunciation
"""

    translated_msg = await translate_text(completion_msg, "en", native_lang_code)

    # Create options menu
    vocab_text = await translate_text("📝 Vocabulary Practice", "en", native_lang_code)
    phrases_text = await translate_text("💬 Useful Phrases", "en", native_lang_code)
    conversation_text = await translate_text("🗣️ Conversation Practice", "en", native_lang_code)
    pronunciation_text = await translate_text("🎤 Pronunciation Practice", "en", native_lang_code)
    assessment_text = await translate_text("📊 Retake Assessment", "en", native_lang_code)
    main_menu_text = await translate_text("🏠 Main Menu", "en", native_lang_code)

    keyboard = [
        [InlineKeyboardButton(vocab_text, callback_data="mode_vocabulary")],
        [InlineKeyboardButton(phrases_text, callback_data="mode_phrases")],
        [InlineKeyboardButton(conversation_text, callback_data="mode_conversation")],
        [InlineKeyboardButton(pronunciation_text, callback_data="mode_pronunciation")],
        [InlineKeyboardButton(assessment_text, callback_data="retake_assessment")],
        [InlineKeyboardButton(main_menu_text, callback_data="main_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=translated_msg,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text=translated_msg,
            reply_markup=reply_markup
        )

async def create_progress_summary(user_id):
    """Create a summary of user's learning progress."""
    if user_id not in user_data:
        return "No progress data available."

    native_lang_code = user_data[user_id]["native_language"]["code"]
    target_lang_name = user_data[user_id]["target_language"]["name"]
    proficiency = user_data[user_id].get("proficiency_level", "Not assessed")

    # Count voice interactions
    voice_count = len(user_data[user_id].get("voice_interactions", []))

    # Create progress summary
    progress_text = f"""
📈 Your Learning Progress 📈

🌍 Learning: {target_lang_name}
📊 Current Level: {proficiency}
📚 Assessment: {"✅ Completed" if user_data[user_id]["assessment"].get("completed") else "❌ Not completed"}
🎤 Voice Interactions: {voice_count}

📖 Curriculum Progress:
"""

    # Add curriculum progress
    completed_days = user_data[user_id]["curriculum"].get("completed_days", [])
    for day in range(1, CURRICULUM_DAYS + 1):
        status = "✅" if day in completed_days else "⭕"
        progress_text += f"{status} Day {day}\n"

    # Add learning history if available
    learning_history = user_data[user_id].get("learning_history", [])
    if learning_history:
        progress_text += f"\n🕒 Recent Activity:\n"
        for activity in learning_history[-3:]:  # Show last 3 activities
            progress_text += f"• {activity}\n"

    progress_text += f"\n💡 Keep practicing to improve your {target_lang_name} skills!"

    # Translate to user's native language
    translated_progress = await translate_text(progress_text, "en", native_lang_code)

    return translated_progress

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user messages."""
    user_id = update.effective_user.id

    if user_id not in user_data:
        await load_user_data(user_id)

    if user_id not in user_data:
        await start(update, context)
        return

    # Check if this is a voice message
    if update.message.voice:
        await handle_voice_message(update, context)
        return

    # Handle text messages
    if update.message.text:
        message_text = update.message.text
        
        # Generate response
        response = await generate_personalized_response(message_text, user_data[user_id])
        
        # Add menu suggestion
        native_lang_code = user_data[user_id]["native_language"]["code"]
        menu_suggestion = "\n\n💡 Use /start to access the main menu anytime!"
        voice_suggestion = "\n\n🎤 You can also send voice messages to practice your pronunciation!"
        translated_menu_suggestion = await translate_text(menu_suggestion + voice_suggestion, "en", native_lang_code)
        
        await update.message.reply_text(response + translated_menu_suggestion)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages from users."""
    user_id = update.effective_user.id
    voice = update.message.voice

    if user_id not in user_data:
        await load_user_data(user_id)

    if user_id not in user_data:
        await start(update, context)
        return

    native_lang_code = user_data[user_id]["native_language"]["code"]
    target_lang_code = user_data[user_id]["target_language"]["code"]
    target_lang_name = user_data[user_id]["target_language"]["name"]
    proficiency = user_data[user_id].get("proficiency_level", "Beginner")

    processing_msg = "🎤 Processing your voice message..."
    translated_processing = await translate_text(processing_msg, "en", native_lang_code)
    processing_message = await update.message.reply_text(translated_processing)

    try:
        voice_file = await context.bot.get_file(voice.file_id)
        
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            await voice_file.download_to_drive(temp_file.name)
            temp_file_path = temp_file.name
        
        transcription = await transcribe_audio(temp_file_path, target_lang_code)
        
        try:
            os.unlink(temp_file_path)
        except Exception as e:
            logger.error(f"Error deleting temporary file: {e}")
        
        if "voice_interactions" not in user_data[user_id]:
            user_data[user_id]["voice_interactions"] = []
        
        user_data[user_id]["voice_interactions"].append({
            "timestamp": str(update.message.date),
            "duration": voice.duration,
            "transcription": transcription
        })
        
        await save_user_data(user_id)
        
        feedback = await generate_voice_feedback(transcription, target_lang_name, native_lang_code, proficiency)
        
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=processing_message.message_id
        )
        
        transcription_header = "🎤 I heard:"
        translated_header = await translate_text(transcription_header, "en", native_lang_code)
        
        feedback_message = f"{translated_header}\n\n\"{transcription}\"\n\n{feedback}"
        
        menu_suggestion = "\n\n💡 You can continue practicing or use /start to access the main menu!"
        translated_menu_suggestion = await translate_text(menu_suggestion, "en", native_lang_code)
        
        await update.message.reply_text(feedback_message + translated_menu_suggestion)
        
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id
            )
        except:
            pass
        
        error_msg = "Sorry, I couldn't process your voice message. Please try again later."
        translated_error = await translate_text(error_msg, "en", native_lang_code)
        await update.message.reply_text(translated_error)

async def transcribe_audio(audio_file_path, language_code):
    """Transcribe audio file using OpenAI Whisper API."""
    try:
        with open(audio_file_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language=language_code
            )
            return response["text"]
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return "Sorry, I couldn't transcribe your audio."

async def generate_voice_feedback(transcription, target_lang, native_lang_code, proficiency):
    """Generate feedback on the user's voice message."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": f"You are a language teacher providing feedback on a student's speaking practice. The student is at {proficiency} level in {target_lang}. Analyze the transcription and provide: 1. Positive feedback 2. Corrections 3. Pronunciation tips 4. Improvement suggestions. Be encouraging and supportive."
                },
                {
                    "role": "user", 
                    "content": f"Here is the transcription of my speech practice in {target_lang}: \"{transcription}\""
                }
            ]
        )
        
        feedback = response.choices[0].message['content']
        translated_feedback = await translate_text(feedback, "en", native_lang_code)
        return translated_feedback
        
    except Exception as e:
        logger.error(f"Error generating voice feedback: {e}")
        error_message = "Thank you for practicing your speaking! Keep practicing to improve your pronunciation and fluency."
        translated_error = await translate_text(error_message, "en", native_lang_code)
        return translated_error

async def generate_personalized_response(user_message, user_profile):
    """Generate a personalized response based on user's profile and message."""
    try:
        native_lang_code = user_profile["native_language"]["code"]
        native_lang_name = user_profile["native_language"]["name"]
        target_lang_name = user_profile["target_language"]["name"]
        proficiency = user_profile.get("proficiency_level", "Beginner")
        
        system_prompt = f"You are a personalized language learning assistant. User profile: Native Language: {native_lang_name}, Learning: {target_lang_name}, Level: {proficiency}. Respond helpfully in {native_lang_name} with {target_lang_name} examples when relevant."
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        
        return response.choices[0].message['content']
        
    except Exception as e:
        logger.error(f"Error generating personalized response: {e}")
        error_message = "I'm here to help you learn! Feel free to ask me any questions about grammar, vocabulary, or language learning tips."
        translated_error = await translate_text(error_message, "en", native_lang_code)
        return translated_error

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message."""
    user_id = update.effective_user.id

    if user_id not in user_data:
        await load_user_data(user_id)

    help_text = "Help & Instructions 📖\n\n🤖 You can ask me any question about:\n• Grammar explanations\n• Vocabulary meanings\n• Language learning tips\n• Cultural information\n• Practice exercises\n\n🎤 Voice Messages:\n• Send voice messages to practice pronunciation\n• Get feedback on your speaking\n• Practice conversations\n\n📱 Commands:\n/start - Show main menu\n/help - Show this help message\n/reset - Reset your learning progress\n\n🎯 Use the menu buttons to navigate between different learning modes and features.\n\n💡 Tip: The more you practice, the better you'll become!"

    if user_id in user_data and user_data[user_id].get("native_language"):
        native_lang = user_data[user_id]["native_language"]["code"]
        translated_help = await translate_text(help_text, "en", native_lang)
        
        main_menu_text = await translate_text("🏠 Main Menu", "en", native_lang)
        keyboard = [[InlineKeyboardButton(main_menu_text, callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(translated_help, reply_markup=reply_markup)
    else:
        await update.message.reply_text(help_text)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset user data."""
    user_id = update.effective_user.id

    if user_id not in user_data:
        await load_user_data(user_id)

    if user_id in user_data:
        native_lang_code = None
        if user_data[user_id].get("native_language"):
            native_lang_code = user_data[user_id]["native_language"]["code"]
        
        user_data[user_id] = {
            "native_language": None,
            "target_language": None,
            "proficiency_level": None,
            "current_state": "selecting_native_language",
            "learning_mode": None,
            "assessment": {
                "questions": [],
                "answers": [],
                "current_question": 0,
                "completed": False
            },
            "curriculum": {
                "overview": "",
                "days": {},
                "current_day": 0,
                "completed_days": []
            },
            "learning_history": [],
            "preferences": {},
            "voice_interactions": []
        }
        
        await save_user_data(user_id)
        
        if native_lang_code:
            original_reset_text = "Your learning progress has been completely reset. Let's start fresh!"
            translated_reset = await translate_text(original_reset_text, "en", native_lang_code)
            await update.message.reply_text(translated_reset)
        else:
            await update.message.reply_text("Your learning progress has been completely reset. Let's start fresh!")
        
        await start(update, context)
    else:
        await start(update, context)

def test_translation():
    """Test the translation functionality."""
    test_text = "Hello, welcome to the language learning bot!"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translator. Translate from English to Persian."},
                {"role": "user", "content": test_text}
            ]
        )
        translated = response.choices[0].message['content'].strip()
        logger.info("Translation test:")
        logger.info(f"English: {test_text}")
        logger.info(f"Persian: {translated}")
        
        translation_cache.add_translation(test_text, translated, "en", "fa")
        translation_cache.save_cache()
    except Exception as e:
        logger.error(f"Translation test error: {e}")

def preload_common_translations():
    """Preload translations for common phrases."""
    logger.info("Preloading common translations...")
    translation_cache.save_cache()
    logger.info("Preloading completed.")

def main() -> None:
    """Start the bot."""
    test_translation()
    preload_common_translations()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    application.run_polling()

if __name__ == '__main__':
    main()
