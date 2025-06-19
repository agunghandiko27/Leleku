from flask_mail import Message
from app import mail, db  # ← Tambahkan import db
import random
from datetime import datetime, timedelta

def send_otp_email(user):
    try:
        otp = str(random.randint(100000, 999999))
        user.otp_code = otp
        user.otp_expiry = datetime.utcnow() + timedelta(seconds=60)

        db.session.commit()  # ← Tambahkan ini agar OTP tersimpan

        msg = Message(
            subject="Kode OTP Verifikasi",
            recipients=[user.email],
            body=f"Kode OTP kamu: {otp} (berlaku 60 detik)"
        )
        mail.send(msg)
        print("✅ Email OTP berhasil dikirim")
    except Exception as e:
        print(f"❌ Gagal mengirim email OTP: {e}")
        raise e
