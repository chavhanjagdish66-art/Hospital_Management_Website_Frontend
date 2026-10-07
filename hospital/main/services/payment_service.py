# =========================================================
# PATIL HOSPITAL – Payment Service (Razorpay)
# =========================================================

import hmac
import hashlib
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_razorpay_client():
    """Return a Razorpay client if credentials are configured."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return None
    try:
        import razorpay
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        return client
    except Exception as e:
        logger.error(f"Razorpay client error: {e}")
        return None


def is_razorpay_configured():
    """Check whether Razorpay is configured."""
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def create_razorpay_order(amount_rupees, receipt_id):
    """
    Create a Razorpay order.
    amount_rupees: Decimal or float
    Returns (order_dict, error_msg)
    """
    client = get_razorpay_client()
    if not client:
        return None, "Razorpay not configured. Please add credentials to .env"

    try:
        amount_paise = int(float(amount_rupees) * 100)
        order_data = {
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': str(receipt_id),
            'payment_capture': 1,
        }
        order = client.order.create(data=order_data)
        logger.info(f"Razorpay order created: {order['id']}")
        return order, None
    except Exception as e:
        logger.error(f"Razorpay order creation error: {e}")
        return None, str(e)


def verify_razorpay_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Verify Razorpay payment signature.
    Returns True if valid, False otherwise.
    """
    if not settings.RAZORPAY_KEY_SECRET:
        return False

    try:
        key_secret = settings.RAZORPAY_KEY_SECRET.encode('utf-8')
        msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8')
        expected_signature = hmac.new(key_secret, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_signature, razorpay_signature)
    except Exception as e:
        logger.error(f"Razorpay signature verification error: {e}")
        return False


def mark_payment_success(payment, razorpay_payment_id, razorpay_order_id, razorpay_signature):
    """Update payment record after successful Razorpay payment."""
    from main.models import Bill

    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_order_id = razorpay_order_id
    payment.razorpay_signature = razorpay_signature
    payment.payment_status = 'Paid'
    payment.payment_date = timezone.now()
    payment.save()

    # Update bill
    payment.bill.payment_status = 'Paid'
    payment.bill.save()

    logger.info(f"Payment marked success: {razorpay_payment_id}")


def mark_cash_payment(payment, received_by="Reception"):
    """Mark a cash payment as pending (to be confirmed by admin)."""
    payment.payment_method = 'Cash'
    payment.payment_status = 'Pending'
    payment.received_by = received_by
    payment.save()

    payment.bill.payment_status = 'Pending'
    payment.bill.save()


def mark_cash_received(payment, received_by="Reception"):
    """Admin marks cash as received."""
    payment.payment_status = 'Paid'
    payment.payment_date = timezone.now()
    payment.received_by = received_by
    if not payment.receipt_number:
        payment.receipt_number = f"RCPT-{payment.id:06d}"
    payment.save()

    payment.bill.payment_status = 'Paid'
    payment.bill.save()
