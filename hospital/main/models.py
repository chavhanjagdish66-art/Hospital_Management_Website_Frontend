import uuid
from django.db import models
from django.utils import timezone


# =========================
# DEPARTMENT
# =========================

class Department(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="FontAwesome icon class e.g. fa-heart"
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name

    @property
    def display_icon(self):
        if not self.icon:
            return "🏥"
        icon_str = self.icon.strip()
        if not icon_str.startswith('fa-') and not icon_str.startswith('fa '):
            return icon_str
        icon_map = {
            'fa-heart': '🫀',
            'fa-tooth': '🦷',
            'fa-user-md': '🩺',
            'fa-stethoscope': '🩺',
            'fa-ear-listen': '👂',
            'fa-venus': '♀️',
            'fa-brain': '🧠',
            'fa-bone': '🦴',
            'fa-child': '👶',
            'fa-eye': '👁️',
            'fa-pills': '💊',
            'fa-syringe': '💉',
            'fa-hospital': '🏥',
        }
        return icon_map.get(icon_str, "🏥")

    class Meta:
        ordering = ['name']


# =========================
# DOCTOR
# =========================

class Doctor(models.Model):

    AVAILABLE_DAYS_CHOICES = [
        ('Mon-Fri', 'Monday to Friday'),
        ('Mon-Sat', 'Monday to Saturday'),
        ('Mon-Sun', 'Monday to Sunday'),
        ('Weekends', 'Weekends Only'),
        ('Custom', 'Custom Schedule'),
    ]

    user = models.OneToOneField(
        "auth.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doctors"
    )

    name = models.CharField(
        max_length=100
    )

    email = models.EmailField(
        unique=True
    )

    phone = models.CharField(
        max_length=15
    )

    specialization = models.CharField(
        max_length=100
    )

    qualification = models.CharField(
        max_length=100
    )

    experience = models.PositiveIntegerField(
        default=0
    )

    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    profile_image = models.ImageField(
        upload_to='doctors/',
        null=True,
        blank=True
    )

    available = models.BooleanField(
        default=True
    )

    available_days = models.CharField(
        max_length=20,
        choices=AVAILABLE_DAYS_CHOICES,
        default='Mon-Sat'
    )

    available_time_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Availability start time"
    )

    available_time_end = models.TimeField(
        null=True,
        blank=True,
        help_text="Availability end time"
    )

    bio = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


# =========================
# PATIENT
# =========================

class Patient(models.Model):

    user = models.OneToOneField(
        "auth.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    name = models.CharField(
        max_length=100
    )

    email = models.EmailField(
        unique=True
    )

    phone = models.CharField(
        max_length=15
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    age = models.PositiveIntegerField(
        default=0
    )

    gender = models.CharField(
        max_length=20
    )

    address = models.TextField()

    blood_group = models.CharField(
        max_length=5,
        blank=True
    )

    medical_history = models.TextField(
        blank=True
    )

    profile_image = models.ImageField(
        upload_to='patients/',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


# =========================
# APPOINTMENT
# =========================

class Appointment(models.Model):

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Rejected", "Rejected"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    appointment_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments"
    )

    appointment_date = models.DateField()

    appointment_time = models.TimeField()

    reason = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    notes = models.TextField(
        blank=True,
        help_text="Doctor's notes"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"APT-{str(self.appointment_id)[:8].upper()} | {self.patient.name} → Dr. {self.doctor.name}"

    def get_appointment_id_short(self):
        return f"APT-{str(self.appointment_id)[:8].upper()}"

    class Meta:
        unique_together = [['doctor', 'appointment_date', 'appointment_time']]
        ordering = ['-appointment_date', '-appointment_time']


# =========================
# MEDICAL RECORD
# =========================

class MedicalRecord(models.Model):

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="medical_records"
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="medical_records"
    )

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medical_record"
    )

    symptoms = models.TextField()

    diagnosis = models.TextField()

    treatment = models.TextField(
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.patient.name} - {self.diagnosis}"


# =========================
# OTP VERIFICATION
# =========================

class OTPVerification(models.Model):

    email = models.EmailField()

    otp = models.CharField(
        max_length=6
    )

    attempts = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_verified = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f"{self.email} - {'Verified' if self.is_verified else 'Pending'}"


# =========================
# PRESCRIPTION
# =========================

class Prescription(models.Model):

    FREQUENCY_CHOICES = [
        ('Once daily', 'Once daily'),
        ('Twice daily', 'Twice daily'),
        ('Thrice daily', 'Thrice daily'),
        ('Four times daily', 'Four times daily'),
        ('As needed', 'As needed'),
        ('Before meals', 'Before meals'),
        ('After meals', 'After meals'),
        ('At bedtime', 'At bedtime'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="prescriptions"
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="prescriptions"
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prescriptions"
    )

    diagnosis = models.TextField(
        blank=True
    )

    medicine_name = models.CharField(
        max_length=200
    )

    dosage = models.CharField(
        max_length=100
    )

    frequency = models.CharField(
        max_length=50,
        choices=FREQUENCY_CHOICES,
        default='Twice daily'
    )

    duration = models.CharField(
        max_length=100
    )

    instructions = models.TextField(
        blank=True
    )

    follow_up_date = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.patient.name} - {self.medicine_name}"


# =========================
# TEST REPORT
# =========================

class TestReport(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="test_reports"
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="test_reports"
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="test_reports"
    )

    test_name = models.CharField(
        max_length=200
    )

    test_date = models.DateField()

    report_details = models.TextField(
        blank=True
    )

    report_file = models.FileField(
        upload_to='test_reports/',
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.patient.name} - {self.test_name}"


# =========================
# BILL
# =========================

class Bill(models.Model):

    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
    ]

    bill_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="bills"
    )

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name="bill"
    )

    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    test_charges = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    medicine_charges = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    other_charges = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='Pending'
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        if not self.bill_number:
            last = Bill.objects.order_by('-id').first()
            next_id = (last.id + 1) if last else 1
            self.bill_number = f"BILL-{next_id:05d}"
        if not self.total_amount:
            self.total_amount = (
                self.consultation_fee +
                self.test_charges +
                self.medicine_charges +
                self.other_charges
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bill_number} | {self.patient.name}"


# =========================
# PAYMENT
# =========================

class Payment(models.Model):

    PAYMENT_METHOD_CHOICES = [
        ('Online', 'Online (Razorpay)'),
        ('Cash', 'Cash at Hospital'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    bill = models.OneToOneField(
        Bill,
        on_delete=models.CASCADE,
        related_name="payment"
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='Cash'
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='Pending'
    )

    # Razorpay fields
    razorpay_order_id = models.CharField(
        max_length=100,
        blank=True
    )

    razorpay_payment_id = models.CharField(
        max_length=100,
        blank=True
    )

    razorpay_signature = models.CharField(
        max_length=200,
        blank=True
    )

    # Cash payment
    received_by = models.CharField(
        max_length=100,
        blank=True,
        help_text="Staff who received cash"
    )

    receipt_number = models.CharField(
        max_length=20,
        blank=True
    )

    payment_date = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.patient.name} | {self.payment_method} | ₹{self.amount} | {self.payment_status}"


# =========================
# NOTIFICATION
# =========================

class Notification(models.Model):

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(
        max_length=200
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.patient.name} – {self.title}"

    class Meta:
        ordering = ['-created_at']