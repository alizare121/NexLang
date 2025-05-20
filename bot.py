import os
import logging
import json
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

# User data storage (in a real application, use a database)
user_data = {}

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
                {"role": "system", "content": "You are a professional translator. Provide only the translation, no explanations or additional text."},
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user_id = update.effective_user.id
    
    # Initialize user data
    user_data[user_id] = {
        "native_language": None,
        "target_language": None,
        "proficiency_level": None,
        "current_state": "selecting_native_language",
        "assessment": {
            "questions": [],
            "answers": [],
            "current_question": 0
        }
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
        
        # تغییر حالت به مرحله اول ارزیابی
        user_data[user_id]["current_state"] = "assessment_intro"
        
        native_lang = user_data[user_id]["native_language"]["code"]
        
        # پیام اصلی به انگلیسی
        original_message = f"""
Excellent! You've chosen to learn {lang_name}.

Now I'm going to ask you {ASSESSMENT_QUESTIONS_COUNT} questions to assess your current proficiency level in {lang_name}. 
Try to answer in {lang_name} as best as you can. If you don't know the answer, you can say "I don't know" in {lang_name}.

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
        
        # Ask the first question
        await ask_next_assessment_question(update, context, user_id)
    
    elif callback_data == "assessment_cancel":
        # Cancel the assessment and go back to target language selection
        native_lang = user_data[user_id]["native_language"]["code"]
        target_lang = user_data[user_id]["target_language"]["name"]
        
        original_message = f"No problem. You can start the assessment when you're ready. In the meantime, I'll assume you're a beginner in {target_lang}."
        translated_message = await translate_text(original_message, "en", native_lang)
        
        # Set the proficiency level to beginner by default
        user_data[user_id]["proficiency_level"] = "Beginner"
        user_data[user_id]["current_state"] = "selecting_learning_mode"
        
        # Create learning mode selection keyboard with translated labels
        mode_buttons = [
            "Curriculum", "Vocabulary Practice", "Useful Phrases", "Conversation Practice"
        ]
        
        # ترجمه دکمه‌ها
        translated_buttons = await translate_buttons(mode_buttons, "en", native_lang)
        
        # Show learning mode options
        original_learning_prompt = f"Please select a learning mode:"
        translated_learning_prompt = await translate_text(original_learning_prompt, "en", native_lang)
        
        keyboard = [
            [InlineKeyboardButton(translated_buttons[0], callback_data="mode_curriculum")],
            [InlineKeyboardButton(translated_buttons[1], callback_data="mode_vocabulary")],
            [InlineKeyboardButton(translated_buttons[2], callback_data="mode_phrases")],
            [InlineKeyboardButton(translated_buttons[3], callback_data="mode_conversation")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"{translated_message}\n\n{translated_learning_prompt}",
            reply_markup=reply_markup
        )
        
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
        
        # ترجمه پاسخ به زبان کاربر
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
    
    if current_state == "assessment_in_progress":
        # Handle assessment question response
        current_question = user_data[user_id]["assessment"]["current_question"]
        
        # Store the answer
        user_data[user_id]["assessment"]["answers"].append(message_text)
        
        # Move to the next question or finish assessment
        if current_question + 1 < len(user_data[user_id]["assessment"]["questions"]):
            user_data[user_id]["assessment"]["current_question"] += 1
            await ask_next_assessment_question(update, context, user_id)
        else:
            # Assessment complete, evaluate proficiency
            await complete_assessment(update, context, user_id)
    
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
                target_question = await translate_text(question, "en", LANGUAGES[target_lang])
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
    instruction = "Please answer in the language you are learning."
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
        user_data[user_id]["current_state"] = "selecting_learning_mode"
        
        # Prepare the result message
        original_message = f"""
Assessment complete! Based on your answers, your proficiency level in {target_lang} is: {proficiency_level}.

Analysis: {analysis}

Focus areas: {', '.join(focus_areas) if focus_areas else 'General language skills'}

Now, please select a learning mode:
"""
        
        # ترجمه پیام به زبان کاربر
        translated_message = await translate_text(original_message, "en", native_lang_code)
        
        # Create learning mode selection keyboard with translated labels
        mode_buttons = [
            "Curriculum", "Vocabulary Practice", "Useful Phrases", "Conversation Practice"
        ]
        
        # ترجمه دکمه‌ها
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
        
    except Exception as e:
        logger.error(f"Error analyzing assessment: {e}")
        
        # Fallback to a simpler assessment
        proficiency_level = await simple_assess_proficiency(answers, target_lang)
        user_data[user_id]["proficiency_level"] = proficiency_level
        user_data[user_id]["current_state"] = "selecting_learning_mode"
        
        # Create simplified result message
        original_message = f"""
Assessment complete! Based on your answers, your proficiency level in {target_lang} is: {proficiency_level}.

Now, please select a learning mode:
"""
        
        # ترجمه پیام به زبان کاربر
        translated_message = await translate_text(original_message, "en", native_lang_code)
        
        # Create learning mode selection keyboard with translated labels
        mode_buttons = [
            "Curriculum", "Vocabulary Practice", "Useful Phrases", "Conversation Practice"
        ]
        
        # ترجمه دکمه‌ها
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

async def generate_learning_content(mode, target_lang, native_lang, proficiency, native_lang_code):
    """Generate learning content based on mode and proficiency."""
    prompts = {
        "curriculum": f"Create a weekly curriculum for {proficiency} level students learning {target_lang} from {native_lang}. Include daily activities, grammar points, and vocabulary themes.",
        "vocabulary": f"Provide a list of 10 important {proficiency} level vocabulary words in {target_lang} with translations to {native_lang} and example sentences.",
        "phrases": f"List 5 useful everyday phrases in {target_lang} for {proficiency} level learners, with translations to {native_lang} and pronunciation guides.",
        "conversation": f"Start a simple conversation in {target_lang} appropriate for {proficiency} level learners. Provide translations to {native_lang}."
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

async def generate_response(user_message, mode, target_lang, native_lang, native_lang_code, proficiency):
    """Generate a response to the user's message based on learning mode."""
    system_prompts = {
        "curriculum": f"You are a language teacher creating a curriculum for {proficiency} level students learning {target_lang} from {native_lang}. Respond to their questions about the curriculum. Write your response in {native_lang}, with examples in {target_lang} when appropriate.",
        "vocabulary": f"You are a language teacher helping {proficiency} level students learn {target_lang} vocabulary from {native_lang}. Provide vocabulary explanations, examples, and practice. Write your response in {native_lang}, with examples in {target_lang}.",
        "phrases": f"You are a language teacher helping {proficiency} level students learn useful phrases in {target_lang} from {native_lang}. Provide phrase explanations, cultural context, and practice. Write your response in {native_lang}, with examples in {target_lang}.",
        "conversation": f"You are a conversation partner for {proficiency} level students learning {target_lang} from {native_lang}. Maintain a natural conversation, correct major errors gently, and provide translations when helpful. Write your response in {native_lang} and {target_lang}."
    }
    
    try:
        # استفاده از API قدیمی OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompts[mode]},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message['content']
    except Exception as e:
        logger.error(f"Response generation error: {e}")
        
        # ترجمه پیام خطا به زبان کاربر
        error_message = "Sorry, I couldn't generate a response at this time. Please try again later."
        translated_error = await translate_text(error_message, "en", native_lang_code)
        
        return translated_error

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
        
        # ترجمه پیام راهنما به زبان کاربر
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
            "current_state": "selecting_target_language" if native_lang_code else "selecting_native_language",
            "assessment": {
                "questions": [],
                "answers": [],
                "current_question": 0
            }
        }
        
        if native_lang_code:
            # Create target language selection keyboard with pagination (same as in button_callback)
            original_reset_text = "Your learning progress has been reset. Please select the language you want to learn:"
            
            # ترجمه پیام به زبان کاربر
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
                    
                    # ترجمه دکمه‌های ناوبری
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
            "Previous",
            "Next",
            "Your learning progress has been reset. Please select the language you want to learn:",
            "This bot helps you learn a new language. Commands:\n/start - Restart the language selection process\n/help - Show this help message\n/reset - Reset your learning progress",
            "Sorry, I couldn't generate learning content at this time. Please try again later.",
            "Sorry, I couldn't generate a response at this time. Please try again later."
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

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    # بدون استفاده از asyncio.run
    main()