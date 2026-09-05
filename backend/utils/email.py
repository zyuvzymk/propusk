import subprocess
from typing import List

def send_email(to: List[str], subject: str, body: str):
    """
    Отправка письма через msmtp
    to: список email-адресов
    subject: тема письма
    body: тело письма
    """
    if isinstance(to, str):
        to = [to]

    recipients = ", ".join(to)

    msg = f"To: {recipients}\n" \
          f"Subject: {subject}\n\n" \
          f"{body}"

    try:
        process = subprocess.Popen(
            ["/usr/bin/msmtp", "-a", "default", "-t"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = process.communicate(msg.encode())
        if process.returncode != 0:
            print(f"Ошибка отправки письма: {err.decode()}")
            return False
        return True
    except Exception as e:
        print(f"Исключение при отправке письма: {e}")
        return False
