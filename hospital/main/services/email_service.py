# =========================================================
# PATIL HOSPITAL – Email Service
# =========================================================

import logging
from datetime import datetime
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def _fmt_date(val, fmt='%d %B %Y'):
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


def _send(subject, message, recipient_list):
    """Core send helper – never crashes the app on email failure."""
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        logger.info(f"Email sent to {recipient_list}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email error to {recipient_list}: {e}")
        return False


# =========================================================
# OTP EMAIL
# =========================================================

def send_otp_email(email, name, otp):
    subject = "Your OTP – Patil Hospital"
    message = f"""Dear {name},

Your One-Time Password (OTP) for Patil Hospital patient registration is:

  {otp}

This OTP is valid for 5 minutes. Please do not share it with anyone.

If you did not request this, please ignore this email.

Regards,
Patil Hospital
Quality Healthcare & Patient Care
"""
    return _send(subject, message, [email])


# =========================================================
# APPOINTMENT CONFIRMATION
# =========================================================

def send_appointment_confirmation_email(appointment):
    patient = appointment.patient
    doctor = appointment.doctor
    dept = appointment.department.name if appointment.department else doctor.specialization
    apt_id = appointment.get_appointment_id_short()

    subject = "Appointment Confirmation – Patil Hospital"
    message = f"""Dear {patient.name},

Your appointment at Patil Hospital has been successfully booked.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPOINTMENT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Appointment ID : {apt_id}
Patient        : {patient.name}
Doctor         : Dr. {doctor.name}
Department     : {dept}
Date           : {_fmt_date(appointment.appointment_date)}
Time           : {_fmt_time(appointment.appointment_time)}
Status         : {appointment.status}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please arrive 10 minutes before your appointment.

For any queries, contact Patil Hospital:
📞 Emergency: +91-XXXXX-XXXXX
📧 info@patilhospital.com

Thank you for choosing Patil Hospital.

Regards,
Patil Hospital
Quality Healthcare & Patient Care
"""
    return _send(subject, message, [patient.email])


# =========================================================
# APPOINTMENT STATUS UPDATE
# =========================================================

def send_appointment_status_email(appointment):
    patient = appointment.patient
    doctor = appointment.doctor
    apt_id = appointment.get_appointment_id_short()
    status = appointment.status

    if status == 'Confirmed':
        status_msg = "Your appointment has been CONFIRMED by the doctor."
    elif status == 'Rejected':
        status_msg = "Unfortunately, your appointment has been REJECTED. Please book a new appointment."
    elif status == 'Completed':
        status_msg = "Your appointment has been marked as COMPLETED. We hope you had a good experience."
    elif status == 'Cancelled':
        status_msg = "Your appointment has been CANCELLED."
    else:
        status_msg = f"Your appointment status has been updated to: {status}"

    subject = f"Appointment {status} – Patil Hospital"
    message = f"""Dear {patient.name},

{status_msg}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPOINTMENT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Appointment ID : {apt_id}
Doctor         : Dr. {doctor.name}
Date           : {_fmt_date(appointment.appointment_date)}
Time           : {_fmt_time(appointment.appointment_time)}
Status         : {status}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For any queries, contact Patil Hospital.

Thank you for choosing Patil Hospital.

Regards,
Patil Hospital
"""
    return _send(subject, message, [patient.email])


# =========================================================
# CANCELLATION
# =========================================================

def send_cancellation_email(appointment):
    appointment.status = 'Cancelled'
    return send_appointment_status_email(appointment)


# =========================================================
# PRESCRIPTION
# =========================================================

def send_prescription_email(prescription):
    patient = prescription.patient
    doctor = prescription.doctor

    subject = "Prescription Added – Patil Hospital"
    message = f"""Dear {patient.name},

Dr. {doctor.name} has added a new prescription for you.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRESCRIPTION DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Medicine  : {prescription.medicine_name}
Dosage    : {prescription.dosage}
Frequency : {prescription.frequency}
Duration  : {prescription.duration}
{f"Instructions: {prescription.instructions}" if prescription.instructions else ""}
{f"Follow-up   : {_fmt_date(prescription.follow_up_date)}" if prescription.follow_up_date else ""}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please login to Patil Hospital to view full details.

Regards,
Patil Hospital
"""
    return _send(subject, message, [patient.email])


# =========================================================
# PAYMENT CONFIRMATION
# =========================================================

def send_payment_confirmation_email(payment):
    patient = payment.patient
    bill = payment.bill
    appointment = payment.appointment
    apt_id = appointment.get_appointment_id_short()

    subject = "Payment Confirmation – Patil Hospital"
    message = f"""Dear {patient.name},

Your payment at Patil Hospital has been processed successfully.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAYMENT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bill Number    : {bill.bill_number}
Appointment ID : {apt_id}
Patient        : {patient.name}
Doctor         : Dr. {appointment.doctor.name}
Amount Paid    : ₹{payment.amount}
Payment Method : {payment.payment_method}
Payment Status : {payment.payment_status}
{f"Transaction ID : {payment.razorpay_payment_id}" if payment.razorpay_payment_id else ""}
Payment Date   : {_fmt_date(payment.payment_date, '%d %B %Y, %I:%M %p') if payment.payment_date else 'N/A'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please keep this as your payment reference.

Thank you for choosing Patil Hospital.

Regards,
Patil Hospital
Quality Healthcare & Patient Care
"""
    return _send(subject, message, [patient.email])


# =========================================================
# TEST REPORT AVAILABLE
# =========================================================

def send_test_report_email(test_report):
    patient = test_report.patient
    subject = "Test Report Available – Patil Hospital"
    message = f"""Dear {patient.name},

Your test report is now available at Patil Hospital.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST REPORT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test Name : {test_report.test_name}
Test Date : {_fmt_date(test_report.test_date)}
Status    : {test_report.status}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please login to Patil Hospital to view and download your report.

Regards,
Patil Hospital
"""
    return _send(subject, message, [patient.email])
