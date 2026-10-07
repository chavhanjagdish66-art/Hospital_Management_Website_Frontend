from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from main import views


urlpatterns = [

    # =========================================================
    # DJANGO ADMIN
    # =========================================================

    path(
        "admin/",
        admin.site.urls
    ),


    # =========================================================
    # PUBLIC PAGES
    # =========================================================

    path(
        "",
        views.home,
        name="home"
    ),

    path(
        "about/",
        views.about,
        name="about"
    ),

    path(
        "departments/",
        views.departments_page,
        name="departments"
    ),

    path(
        "doctors/",
        views.our_doctors,
        name="our_doctors"
    ),

    path(
        "services/",
        views.services,
        name="services"
    ),

    path(
        "emergency/",
        views.emergency,
        name="emergency"
    ),

    path(
        "contact/",
        views.contact,
        name="contact"
    ),


    # =========================================================
    # LOGIN / LOGOUT / REGISTER
    # =========================================================

    path(
        "login/",
        views.login_page,
        name="login"
    ),

    path(
        "logout/",
        views.logout_user,
        name="logout"
    ),

    path(
        "register/",
        views.patient_register,
        name="patient_register"
    ),

    # Old OTP compatibility URLs
    path(
        "verify-otp/",
        views.verify_otp,
        name="verify_otp"
    ),

    path(
        "resend-otp/",
        views.resend_otp,
        name="resend_otp"
    ),


    # =========================================================
    # ADMIN DASHBOARD
    # =========================================================

    path(
        "admin-dashboard/",
        views.admin_dashboard,
        name="admin_dashboard"
    ),

    path(
        "doctors-list/",
        views.admin_doctors_list,
        name="admin_doctors_list"
    ),

    path(
        "patients-list/",
        views.admin_patients_list,
        name="admin_patients_list"
    ),

    path(
        "appointments-list/",
        views.admin_appointments_list,
        name="admin_appointments_list"
    ),

    path(
        "revenue-records/",
        views.admin_revenue_records,
        name="admin_revenue_records"
    ),

    path(
        "add-doctor/",
        views.add_doctor,
        name="add_doctor"
    ),

    path(
        "edit-doctor/<int:doctor_id>/",
        views.edit_doctor,
        name="edit_doctor"
    ),

    path(
        "delete-doctor/<int:doctor_id>/",
        views.delete_doctor,
        name="delete_doctor"
    ),

    path(
        "toggle-doctor-availability/<int:doctor_id>/",
        views.toggle_doctor_availability,
        name="toggle_doctor_availability"
    ),

    path(
        "delete-patient/<int:patient_id>/",
        views.delete_patient,
        name="delete_patient"
    ),


    # =========================================================
    # DEPARTMENTS
    # =========================================================

    path(
        "departments/manage/",
        views.manage_departments,
        name="manage_departments"
    ),

    path(
        "departments/add/",
        views.add_department,
        name="add_department"
    ),

    path(
        "departments/edit/<int:dept_id>/",
        views.edit_department,
        name="edit_department"
    ),

    path(
        "departments/delete/<int:dept_id>/",
        views.delete_department,
        name="delete_department"
    ),

    path(
        "departments/toggle-status/<int:dept_id>/",
        views.toggle_department_status,
        name="toggle_department_status"
    ),


    # =========================================================
    # ADMIN BILLS & PAYMENTS
    # =========================================================

    path(
        "admin/bills/",
        views.manage_bills,
        name="manage_bills"
    ),

    path(
        "admin/payments/",
        views.manage_payments,
        name="manage_payments"
    ),

    path(
        "admin/payments/<int:payment_id>/mark-paid/",
        views.mark_cash_paid,
        name="mark_cash_paid"
    ),


    # =========================================================
    # DOCTOR DASHBOARD
    # =========================================================

    path(
        "doctor-dashboard/",
        views.doctor_dashboard,
        name="doctor_dashboard"
    ),
    path(
    "doctor-profile-change/",
    views.doctor_profile_change,
    name="doctor_profile_change"
),


    # =========================================================
    # DOCTOR APPOINTMENT ACTIONS
    # =========================================================

    path(
        "appointment/<int:appointment_id>/confirm/",
        lambda request, appointment_id:
            views.update_appointment_status(
                request,
                appointment_id,
                "Confirmed"
            ),
        name="confirm_appointment"
    ),

    path(
        "appointment/<int:appointment_id>/reject/",
        lambda request, appointment_id:
            views.update_appointment_status(
                request,
                appointment_id,
                "Rejected"
            ),
        name="reject_appointment"
    ),

    path(
        "appointment/<int:appointment_id>/cancel/",
        lambda request, appointment_id:
            views.update_appointment_status(
                request,
                appointment_id,
                "Cancelled"
            ),
        name="cancel_appointment_doctor"
    ),

    path(
        "appointment/<int:appointment_id>/complete/",
        lambda request, appointment_id:
            views.update_appointment_status(
                request,
                appointment_id,
                "Completed"
            ),
        name="complete_appointment"
    ),


    # =========================================================
    # MEDICAL RECORDS
    # =========================================================

    path(
        "medical-record/<int:appointment_id>/",
        views.add_medical_record,
        name="add_medical_record"
    ),

    path(
        "add-prescription/<int:appointment_id>/",
        views.add_prescription,
        name="add_prescription"
    ),

    path(
        "upload-test-report/<int:appointment_id>/",
        views.upload_test_report,
        name="upload_test_report"
    ),

    path(
        "medical-history/<int:patient_id>/",
        views.medical_history,
        name="medical_history"
    ),


    # =========================================================
    # PATIENT DASHBOARD
    # =========================================================

    path(
        "patient-dashboard/",
        views.patient_dashboard,
        name="patient_dashboard"
    ),

    path(
        "patient/edit-profile/",
        views.edit_profile,
        name="edit_profile"
    ),

    path(
        "patient/cancel-appointment/<int:appointment_id>/",
        views.cancel_appointment,
        name="cancel_appointment"
    ),

    path(
        "patient/appointment/<int:appointment_id>/",
        views.appointment_detail,
        name="appointment_detail"
    ),


    # =========================================================
    # PATIENT BILLS & PAYMENTS
    # =========================================================

    path(
        "patient/bill/<int:bill_id>/",
        views.view_bill,
        name="view_bill"
    ),

    path(
        "patient/bill/<int:bill_id>/pay-online/",
        views.initiate_payment,
        name="initiate_payment"
    ),

    path(
        "patient/bill/<int:bill_id>/cash/",
        views.cash_payment,
        name="cash_payment"
    ),

    path(
        "patient/payment/success/",
        views.payment_success,
        name="payment_success"
    ),

    path(
        "patient/pay-direct/<int:bill_id>/",
        views.process_direct_payment,
        name="process_direct_payment"
    ),

    path(
        "patient/pay-appointment/<int:appointment_id>/",
        views.pay_appointment_fee,
        name="pay_appointment_fee"
    ),

    path(
        "patient/payment/receipt/<int:payment_id>/",
        views.payment_receipt,
        name="payment_receipt"
    ),


    # =========================================================
    # NOTIFICATIONS
    # =========================================================

    path(
        "patient/notifications/",
        views.notifications,
        name="notifications"
    ),

    path(
        "patient/notifications/<int:notif_id>/read/",
        views.mark_notification_read,
        name="mark_notification_read"
    ),


    # =========================================================
    # TEST REPORTS
    # =========================================================

    path(
        "patient/test-reports/",
        views.patient_test_reports,
        name="patient_test_reports"
    ),


    # =========================================================
    # BOOK APPOINTMENT
    # =========================================================

    path(
        "book-appointment/",
        views.book_appointment,
        name="book_appointment"
    ),


    # =========================================================
    # AJAX
    # =========================================================

    path(
        "ajax/slots/",
        views.get_available_slots,
        name="get_available_slots"
    ),

    path(
        "ajax/doctors/",
        views.get_doctors_by_dept,
        name="get_doctors_by_dept"
    ),
]


# =========================================================
# MEDIA FILES
# =========================================================

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)