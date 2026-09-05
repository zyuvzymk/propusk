import sys
import os
import re
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import PassRequest, RequestStatus
from utils.email import send_email

def send_reminders():
    db = SessionLocal()
    today = datetime.now().date()
    target_date = today + timedelta(days=5)

    requests = db.query(PassRequest).filter(
        PassRequest.status == RequestStatus.APPROVED.value,
        PassRequest.end_date >= target_date,
        PassRequest.end_date < target_date + timedelta(days=1)
    ).all()

    for req in requests:
        email_match = re.search(r'Email:\s*([^\s,|]+)', req.purpose)
        if email_match:
            client_email = email_match.group(1)
            send_email(
                to=[client_email],
                subject=f"Напоминание: заявка №{req.id} заканчивается через 5 дней",
                body=f"Уважаемый пользователь,\n\nВаша заявка №{req.id} заканчивается через 5 дней (до {req.end_date.date()}).\n\nПожалуйста, продлите её при необходимости."
            )

    db.close()

if __name__ == "__main__":
    send_reminders()
