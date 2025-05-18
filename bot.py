import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import openai

# تلاش برای import کردن dotenv، اگر نصب نبود از آن صرف نظر کن
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # اگر dotenv نصب نبود، از آن صرف نظر کن

# تنظیم کلیدهای API
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7731221586:AAF0uDfEW-CkQ8C_zs5Wfmrf4oGPo_ZffKc')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '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')

# تنظیم کلید OpenAI
openai.api_key = OPENAI_API_KEY

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ترجمه‌های پیش‌فرض برای پیام‌های پرکاربرد
TRANSLATIONS = {
    "fa": {  # Persian translations
        "Welcome to the Language Learning Bot! 🌍\n\nPlease select your native language:": 
            "به ربات آموزش زبان خوش آمدید! 🌍\n\nلطفاً زبان مادری خود را انتخاب کنید:",
        
        "Great! You've selected {language} as your native language. Now, please select the language you want to learn:": 
            "عالی! شما {language} را به عنوان زبان مادری خود انتخاب کرده‌اید. حالا لطفاً زبانی را که می‌خواهید یاد بگیرید انتخاب کنید:",
        
        "Excellent! You've chosen to learn {language}. Now, let's assess your current proficiency level. Please write a few sentences in {language} so I can evaluate your level.": 
            "عالی! شما انتخاب کرده‌اید که {language} را یاد بگیرید. حالا بیایید سطح مهارت فعلی شما را ارزیابی کنیم. لطفاً چند جمله به {language} بنویسید تا بتوانم سطح شما را ارزیابی کنم.",
        
        "Based on your sample, your proficiency level in {language} is: {level}.\n\nPlease select a learning mode:": 
            "بر اساس نمونه شما، سطح مهارت شما در {language} برابر است با: {level}.\n\nلطفاً یک حالت یادگیری را انتخاب کنید:",
        
        "Curriculum": "برنامه درسی",
        "Vocabulary Practice": "تمرین لغات",
        "Useful Phrases": "عبارات کاربردی",
        "Conversation Practice": "تمرین مکالمه",
        
        "Previous": "قبلی",
        "Next": "بعدی",
        
        "Here's a personalized curriculum for your {level} level in {language}.": 
            "در اینجا یک برنامه درسی شخصی‌سازی شده برای سطح {level} شما در {language} آمده است.",
        
        "Let's practice some vocabulary appropriate for your {level} level in {language}.": 
            "بیایید برخی از لغات مناسب برای سطح {level} شما در {language} را تمرین کنیم.",
        
        "Let's learn some useful phrases in {language} for your {level} level.": 
            "بیایید برخی از عبارات مفید در {language} را برای سطح {level} شما یاد بگیریم.",
        
        "Let's practice conversation in {language}. I'll help you with dialogue practice.": 
            "بیایید مکالمه در {language} را تمرین کنیم. من به شما در تمرین گفتگو کمک خواهم کرد.",
            
        "Please select your native language:":
            "لطفاً زبان مادری خود را انتخاب کنید:",
            
        "Please select the language you want to learn:":
            "لطفاً زبانی را که می‌خواهید یاد بگیرید انتخاب کنید:",
            
        "Your learning progress has been reset. Please select the language you want to learn:":
            "پیشرفت یادگیری شما بازنشانی شد. لطفاً زبانی را که می‌خواهید یاد بگیرید انتخاب کنید:",
            
        "This bot helps you learn a new language. Commands:\n/start - Restart the language selection process\n/help - Show this help message\n/reset - Reset your learning progress":
            "این ربات به شما کمک می‌کند زبان جدیدی یاد بگیرید. دستورات:\n/start - شروع مجدد فرآیند انتخاب زبان\n/help - نمایش این پیام راهنما\n/reset - بازنشانی پیشرفت یادگیری شما",
            
        "Sorry, I couldn't generate learning content at this time. Please try again later.":
            "متأسفم، در حال حاضر نمی‌توانم محتوای آموزشی تولید کنم. لطفاً بعداً دوباره امتحان کنید.",
            
        "Sorry, I couldn't generate a response at this time. Please try again later.":
            "متأسفم، در حال حاضر نمی‌توانم پاسخی تولید کنم. لطفاً بعداً دوباره امتحان کنید."
    },
    # می‌توانید ترجمه‌های سایر زبان‌ها را نیز اضافه کنید
}

def get_translation(text, lang_code, **kwargs):
    """Get translation for a text in the specified language."""
    if lang_code not in TRANSLATIONS:
        return text
    
    # جستجو در ترجمه‌های موجود
    if text in TRANSLATIONS[lang_code]:
        translated = TRANSLATIONS[lang_code][text]
    else:
        # جستجو با الگوی متن
        for template, translation in TRANSLATIONS[lang_code].items():
            if "{" in template and "}" in template:
                # تبدیل الگو به regex برای تطبیق
                import re
                pattern = re.escape(template).replace("\\{", "{").replace("\\}", "}")
                for key, value in kwargs.items():
                    pattern = pattern.replace("{" + key + "}", re.escape(str(value)))
                
                if re.match(pattern, text):
                    translated = translation
                    for key, value in kwargs.items():
                        translated = translated.replace("{" + key + "}", str(value))
                    return translated
        
        # اگر ترجمه پیدا نشد
        return text
    
    # جایگزینی پارامترها
    for key, value in kwargs.items():
        translated = translated.replace("{" + key + "}", str(value))
    
    return translated

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

# User data storage (in a real application, use a database)
user_data = {}

async def translate_text(text, source_lang, target_lang):
    """Translate text using OpenAI."""
    if source_lang == target_lang:
        return text
    
    # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
    if target_lang == "fa":
        # بررسی کنید آیا ترجمه پیش‌فرض وجود دارد
        for template in TRANSLATIONS["fa"]:
            if text == template or text.startswith(template.split("{")[0]):
                # استخراج پارامترها
                params = {}
                if "{language}" in template and "{" in text:
                    try:
                        language = text.split("You've selected ")[1].split(" as")[0]
                        params["language"] = language
                    except:
                        pass
                
                if "{level}" in template and "level in" in text:
                    try:
                        level = text.split("level is: ")[1].split(".")[0]
                        params["level"] = level
                    except:
                        pass
                
                return get_translation(template, "fa", **params)
    
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
            "tr": "Turkish"
        }
        
        source_lang_name = language_names.get(source_lang, source_lang)
        target_lang_name = language_names.get(target_lang, target_lang)
        
        # استفاده از پرامپت واضح‌تر برای ترجمه
        prompt = f"""
        Translate the following text from {source_lang_name} to {target_lang_name}.
        Return ONLY the translated text, nothing else.
        
        Text to translate: {text}
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",  # استفاده از مدل سریع‌تر
            messages=[
                {"role": "system", "content": "You are a professional translator. Provide only the translation, no explanations or additional text."},
                {"role": "user", "content": prompt}
            ]
        )
        
        translated_text = response.choices[0].message.content.strip()
        logger.info(f"Translated from {source_lang} to {target_lang}: {text} -> {translated_text}")
        return translated_text
    except Exception as e:
        logger.error(f"Translation error: {e}")
        
        # برای زبان فارسی، اگر ترجمه با OpenAI شکست خورد، از ترجمه‌های پیش‌فرض استفاده کنید
        if target_lang == "fa":
            for key, value in TRANSLATIONS["fa"].items():
                if text.startswith(key.split("{")[0]):
                    return value
        
        return text  # Fallback to original text

async def translate_buttons(buttons, source_lang, target_lang):
    """Translate a list of button labels."""
    translated_buttons = []
    
    # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
    if target_lang == "fa":
        for button in buttons:
            if button in TRANSLATIONS["fa"]:
                translated_buttons.append(TRANSLATIONS["fa"][button])
            else:
                try:
                    translated = await translate_text(button, source_lang, target_lang)
                    translated_buttons.append(translated)
                except:
                    translated_buttons.append(button)
        return translated_buttons
    
    # برای سایر زبان‌ها، از OpenAI استفاده کنید
    for button in buttons:
        try:
            translated_button = await translate_text(button, source_lang, target_lang)
            translated_buttons.append(translated_button)
        except:
            translated_buttons.append(button)
    
    return translated_buttons

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user_id = update.effective_user.id
    
    # Initialize user data
    user_data[user_id] = {
        "native_language": None,
        "target_language": None,
        "proficiency_level": None,
        "current_state": "selecting_native_language"
    }
    
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
        
        logger.info(f"User {user_id} selected native language: {lang_name} ({lang_code})")
        
        # پیام اصلی به انگلیسی
        original_message = f"Great! You've selected {lang_name} as your native language. Now, please select the language you want to learn:"
        
        # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
        if lang_code == "fa":
            translated_message = get_translation(
                "Great! You've selected {language} as your native language. Now, please select the language you want to learn:",
                "fa",
                language=lang_name
            )
        else:
            # برای سایر زبان‌ها، از OpenAI استفاده کنید
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
                
                # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
                if lang_code == "fa":
                    prev_text = "قبلی"
                    next_text = "بعدی"
                else:
                    # برای سایر زبان‌ها، از OpenAI استفاده کنید
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
        
        # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
        if native_lang == "fa":
            translated_message = get_translation(original_message, "fa")
        else:
            # برای سایر زبان‌ها، از OpenAI استفاده کنید
            translated_message = await translate_text(original_message, "en", native_lang)
        
        await query.edit_message_text(
            text=translated_message,
            reply_markup=InlineKeyboardMarkup(keyboards[page])
        )
        
    elif callback_data.startswith("target_"):
        # Handle target language selection
        _, lang_code, lang_name = callback_data.split("_", 2)
        user_data[user_id]["target_language"] = {"code": lang_code, "name": lang_name}
        user_data[user_id]["current_state"] = "proficiency_assessment"
        
        native_lang = user_data[user_id]["native_language"]["code"]
        
        # پیام اصلی به انگلیسی
        original_message = f"Excellent! You've chosen to learn {lang_name}. Now, let's assess your current proficiency level. Please write a few sentences in {lang_name} so I can evaluate your level."
        
        # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
        if native_lang == "fa":
            translated_message = get_translation(
                "Excellent! You've chosen to learn {language}. Now, let's assess your current proficiency level. Please write a few sentences in {language} so I can evaluate your level.",
                "fa",
                language=lang_name
            )
        else:
            # برای سایر زبان‌ها، از OpenAI استفاده کنید
            translated_message = await translate_text(original_message, "en", native_lang)
        
        await query.edit_message_text(text=translated_message)
        
    elif callback_data.startswith("mode_"):
        # Handle learning mode selection
        _, mode = callback_data.split("_", 1)
        user_data[user_id]["learning_mode"] = mode
        user_data[user_id]["current_state"] = "learning"
        
        native_lang_code = user_data[user_id]["native_language"]["code"]
        target_lang_name = user_data[user_id]["target_language"]["name"]
        proficiency = user_data[user_id]["proficiency_level"]
        
        # Prepare response based on selected mode
        if mode == "curriculum":
            original_response = f"Here's a personalized curriculum for your {proficiency} level in {target_lang_name}."
        elif mode == "vocabulary":
            original_response = f"Let's practice some vocabulary appropriate for your {proficiency} level in {target_lang_name}."
        elif mode == "phrases":
            original_response = f"Let's learn some useful phrases in {target_lang_name} for your {proficiency} level."
        elif mode == "conversation":
            original_response = f"Let's practice conversation in {target_lang_name}. I'll help you with dialogue practice."
        
        # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
        if native_lang_code == "fa":
            if mode == "curriculum":
                translated_response = get_translation(
                    "Here's a personalized curriculum for your {level} level in {language}.",
                    "fa",
                    level=proficiency,
                    language=target_lang_name
                )
            elif mode == "vocabulary":
                translated_response = get_translation(
                    "Let's practice some vocabulary appropriate for your {level} level in {language}.",
                    "fa",
                    level=proficiency,
                    language=target_lang_name
                )
            elif mode == "phrases":
                translated_response = get_translation(
                    "Let's learn some useful phrases in {language} for your {level} level.",
                    "fa",
                    level=proficiency,
                    language=target_lang_name
                )
            elif mode == "conversation":
                translated_response = get_translation(
                    "Let's practice conversation in {language}. I'll help you with dialogue practice.",
                    "fa",
                    language=target_lang_name
                )
        else:
            # برای سایر زبان‌ها، از OpenAI استفاده کنید
            translated_response = await translate_text(original_response, "en", native_lang_code)
        
        # Generate learning content based on mode
        learning_content = await generate_learning_content(
            mode, 
            target_lang_name,
            user_data[user_id]["native_language"]["name"],
            proficiency,
            native_lang_code  # Pass native language code for translation
        )
        
        await query.edit_message_text(
            text=f"{translated_response}\n\n{learning_content}"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user messages."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # If user is not in our database, start the conversation
    if user_id not in user_data:
        await start(update, context)
        return
    
    current_state = user_data[user_id]["current_state"]
    
    if current_state == "proficiency_assessment":
        # Assess user's proficiency level
        target_lang = user_data[user_id]["target_language"]["name"]
        native_lang_code = user_data[user_id]["native_language"]["code"]
        native_lang_name = user_data[user_id]["native_language"]["name"]
        
        # Use OpenAI to assess proficiency
        proficiency_level = await assess_proficiency(message_text, target_lang)
        user_data[user_id]["proficiency_level"] = proficiency_level
        user_data[user_id]["current_state"] = "selecting_learning_mode"
        
        # Create untranslated message
        original_message = (
            f"Based on your sample, your proficiency level in {target_lang} is: {proficiency_level}.\n\n"
            f"Please select a learning mode:"
        )
        
        # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
        if native_lang_code == "fa":
            translated_message = get_translation(
                "Based on your sample, your proficiency level in {language} is: {level}.\n\nPlease select a learning mode:",
                "fa",
                language=target_lang,
                level=proficiency_level
            )
        else:
            # برای سایر زبان‌ها، از OpenAI استفاده کنید
            translated_message = await translate_text(original_message, "en", native_lang_code)
        
        # Create learning mode selection keyboard with translated labels
        mode_buttons = [
            "Curriculum", "Vocabulary Practice", "Useful Phrases", "Conversation Practice"
        ]
        
        # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
        if native_lang_code == "fa":
            translated_buttons = [
                get_translation("Curriculum", "fa"),
                get_translation("Vocabulary Practice", "fa"),
                get_translation("Useful Phrases", "fa"),
                get_translation("Conversation Practice", "fa")
            ]
        else:
            # برای سایر زبان‌ها، از OpenAI استفاده کنید
            translated_buttons = await translate_buttons(mode_buttons, "en", native_lang_code)
        
        keyboard = [
            [InlineKeyboardButton(translated_buttons[0], callback_data="mode_curriculum")],
            [InlineKeyboardButton(translated_buttons[1], callback_data="mode_vocabulary")],
            [InlineKeyboardButton(translated_buttons[2], callback_data="mode_phrases")],
            [InlineKeyboardButton(translated_buttons[3], callback_data="mode_conversation")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=translated_message,
            reply_markup=reply_markup
        )
    
    elif current_state == "learning":
        # Handle learning interaction
        learning_mode = user_data[user_id]["learning_mode"]
        target_lang_name = user_data[user_id]["target_language"]["name"]
        native_lang_name = user_data[user_id]["native_language"]["name"]
        native_lang_code = user_data[user_id]["native_language"]["code"]
        proficiency = user_data[user_id]["proficiency_level"]
        
        # Generate response based on user's message and learning mode
        response = await generate_response(
            message_text,
            learning_mode,
            target_lang_name,
            native_lang_name,
            native_lang_code,
            proficiency
        )
        
        await update.message.reply_text(response)

async def assess_proficiency(text, language):
    """Assess language proficiency using OpenAI."""
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a language proficiency assessor for {language}. Assess the following text and determine the proficiency level (Beginner, Intermediate, Advanced) based on grammar, vocabulary, and fluency. Only respond with one word: the level."},
                {"role": "user", "content": text}
            ]
        )
        level = response.choices[0].message.content.strip()
        # Normalize the response
        if "beginner" in level.lower():
            return "Beginner"
        elif "intermediate" in level.lower():
            return "Intermediate"
        elif "advanced" in level.lower():
            return "Advanced"
        else:
            return "Beginner"  # Default to beginner if unclear
    except Exception as e:
        logger.error(f"Assessment error: {e}")
        return "Beginner"  # Default to beginner on error

async def generate_learning_content(mode, target_lang, native_lang, proficiency, native_lang_code):
    """Generate learning content based on mode and proficiency."""
    prompts = {
        "curriculum": f"Create a weekly curriculum for {proficiency} level students learning {target_lang} from {native_lang}. Include daily activities, grammar points, and vocabulary themes.",
        "vocabulary": f"Provide a list of 10 important {proficiency} level vocabulary words in {target_lang} with translations to {native_lang} and example sentences.",
        "phrases": f"List 5 useful everyday phrases in {target_lang} for {proficiency} level learners, with translations to {native_lang} and pronunciation guides.",
        "conversation": f"Start a simple conversation in {target_lang} appropriate for {proficiency} level learners. Provide translations to {native_lang}."
    }
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a language learning assistant. Provide helpful, structured content for language learners. Write your response in {native_lang}, with examples in {target_lang} when appropriate."},
                {"role": "user", "content": prompts[mode]}
            ]
        )
        content = response.choices[0].message.content
        
        # No need to translate as the content already includes translations to native language
        return content
    except Exception as e:
        logger.error(f"Content generation error: {e}")
        
        # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
        if native_lang_code == "fa":
            error_message = get_translation(
                "Sorry, I couldn't generate learning content at this time. Please try again later.",
                "fa"
            )
        else:
            # برای سایر زبان‌ها، از OpenAI استفاده کنید
            error_message = await translate_text(
                "Sorry, I couldn't generate learning content at this time. Please try again later.",
                "en",
                native_lang_code
            )
        
        return error_message

async def generate_response(user_message, mode, target_lang, native_lang, native_lang_code, proficiency):
    """Generate a response to the user's message based on learning mode."""
    system_prompts = {
        "curriculum": f"You are a language teacher creating a curriculum for {proficiency} level students learning {target_lang} from {native_lang}. Respond to their questions about the curriculum. Write your response in {native_lang}, with examples in {target_lang} when appropriate.",
        "vocabulary": f"You are a language teacher helping {proficiency} level students learn {target_lang} vocabulary from {native_lang}. Provide vocabulary explanations, examples, and practice. Write your response in {native_lang}, with examples in {target_lang}.",
        "phrases": f"You are a language teacher helping {proficiency} level students learn useful phrases in {target_lang} from {native_lang}. Provide phrase explanations, cultural context, and practice. Write your response in {native_lang}, with examples in {target_lang}.",
        "conversation": f"You are a conversation partner for {proficiency} level students learning {target_lang} from {native_lang}. Maintain a natural conversation, correct major errors gently, and provide translations when helpful. Write your response in {native_lang} and {target_lang}."
    }
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompts[mode]},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Response generation error: {e}")
        
        # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
        if native_lang_code == "fa":
            error_message = get_translation(
                "Sorry, I couldn't generate a response at this time. Please try again later.",
                "fa"
            )
        else:
            # برای سایر زبان‌ها، از OpenAI استفاده کنید
            error_message = await translate_text(
                "Sorry, I couldn't generate a response at this time. Please try again later.",
                "en",
                native_lang_code
            )
        
        return error_message

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id
    
    help_text = (
        "This bot helps you learn a new language. Commands:\n"
        "/start - Restart the language selection process\n"
        "/help - Show this help message\n"
        "/reset - Reset your learning progress"
    )
    
    if user_id in user_data and user_data[user_id]["native_language"]:
        native_lang = user_data[user_id]["native_language"]["code"]
        
        # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
        if native_lang == "fa":
            translated_help = get_translation(help_text, "fa")
        else:
            # برای سایر زبان‌ها، از OpenAI استفاده کنید
            translated_help = await translate_text(help_text, "en", native_lang)
        
        await update.message.reply_text(translated_help)
    else:
        await update.message.reply_text(help_text)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset user data when the command /reset is issued."""
    user_id = update.effective_user.id
    
    if user_id in user_data:
        native_lang_code = None
        native_lang_name = None
        if user_data[user_id]["native_language"]:
            native_lang_code = user_data[user_id]["native_language"]["code"]
            native_lang_name = user_data[user_id]["native_language"]["name"]
        
        # Clear user data but keep native language
        user_data[user_id] = {
            "native_language": {"code": native_lang_code, "name": native_lang_name} if native_lang_code else None,
            "target_language": None,
            "proficiency_level": None,
            "current_state": "selecting_target_language" if native_lang_code else "selecting_native_language"
        }
        
        if native_lang_code:
            # Create target language selection keyboard with pagination (same as in button_callback)
            original_reset_text = "Your learning progress has been reset. Please select the language you want to learn:"
            
            # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
            if native_lang_code == "fa":
                translated_reset = get_translation(original_reset_text, "fa")
            else:
                # برای سایر زبان‌ها، از OpenAI استفاده کنید
                translated_reset = await translate_text(original_reset_text, "en", native_lang_code)
            
            # Create language selection keyboard with pagination
            languages_list = list(LANGUAGES.keys())
            keyboards = []
            current_keyboard = []
            row = []
            
            # Create rows with 3 languages each (excluding native language)
            counter = 0
            for i, lang in enumerate(languages_list):
                # Skip the native language
                if LANGUAGES[lang] == native_lang_code:
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
                    
                    # برای زبان فارسی، از ترجمه‌های پیش‌فرض استفاده کنید
                    if native_lang_code == "fa":
                        prev_text = "قبلی"
                        next_text = "بعدی"
                    else:
                        # برای سایر زبان‌ها، از OpenAI استفاده کنید
                        prev_text = await translate_text("Previous", "en", native_lang_code)
                        next_text = await translate_text("Next", "en", native_lang_code)
                    
                    if i > 0:
                        nav_row.append(InlineKeyboardButton(f"◀️ {prev_text}", callback_data=f"target_page_{i-1}"))
                    if i < len(keyboards) - 1:
                        nav_row.append(InlineKeyboardButton(f"{next_text} ▶️", callback_data=f"target_page_{i+1}"))
                    keyboard.append(nav_row)
            
            # Store keyboards in user data for pagination
            user_data[user_id]["target_keyboards"] = keyboards
            user_data[user_id]["current_target_page"] = 0
            
            reply_markup = InlineKeyboardMarkup(keyboards[0])
            
            await update.message.reply_text(
                text=translated_reset,
                reply_markup=reply_markup
            )
        else:
            await start(update, context)
    else:
        await start(update, context)

async def test_translation():
    """Test the translation functionality."""
    test_text = "Hello, welcome to the language learning bot!"
    translated = await translate_text(test_text, "en", "fa")
    logger.info("Translation test:")
    logger.info(f"English: {test_text}")
    logger.info(f"Persian: {translated}")

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()