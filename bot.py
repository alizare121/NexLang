import os
import logging
import json
import re
import tempfile
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import openai  # استفاده از openai به روش قدیمی

# Import the translation cache
from translation_cache import TranslationCache

# تلاش برای import کردن dotenv، اگر نصب نبود از آن صرف نظر کن
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # اگر dotenv نصب نبود، از آن صرف نظر کن

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

# User data storage (in a real application, use a database)
user_data = {}

async def save_user_data(user_id):
    """Save user data to a file (in production, use a proper database)."""
    try:
        filename = f"user_data_{user_id}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(user_data[user_id], f, ensure_ascii=False, indent=2)
        logger.info(f"User data saved for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving user data for user {user_id}: {e}")

async def load_user_data(user_id):
    """Load user data from a file (in production, use a proper database)."""
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
    
    # Check if we have this translation in cache
    cached_translation = translation_cache.get_translation(text, source_lang, target_lang)
    if cached_translation:
        logger.info(f"Using cached translation for {source_lang} -> {target_lang}")
        return cached_translation
    
    try:
        # برای اطمینان از عملکرد صحیح، کد زبان را به نام کامل تبدیل می‌کنیم
        language_names = {
            "en": "English",
            "fa": "Persian",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "zh": "Chinese",
            "ar": "Arabic",
            "hi": "Hindi",
            "tr": "Turkish",
            "ko": "Korean",
            "nl": "Dutch",
            "sv": "Swedish",
            "no": "Norwegian",
            "da": "Danish",
            "fi": "Finnish",
            "pl": "Polish",
            "uk": "Ukrainian",
            "cs": "Czech",
            "hu": "Hungarian",
            "el": "Greek",
            "he": "Hebrew",
            "th": "Thai",
            "vi": "Vietnamese",
            "id": "Indonesian"
            # می‌توانید زبان‌های بیشتری اضافه کنید
        }
        
        source_lang_name = language_names.get(source_lang, source_lang)
        target_lang_name = language_names.get(target_lang, target_lang)
        
        # استفاده از پرامپت واضح‌تر برای ترجمه
        prompt = f"""
        Translate the following text from {source_lang_name} to {target_lang_name}.
        Return ONLY the translated text, nothing else.
        
        Text to translate: {text}
        """
        
        # استفاده از API قدیمی OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a professional translator. Translate from {source_lang_name} to {target_lang_name}. Provide ONLY the translated text, no explanations or additional text."},
                {"role": "user", "content": prompt}
            ]
        )
        
        translated_text = response.choices[0].message['content'].strip()
        logger.info(f"Translated from {source_lang} to {target_lang}: {text} -> {translated_text}")
        
        # Add successful translation to cache
        translation_cache.add_translation(text, translated_text, source_lang, target_lang)
        
        return translated_text
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text  # Fallback to original text

async def translate_buttons(buttons, source_lang, target_lang):
    """Translate a list of button labels."""
    translated_buttons = []
    
    for button in buttons:
        try:
            translated_button = await translate_text(button, source_lang, target_lang)
            translated_buttons.append(translated_button)
        except:
            translated_buttons.append(button)
    
    return translated_buttons

async def create_main_menu(user_id):
    """Create the main menu with all available options."""
    if user_id not in user_data:
        return None
    
    native_lang_code = user_data[user_id].get("native_language", {}).get("code", "en")
    
    # Menu options
    menu_options = [
        ("🏠 Main Menu", "main_menu"),
        ("🌍 Change Languages", "change_languages"),
        ("📊 Retake Assessment", "retake_assessment"),
        ("📚 Learning Modes", "learning_modes"),
        ("📈 My Progress", "my_progress"),
        ("❓ Help", "help_menu")
    ]
    
    # Translate menu options
    translated_options = []
    for text, callback in menu_options:
        # Extract emoji and text
        emoji = text.split()[0] if text.split() else ""
        text_part = " ".join(text.split()[1:]) if len(text.split()) > 1 else text
        
        translated_text = await translate_text(text_part, "en", native_lang_code)
        translated_options.append((f"{emoji} {translated_text}", callback))
    
    # Create keyboard
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
    
    # Learning mode options
    mode_options = [
        ("📚 Curriculum", "mode_curriculum"),
        ("📝 Vocabulary Practice", "mode_vocabulary"),
        ("💬 Useful Phrases", "mode_phrases"),
        ("🗣️ Conversation Practice", "mode_conversation"),
        ("🎤 Pronunciation Practice", "mode_pronunciation")  # اضافه کردن گزینه تمرین تلفظ
    ]
    
    # Translate options
    translated_options = []
    for text, callback in mode_options:
        # Extract emoji and text
        emoji = text.split()[0] if text.split() else ""
        text_part = " ".join(text.split()[1:]) if len(text.split()) > 1 else text
        
        translated_text = await translate_text(text_part, "en", native_lang_code)
        translated_options.append((f"{emoji} {translated_text}", callback))
    
    # Create keyboard
    keyboard = []
    for text, callback in translated_options:
        keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
    
    # Add back button
    back_text = await translate_text("🔙 Back to Main Menu", "en", native_lang_code)
    keyboard.append([InlineKeyboardButton(back_text, callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user_id = update.effective_user.id
    
    # Try to load existing user data
    data_loaded = await load_user_data(user_id)
    
    if not data_loaded:
        # Initialize new user data
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
            "voice_interactions": []  # اضافه کردن آرایه برای ذخیره تعاملات صوتی
        }
    
    # If user already has languages set, show main menu
    if (user_data[user_id].get("native_language") and 
        user_data[user_id].get("target_language")):
        
        native_lang_code = user_data[user_id]["native_language"]["code"]
        target_lang_name = user_data[user_id]["target_language"]["name"]
        
        welcome_back_msg = f"Welcome back! 🎉\n\nYou're learning {target_lang_name}.\n\nYou can ask me any question about language learning, or use the menu below to navigate:"
        translated_welcome = await translate_text(welcome_back_msg, "en", native_lang_code)
        
        # Add instruction about asking questions
        question_instruction = "\n\n💡 Feel free to ask me any question about language learning, grammar, vocabulary, or anything related to your studies!"
        voice_instruction = "\n\n🎤 You can also send voice messages to practice your pronunciation and speaking skills!"
        translated_instruction = await translate_text(question_instruction + voice_instruction, "en", native_lang_code)
        
        main_menu = await create_main_menu(user_id)
        
        await update.message.reply_text(
            translated_welcome + translated_instruction,
            reply_markup=main_menu
        )
        return
    
    # Create language selection keyboard with pagination
    languages_list = list(LANGUAGES.keys())
    keyboards = []
    current_keyboard = []
    row = []
    
    # Create rows with 3 languages each
    for i, lang in enumerate(languages_list):
        row.append(InlineKeyboardButton(lang, callback_data=f"native_{LANGUAGES[lang]}_{lang}"))
        if (i + 1) % 3 == 0:
            current_keyboard.append(row)
            row = []
        
        # Create new keyboard after 15 languages (5 rows)
        if (i + 1) % 15 == 0 and i != 0:
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
            if i > 0:
                nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data=f"page_{i-1}"))
            if i < len(keyboards) - 1:
                nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"page_{i+1}"))
            keyboard.append(nav_row)
    
    # Store keyboards in user data for pagination
    user_data[user_id]["language_keyboards"] = keyboards
    user_data[user_id]["current_page"] = 0
    
    reply_markup = InlineKeyboardMarkup(keyboards[0])
    
    welcome_message = "Welcome to the Language Learning Bot! 🌍\n\nPlease select your native language:"
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    # Load user data if not in memory
    if user_id not in user_data:
        await load_user_data(user_id)
    
    # Handle main menu options
    if callback_data == "main_menu":
        native_lang_code = user_data[user_id]["native_language"]["code"]
        target_lang_name = user_data[user_id]["target_language"]["name"]
        
        welcome_msg = f"Main Menu 🏠\n\nYou're learning {target_lang_name}.\n\nYou can ask me any question about language learning, or use the menu below:"
        translated_welcome = await translate_text(welcome_msg, "en", native_lang_code)
        
        # Add instruction about asking questions
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
        
        await query.edit_message_text(
            translated_msg,
            reply_markup=learning_menu
        )
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
        
        help_text = """
Help & Instructions 📖

🤖 You can ask me any question about:
• Grammar explanations
• Vocabulary meanings
• Language learning tips
• Cultural information
• Practice exercises

🎤 Voice Messages:
• Send voice messages to practice pronunciation
• Get feedback on your speaking
• Practice conversations

📱 Commands:
/start - Restart or show main menu
/help - Show this help
/reset - Reset all progress

🎯 Use the menu buttons to navigate between different learning modes and features.

💡 Tip: The more you practice, the better you'll become!
"""
        
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
    
    # Load user data if not in memory
    if user_id not in user_data:
        await load_user_data(user_id)
    
    # If user is not in our database, start the conversation
    if user_id not in user_data:
        await start(update, context)
        return
    
    current_state = user_data[user_id]["current_state"]
    
    # Check if this is a voice message
    if update.message.voice:
        await handle_voice_message(update, context)
        return
    
    # Handle text messages
    if update.message.text:
        message_text = update.message.text
        
        if current_state == "assessment_in_progress":
            # Handle assessment question response
            current_question = user_data[user_id]["assessment"]["current_question"]
            
            # Store the answer
            user_data[user_id]["assessment"]["answers"].append(message_text)
            
            # Save user data
            await save_user_data(user_id)
            
            # Move to the next question or finish assessment
            if current_question + 1 < len(user_data[user_id]["assessment"]["questions"]):
                user_data[user_id]["assessment"]["current_question"] += 1
                await ask_next_assessment_question(update, context, user_id)
            else:
                # Assessment complete, evaluate proficiency
                await complete_assessment(update, context, user_id)
        
        else:
            # Handle general questions and learning interaction
            learning_mode = user_data[user_id].get("learning_mode", "general")
            target_lang_name = user_data[user_id]["target_language"]["name"]
            native_lang_name = user_data[user_id]["native_language"]["name"]
            native_lang_code = user_data[user_id]["native_language"]["code"]
            proficiency = user_data[user_id].get("proficiency_level", "Beginner")
            
            # Add to learning history
            if "learning_history" not in user_data[user_id]:
                user_data[user_id]["learning_history"] = []
            
            user_data[user_id]["learning_history"].append(f"Asked: {message_text[:50]}...")
            
            # Keep only last 10 activities
            if len(user_data[user_id]["learning_history"]) > 10:
                user_data[user_id]["learning_history"] = user_data[user_id]["learning_history"][-10:]
            
            # Save user data
            await save_user_data(user_id)
            
            # Generate personalized response
            if current_state.startswith("curriculum_day_"):
                day_number = int(current_state.split("_")[-1])
                
                # Generate response based on user's message and current day
                response = await generate_curriculum_response(
                    message_text,
                    day_number,
                    target_lang_name,
                    native_lang_name,
                    native_lang_code,
                    proficiency
                )
            else:
                # Generate general response based on user's profile
                response = await generate_personalized_response(
                    message_text,
                    user_data[user_id]
                )
            
            # Add menu suggestion
            menu_suggestion = "\n\n💡 Use /start to access the main menu anytime!"
            voice_suggestion = "\n\n🎤 You can also send voice messages to practice your pronunciation!"
            translated_menu_suggestion = await translate_text(menu_suggestion + voice_suggestion, "en", native_lang_code)
            
            await update.message.reply_text(response + translated_menu_suggestion)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages from users."""
    user_id = update.effective_user.id
    voice = update.message.voice
    
    # Load user data if not in memory
    if user_id not in user_data:
        await load_user_data(user_id)
    
    # If user is not in our database, start the conversation
    if user_id not in user_data:
        await start(update, context)
        return
    
    # Get user language information
    native_lang_code = user_data[user_id]["native_language"]["code"]
    target_lang_code = user_data[user_id]["target_language"]["code"]
    target_lang_name = user_data[user_id]["target_language"]["name"]
    proficiency = user_data[user_id].get("proficiency_level", "Beginner")
    
    # Send a processing message
    processing_msg = "🎤 Processing your voice message..."
    translated_processing = await translate_text(processing_msg, "en", native_lang_code)
    processing_message = await update.message.reply_text(translated_processing)
    
    try:
        # Get the voice file
        voice_file = await context.bot.get_file(voice.file_id)
        
        # Create a temporary file to save the voice message
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            # Download the voice file
            await voice_file.download_to_drive(temp_file.name)
            temp_file_path = temp_file.name
        
        # Transcribe the voice message
        transcription = await transcribe_audio(temp_file_path, target_lang_code)
        
        # Clean up the temporary file
        try:
            os.unlink(temp_file_path)
        except Exception as e:
            logger.error(f"Error deleting temporary file: {e}")
        
        # Store the voice interaction
        if "voice_interactions" not in user_data[user_id]:
            user_data[user_id]["voice_interactions"] = []
        
        user_data[user_id]["voice_interactions"].append({
            "timestamp": str(update.message.date),
            "duration": voice.duration,
            "transcription": transcription
        })
        
        # Add to learning history
        if "learning_history" not in user_data[user_id]:
            user_data[user_id]["learning_history"] = []
        
        user_data[user_id]["learning_history"].append(f"Voice message: {transcription[:30]}...")
        
        # Keep only last 10 activities
        if len(user_data[user_id]["learning_history"]) > 10:
            user_data[user_id]["learning_history"] = user_data[user_id]["learning_history"][-10:]
        
        # Save user data
        await save_user_data(user_id)
        
        # Generate feedback on pronunciation and language use
        feedback = await generate_voice_feedback(
            transcription,
            target_lang_name,
            native_lang_code,
            proficiency
        )
        
        # Delete the processing message
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=processing_message.message_id
        )
        
        # Send the transcription and feedback
        transcription_header = "🎤 I heard:"
        translated_header = await translate_text(transcription_header, "en", native_lang_code)
        
        feedback_message = f"{translated_header}\n\n\"{transcription}\"\n\n{feedback}"
        
        # Add menu suggestion
        menu_suggestion = "\n\n💡 You can continue practicing or use /start to access the main menu!"
        translated_menu_suggestion = await translate_text(menu_suggestion, "en", native_lang_code)
        
        await update.message.reply_text(feedback_message + translated_menu_suggestion)
        
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        
        # Delete the processing message
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_message.message_id
            )
        except:
            pass
        
        # Send error message
        error_msg = "Sorry, I couldn't process your voice message. Please try again later."
        translated_error = await translate_text(error_msg, "en", native_lang_code)
        await update.message.reply_text(translated_error)

async def transcribe_audio(audio_file_path, language_code):
    """Transcribe audio file using OpenAI Whisper API."""
    try:
        with open(audio_file_path, "rb") as audio_file:
            # استفاده از API قدیمی OpenAI برای Whisper
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
        # استفاده از API قدیمی OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": f"""
                    You are a language teacher providing feedback on a student's speaking practice.
                    The student is at {proficiency} level in {target_lang}.
                    
                    Analyze the transcription of their speech and provide:
                    1. Positive feedback on what they did well
                    2. Corrections for any grammar or vocabulary errors
                    3. Pronunciation tips (based on common issues for speakers of their level)
                    4. A suggestion for how they can improve
                    
                    Be encouraging and supportive. Write your response in their native language.
                    """
                },
                {
                    "role": "user", 
                    "content": f"Here is the transcription of my speech practice in {target_lang}: \"{transcription}\""
                }
            ]
        )
        
        feedback = response.choices[0].message['content']
        
        # The feedback is already generated in the user's native language, no need to translate
        translated_feedback = feedback
        
        return translated_feedback
        
    except Exception as e:
        logger.error(f"Error generating voice feedback: {e}")
        
        # Fallback feedback
        error_message = "Thank you for practicing your speaking! Keep practicing to improve your pronunciation and fluency."
        translated_error = await translate_text(error_message, "en", native_lang_code)
        
        return translated_error

async def generate_pronunciation_instructions(target_lang, native_lang, proficiency, native_lang_code):
    """Generate pronunciation practice instructions."""
    try:
        # استفاده از API قدیمی OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": f"""
                    You are a language pronunciation coach creating instructions for {proficiency} level students learning {target_lang} from {native_lang}.
                    
                    Create comprehensive pronunciation practice instructions that include:
                    1. 5-10 words or phrases to practice with phonetic transcriptions
                    2. Common pronunciation challenges for {native_lang} speakers learning {target_lang}
                    3. Specific sounds to focus on
                    4. Tips for improving accent and intonation
                    5. Instructions for recording and self-evaluating pronunciation
                    
                    Format your response in a clear, organized way with sections and examples.
                    Write in {native_lang}, with {target_lang} examples where appropriate.
                    Make it engaging and educational.
                    """
                },
                {
                    "role": "user", 
                    "content": f"Create pronunciation practice instructions for {proficiency} level {target_lang} learners who speak {native_lang}."
                }
            ]
        )
        
        instructions = response.choices[0].message['content']
        
        # Add voice message instructions - this will be included in the main instructions
        voice_instructions = "\n\n🎤 **How to Practice**: Record voice messages pronouncing these words and phrases, and I'll give you feedback on your pronunciation!"
        translated_voice_instructions = await translate_text(voice_instructions, "en", native_lang_code)

        return instructions + translated_voice_instructions
        
    except Exception as e:
        logger.error(f"Error generating pronunciation instructions: {e}")
        
        # ترجمه پیام خطا به زبان کاربر
        error_message = "Sorry, I couldn't generate pronunciation instructions at this time. Please try again later."
        translated_error = await translate_text(error_message, "en", native_lang_code)
        
        return translated_error

async def generate_personalized_response(user_message, user_profile):
    """Generate a personalized response based on user's profile and message."""
    try:
        native_lang_code = user_profile["native_language"]["code"]
        native_lang_name = user_profile["native_language"]["name"]
        target_lang_name = user_profile["target_language"]["name"]
        proficiency = user_profile.get("proficiency_level", "Beginner")
        learning_mode = user_profile.get("learning_mode", "general")
        
        # Create a comprehensive prompt based on user's profile
        system_prompt = f"""
You are a personalized language learning assistant. Here's the user's profile:

- Native Language: {native_lang_name}
- Learning: {target_lang_name}
- Proficiency Level: {proficiency}
- Current Learning Mode: {learning_mode}
- Assessment Completed: {user_profile["assessment"].get("completed", False)}

IMPORTANT: Respond ONLY in {native_lang_name}. All explanations, instructions, and feedback should be in {native_lang_name}.
When providing examples in {target_lang_name}, always include the translation to {native_lang_name}.

Respond to their question or message in a helpful, educational way that's appropriate for their level.
Be encouraging and supportive.
If they ask about grammar, vocabulary, or language concepts, provide clear explanations with examples.
If they practice in {target_lang_name}, provide constructive feedback and corrections.

Remember to:
1. Write everything in {native_lang_name}
2. Match your response complexity to their proficiency level
3. Provide translations when helpful
4. Encourage continued learning
5. Suggest related practice activities when appropriate
"""
        
        # استفاده از API قدیمی OpenAI
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
        
        # Fallback response
        error_message = "I'm here to help you learn! Feel free to ask me any questions about grammar, vocabulary, or language learning tips."
        translated_error = await translate_text(error_message, "en", native_lang_code)
        
        return translated_error

async def generate_assessment_questions(target_lang, native_lang_code):
    """Generate assessment questions for the target language."""
    try:
        # Generate questions with OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": f"""
                    You are a language proficiency assessor for {target_lang}. 
                    Create {ASSESSMENT_QUESTIONS_COUNT} assessment questions to determine a language learner's proficiency level (Beginner, Intermediate, Advanced).
                    
                    Questions should:
                    1. Be of increasing difficulty
                    2. Test grammar, vocabulary, comprehension, and expression
                    3. Include a mix of multiple choice, short answer, and open-ended questions
                    4. Be appropriate for assessing proficiency in {target_lang}
                    
                    Format your response as a JSON array of question objects with these fields:
                    - question: The question text in the target language
                    - translation: Translation of the question into the user's native language
                    - type: The question type (multiple_choice, short_answer, open_ended)
                    - options: Array of options (only for multiple_choice questions)
                    - difficulty: The difficulty level (1-10)
                    
                    Do not include the correct answer in the output.
                    """
                }
            ]
        )
        
        # Extract and parse the questions
        questions_json = response.choices[0].message['content']
        try:
            questions = json.loads(questions_json)
        except json.JSONDecodeError:
            # Try to extract JSON from the text if it's not pure JSON
            import re
            json_pattern = r'(\[\s*\{.*\}\s*\])'
            match = re.search(json_pattern, questions_json, re.DOTALL)
            if match:
                questions_json = match.group(1)
                questions = json.loads(questions_json)
            else:
                # Fallback to a simpler approach if JSON parsing fails
                logger.error("Failed to parse JSON response for assessment questions")
                questions = await generate_simple_assessment_questions(target_lang, native_lang_code)
        
        # Translate questions to user's native language if needed
        for question in questions:
            if "translation" not in question or not question["translation"]:
                question["translation"] = await translate_text(question["question"], "auto", native_lang_code)
        
        return questions
    
    except Exception as e:
        logger.error(f"Error generating assessment questions: {e}")
        # Fallback to simpler questions if there's an error
        return await generate_simple_assessment_questions(target_lang, native_lang_code)

async def generate_simple_assessment_questions(target_lang, native_lang_code):
    """Generate simple assessment questions as a fallback."""
    questions = []
    
    # Basic questions that should work for any language
    basic_questions = [
        "What is your name?",
        "How are you today?",
        "Can you count from 1 to 10?",
        "What day is it today?",
        "What is your favorite color?",
        "What do you do for work or study?",
        "Describe your family briefly.",
        "What did you do yesterday?",
        "What will you do tomorrow?",
        "Why are you learning this language?"
    ]
    
    # Translate each question to the target language
    for i, question in enumerate(basic_questions):
        if i < ASSESSMENT_QUESTIONS_COUNT:
            try:
                # Translate to target language
                target_question = await translate_text(question, "en", LANGUAGES.get(target_lang, "en"))
                # Translate to native language
                native_question = await translate_text(question, "en", native_lang_code)
                
                questions.append({
                    "question": target_question,
                    "translation": native_question,
                    "type": "open_ended",
                    "difficulty": min(i+1, 10)
                })
            except Exception as e:
                logger.error(f"Error translating simple assessment question: {e}")
                # Fallback to English if translation fails
                questions.append({
                    "question": question,
                    "translation": question,
                    "type": "open_ended",
                    "difficulty": min(i+1, 10)
                })
    
    return questions

async def ask_next_assessment_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """Ask the next assessment question to the user."""
    assessment_data = user_data[user_id]["assessment"]
    current_question_idx = assessment_data["current_question"]
    current_question = assessment_data["questions"][current_question_idx]
    
    native_lang_code = user_data[user_id]["native_language"]["code"]
    
    # Create the question message with both languages
    question_number = current_question_idx + 1
    total_questions = len(assessment_data["questions"])
    
    # ترجمه عنوان سوال
    question_header = f"Question {question_number}/{total_questions}:"
    translated_header = await translate_text(question_header, "en", native_lang_code)
    
    # متن سوال به زبان هدف و ترجمه آن
    target_question = current_question["question"]
    native_question = current_question["translation"]
    
    # دستورالعمل پاسخ
    instruction = "Please answer in the language you are learning, or send a voice message to practice speaking."
    translated_instruction = await translate_text(instruction, "en", native_lang_code)
    
    # ترکیب همه بخش‌ها
    message = f"{translated_header}\n\n{target_question}\n\n{native_question}\n\n{translated_instruction}"
    
    # اگر سوال چندگزینه‌ای است، گزینه‌ها را نمایش بده
    if current_question.get("type") == "multiple_choice" and "options" in current_question:
        message += "\n\n" + "\n".join([f"{i+1}. {option}" for i, option in enumerate(current_question["options"])])
        message += "\n\n" + await translate_text("Enter the number of your choice.", "en", native_lang_code)
    
    # Trigger a reply handler for the user's answer
    if update.callback_query:
        # If coming from a callback (button press)
        await update.callback_query.message.reply_text(message)
    else:
        # If coming from a message handler
        await update.message.reply_text(message)

async def complete_assessment(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """Complete the assessment and determine proficiency level."""
    assessment_data = user_data[user_id]["assessment"]
    questions = assessment_data["questions"]
    answers = assessment_data["answers"]
    target_lang = user_data[user_id]["target_language"]["name"]
    native_lang_code = user_data[user_id]["native_language"]["code"]
    
    # Combine questions and answers for analysis
    qa_pairs = []
    for i, (question, answer) in enumerate(zip(questions, answers)):
        qa_pairs.append({
            "question": question["question"],
            "answer": answer,
            "difficulty": question.get("difficulty", i+1)
        })
    
    # Analyze proficiency with OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": f"""
                    You are a language proficiency assessor for {target_lang}. 
                    Analyze the following question-answer pairs to determine the learner's proficiency level.
                    Provide a detailed assessment and classify the learner into one of these levels:
                    - Beginner: Basic vocabulary, simple sentences, frequent errors
                    - Intermediate: Good vocabulary, can form complex sentences, some errors
                    - Advanced: Rich vocabulary, complex sentence structures, few errors
                    
                    For your response, include:
                    1. A brief analysis of their strengths and weaknesses
                    2. Their FINAL proficiency level (Beginner, Intermediate, or Advanced only)
                    3. What they should focus on improving
                    
                    Format: Use JSON with the following structure:
                    {{"analysis": "your analysis", "level": "their proficiency level", "focus_areas": ["area1", "area2", ...]}}
                    """
                },
                {
                    "role": "user", 
                    "content": f"Assessment for {target_lang} learner:\n\n{json.dumps(qa_pairs, ensure_ascii=False)}"
                }
            ]
        )
        
        # Extract the assessment result
        result_text = response.choices[0].message['content']
        
        try:
            # Try to parse as JSON
            result = json.loads(result_text)
            proficiency_level = result.get("level", "Beginner")
            analysis = result.get("analysis", "")
            focus_areas = result.get("focus_areas", [])
            
            # Normalize the level
            if "beginner" in proficiency_level.lower():
                proficiency_level = "Beginner"
            elif "intermediate" in proficiency_level.lower():
                proficiency_level = "Intermediate"
            elif "advanced" in proficiency_level.lower():
                proficiency_level = "Advanced"
            else:
                proficiency_level = "Beginner"
            
        except json.JSONDecodeError:
            # If not valid JSON, extract the level with simple logic
            logger.error("Failed to parse JSON response for assessment result")
            if "advanced" in result_text.lower():
                proficiency_level = "Advanced"
            elif "intermediate" in result_text.lower():
                proficiency_level = "Intermediate"
            else:
                proficiency_level = "Beginner"
            
            # Extract analysis with a simplified approach
            analysis = result_text
            focus_areas = []
        
        # Store the proficiency level
        user_data[user_id]["proficiency_level"] = proficiency_level
        user_data[user_id]["assessment"]["completed"] = True
        user_data[user_id]["current_state"] = "assessment_complete"
        
        # Save user data
        await save_user_data(user_id)
        
        # Prepare the result message
        original_message = f"""
Assessment complete! Based on your answers, your proficiency level in {target_lang} is: {proficiency_level}.

Analysis: {analysis}

Focus areas: {', '.join(focus_areas) if focus_areas else 'General language skills'}

Now, please select what you'd like to do next:
"""
        
        # ترجمه پیام به زبان کاربر
        translated_message = await translate_text(original_message, "en", native_lang_code)
        
        # Create learning mode selection keyboard with translated labels
        mode_options = [
            ("📚 Curriculum", "mode_curriculum"),
            ("📝 Vocabulary Practice", "mode_vocabulary"),
            ("💬 Useful Phrases", "mode_phrases"),
            ("🗣️ Conversation Practice", "mode_conversation"),
            ("🎤 Pronunciation Practice", "mode_pronunciation")
        ]
        
        # Translate options
        translated_options = []
        for text, callback in mode_options:
            # Extract emoji and text
            emoji = text.split()[0] if text.split() else ""
            text_part = " ".join(text.split()[1:]) if len(text.split()) > 1 else text
            
            translated_text = await translate_text(text_part, "en", native_lang_code)
            translated_options.append((f"{emoji} {translated_text}", callback))
        
        keyboard = []
        for text, callback in translated_options:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
        
        # Add main menu button
        main_menu_text = await translate_text("🏠 Main Menu", "en", native_lang_code)
        keyboard.append([InlineKeyboardButton(main_menu_text, callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=translated_message,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error analyzing assessment: {e}")
        
        # Fallback to a simpler assessment
        proficiency_level = await simple_assess_proficiency(answers, target_lang)
        user_data[user_id]["proficiency_level"] = proficiency_level
        user_data[user_id]["assessment"]["completed"] = True
        user_data[user_id]["current_state"] = "assessment_complete"
        
        # Save user data
        await save_user_data(user_id)
        
        # Create simplified result message
        original_message = f"""
Assessment complete! Based on your answers, your proficiency level in {target_lang} is: {proficiency_level}.

Now, please select what you'd like to do next:
"""
        
        # ترجمه پیام به زبان کاربر
        translated_message = await translate_text(original_message, "en", native_lang_code)
        
        # Create learning mode selection keyboard with translated labels
        mode_options = [
            ("📚 Curriculum", "mode_curriculum"),
            ("📝 Vocabulary Practice", "mode_vocabulary"),
            ("💬 Useful Phrases", "mode_phrases"),
            ("🗣️ Conversation Practice", "mode_conversation"),
            ("🎤 Pronunciation Practice", "mode_pronunciation")
        ]
        
        # Translate options
        translated_options = []
        for text, callback in mode_options:
            # Extract emoji and text
            emoji = text.split()[0] if text.split() else ""
            text_part = " ".join(text.split()[1:]) if len(text.split()) > 1 else text
            
            translated_text = await translate_text(text_part, "en", native_lang_code)
            translated_options.append((f"{emoji} {translated_text}", callback))
        
        keyboard = []
        for text, callback in translated_options:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
        
        # Add main menu button
        main_menu_text = await translate_text("🏠 Main Menu", "en", native_lang_code)
        keyboard.append([InlineKeyboardButton(main_menu_text, callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=translated_message,
            reply_markup=reply_markup
        )

async def simple_assess_proficiency(answers, language):
    """Simple assessment based on answer length and complexity."""
    try:
        # For simplicity, we'll use the average answer length as a basic heuristic
        # This is a fallback and not a proper assessment
        total_length = sum(len(answer) for answer in answers)
        avg_length = total_length / len(answers) if answers else 0
        
        # Very simple heuristic based on average answer length
        if avg_length < 10:
            return "Beginner"
        elif avg_length < 30:
            return "Intermediate"
        else:
            return "Advanced"
    except Exception as e:
        logger.error(f"Error in simple assessment: {e}")
        return "Beginner"  # Default to beginner on error

async def generate_curriculum_overview(target_lang, native_lang, proficiency, native_lang_code):
    """Generate a 5-day curriculum overview."""
    try:
        # استفاده از API قدیمی OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": f"""
                    You are a language curriculum designer. Create a 5-day curriculum for {proficiency} level students learning {target_lang} from {native_lang}.
                    
                    For each day, provide:
                    1. A brief title/theme for the day
                    2. A short description of what will be covered (1-2 sentences)
                    
                    Format your response as a clear, organized curriculum overview. Write in {native_lang}.
                    Keep it concise but informative. Do not include detailed lessons yet.
                    """
                },
                {
                    "role": "user", 
                    "content": f"Create a 5-day curriculum for {proficiency} level {target_lang} learners who speak {native_lang}."
                }
            ]
        )
        
        curriculum_overview = response.choices[0].message['content']
        return curriculum_overview
        
    except Exception as e:
        logger.error(f"Error generating curriculum overview: {e}")
        
        # ترجمه پیام خطا به زبان کاربر
        error_message = "Sorry, I couldn't generate a curriculum at this time. Please try again later."
        translated_error = await translate_text(error_message, "en", native_lang_code)
        
        return translated_error

async def generate_curriculum_day(day_number, target_lang, native_lang, proficiency, native_lang_code):
    """Generate detailed content for a specific day in the curriculum."""
    try:
        # استفاده از API قدیمی OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": f"""
                    You are a language teacher creating detailed lesson content for Day {day_number} of a 5-day curriculum for {proficiency} level students learning {target_lang} from {native_lang}.
                    
                    Create a comprehensive lesson that includes:
                    1. Vocabulary (5-10 words/phrases with translations and examples)
                    2. Grammar point(s) appropriate for {proficiency} level
                    3. Practice exercises or activities
                    4. Cultural notes or interesting facts
                    5. Homework or self-study suggestions
                    
                    Format your response in a clear, organized way with sections and examples.
                    Write in {native_lang}, with {target_lang} examples where appropriate.
                    Make it engaging and educational.
                    """
                },
                {
                    "role": "user", 
                    "content": f"Create detailed lesson content for Day {day_number} of a 5-day curriculum for {proficiency} level {target_lang} learners who speak {native_lang}."
                }
            ]
        )
        
        day_content = response.choices[0].message['content']
        return day_content
        
    except Exception as e:
        logger.error(f"Error generating curriculum day content: {e}")
        
        # ترجمه پیام خطا به زبان کاربر
        error_message = f"Sorry, I couldn't generate content for Day {day_number} at this time. Please try again later."
        translated_error = await translate_text(error_message, "en", native_lang_code)
        
        return translated_error

async def generate_curriculum_response(user_message, day_number, target_lang, native_lang, native_lang_code, proficiency):
    """Generate a response to the user's message in the context of the current curriculum day."""
    try:
        # استفاده از API قدیمی OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": f"""
                    You are a language teacher helping a {proficiency} level student with Day {day_number} of their {target_lang} curriculum.
                    
                    Respond to their question or comment in a helpful, educational way.
                    If they ask about vocabulary, grammar, or exercises from Day {day_number}, provide detailed explanations.
                    If they share their work or practice, provide constructive feedback and corrections.
                    If they ask about something unrelated to the current day's lesson, gently guide them back to the topic.
                    
                    Write your response in {native_lang}, with {target_lang} examples where appropriate.
                    Be encouraging and supportive.
                    """
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ]
        )
        
        return response.choices[0].message['content']
        
    except Exception as e:
        logger.error(f"Error generating curriculum response: {e}")
        
        # ترجمه پیام خطا به زبان کاربر
        error_message = "Sorry, I couldn't generate a response at this time. Please try again later."
        translated_error = await translate_text(error_message, "en", native_lang_code)
        
        return translated_error

async def generate_learning_content(mode, target_lang, native_lang, proficiency, native_lang_code):
    """Generate learning content based on mode and proficiency."""
    prompts = {
        "curriculum": f"Create a weekly curriculum for {proficiency} level students learning {target_lang} from {native_lang}. Include daily activities, grammar points, and vocabulary themes.",
        "vocabulary": f"Provide a list of 10 important {proficiency} level vocabulary words in {target_lang} with translations to {native_lang} and example sentences.",
        "phrases": f"List 5 useful everyday phrases in {target_lang} for {proficiency} level learners, with translations to {native_lang} and pronunciation guides.",
        "conversation": f"Start a simple conversation in {target_lang} appropriate for {proficiency} level learners. Provide translations to {native_lang}.",
        "pronunciation": f"Create pronunciation exercises for {proficiency} level {target_lang} learners who speak {native_lang}. Include common pronunciation challenges and practice words."
    }
    
    try:
        # استفاده از API قدیمی OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a language learning assistant. Provide helpful, structured content for language learners. Write your response in {native_lang}, with examples in {target_lang} when appropriate."},
                {"role": "user", "content": prompts[mode]}
            ]
        )
        content = response.choices[0].message['content']
        
        # No need to translate as the content already includes translations to native language
        return content
    except Exception as e:
        logger.error(f"Content generation error: {e}")
        
        # ترجمه پیام خطا به زبان کاربر
        error_message = "Sorry, I couldn't generate learning content at this time. Please try again later."
        translated_error = await translate_text(error_message, "en", native_lang_code)
        
        return translated_error

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id
    
    # Load user data if not in memory
    if user_id not in user_data:
        await load_user_data(user_id)
    
    help_text = """
Help & Instructions 📖

🤖 You can ask me any question about:
• Grammar explanations
• Vocabulary meanings
• Language learning tips
• Cultural information
• Practice exercises

🎤 Voice Messages:
• Send voice messages to practice pronunciation
• Get feedback on your speaking
• Practice conversations

📱 Commands:
/start - Show main menu
/help - Show this help message
/reset - Reset your learning progress

🎯 Use the menu buttons to navigate between different learning modes and features.

💡 Tip: The more you practice, the better you'll become!
"""
    
    if user_id in user_data and user_data[user_id].get("native_language"):
        native_lang = user_data[user_id]["native_language"]["code"]
        
        # ترجمه پیام راهنما به زبان کاربر
        translated_help = await translate_text(help_text, "en", native_lang)
        
        # Add main menu button
        main_menu_text = await translate_text("🏠 Main Menu", "en", native_lang)
        keyboard = [[InlineKeyboardButton(main_menu_text, callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(translated_help, reply_markup=reply_markup)
    else:
        await update.message.reply_text(help_text)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset user data when the command /reset is issued."""
    user_id = update.effective_user.id
    
    # Load user data if not in memory
    if user_id not in user_data:
        await load_user_data(user_id)
    
    if user_id in user_data:
        native_lang_code = None
        if user_data[user_id].get("native_language"):
            native_lang_code = user_data[user_id]["native_language"]["code"]
        
        # Clear user data completely
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
        
        # Save user data
        await save_user_data(user_id)
        
        if native_lang_code:
            # ترجمه پیام به زبان کاربر
            original_reset_text = "Your learning progress has been completely reset. Let's start fresh!"
            translated_reset = await translate_text(original_reset_text, "en", native_lang_code)
            
            await update.message.reply_text(translated_reset)
        else:
            await update.message.reply_text("Your learning progress has been completely reset. Let's start fresh!")
        
        # Restart the bot
        await start(update, context)
    else:
        await start(update, context)

def test_translation():
    """Test the translation functionality."""
    test_text = "Hello, welcome to the language learning bot!"
    try:
        # استفاده از API قدیمی OpenAI
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
        
        # Add to cache
        translation_cache.add_translation(test_text, translated, "en", "fa")
        translation_cache.save_cache()
    except Exception as e:
        logger.error(f"Translation test error: {e}")

def preload_common_translations():
    """Preload translations for common phrases to the cache."""
    # این تابع را به صورت غیر async بازنویسی کردیم
    common_phrases = {
        "en": [
            "Welcome to the Language Learning Bot! 🌍\n\nPlease select your native language:",
            "Please select your native language:",
            "Great! You've selected English as your native language. Now, please select the language you want to learn:",
            "Please select the language you want to learn:",
            "Excellent! You've chosen to learn English. Now, I'm going to ask you 10 questions to assess your current proficiency level.",
            "Based on your sample, your proficiency level in English is: Beginner.\n\nPlease select a learning mode:",
            "Curriculum",
            "Vocabulary Practice",
            "Useful Phrases",
            "Conversation Practice",
            "Pronunciation Practice",
            "Previous",
            "Next",
            "Your learning progress has been reset. Please select the language you want to learn:",
            "This bot helps you learn a new language. Commands:\n/start - Restart the language selection process\n/help - Show this help message\n/reset - Reset your learning progress",
            "Sorry, I couldn't generate learning content at this time. Please try again later.",
            "Sorry, I couldn't generate a response at this time. Please try again later.",
            "Main Menu",
            "Learning Modes",
            "Back to Menu",
            "Feel free to ask me any question!",
            "You can also send voice messages to practice your pronunciation and speaking skills!"
        ]
    }
    
    logger.info("Preloading common translations...")
    translation_cache.save_cache()
    logger.info("Preloading completed.")

def main() -> None:
    """Start the bot."""
    # تست ترجمه
    test_translation()
    
    # پیش‌بارگذاری ترجمه‌های پرکاربرد
    preload_common_translations()
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))  # اضافه کردن handler برای پیام‌های صوتی

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    # بدون استفاده از asyncio.run
    main()
