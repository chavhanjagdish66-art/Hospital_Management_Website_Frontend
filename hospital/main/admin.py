from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Doctor, Patient, Appointment, MedicalRecord,
    Prescription, OTPVerification, Department,
    Bill, Payment, TestReport, Notification
)


# ─── Department ──────────────────────────────────────────────────────────────

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)
    list_editable = ("is_active",)


# ─── Doctor ───────────────────────────────────────────────────────────────────

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "department", "specialization", "experience", "consultation_fee", "available")
    search_fields = ("name", "email", "specialization")
    list_filter = ("specialization", "available", "department")
    list_editable = ("available",)


# ─── Patient ──────────────────────────────────────────────────────────────────

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "age", "gender", "blood_group", "created_at")
    search_fields = ("name", "email", "phone")
    list_filter = ("gender", "blood_group")


# ─── Appointment ──────────────────────────────────────────────────────────────

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("get_apt_id", "patient", "doctor", "department", "appointment_date", "appointment_time", "status", "created_at")
    search_fields = ("patient__name", "doctor__name")
    list_filter = ("status", "appointment_date", "doctor", "department")
    list_editable = ("status",)
    readonly_fields = ("appointment_id",)

    def get_apt_id(self, obj):
        return obj.get_appointment_id_short()
    get_apt_id.short_description = "Appointment ID"


# ─── MedicalRecord ────────────────────────────────────────────────────────────

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "diagnosis", "created_at")
    search_fields = ("patient__name", "doctor__name", "diagnosis")
    list_filter = ("doctor", "created_at")


# ─── Prescription ─────────────────────────────────────────────────────────────

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "medicine_name", "dosage", "frequency", "duration", "created_at")
    search_fields = ("patient__name", "doctor__name", "medicine_name")
    list_filter = ("doctor", "created_at")


# ─── TestReport ───────────────────────────────────────────────────────────────

@admin.register(TestReport)
class TestReportAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "test_name", "test_date", "status", "created_at")
    search_fields = ("patient__name", "test_name")
    list_filter = ("status", "test_date", "doctor")
    list_editable = ("status",)


# ─── Bill ─────────────────────────────────────────────────────────────────────

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("bill_number", "patient", "total_amount", "payment_status", "created_at")
    search_fields = ("bill_number", "patient__name")
    list_filter = ("payment_status",)
    readonly_fields = ("bill_number",)


# ─── Payment ──────────────────────────────────────────────────────────────────

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("patient", "bill", "amount", "payment_method", "payment_status", "payment_date", "created_at")
    search_fields = ("patient__name", "razorpay_payment_id", "receipt_number")
    list_filter = ("payment_method", "payment_status")


# ─── Notification ─────────────────────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("patient", "title", "is_read", "created_at")
    search_fields = ("patient__name", "title")
    list_filter = ("is_read",)
    list_editable = ("is_read",)


# ─── OTPVerification ──────────────────────────────────────────────────────────

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ("email", "is_verified", "attempts", "created_at")
    list_filter = ("is_verified",)
    readonly_fields = ("otp",)

    def get_readonly_fields(self, request, obj=None):
        return ["otp", "created_at"]