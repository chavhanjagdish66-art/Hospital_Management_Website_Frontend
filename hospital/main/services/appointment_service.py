# =========================================================
# PATIL HOSPITAL – Appointment Service
# =========================================================

from datetime import time, timedelta
import logging

logger = logging.getLogger(__name__)

# Appointment slot interval in minutes
SLOT_INTERVAL = 30

# Default working hours if doctor has none set
DEFAULT_START = time(9, 0)
DEFAULT_END = time(17, 0)


def get_available_slots(doctor, date):
    """
    Return list of available time slots for a doctor on a given date.
    Excludes already-booked slots.
    """
    from main.models import Appointment

    start_time = doctor.available_time_start or DEFAULT_START
    end_time = doctor.available_time_end or DEFAULT_END

    # Generate all slots
    slots = []
    current = timedelta(
        hours=start_time.hour,
        minutes=start_time.minute
    )
    end = timedelta(
        hours=end_time.hour,
        minutes=end_time.minute
    )

    while current < end:
        total_seconds = int(current.total_seconds())
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        slots.append(time(h, m))
        current += timedelta(minutes=SLOT_INTERVAL)

    # Get booked slots for this doctor on this date
    booked = set(
        Appointment.objects.filter(
            doctor=doctor,
            appointment_date=date,
        ).exclude(
            status__in=['Cancelled', 'Rejected']
        ).values_list('appointment_time', flat=True)
    )

    available = [s for s in slots if s not in booked]
    return available


def is_slot_available(doctor, date, slot_time):
    """Check if a specific slot is available."""
    from main.models import Appointment
    return not Appointment.objects.filter(
        doctor=doctor,
        appointment_date=date,
        appointment_time=slot_time,
    ).exclude(
        status__in=['Cancelled', 'Rejected']
    ).exists()


def generate_bill_for_appointment(appointment):
    """
    Auto-generate a Bill for a newly booked appointment.
    Uses doctor's consultation fee.
    """
    from main.models import Bill

    # Don't create duplicate bills
    if hasattr(appointment, 'bill') and appointment.bill:
        return appointment.bill

    consultation_fee = appointment.doctor.consultation_fee or 0

    bill = Bill.objects.create(
        patient=appointment.patient,
        appointment=appointment,
        consultation_fee=consultation_fee,
        total_amount=consultation_fee,
        payment_status='Pending',
    )
    return bill
