from email.header import decode_header
import quopri  # Кодирование и декодирование Quoted-Printable
import base64  # Кодирование и декодирование Base64

# Функция для декодирования заголовка
def decode_header_text(header):
    # Декодирование заголовка сообщения
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
