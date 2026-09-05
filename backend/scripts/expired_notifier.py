import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import PassRequest, RequestStatus
from utils.email import send_email

def send_expired_notifications():
    db = SessionLocal()
    today = datetime.now().date()

    requests = db.query(PassRequest).filter(
        PassRequest.status == RequestStatus.APPROVED.value,
        PassRequest.end_date >= today,
        PassRequest.end_date < today + timedelta(days=1)
    ).all()

    for req in requests:
        send_email(
            to=["security@zymk.ru"],
            subject=f"⚠️ Заявка №{req.id} истекла",
            body=f"Заявка №{req.id} на компанию {req.company_name} сегодня истекла."
        )

    db.close()

if __name__ == "__main__":
    send_expired_notifications()
