import traceback
import telebot
import imaplib
import threading
import schedule
import time
from email import message_from_string
from email.header import decode_header
from email import quoprimime
from peewee import SqliteDatabase, Model, CharField
import quopri
import base64
import config


# Инициализация бота и базы данных
bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)
db = SqliteDatabase(config.DATABASE_NAME)

# Определение модели базы данных
class User(Model):
    chat_id = CharField()
    email = CharField()
    password = CharField()

    class Meta:
        database = db

# Определение модели базы данных
class messages(Model):
    user_id = CharField()
    message_id = CharField()

    class Meta:
        database = db

# Создание таблицы в базе данных (если ее еще нет)
db.connect()
db.create_tables([User], safe=True)


# Функция для отправки уведомлений в Telegram
def send_notification(chat_id, box, sender,subject,message_text):
    notification_text = f"Новое письмо на *{box}*!\n*От:* {sender}\n*Тема:* {subject}\n*Текст:* _{message_text}_"
    try:
        bot.send_message(chat_id, notification_text, parse_mode="Markdown")
    except:
        notification_text = f"Новое письмо на *{box}*!\n*От:* {sender}\n*Тема:* {subject}\n*Текст:* [Текст слишком большой для сообщения..]"
        bot.send_message(chat_id, notification_text, parse_mode="Markdown")
# Функция для декодирования заголовка
def decode_header_text(header):
    decoded, encoding = decode_header(header)[0]
    return decoded.decode(encoding) if encoding else decoded

# Функция для декодирования текста сообщения
def decode_message_text(text):
    try:
        # Попробуем декодировать как Quoted-Printable
        decoded_text = quopri.decodestring(text).decode('utf-8')
        return decoded_text
    except UnicodeDecodeError:
        # Если не удалось декодировать Quoted-Printable, попробуем base64
        try:
            decoded_text = base64.b64decode(text).decode('utf-8')
            return decoded_text
        except Exception as e:
            print(f"Ошибка декодирования текста: {e}")
            return "Не удалось декодировать текст"


# Функция для обработки новых писем
def check_email(user):
    message_id = False
    mail = imaplib.IMAP4_SSL("imap."+user.email.split('@')[1])
    try:
        mail.login(user.email, user.password)
    except Exception as e:
        if "AUTHENTICATIONFAILED" in str(e):
            user.delete_instance()
    mail.select("inbox")

    status, messages = mail.search(None, "(UNSEEN)")
    message_ids = reversed(messages[0].split())
    for i in message_ids:
        message_id  = i
        break
    if message_id != False:
        _, msg_data = mail.fetch(message_id, "(RFC822)")
        email_content = msg_data[0][1].decode("utf-8")
        msg = message_from_string(email_content)
        sender = decode_header_text(msg["From"])
        subject = decode_header_text(msg["Subject"])

        body = msg.get_payload()
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True)
                    break
        try:
            message_text = decode_message_text(body)
        except:
            message_text = "Текст не может быть обработан."

        send_notification(user.chat_id,user.email,sender,subject,message_text)

        mail.close()
        mail.logout()
# Функция для проверки почты для всех пользователей
def check_all_emails():
    try:
        users = User.select()
        for user in users:
            check_email(user)
    except Exception as e:
        print(traceback.format_exc())
        print(f"Ошибка при проверке почты: {e}")

# Регулярная проверка почты каждые 5 минут
schedule.every(5).seconds.do(check_all_emails)

# Функция для запуска планировщика
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Запуск отдельного потока для планировщика
threading.Thread(target=run_scheduler, daemon=True).start()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "Привет! Для начала работы введите /register")

# Обработчик команды /register
@bot.message_handler(commands=['register'])
def handle_register(message):
    bot.send_message(message.chat.id, "Введите свой email:")
    bot.register_next_step_handler(message, register_email)

# Обработчик ввода email
def register_email(message):
    chat_id = str(message.chat.id)
    email = message.text.lower()
    bot.send_message(message.chat.id, "Теперь введите пароль:")
    bot.register_next_step_handler(message, register_password, chat_id, email)

# Обработчик ввода пароля
def register_password(message, chat_id, email):
    password = message.text
    try:
        user = User.create(chat_id=chat_id, email=email, password=password)
        user.save()
        bot.send_message(message.chat.id, "Регистрация успешно завершена. Теперь вы будете получать уведомления о новых письмах.")
    except:
        bot.send_message(message.chat.id, "Ошибка регистрации. Возможно, вы уже зарегистрированы.")

# Обработчик команды /check_email
@bot.message_handler(commands=['check_email'])
def handle_check_email(message):
    chat_id = str(message.chat.id)
    try:
        user = User.get(User.chat_id == chat_id)
        print(user)
        check_email(user)
        bot.send_message(message.chat.id, "Проверка почты завершена. Уведомления отправлены, если есть новые письма.")
    except User.DoesNotExist:
        bot.send_message(message.chat.id, "Вы не зарегистрированы. Введите /register для регистрации.")

# Запуск бота
bot.polling(none_stop=True)
