import requests

class TelegramProvider:
    def send_message(self, token: str, chat_id: str, message: str) -> tuple[bool, str]:
        """
        Sends a text message to the specified Telegram chat.
        Returns a tuple of (success_boolean, status_message).
        """
        if not token or not chat_id:
            return False, "❌ Нет токена или Chat ID."

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return True, "✅ Отчет отправлен!"
            else:
                return False, f"Ошибка Telegram: {response.text}"
        except Exception as e:
            return False, f"Ошибка сети: {str(e)}"
