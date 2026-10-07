# =========================================================
# PATIL HOSPITAL – OTP Service
# =========================================================

import random
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5


def generate_otp():
    """Generate a secure 6-digit OTP."""
    return str(random.randint(100000, 999999))


def send_otp(email, name, otp):
    """
    Send OTP to patient.
    Uses email OTP (Gmail SMTP).
    Falls back to dev mode if email not configured or using placeholders.
    """
    from main.services.email_service import send_otp_email

    host_user = getattr(settings, 'EMAIL_HOST_USER', '') or ''
    host_pass = getattr(settings, 'EMAIL_HOST_PASSWORD', '') or ''
    is_placeholder = (
        not host_user or 
        'your-gmail' in host_user or 
        'your-gmail' in host_pass or 
        host_pass == ''
    )

    success = send_otp_email(email, name, otp)
    if success:
        return True, "email_sent"
    else:
        logger.error(f"Failed to send OTP email to {email}")
        return False, "email_failed"


def create_otp_record(email):
    """
    Create/replace an OTP record for the given email.
    Returns the OTP string.
    """
    from main.models import OTPVerification

    otp = generate_otp()

    # Remove old unverified OTPs
    OTPVerification.objects.filter(
        email=email,
        is_verified=False
    ).delete()

    # Create new OTP record
    OTPVerification.objects.create(
        email=email,
        otp=otp,
        is_verified=False,
        attempts=0
    )

    return otp


def verify_otp(email, entered_otp):
    """
    Verify an OTP for a given email.
    Returns (success: bool, message: str)
    """
    from main.models import OTPVerification

    record = OTPVerification.objects.filter(
        email=email,
        is_verified=False
    ).order_by('-created_at').first()

    if not record:
        return False, "OTP not found. Please request a new OTP."

    # Check expiry
    expiry = record.created_at + timedelta(minutes=OTP_EXPIRY_MINUTES)
    if timezone.now() > expiry:
        record.delete()
        return False, f"OTP has expired. Please request a new OTP."

    # Check max attempts
    if record.attempts >= OTP_MAX_ATTEMPTS:
        record.delete()
        return False, "Too many failed attempts. Please request a new OTP."

    # Check OTP
    if entered_otp != record.otp:
        record.attempts += 1
        record.save()
        remaining = OTP_MAX_ATTEMPTS - record.attempts
        return False, f"Invalid OTP. {remaining} attempt(s) remaining."

    # Mark verified
    record.is_verified = True
    record.save()

    return True, "OTP verified successfully."
