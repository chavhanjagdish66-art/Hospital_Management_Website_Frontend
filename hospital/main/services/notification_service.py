# =========================================================
# PATIL HOSPITAL – Notification Service
# =========================================================

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _fmt_date(val, fmt='%d %b %Y'):
    if not val:
        return ""
    if hasattr(val, 'strftime'):
        return val.strftime(fmt)
    try:
        d = datetime.strptime(str(val), '%Y-%m-%d').date()
        return d.strftime(fmt)
    except Exception:
        return str(val)


def _fmt_time(val, fmt='%I:%M %p'):
    if not val:
        return ""
    if hasattr(val, 'strftime'):
        return val.strftime(fmt)
    s = str(val).strip()
    try:
        t = datetime.strptime(s, '%H:%M').time()
        return t.strftime(fmt)
    except Exception:
        try:
            t = datetime.strptime(s, '%H:%M:%S').time()
            return t.strftime(fmt)
        except Exception:
            return s


def create_notification(patient, title, message):
    """Create an in-app notification for the patient."""
    from main.models import Notification
    try:
        notif = Notification.objects.create(
            patient=patient,
            title=title,
            message=message
        )
        return notif
    except Exception as e:
        logger.error(f"Notification creation error: {e}")
        return None


def get_unread_count(patient):
    """Return unread notification count for a patient."""
    from main.models import Notification
    return Notification.objects.filter(patient=patient, is_read=False).count()


def notify_appointment_booked(appointment):
    create_notification(
        appointment.patient,
        "Appointment Booked",
        f"Your appointment with Dr. {appointment.doctor.name} on "
        f"{_fmt_date(appointment.appointment_date)} at "
        f"{_fmt_time(appointment.appointment_time)} has been booked. "
        f"Appointment ID: {appointment.get_appointment_id_short()}"
    )


def notify_appointment_confirmed(appointment):
    create_notification(
        appointment.patient,
        "Appointment Confirmed ✓",
        f"Dr. {appointment.doctor.name} has confirmed your appointment on "
        f"{_fmt_date(appointment.appointment_date)} at "
        f"{_fmt_time(appointment.appointment_time)}."
    )


def notify_appointment_rejected(appointment):
    create_notification(
        appointment.patient,
        "Appointment Rejected",
        f"Your appointment with Dr. {appointment.doctor.name} on "
        f"{_fmt_date(appointment.appointment_date)} has been rejected. "
        f"Please book a new appointment."
    )


def notify_appointment_cancelled(appointment):
    create_notification(
        appointment.patient,
        "Appointment Cancelled",
        f"Your appointment with Dr. {appointment.doctor.name} on "
        f"{_fmt_date(appointment.appointment_date)} has been cancelled."
    )


def notify_appointment_completed(appointment):
    create_notification(
        appointment.patient,
        "Appointment Completed",
        f"Your appointment with Dr. {appointment.doctor.name} has been completed. "
        f"Please check your prescription and bill."
    )


def notify_prescription_added(prescription):
    create_notification(
        prescription.patient,
        "New Prescription",
        f"Dr. {prescription.doctor.name} has added a prescription for "
        f"{prescription.medicine_name}. Please follow the instructions carefully."
    )


def notify_test_report_available(test_report):
    create_notification(
        test_report.patient,
        "Test Report Available",
        f"Your {test_report.test_name} report is now available. "
        f"Please login to view and download your report."
    )


def notify_bill_generated(bill):
    create_notification(
        bill.patient,
        "Bill Generated",
        f"Your bill (₹{bill.total_amount}) has been generated. "
        f"Bill Number: {bill.bill_number}. Please complete your payment."
    )


def notify_payment_success(payment):
    create_notification(
        payment.patient,
        "Payment Successful ✓",
        f"Your payment of ₹{payment.amount} via {payment.payment_method} "
        f"has been received successfully. Bill: {payment.bill.bill_number}."
    )
