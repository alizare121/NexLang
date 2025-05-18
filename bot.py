import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set up OpenAI API
openai.api_key = os.getenv('OPENAI_API_KEY')

# Available languages
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
    "Arabic": "ar",
    "Hindi": "hi",
    "Persian": "fa",
    "Turkish": "tr",
    "Korean": "ko"
}

# User data storage (in a real application, use a database)
user_data = {}

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
    
    # Create language selection keyboard
    keyboard = []
    row = []
    for i, lang in enumerate(LANGUAGES.keys()):
        row.append(InlineKeyboardButton(lang, callback_data=f"native_{LANGUAGES[lang]}_{lang}"))
        if (i + 1) % 3 == 0 or i == len(LANGUAGES) - 1:
            keyboard.append(row)
            row = []
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome to the Language Learning Bot! 🌍\n\n"
        "Please select your native language:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data.startswith("native_"):
        # Handle native language selection
        _, lang_code, lang_name = callback_data.split("_", 2)
        user_data[user_id]["native_language"] = {"code": lang_code, "name": lang_name}
        user_data[user_id]["current_state"] = "selecting_target_language"
        
        # Translate message to user's native language
        translated_message = await translate_text(
            f"Great! You've selected {lang_name} as your native language. Now, please select the language you want to learn:",
            "en",
            lang_code
        )
        
        # Create target language selection keyboard
        keyboard = []
        row = []
        for i, lang in enumerate(LANGUAGES.keys()):
            # Skip the native language
            if LANGUAGES[lang] == lang_code:
                continue
            row.append(InlineKeyboardButton(lang, callback_data=f"target_{LANGUAGES[lang]}_{lang}"))
            if (i + 1) % 3 == 0 or i == len(LANGUAGES) - 1:
                keyboard.append(row)
                row = []
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=translated_message,
            reply_markup=reply_markup
        )
        
    elif callback_data.startswith("target_"):
        # Handle target language selection
        _, lang_code, lang_name = callback_data.split("_", 2)
        user_data[user_id]["target_language"] = {"code": lang_code, "name": lang_name}
        user_data[user_id]["current_state"] = "proficiency_assessment"
        
        native_lang = user_data[user_id]["native_language"]["code"]
        
        # Translate message to user's native language
        translated_message = await translate_text(
            f"Excellent! You've chosen to learn {lang_name}. Now, let's assess your current proficiency level. Please write a few sentences in {lang_name} so I can evaluate your level.",
            "en",
            native_lang
        )
        
        await query.edit_message_text(text=translated_message)
        
    elif callback_data.startswith("mode_"):
        # Handle learning mode selection
        _, mode = callback_data.split("_", 1)
        user_data[user_id]["learning_mode"] = mode
        user_data[user_id]["current_state"] = "learning"
        
        native_lang = user_data[user_id]["native_language"]["code"]
        target_lang = user_data[user_id]["target_language"]["code"]
        proficiency = user_data[user_id]["proficiency_level"]
        
        # Prepare response based on selected mode
        if mode == "curriculum":
            response = f"Here's a personalized curriculum for your {proficiency} level in {user_data[user_id]['target_language']['name']}."
        elif mode == "vocabulary":
            response = f"Let's practice some vocabulary appropriate for your {proficiency} level in {user_data[user_id]['target_language']['name']}."
        elif mode == "phrases":
            response = f"Let's learn some useful phrases in {user_data[user_id]['target_language']['name']} for your {proficiency} level."
        elif mode == "conversation":
            response = f"Let's practice conversation in {user_data[user_id]['target_language']['name']}. I'll send voice messages and you can respond."
        
        # Translate response
        translated_response = await translate_text(response, "en", native_lang)
        
        # Generate learning content based on mode
        learning_content = await generate_learning_content(
            mode, 
            user_data[user_id]["target_language"]["name"],
            user_data[user_id]["native_language"]["name"],
            proficiency
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
        native_lang = user_data[user_id]["native_language"]["code"]
        
        # Use OpenAI to assess proficiency
        proficiency_level = await assess_proficiency(message_text, target_lang)
        user_data[user_id]["proficiency_level"] = proficiency_level
        user_data[user_id]["current_state"] = "selecting_learning_mode"
        
        # Translate message to user's native language
        translated_message = await translate_text(
            f"Based on your sample, your proficiency level in {target_lang} is: {proficiency_level}.\n\n"
            "Please select a learning mode:",
            "en",
            native_lang
        )
        
        # Create learning mode selection keyboard
        keyboard = [
            [InlineKeyboardButton("Curriculum", callback_data="mode_curriculum")],
            [InlineKeyboardButton("Vocabulary Practice", callback_data="mode_vocabulary")],
            [InlineKeyboardButton("Useful Phrases", callback_data="mode_phrases")],
            [InlineKeyboardButton("Conversation Practice", callback_data="mode_conversation")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=translated_message,
            reply_markup=reply_markup
        )
    
    elif current_state == "learning":
        # Handle learning interaction
        learning_mode = user_data[user_id]["learning_mode"]
        target_lang = user_data[user_id]["target_language"]["name"]
        native_lang = user_data[user_id]["native_language"]["name"]
        proficiency = user_data[user_id]["proficiency_level"]
        
        # Generate response based on user's message and learning mode
        response = await generate_response(
            message_text,
            learning_mode,
            target_lang,
            native_lang,
            proficiency
        )
        
        await update.message.reply_text(response)

async def translate_text(text, source_lang, target_lang):
    """Translate text using OpenAI."""
    if source_lang == target_lang:
        return text
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": f"You are a translator. Translate the following text from {source_lang} to {target_lang}. Preserve formatting and keep the translation natural."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text  # Fallback to original text

async def assess_proficiency(text, language):
    """Assess language proficiency using OpenAI."""
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4-turbo",
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

async def generate_learning_content(mode, target_lang, native_lang, proficiency):
    """Generate learning content based on mode and proficiency."""
    prompts = {
        "curriculum": f"Create a weekly curriculum for {proficiency} level students learning {target_lang} from {native_lang}. Include daily activities, grammar points, and vocabulary themes.",
        "vocabulary": f"Provide a list of 10 important {proficiency} level vocabulary words in {target_lang} with translations to {native_lang} and example sentences.",
        "phrases": f"List 5 useful everyday phrases in {target_lang} for {proficiency} level learners, with translations to {native_lang} and pronunciation guides.",
        "conversation": f"Start a simple conversation in {target_lang} appropriate for {proficiency} level learners. Provide translations to {native_lang}."
    }
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a language learning assistant. Provide helpful, structured content for language learners."},
                {"role": "user", "content": prompts[mode]}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Content generation error: {e}")
        return "Sorry, I couldn't generate learning content at this time. Please try again later."

async def generate_response(user_message, mode, target_lang, native_lang, proficiency):
    """Generate a response to the user's message based on learning mode."""
    system_prompts = {
        "curriculum": f"You are a language teacher creating a curriculum for {proficiency} level students learning {target_lang} from {native_lang}. Respond to their questions about the curriculum.",
        "vocabulary": f"You are a language teacher helping {proficiency} level students learn {target_lang} vocabulary from {native_lang}. Provide vocabulary explanations, examples, and practice.",
        "phrases": f"You are a language teacher helping {proficiency} level students learn useful phrases in {target_lang} from {native_lang}. Provide phrase explanations, cultural context, and practice.",
        "conversation": f"You are a conversation partner for {proficiency} level students learning {target_lang} from {native_lang}. Maintain a natural conversation, correct major errors gently, and provide translations when helpful."
    }
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompts[mode]},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Response generation error: {e}")
        return "Sorry, I couldn't generate a response at this time. Please try again later."

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id
    
    if user_id in user_data and user_data[user_id]["native_language"]:
        native_lang = user_data[user_id]["native_language"]["code"]
        help_text = (
            "This bot helps you learn a new language. Commands:\n"
            "/start - Restart the language selection process\n"
            "/help - Show this help message\n"
            "/reset - Reset your learning progress"
        )
        translated_help = await translate_text(help_text, "en", native_lang)
        await update.message.reply_text(translated_help)
    else:
        await update.message.reply_text(
            "This bot helps you learn a new language. Commands:\n"
            "/start - Start the language selection process\n"
            "/help - Show this help message"
        )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset user data when the command /reset is issued."""
    user_id = update.effective_user.id
    
    if user_id in user_data:
        native_lang_code = None
        if user_data[user_id]["native_language"]:
            native_lang_code = user_data[user_id]["native_language"]["code"]
        
        # Clear user data
        user_data[user_id] = {
            "native_language": user_data[user_id]["native_language"],
            "target_language": None,
            "proficiency_level": None,
            "current_state": "selecting_target_language"
        }
        
        if native_lang_code:
            reset_text = "Your learning progress has been reset. Please select the language you want to learn:"
            translated_reset = await translate_text(reset_text, "en", native_lang_code)
            
            # Create target language selection keyboard
            keyboard = []
            row = []
            for i, lang in enumerate(LANGUAGES.keys()):
                # Skip the native language
                if LANGUAGES[lang] == native_lang_code:
                    continue
                row.append(InlineKeyboardButton(lang, callback_data=f"target_{LANGUAGES[lang]}_{lang}"))
                if (i + 1) % 3 == 0 or i == len(LANGUAGES) - 1:
                    keyboard.append(row)
                    row = []
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text=translated_reset,
                reply_markup=reply_markup
            )
        else:
            await start(update, context)
    else:
        await start(update, context)

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

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