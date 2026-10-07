import json
import logging
from datetime import date as date_type

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.db.models import Q, Sum, Count
from django.conf import settings
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from main.models import (
    Doctor, Patient, Appointment, MedicalRecord,
    Prescription, OTPVerification, Department,
    Bill, Payment, TestReport, Notification
)
from main.services import (
    email_service, otp_service, payment_service,
    notification_service, appointment_service
)

logger = logging.getLogger(__name__)


# =========================================================
# HELPERS
# =========================================================

def get_patient_or_redirect(request):
    patient = Patient.objects.filter(user=request.user).first()
    if not patient:
        messages.error(request, "Patient profile not found.")
        return None
    return patient


def get_doctor_or_redirect(request):
    doctor = Doctor.objects.filter(user=request.user).first()
    if not doctor:
        messages.error(request, "Doctor profile not found.")
        return None
    return doctor


# =========================================================
# PUBLIC PAGES
# =========================================================

def home(request):
    departments = Department.objects.filter(is_active=True)[:8]
    doctors = Doctor.objects.filter(available=True).select_related('department')[:6]
    stats = {
        'patients': Patient.objects.count(),
        'doctors': Doctor.objects.count(),
        'departments': Department.objects.filter(is_active=True).count(),
        'appointments': Appointment.objects.count(),
    }
    return render(request, "index.html", {
        "departments": departments,
        "doctors": doctors,
        "stats": stats,
    })


def about(request):
    doctors = Doctor.objects.filter(available=True).select_related('department')[:4]
    return render(request, "about.html", {"doctors": doctors})


def departments_page(request):
    departments = Department.objects.filter(is_active=True).prefetch_related('doctors')
    return render(request, "departments.html", {"departments": departments})


def our_doctors(request):
    dept_id = request.GET.get('dept')
    doctors = Doctor.objects.filter(available=True).select_related('department')
    departments = Department.objects.filter(is_active=True)
    if dept_id:
        doctors = doctors.filter(department_id=dept_id)
    return render(request, "our_doctors.html", {
        "doctors": doctors,
        "departments": departments,
        "selected_dept": dept_id,
    })


def services(request):
    departments = Department.objects.filter(is_active=True)
    return render(request, "services.html", {"departments": departments})


def emergency(request):
    return render(request, "emergency.html")


def contact(request):
    if request.method == "POST":
        messages.success(request, "Your message has been received. We will contact you soon.")
        return redirect("contact")
    return render(request, "contact.html")


from django.views.decorators.csrf import ensure_csrf_cookie

# =========================================================
# LOGIN
# =========================================================

@ensure_csrf_cookie
def login_page(request):

    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == "POST":

        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        role = request.POST.get("role", "").strip().lower()

        if not email or not password or not role:

            messages.error(
                request,
                "Please enter Gmail, password and select your role."
            )

            return render(request, "login.html")

        user = None

        # =====================================================
        # LOGIN USING EMAIL
        # =====================================================

        users = User.objects.filter(
            email__iexact=email
        )

        for user_obj in users:

            authenticated_user = authenticate(
                request,
                username=user_obj.username,
                password=password
            )

            if authenticated_user is not None:

                user = authenticated_user
                break

        # =====================================================
        # FALLBACK - USERNAME
        # =====================================================

        if user is None:

            user = authenticate(
                request,
                username=email,
                password=password
            )

        # =====================================================
        # INVALID LOGIN
        # =====================================================

        if user is None:

            messages.error(
                request,
                "Invalid Gmail/email or password."
            )

            return render(
                request,
                "login.html"
            )

        # =====================================================
        # ADMIN
        # =====================================================

        if role == "admin":

            if user.is_staff or user.is_superuser:

                login(request, user)

                return redirect(
                    "admin_dashboard"
                )

            messages.error(
                request,
                "This account does not have Admin access."
            )

            return render(
                request,
                "login.html"
            )

        # =====================================================
        # DOCTOR
        # =====================================================

        if role == "doctor":

            doctor = Doctor.objects.filter(
                user=user
            ).first()

            if doctor:

                login(request, user)

                return redirect(
                    "doctor_dashboard"
                )

            messages.error(
                request,
                "Doctor profile is not linked with this Gmail."
            )

            return render(
                request,
                "login.html"
            )

        # =====================================================
        # PATIENT
        # =====================================================

        if role == "patient":

            patient = Patient.objects.filter(
                user=user
            ).first()

            if patient:

                login(request, user)

                return redirect(
                    "patient_dashboard"
                )

            messages.error(
                request,
                "Patient profile is not linked with this Gmail."
            )

            return render(
                request,
                "login.html"
            )

        # =====================================================
        # INVALID ROLE
        # =====================================================

        messages.error(
            request,
            "Invalid role selected."
        )

        return render(
            request,
            "login.html"
        )

    # On GET request, clear out any stale non-login messages (e.g. "deleted successfully") from previous admin actions
    storage = messages.get_messages(request)
    valid_msgs = []
    for msg in storage:
        msg_text = str(msg.message).lower()
        if "deleted" not in msg_text and "profile not found" not in msg_text:
            valid_msgs.append(msg)
    
    # Re-add relevant messages if any
    for msg in valid_msgs:
        messages.add_message(request, msg.level, msg.message, extra_tags=msg.tags)

    return render(
        request,
        "login.html"
    )


# =========================================================
# REDIRECT BY ROLE
# =========================================================

def _redirect_by_role(user):

    if user.is_staff or user.is_superuser:

        return redirect(
            "admin_dashboard"
        )

    if Doctor.objects.filter(
        user=user
    ).exists():

        return redirect(
            "doctor_dashboard"
        )

    if Patient.objects.filter(
        user=user
    ).exists():

        return redirect(
            "patient_dashboard"
        )

    return redirect(
        "home"
    )


# =========================================================
# PATIENT REGISTRATION - SINGLE PAGE OTP
# =========================================================

def patient_register(request):
    """
    Single-page patient registration with OTP verification.

    Actions:
    - send_otp / resend_otp: validate details and send Gmail OTP
    - verify_otp: verify OTP on the same page
    - register: create User + Patient after OTP verification
    """

    def context(extra=None):
        curr_session = request.session.get("registration_data", {})
        data = dict(curr_session)
        if extra:
            data.update(extra)
        
        is_verified = (
            request.session.get("registration_otp_verified", False) or
            request.session.get("email_verified", False)
        )
        is_sent = request.session.get("registration_otp_sent", False) and not is_verified

        clean_data = dict(data)

        ctx = {
            "name": clean_data.get("name", ""),
            "email": clean_data.get("email", ""),
            "phone": clean_data.get("phone", ""),
            "age": clean_data.get("age", ""),
            "gender": clean_data.get("gender", ""),
            "blood_group": clean_data.get("blood_group", ""),
            "address": clean_data.get("address", ""),
            "otp_verified": is_verified,
            "email_verified": is_verified,
            "otp_sent": is_sent,
            "registration_data": clean_data,
        }
        return ctx

    if request.method == "POST":

        action = request.POST.get("action", "").strip().lower()

        # -----------------------------------------------------
        # COMMON FORM DATA
        # -----------------------------------------------------

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        age = request.POST.get("age", "").strip()
        gender = request.POST.get("gender", "").strip()
        blood_group = request.POST.get("blood_group", "").strip()
        address = request.POST.get("address", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        # Persist posted values into session registration_data
        curr_data = request.session.get("registration_data", {})
        if name: curr_data["name"] = name
        if email: curr_data["email"] = email
        if phone: curr_data["phone"] = phone
        if age: curr_data["age"] = age
        if gender: curr_data["gender"] = gender
        if blood_group: curr_data["blood_group"] = blood_group
        if address: curr_data["address"] = address
        if password: curr_data["password"] = password
        request.session["registration_data"] = curr_data

        # -----------------------------------------------------
        # SEND / RESEND OTP
        # -----------------------------------------------------

        if action in ["send_otp", "resend_otp"]:

            if not email:
                messages.error(
                    request,
                    "Please enter your Gmail address."
                )
                return render(request, "register.html", context({
                    "name": name,
                    "email": email,
                }))

            if not email.endswith("@gmail.com"):
                messages.error(
                    request,
                    "Please enter a valid Gmail address."
                )
                return render(request, "register.html", context({
                    "name": name,
                    "email": email,
                }))

            if User.objects.filter(email__iexact=email).exists():
                messages.error(
                    request,
                    "An account with this Gmail already exists."
                )
                return render(request, "register.html", context({
                    "name": name,
                    "email": email,
                }))

            if Patient.objects.filter(email__iexact=email).exists():
                messages.error(
                    request,
                    "A patient with this Gmail already exists."
                )
                return render(request, "register.html", context({
                    "name": name,
                    "email": email,
                }))

            # Save registration data in session until registration finishes.
            request.session["registration_data"] = {
                "name": name,
                "email": email,
                "phone": phone,
                "age": age,
                "gender": gender,
                "blood_group": blood_group,
                "address": address,
                "password": password,
            }

            try:
                otp = otp_service.create_otp_record(email)
                success, mode = otp_service.send_otp(
                    email,
                    name,
                    otp
                )

                if not success:
                    messages.error(
                        request,
                        "Unable to send OTP. Please check your email configuration."
                    )
                    return render(
                        request,
                        "register.html",
                        context()
                    )

                request.session["registration_otp_sent"] = True
                request.session["registration_otp_verified"] = False
                request.session["email_verified"] = False

                if mode == "dev_mode":
                    messages.info(
                        request,
                        f"OTP generated in DEV MODE ({otp}). Check server console."
                    )
                else:
                    msg_txt = "New OTP sent to your Gmail. Enter it below." if action == "resend_otp" else "OTP has been sent to your Gmail. Enter it below to verify."
                    messages.success(
                        request,
                        msg_txt
                    )

            except Exception as e:
                logger.error(f"OTP send error: {e}")
                messages.error(
                    request,
                    "Unable to send OTP. Please try again."
                )

            return render(
                request,
                "register.html",
                context()
            )

        # -----------------------------------------------------
        # VERIFY OTP
        # -----------------------------------------------------

        if action == "verify_otp":

            reg = request.session.get("registration_data")

            if not reg:
                messages.error(
                    request,
                    "Registration session expired. Please enter Gmail again."
                )
                return redirect("patient_register")

            entered_otp = request.POST.get("otp", "").strip()

            if not entered_otp:
                messages.error(
                    request,
                    "Please enter the OTP."
                )
                return render(
                    request,
                    "register.html",
                    context()
                )

            try:
                success, msg = otp_service.verify_otp(
                    reg.get("email"),
                    entered_otp
                )

                if success:
                    request.session["registration_otp_verified"] = True
                    request.session["email_verified"] = True
                    request.session["registration_otp_sent"] = False
                    messages.success(
                        request,
                        "Gmail verified successfully!"
                    )
                else:
                    request.session["registration_otp_verified"] = False
                    request.session["email_verified"] = False
                    messages.error(
                        request,
                        msg
                    )

            except Exception as e:
                logger.error(f"OTP verification error: {e}")
                request.session["registration_otp_verified"] = False
                request.session["email_verified"] = False
                messages.error(
                    request,
                    "OTP verification failed. Please try again."
                )

            return render(
                request,
                "register.html",
                context()
            )

        # -----------------------------------------------------
        # REGISTER PATIENT
        # -----------------------------------------------------

        if action == "register":

            reg = request.session.get("registration_data")

            if not reg:
                messages.error(
                    request,
                    "Registration session expired. Please start again."
                )
                return redirect("patient_register")

            is_verified = (
                request.session.get("registration_otp_verified", False) or
                request.session.get("email_verified", False)
            )

            if not is_verified:
                messages.error(
                    request,
                    "Please verify your Gmail OTP before registration."
                )
                return render(
                    request,
                    "register.html",
                    context()
                )

            # Use the latest form values for non-email fields.
            name = name or reg.get("name", "")
            email = email or reg.get("email", "")
            phone = phone or reg.get("phone", "")
            age = age or str(reg.get("age", ""))
            gender = gender or reg.get("gender", "")
            blood_group = blood_group or reg.get("blood_group", "")
            address = address or reg.get("address", "")

            if not all([
                name,
                email,
                phone,
                age,
                gender,
                address,
                password,
                confirm_password
            ]):
                messages.error(
                    request,
                    "Please fill all required fields."
                )
                return render(
                    request,
                    "register.html",
                    context()
                )

            if password != confirm_password:
                messages.error(
                    request,
                    "Passwords do not match."
                )
                return render(
                    request,
                    "register.html",
                    context()
                )

            if len(password) < 8:
                messages.error(
                    request,
                    "Password must be at least 8 characters."
                )
                return render(
                    request,
                    "register.html",
                    context()
                )

            try:
                age_int = int(age)
            except (ValueError, TypeError):
                messages.error(
                    request,
                    "Please enter a valid age."
                )
                return render(
                    request,
                    "register.html",
                    context()
                )

            if not 1 <= age_int <= 120:
                messages.error(
                    request,
                    "Age must be between 1 and 120."
                )
                return render(
                    request,
                    "register.html",
                    context()
                )

            if User.objects.filter(email__iexact=email).exists():
                messages.error(
                    request,
                    "An account with this Gmail already exists."
                )
                return render(
                    request,
                    "register.html",
                    context()
                )

            if Patient.objects.filter(email__iexact=email).exists():
                messages.error(
                    request,
                    "A patient with this Gmail already exists."
                )
                return render(
                    request,
                    "register.html",
                    context()
                )

            if Patient.objects.filter(phone=phone).exists():
                messages.error(
                    request,
                    "An account with this mobile number already exists."
                )
                return render(
                    request,
                    "register.html",
                    context()
                )

            try:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password
                )

                Patient.objects.create(
                    user=user,
                    name=name,
                    email=email,
                    phone=phone,
                    age=age_int,
                    gender=gender,
                    address=address,
                    blood_group=blood_group
                )

                request.session.pop("registration_data", None)
                request.session.pop("registration_otp_sent", None)
                request.session.pop("registration_otp_verified", None)
                request.session.pop("email_verified", None)

                messages.success(
                    request,
                    "Registration successful! Please login."
                )

                return redirect("login")

            except Exception as e:
                logger.error(f"Registration error: {e}")
                messages.error(
                    request,
                    "Registration failed. Please try again."
                )
                return render(
                    request,
                    "register.html",
                    context()
                )

        messages.error(
            request,
            "Invalid registration action."
        )
        return render(
            request,
            "register.html",
            context()
        )

    # GET
    request.session.pop("registration_otp_sent", None)
    request.session.pop("registration_otp_verified", None)
    request.session.pop("email_verified", None)
    return render(
        request,
        "register.html",
        context()
    )


# =========================================================
# VERIFY OTP - COMPATIBILITY ROUTE
# =========================================================

def verify_otp(request):
    """
    Kept for compatibility with an old verify-otp URL.
    The new registration page verifies OTP directly through
    patient_register().
    """

    if request.method == "POST":
        request.POST = request.POST.copy()
        request.POST["action"] = "verify_otp"
        return patient_register(request)

    reg = request.session.get("registration_data")

    if not reg:
        messages.error(
            request,
            "Registration session expired. Please register again."
        )
        return redirect("patient_register")

    return render(
        request,
        "register.html",
        {
            **reg,
            "otp_sent": request.session.get(
                "registration_otp_sent",
                False
            ),
            "otp_verified": request.session.get(
                "registration_otp_verified",
                False
            ),
        }
    )


# =========================================================
# RESEND OTP
# =========================================================

def resend_otp(request):

    reg = request.session.get("registration_data")

    if not reg:
        messages.error(
            request,
            "Registration session expired."
        )
        return redirect("patient_register")

    email = reg.get("email")
    name = reg.get("name")

    try:
        otp = otp_service.create_otp_record(email)
        success, mode = otp_service.send_otp(
            email,
            name,
            otp
        )

        if success:

            request.session["registration_otp_sent"] = True
            request.session["registration_otp_verified"] = False

            if mode == "dev_mode":
                messages.info(
                    request,
                    "New OTP generated in DEV MODE. Check the server console."
                )
            else:
                messages.success(
                    request,
                    "New OTP sent to your Gmail."
                )

        else:
            messages.error(
                request,
                "Unable to send OTP."
            )

    except Exception as e:
        logger.error(f"Resend OTP error: {e}")
        messages.error(
            request,
            "Unable to send OTP."
        )

    return redirect("patient_register")


# =========================================================
# LOGOUT
# =========================================================

def logout_user(request):
    logout(request)
    return redirect("home")


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@login_required
def admin_dashboard(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect("login")

    today = timezone.localdate()

    # Search & Filter Parameters
    patient_q = request.GET.get('patient_q', '').strip()
    doctor_q = request.GET.get('doctor_q', '').strip()
    doctor_avail = request.GET.get('doctor_avail', '').strip()
    apt_status = request.GET.get('apt_status', '').strip()
    apt_date = request.GET.get('apt_date', '').strip()

    # Doctors Queryset & Pagination
    doctors_qs = Doctor.objects.all().select_related('department').order_by('name')
    if doctor_q:
        doctors_qs = doctors_qs.filter(
            Q(name__icontains=doctor_q) |
            Q(email__icontains=doctor_q) |
            Q(specialization__icontains=doctor_q) |
            Q(qualification__icontains=doctor_q)
        )
    if doctor_avail == 'true':
        doctors_qs = doctors_qs.filter(available=True)
    elif doctor_avail == 'false':
        doctors_qs = doctors_qs.filter(available=False)

    doctor_paginator = Paginator(doctors_qs, 5)
    doctor_page = request.GET.get('doctor_page', 1)
    doctors = doctor_paginator.get_page(doctor_page)

    # Patients Queryset & Pagination
    patients_qs = Patient.objects.all().order_by('-created_at')
    if patient_q:
        patients_qs = patients_qs.filter(
            Q(name__icontains=patient_q) |
            Q(email__icontains=patient_q) |
            Q(phone__icontains=patient_q)
        )
    patient_paginator = Paginator(patients_qs, 5)
    patient_page = request.GET.get('patient_page', 1)
    patients = patient_paginator.get_page(patient_page)

    # Appointments Queryset & Pagination
    appointments_qs = Appointment.objects.all().select_related('patient', 'doctor', 'department').order_by('-appointment_date', '-appointment_time')
    if apt_status:
        appointments_qs = appointments_qs.filter(status=apt_status)
    if apt_date:
        appointments_qs = appointments_qs.filter(appointment_date=apt_date)
    apt_paginator = Paginator(appointments_qs, 5)
    apt_page = request.GET.get('apt_page', 1)
    appointments = apt_paginator.get_page(apt_page)

    departments = Department.objects.all()
    bills = Bill.objects.all().select_related('patient', 'appointment').order_by('-created_at')
    payments = Payment.objects.all().select_related('patient', 'bill', 'appointment', 'appointment__doctor').order_by('-created_at')
    today_payments = Payment.objects.filter(created_at__date=today).select_related('patient', 'bill', 'appointment', 'appointment__doctor').order_by('-created_at')

    # Department-wise today revenue breakdown for modal
    dept_revenue_list = []
    for dept in departments:
        today_dept_rev = Payment.objects.filter(
            payment_status='Paid',
            created_at__date=today,
            appointment__doctor__department=dept
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_dept_rev = Payment.objects.filter(
            payment_status='Paid',
            appointment__doctor__department=dept
        ).aggregate(total=Sum('amount'))['total'] or 0

        dept_revenue_list.append({
            'department': dept,
            'today_revenue': today_dept_rev,
            'total_revenue': total_dept_rev,
        })
    dept_revenue_list.sort(key=lambda x: x['today_revenue'], reverse=True)

    # Stats
    today_revenue = Payment.objects.filter(payment_status='Paid', created_at__date=today).aggregate(total=Sum('amount'))['total'] or 0
    today_online_revenue = Payment.objects.filter(payment_status='Paid', created_at__date=today).filter(Q(payment_method__icontains='Online') | Q(payment_method__icontains='UPI')).aggregate(total=Sum('amount'))['total'] or 0
    today_cash_revenue = Payment.objects.filter(payment_status='Paid', created_at__date=today, payment_method__icontains='Cash').aggregate(total=Sum('amount'))['total'] or 0
    
    total_revenue = Payment.objects.filter(payment_status='Paid').aggregate(total=Sum('amount'))['total'] or 0
    online_revenue = Payment.objects.filter(payment_status='Paid', payment_method='Online').aggregate(total=Sum('amount'))['total'] or 0
    cash_revenue = Payment.objects.filter(payment_status='Paid', payment_method='Cash').aggregate(total=Sum('amount'))['total'] or 0
    pending_payments = Payment.objects.filter(payment_status='Pending').count()

    available_doctors = Doctor.objects.filter(available=True).count()
    unavailable_doctors = Doctor.objects.filter(available=False).count()

    stats = {
        'total_patients': Patient.objects.count(),
        'total_doctors': Doctor.objects.count(),
        'available_doctors': available_doctors,
        'unavailable_doctors': unavailable_doctors,
        'total_departments': Department.objects.filter(is_active=True).count(),
        'total_appointments': Appointment.objects.count(),
        'today_appointments': Appointment.objects.filter(appointment_date=today).count(),
        'pending_appointments': Appointment.objects.filter(status='Pending').count(),
        'confirmed_appointments': Appointment.objects.filter(status='Confirmed').count(),
        'completed_appointments': Appointment.objects.filter(status='Completed').count(),
        'cancelled_appointments': Appointment.objects.filter(status='Cancelled').count(),
        'today_revenue': today_revenue,
        'today_online_revenue': today_online_revenue,
        'today_cash_revenue': today_cash_revenue,
        'total_revenue': total_revenue,
        'online_revenue': online_revenue,
        'cash_revenue': cash_revenue,
        'pending_payments': pending_payments,
    }

    return render(request, "admin.html", {
        "patients": patients,
        "doctors": doctors,
        "appointments": appointments,
        "departments": departments,
        "bills": bills,
        "payments": payments,
        "today_payments": today_payments,
        "dept_revenue_list": dept_revenue_list,
        "stats": stats,
        "today": today,
        "patient_q": patient_q,
        "doctor_q": doctor_q,
        "doctor_avail": doctor_avail,
        "apt_status": apt_status,
        "apt_date": apt_date,
    })


# =========================================================
# DETAILED DOCTORS LIST PAGE
# =========================================================

@login_required
def admin_doctors_list(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect("login")

    search_q = request.GET.get('q', '').strip()
    per_page_raw = request.GET.get('per_page', '10')
    dept_id = request.GET.get('department', '').strip()
    avail_filter = request.GET.get('available', '').strip()

    try:
        per_page = int(per_page_raw)
        if per_page not in [5, 10, 20, 50]:
            per_page = 10
    except ValueError:
        per_page = 10

    doctors_qs = Doctor.objects.all().select_related('department').order_by('name')

    if search_q:
        doctors_qs = doctors_qs.filter(
            Q(name__icontains=search_q) |
            Q(email__icontains=search_q) |
            Q(specialization__icontains=search_q) |
            Q(qualification__icontains=search_q) |
            Q(phone__icontains=search_q)
        )

    if dept_id:
        doctors_qs = doctors_qs.filter(department_id=dept_id)

    if avail_filter == 'true':
        doctors_qs = doctors_qs.filter(available=True)
    elif avail_filter == 'false':
        doctors_qs = doctors_qs.filter(available=False)

    paginator = Paginator(doctors_qs, per_page)
    page_number = request.GET.get('page', 1)
    doctors_page = paginator.get_page(page_number)

    departments = Department.objects.filter(is_active=True)

    return render(request, "admin_doctors_list.html", {
        "doctors": doctors_page,
        "search_q": search_q,
        "per_page": per_page,
        "dept_id": dept_id,
        "avail_filter": avail_filter,
        "departments": departments,
        "total_count": paginator.count,
    })


@login_required
def toggle_doctor_availability(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    
    # Permission check: Admin/Staff OR doctor editing their own availability
    is_admin = request.user.is_staff or request.user.is_superuser
    is_own_doctor = hasattr(request.user, 'doctor') and request.user.doctor.id == doctor.id

    if not is_admin and not is_own_doctor:
        messages.error(request, "Permission denied.")
        return redirect("login")

    doctor.available = not doctor.available
    doctor.save()

    status_str = "Available" if doctor.available else "Unavailable"
    messages.success(request, f"Status for Dr. {doctor.name} updated to '{status_str}'.")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'available': doctor.available,
            'status_str': status_str,
            'message': f"Status for Dr. {doctor.name} updated to '{status_str}'."
        })

    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER')
    if next_url and "/login" not in next_url and "/toggle-doctor-availability" not in next_url:
        return redirect(next_url)
    
    if hasattr(request.user, 'doctor') and not is_admin:
        return redirect("doctor_dashboard")
        
    return redirect("admin_doctors_list")


# =========================================================
# DETAILED PATIENTS LIST PAGE
# =========================================================

@login_required
def admin_patients_list(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect("login")

    search_q = request.GET.get('q', '').strip()
    per_page_raw = request.GET.get('per_page', '10')

    try:
        per_page = int(per_page_raw)
        if per_page not in [5, 10, 20, 50]:
            per_page = 10
    except ValueError:
        per_page = 10

    patients_qs = Patient.objects.all().order_by('-created_at')

    if search_q:
        patients_qs = patients_qs.filter(
            Q(name__icontains=search_q) |
            Q(email__icontains=search_q) |
            Q(phone__icontains=search_q) |
            Q(blood_group__icontains=search_q)
        )

    paginator = Paginator(patients_qs, per_page)
    page_number = request.GET.get('page', 1)
    patients_page = paginator.get_page(page_number)

    return render(request, "admin_patients_list.html", {
        "patients": patients_page,
        "search_q": search_q,
        "per_page": per_page,
        "total_count": paginator.count,
    })


# =========================================================
# DETAILED APPOINTMENTS LIST PAGE
# =========================================================

@login_required
def admin_appointments_list(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect("login")

    search_q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_filter = request.GET.get('date', '').strip()
    per_page_raw = request.GET.get('per_page', '10')

    try:
        per_page = int(per_page_raw)
        if per_page not in [5, 10, 20, 50]:
            per_page = 10
    except ValueError:
        per_page = 10

    appointments_qs = Appointment.objects.all().select_related('patient', 'doctor', 'department').order_by('-appointment_date', '-appointment_time')

    if search_q:
        appointments_qs = appointments_qs.filter(
            Q(patient__name__icontains=search_q) |
            Q(doctor__name__icontains=search_q) |
            Q(reason__icontains=search_q)
        )

    if status_filter:
        appointments_qs = appointments_qs.filter(status=status_filter)

    if date_filter:
        appointments_qs = appointments_qs.filter(appointment_date=date_filter)

    paginator = Paginator(appointments_qs, per_page)
    page_number = request.GET.get('page', 1)
    appointments_page = paginator.get_page(page_number)

    return render(request, "admin_appointments_list.html", {
        "appointments": appointments_page,
        "search_q": search_q,
        "status_filter": status_filter,
        "date_filter": date_filter,
        "per_page": per_page,
        "total_count": paginator.count,
    })


# =========================================================
# ADD DOCTOR
# =========================================================

@login_required
def add_doctor(request):
    if not request.user.is_staff:
        return redirect("login")

    departments = Department.objects.filter(is_active=True)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        specialization = request.POST.get("specialization", "").strip()
        qualification = request.POST.get("qualification", "").strip()
        experience = request.POST.get("experience", "0")
        consultation_fee = request.POST.get("consultation_fee", "0")
        password = request.POST.get("password", "")
        dept_id = request.POST.get("department")
        bio = request.POST.get("bio", "").strip()
        available_days = request.POST.get("available_days", "Mon-Sat")
        available_time_start = request.POST.get("available_time_start") or None
        available_time_end = request.POST.get("available_time_end") or None

        if not name or not email or not password:
            messages.error(request, "Name, Email and Password are required.")
            return render(request, "add_doctor.html", {"departments": departments})

        if User.objects.filter(email=email).exists() or Doctor.objects.filter(email=email).exists():
            messages.error(request, "A user with this email already exists.")
            return render(request, "add_doctor.html", {"departments": departments})

        try:
            experience = int(experience or 0)
        except ValueError:
            experience = 0

        dept = Department.objects.filter(id=dept_id).first() if dept_id else None

        user = User.objects.create_user(username=email, email=email, password=password)

        doctor = Doctor(
            user=user, name=name, email=email, phone=phone,
            specialization=specialization, qualification=qualification,
            experience=experience, consultation_fee=consultation_fee or 0,
            department=dept, bio=bio, available=True,
            available_days=available_days,
        )
        if available_time_start:
            doctor.available_time_start = available_time_start
        if available_time_end:
            doctor.available_time_end = available_time_end

        if request.FILES.get("profile_image"):
            doctor.profile_image = request.FILES["profile_image"]

        doctor.save()
        messages.success(request, f"Dr. {name} added successfully.")
        return redirect("admin_dashboard")

    return render(request, "add_doctor.html", {"departments": departments})


# =========================================================
# EDIT DOCTOR
# =========================================================

@login_required
def edit_doctor(request, doctor_id):
    if not request.user.is_staff:
        return redirect("login")

    doctor = get_object_or_404(Doctor, id=doctor_id)
    departments = Department.objects.filter(is_active=True)

    if request.method == "POST":
        doctor.name = request.POST.get("name", doctor.name).strip()
        doctor.phone = request.POST.get("phone", doctor.phone).strip()
        doctor.specialization = request.POST.get("specialization", doctor.specialization).strip()
        doctor.qualification = request.POST.get("qualification", doctor.qualification).strip()
        doctor.experience = int(request.POST.get("experience", doctor.experience) or 0)
        doctor.consultation_fee = request.POST.get("consultation_fee", doctor.consultation_fee) or 0
        doctor.bio = request.POST.get("bio", "").strip()
        doctor.available = request.POST.get("available") == "on"
        doctor.available_days = request.POST.get("available_days", doctor.available_days)
        dept_id = request.POST.get("department")
        doctor.department = Department.objects.filter(id=dept_id).first() if dept_id else doctor.department

        t_start = request.POST.get("available_time_start")
        t_end = request.POST.get("available_time_end")
        if t_start:
            doctor.available_time_start = t_start
        if t_end:
            doctor.available_time_end = t_end

        if request.FILES.get("profile_image"):
            doctor.profile_image = request.FILES["profile_image"]

        doctor.save()
        messages.success(request, f"Dr. {doctor.name} updated successfully.")
        
        next_url = request.POST.get("next_url")
        if next_url and "/edit-doctor/" not in next_url:
            return redirect(next_url)
        referer = request.META.get("HTTP_REFERER")
        if referer and "/edit-doctor/" not in referer and "/login" not in referer:
            return redirect(referer)
        return redirect("admin_doctors_list")

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER", "")
    if "/edit-doctor/" in next_url:
        next_url = ""

    return render(request, "edit_doctor.html", {
        "doctor": doctor,
        "departments": departments,
        "next_url": next_url
    })


# =========================================================
# DELETE DOCTOR
# =========================================================

@login_required
def delete_doctor(request, doctor_id):
    if not request.user.is_staff:
        return redirect("login")
    doctor = get_object_or_404(Doctor, id=doctor_id)
    doc_name = doctor.name
    user_obj = doctor.user

    doctor.delete()
    if user_obj:
        user_obj.delete()

    messages.success(request, f"Dr. {doc_name} deleted successfully.")

    referer = request.META.get("HTTP_REFERER")
    if referer and "/login" not in referer and "/delete-doctor" not in referer:
        return redirect(referer)
    return redirect("admin_doctors_list")


# =========================================================
# DELETE PATIENT
# =========================================================

@login_required
def delete_patient(request, patient_id):
    if not request.user.is_staff:
        return redirect("login")
    patient = get_object_or_404(Patient, id=patient_id)
    pat_name = patient.name
    user_obj = patient.user

    patient.delete()
    if user_obj:
        user_obj.delete()

    messages.success(request, f"Patient {pat_name} deleted successfully.")

    referer = request.META.get("HTTP_REFERER")
    if referer and "/login" not in referer and "/delete-patient" not in referer:
        return redirect(referer)
    return redirect("admin_patients_list")


# =========================================================
# DEPARTMENT MANAGEMENT
# =========================================================

@login_required
def manage_departments(request):
    if not request.user.is_staff:
        messages.error(request, "Admin access required.")
        return redirect("login")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        icon = request.POST.get("icon", "🏥").strip() or "🏥"
        
        if not name:
            messages.error(request, "Department name is required.")
        elif Department.objects.filter(name__iexact=name).exists():
            messages.error(request, f"Department '{name}' already exists.")
        else:
            Department.objects.create(name=name, description=description, icon=icon)
            messages.success(request, f"Department '{name}' created successfully as a Dynamic Field!")
        return redirect("manage_departments")

    search_q = request.GET.get("q", "").strip()
    depts_qs = Department.objects.all().annotate(doctor_count=Count('doctors')).order_by("name")

    if search_q:
        depts_qs = depts_qs.filter(
            Q(name__icontains=search_q) | Q(description__icontains=search_q)
        )

    stats = {
        'total_departments': Department.objects.count(),
        'active_departments': Department.objects.filter(is_active=True).count(),
        'total_linked_doctors': Doctor.objects.filter(department__isnull=False).count(),
    }

    return render(request, "manage_departments.html", {
        "departments": depts_qs,
        "search_q": search_q,
        "stats": stats,
    })


@login_required
def add_department(request):
    if not request.user.is_staff:
        messages.error(request, "Admin access required.")
        return redirect("login")
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        icon = request.POST.get("icon", "🏥").strip() or "🏥"
        if not name:
            messages.error(request, "Department name is required.")
            return render(request, "add_department.html")
        if Department.objects.filter(name__iexact=name).exists():
            messages.error(request, f"Department '{name}' already exists.")
            return render(request, "add_department.html")
        Department.objects.create(name=name, description=description, icon=icon)
        messages.success(request, f"Department '{name}' added successfully.")
        return redirect("manage_departments")
    return render(request, "add_department.html")


@login_required
def edit_department(request, dept_id):
    if not request.user.is_staff:
        messages.error(request, "Admin access required.")
        return redirect("login")
    dept = get_object_or_404(Department, id=dept_id)
    if request.method == "POST":
        dept.name = request.POST.get("name", dept.name).strip()
        dept.description = request.POST.get("description", "").strip()
        dept.icon = request.POST.get("icon", dept.icon).strip()
        dept.is_active = request.POST.get("is_active") == "on" or request.POST.get("is_active") == "true"
        dept.save()
        messages.success(request, f"Department '{dept.name}' updated successfully.")
        return redirect("manage_departments")
    return render(request, "edit_department.html", {"dept": dept})


@login_required
def toggle_department_status(request, dept_id):
    if not request.user.is_staff:
        messages.error(request, "Admin access required.")
        return redirect("login")
    dept = get_object_or_404(Department, id=dept_id)
    dept.is_active = not dept.is_active
    dept.save()
    status_str = "Active" if dept.is_active else "Inactive"
    messages.success(request, f"Department '{dept.name}' status set to {status_str}.")
    return redirect("manage_departments")


@login_required
def delete_department(request, dept_id):
    if not request.user.is_staff:
        messages.error(request, "Admin access required.")
        return redirect("login")
    dept = get_object_or_404(Department, id=dept_id)
    if request.method == "POST":
        name = dept.name
        dept.delete()
        messages.success(request, f"Department '{name}' deleted successfully.")
    return redirect("manage_departments")


# =========================================================
# BILL MANAGEMENT (ADMIN)
# =========================================================

@login_required
def manage_bills(request):
    if not request.user.is_staff:
        return redirect("login")
    bills = Bill.objects.all().select_related('patient', 'appointment').order_by('-created_at')
    return render(request, "manage_bills.html", {"bills": bills})


@login_required
def manage_payments(request):
    if not request.user.is_staff:
        return redirect("login")
    payments = Payment.objects.all().select_related('patient', 'bill').order_by('-created_at')
    return render(request, "manage_payments.html", {"payments": payments})


@login_required
def mark_cash_paid(request, payment_id):
    if not request.user.is_staff:
        return redirect("login")
    payment = get_object_or_404(Payment, id=payment_id)
    if request.method == "POST":
        received_by = request.POST.get("received_by", "Reception").strip() or "Reception"
        payment_service.mark_cash_received(payment, received_by)
        notification_service.notify_payment_success(payment)
        try:
            email_service.send_payment_confirmation_email(payment)
        except Exception as e:
            logger.error(f"Payment email error: {e}")
        messages.success(request, f"Cash payment marked as received for {payment.patient.name}.")
    return redirect("manage_payments")


# =========================================================
# DOCTOR DASHBOARD
# =========================================================

@login_required
def doctor_dashboard(request):
    doctor = get_doctor_or_redirect(request)
    if not doctor:
        return redirect("login")

    today = timezone.localdate()
    apt_status = request.GET.get('status', '')
    patient_q = request.GET.get('patient_q', '')

    appointments = Appointment.objects.filter(doctor=doctor).select_related(
        'patient', 'department'
    ).order_by('-appointment_date', '-appointment_time')

    if apt_status:
        appointments = appointments.filter(status=apt_status)
    if patient_q:
        appointments = appointments.filter(patient__name__icontains=patient_q)

    today_apts = Appointment.objects.filter(doctor=doctor, appointment_date=today)

    stats = {
        'total': Appointment.objects.filter(doctor=doctor).count(),
        'pending': Appointment.objects.filter(doctor=doctor, status='Pending').count(),
        'confirmed': Appointment.objects.filter(doctor=doctor, status='Confirmed').count(),
        'completed': Appointment.objects.filter(doctor=doctor, status='Completed').count(),
        'today': today_apts.count(),
    }

    return render(request, "doctor.html", {
        "doctor": doctor,
        "appointments": appointments,
        "today_appointments": today_apts,
        "stats": stats,
        "today": today,
        "apt_status": apt_status,
        "patient_q": patient_q,
    })

# =========================================================
# DOCTOR PROFILE CHANGE
# =========================================================

@login_required
def doctor_profile_change(request):

    doctor = get_doctor_or_redirect(request)

    if not doctor:
        return redirect("login")

    if request.method == "POST":

        # Basic information
        doctor.name = request.POST.get(
            "name",
            doctor.name
        ).strip()

        doctor.email = request.POST.get(
            "email",
            doctor.email
        ).strip().lower()

        doctor.phone = request.POST.get(
            "phone",
            doctor.phone
        ).strip()

        doctor.specialization = request.POST.get(
            "specialization",
            doctor.specialization
        ).strip()

        doctor.qualification = request.POST.get(
            "qualification",
            doctor.qualification
        ).strip()

        try:
            doctor.experience = int(
                request.POST.get(
                    "experience",
                    doctor.experience
                ) or 0
            )
        except (ValueError, TypeError):
            doctor.experience = 0

        # Profile Photo
        if request.FILES.get("profile_image"):
            doctor.profile_image = request.FILES["profile_image"]

        doctor.save()

        messages.success(
            request,
            "Doctor profile updated successfully."
        )

        return redirect("doctor_dashboard")

    return render(
        request,
        "profile_change.html",
        {
            "doctor": doctor
        }
    )

# =========================================================
# UPDATE APPOINTMENT STATUS (Doctor)
# =========================================================

@login_required
def update_appointment_status(request, appointment_id, status):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    doctor = get_doctor_or_redirect(request)

    if not doctor:
        return redirect("login")

    if appointment.doctor != doctor:
        messages.error(request, "You are not authorized to update this appointment.")
        return redirect("doctor_dashboard")

    valid_statuses = ["Pending", "Confirmed", "Rejected", "Completed", "Cancelled"]
    if status not in valid_statuses:
        messages.error(request, "Invalid status.")
        return redirect("doctor_dashboard")

    appointment.status = status
    appointment.save()

    # Notifications
    if status == 'Confirmed':
        notification_service.notify_appointment_confirmed(appointment)
    elif status == 'Rejected':
        notification_service.notify_appointment_rejected(appointment)
    elif status == 'Completed':
        notification_service.notify_appointment_completed(appointment)
    elif status == 'Cancelled':
        notification_service.notify_appointment_cancelled(appointment)

    # Email
    try:
        email_service.send_appointment_status_email(appointment)
    except Exception as e:
        logger.error(f"Status email error: {e}")

    messages.success(request, f"Appointment marked as {status}.")
    return redirect("doctor_dashboard")


# =========================================================
# ADD MEDICAL RECORD
# =========================================================

@login_required
def add_medical_record(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    doctor = get_doctor_or_redirect(request)

    if not doctor or appointment.doctor != doctor:
        messages.error(request, "Unauthorized.")
        return redirect("doctor_dashboard")

    if request.method == "POST":
        symptoms = request.POST.get("symptoms", "").strip()
        diagnosis = request.POST.get("diagnosis", "").strip()
        treatment = request.POST.get("treatment", "").strip()
        notes = request.POST.get("notes", "").strip()

        if not symptoms or not diagnosis:
            messages.error(request, "Symptoms and diagnosis are required.")
            return render(request, "medical_record.html", {"appointment": appointment})

        MedicalRecord.objects.create(
            patient=appointment.patient,
            doctor=doctor,
            appointment=appointment,
            symptoms=symptoms, diagnosis=diagnosis,
            treatment=treatment, notes=notes
        )
        messages.success(request, "Medical record added.")
        return redirect("doctor_dashboard")

    return render(request, "medical_record.html", {"appointment": appointment})


# =========================================================
# ADD PRESCRIPTION
# =========================================================

@login_required
def add_prescription(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    doctor = get_doctor_or_redirect(request)

    if not doctor or appointment.doctor != doctor:
        messages.error(request, "Unauthorized.")
        return redirect("doctor_dashboard")

    if request.method == "POST":
        med_names = request.POST.getlist("medicine_name")
        dosages = request.POST.getlist("dosage")
        freqs = request.POST.getlist("frequency")
        durations = request.POST.getlist("duration")

        diagnosis = request.POST.get("diagnosis", "").strip()
        instructions = request.POST.get("instructions", "").strip()
        follow_up_date = request.POST.get("follow_up_date") or None

        # Process multi-row inputs
        combined_meds = []
        combined_dosages = []
        combined_freqs = []
        combined_durations = []

        # If getlist returned empty or 1 item with newline, check single post fallback
        if not med_names:
            single_med = request.POST.get("medicine_name", "").strip()
            if single_med:
                med_names = [single_med]
                dosages = [request.POST.get("dosage", "").strip()]
                freqs = [request.POST.get("frequency", "Twice daily")]
                durations = [request.POST.get("duration", "").strip()]

        for i in range(len(med_names)):
            m = med_names[i].strip() if i < len(med_names) else ""
            d = dosages[i].strip() if i < len(dosages) else ""
            f = freqs[i].strip() if i < len(freqs) else ""
            dur = durations[i].strip() if i < len(durations) else ""

            if m:
                combined_meds.append(m)
                combined_dosages.append(d if d else "-")
                combined_freqs.append(f if f else "As directed")
                combined_durations.append(dur if dur else "-")

        if not combined_meds:
            messages.error(request, "Please add at least one medicine/tablet.")
            return render(request, "prescription.html", {
                "appointment": appointment,
                "freq_choices": Prescription.FREQUENCY_CHOICES,
            })

        if len(combined_meds) > 1:
            medicine_name_str = "\n".join([f"{idx+1}. {med}" for idx, med in enumerate(combined_meds)])
            dosage_str = "\n".join([f"{idx+1}. {dos}" for idx, dos in enumerate(combined_dosages)])
            frequency_str = "\n".join([f"{idx+1}. {frq}" for idx, frq in enumerate(combined_freqs)])
            duration_str = "\n".join([f"{idx+1}. {dur}" for idx, dur in enumerate(combined_durations)])
        else:
            medicine_name_str = combined_meds[0]
            dosage_str = combined_dosages[0]
            frequency_str = combined_freqs[0]
            duration_str = combined_durations[0]

        prescription = Prescription.objects.create(
            patient=appointment.patient,
            doctor=doctor,
            appointment=appointment,
            medicine_name=medicine_name_str,
            dosage=dosage_str,
            frequency=frequency_str,
            duration=duration_str,
            instructions=instructions,
            diagnosis=diagnosis,
            follow_up_date=follow_up_date
        )

        notification_service.notify_prescription_added(prescription)
        try:
            email_service.send_prescription_email(prescription)
        except Exception as e:
            logger.error(f"Prescription email error: {e}")

        messages.success(request, f"Prescription with {len(combined_meds)} medicine(s) saved successfully!")
        return redirect("doctor_dashboard")

    freq_choices = Prescription.FREQUENCY_CHOICES
    return render(request, "prescription.html", {
        "appointment": appointment,
        "freq_choices": freq_choices,
    })


# =========================================================
# UPLOAD TEST REPORT (Doctor/Admin)
# =========================================================

@login_required
def upload_test_report(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    doctor = get_doctor_or_redirect(request)

    if not doctor or appointment.doctor != doctor:
        messages.error(request, "Unauthorized.")
        return redirect("doctor_dashboard")

    if request.method == "POST":
        test_name = request.POST.get("test_name", "").strip()
        test_date = request.POST.get("test_date")
        report_details = request.POST.get("report_details", "").strip()
        status = request.POST.get("status", "Pending")

        if not test_name or not test_date:
            messages.error(request, "Test name and date are required.")
            return render(request, "upload_test_report.html", {"appointment": appointment})

        report = TestReport(
            patient=appointment.patient,
            doctor=doctor,
            appointment=appointment,
            test_name=test_name, test_date=test_date,
            report_details=report_details, status=status
        )
        if request.FILES.get("report_file"):
            report.report_file = request.FILES["report_file"]
        report.save()

        if status == 'Completed':
            notification_service.notify_test_report_available(report)
            try:
                email_service.send_test_report_email(report)
            except Exception as e:
                logger.error(f"Test report email error: {e}")

        messages.success(request, "Test report uploaded.")
        return redirect("doctor_dashboard")

    return render(request, "upload_test_report.html", {"appointment": appointment})


# =========================================================
# MEDICAL HISTORY (Doctor views patient)
# =========================================================

@login_required
def medical_history(request, patient_id):
    doctor = get_doctor_or_redirect(request)
    if not doctor:
        if request.user.is_staff or request.user.is_superuser:
            doctor = Doctor.objects.first()
        else:
            return redirect("login")

    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == "POST":
        action = request.POST.get("action", "")

        # Update general patient medical history text & blood group
        if action == "update_history" or "medical_history" in request.POST:
            history_text = request.POST.get("medical_history", "").strip()
            blood_group = request.POST.get("blood_group", "").strip()

            patient.medical_history = history_text
            if blood_group:
                patient.blood_group = blood_group
            patient.save()
            messages.success(request, f"Medical history for {patient.name} saved successfully!")
            return redirect("medical_history", patient_id=patient.id)

        # Add a new clinical encounter medical record
        elif action == "add_record":
            symptoms = request.POST.get("symptoms", "").strip()
            diagnosis = request.POST.get("diagnosis", "").strip()
            treatment = request.POST.get("treatment", "").strip()
            notes = request.POST.get("notes", "").strip()
            appointment_id = request.POST.get("appointment_id", "").strip()

            appointment = None
            if appointment_id:
                appointment = Appointment.objects.filter(id=appointment_id).first()

            if diagnosis or symptoms:
                MedicalRecord.objects.create(
                    patient=patient,
                    doctor=doctor,
                    appointment=appointment,
                    symptoms=symptoms,
                    diagnosis=diagnosis or "Clinical Evaluation",
                    treatment=treatment,
                    notes=notes
                )
                messages.success(request, f"New clinical medical record logged for {patient.name}!")
                return redirect("medical_history", patient_id=patient.id)
            else:
                messages.error(request, "Please enter at least Diagnosis or Symptoms to save a record.")

        # Delete a medical record entry
        elif action == "delete_record":
            record_id = request.POST.get("record_id")
            if record_id:
                rec = MedicalRecord.objects.filter(id=record_id, patient=patient).first()
                if rec:
                    rec.delete()
                    messages.success(request, "Medical record entry deleted successfully.")
                    return redirect("medical_history", patient_id=patient.id)

    medical_records = MedicalRecord.objects.filter(patient=patient).select_related('doctor', 'appointment').order_by('-created_at')
    prescriptions = Prescription.objects.filter(patient=patient).select_related('doctor', 'appointment').order_by('-created_at')
    appointments = Appointment.objects.filter(patient=patient).select_related('doctor', 'department').order_by('-appointment_date')

    return render(request, "medical_history.html", {
        "doctor": doctor,
        "patient": patient,
        "medical_records": medical_records,
        "prescriptions": prescriptions,
        "appointments": appointments,
    })


# =========================================================
# PATIENT DASHBOARD
# =========================================================

@login_required
def patient_dashboard(request):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    today = timezone.localdate()
    appointments = Appointment.objects.filter(patient=patient).select_related(
        'doctor', 'department'
    ).order_by('-appointment_date', '-appointment_time')

    medical_records = MedicalRecord.objects.filter(patient=patient).select_related('doctor').order_by('-created_at')
    prescriptions = Prescription.objects.filter(patient=patient).select_related('doctor').order_by('-created_at')
    test_reports = TestReport.objects.filter(patient=patient).select_related('doctor').order_by('-created_at')
    bills = Bill.objects.filter(patient=patient).select_related('appointment').order_by('-created_at')
    notifications = Notification.objects.filter(patient=patient).order_by('-created_at')[:10]
    unread_count = notification_service.get_unread_count(patient)

    upcoming = appointments.filter(
        appointment_date__gte=today
    ).exclude(status__in=['Cancelled', 'Rejected'])

    stats = {
        'total_appointments': appointments.count(),
        'upcoming': upcoming.count(),
        'prescriptions': prescriptions.count(),
        'test_reports': test_reports.count(),
        'pending_bills': bills.filter(payment_status='Pending').count(),
        'unread_notifications': unread_count,
    }

    payments = Payment.objects.filter(patient=patient).select_related('appointment__doctor', 'appointment__department', 'bill').order_by('-created_at')

    return render(request, "patient.html", {
        "patient": patient,
        "appointments": appointments,
        "medical_records": medical_records,
        "prescriptions": prescriptions,
        "test_reports": test_reports,
        "bills": bills,
        "payments": payments,
        "notifications": notifications,
        "stats": stats,
        "today": today,
        "unread_count": unread_count,
    })


# =========================================================
# EDIT PROFILE (Patient)
# =========================================================

@login_required
def edit_profile(request):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    if request.method == "POST":
        patient.name = request.POST.get("name", patient.name).strip()
        patient.phone = request.POST.get("phone", patient.phone).strip()
        patient.gender = request.POST.get("gender", patient.gender)
        patient.address = request.POST.get("address", patient.address).strip()
        patient.blood_group = request.POST.get("blood_group", patient.blood_group).strip()
        dob = request.POST.get("date_of_birth")
        if dob:
            patient.date_of_birth = dob
        if request.FILES.get("profile_image"):
            patient.profile_image = request.FILES["profile_image"]
        patient.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("patient_dashboard")

    return render(request, "edit_profile.html", {"patient": patient})


# =========================================================
# BOOK APPOINTMENT
# =========================================================

@login_required
def book_appointment(request):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    departments = Department.objects.filter(is_active=True)
    doctors = Doctor.objects.all().select_related('department')

    if request.method == "POST":
        doctor_id = request.POST.get("doctor")
        dept_id = request.POST.get("department")
        apt_date = request.POST.get("appointment_date")
        apt_time = request.POST.get("appointment_time")
        reason = request.POST.get("reason", "").strip()

        if not doctor_id or not apt_date or not apt_time:
            messages.error(request, "Doctor, date and time are required.")
            return render(request, "book_appointment.html", {
                "patient": patient, "departments": departments, "doctors": doctors
            })

        try:
            doctor = Doctor.objects.get(id=doctor_id, available=True)
        except Doctor.DoesNotExist:
            messages.error(request, "Selected doctor is not available.")
            return render(request, "book_appointment.html", {
                "patient": patient, "departments": departments, "doctors": doctors
            })

        # Validate date
        try:
            from datetime import datetime
            apt_date_obj = datetime.strptime(apt_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date.")
            return render(request, "book_appointment.html", {
                "patient": patient, "departments": departments, "doctors": doctors
            })

        if apt_date_obj < timezone.localdate():
            messages.error(request, "Cannot book appointment for a past date.")
            return render(request, "book_appointment.html", {
                "patient": patient, "departments": departments, "doctors": doctors
            })

        # Check slot availability
        if not appointment_service.is_slot_available(doctor, apt_date_obj, apt_time):
            messages.error(request, "This time slot is already booked. Please choose another.")
            return render(request, "book_appointment.html", {
                "patient": patient, "departments": departments, "doctors": doctors
            })

        # Check for duplicate patient appointment same day
        if Appointment.objects.filter(
            patient=patient, doctor=doctor,
            appointment_date=apt_date_obj
        ).exclude(status__in=['Cancelled', 'Rejected']).exists():
            messages.error(request, "You already have an appointment with this doctor on this date.")
            return render(request, "book_appointment.html", {
                "patient": patient, "departments": departments, "doctors": doctors
            })

        dept = Department.objects.filter(id=dept_id).first() if dept_id else doctor.department

        appointment = Appointment.objects.create(
            patient=patient, doctor=doctor, department=dept,
            appointment_date=apt_date_obj, appointment_time=apt_time,
            reason=reason, status="Pending"
        )

        # Generate bill
        try:
            bill = appointment_service.generate_bill_for_appointment(appointment)
            notification_service.notify_bill_generated(bill)
        except Exception as e:
            logger.error(f"Bill generation error: {e}")

        # Notify patient
        notification_service.notify_appointment_booked(appointment)

        # Email
        try:
            email_service.send_appointment_confirmation_email(appointment)
            messages.success(request, "Appointment booked! Confirmation email sent.")
        except Exception as e:
            logger.error(f"Appointment email error: {e}")
            messages.success(request, "Appointment booked successfully (confirmation email could not be sent).")

        return redirect("patient_dashboard")

    return render(request, "book_appointment.html", {
        "patient": patient,
        "departments": departments,
        "doctors": doctors,
        "today": timezone.localdate().isoformat(),
    })


# =========================================================
# AJAX: GET AVAILABLE SLOTS
# =========================================================

def get_available_slots(request):
    doctor_id = request.GET.get('doctor_id')
    date_str = request.GET.get('date')

    if not doctor_id or not date_str:
        return JsonResponse({'slots': []})

    try:
        from datetime import datetime
        doctor = Doctor.objects.get(id=doctor_id, available=True)
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        slots = appointment_service.get_available_slots(doctor, date_obj)
        slot_list = [s.strftime('%H:%M') for s in slots]
        return JsonResponse({'slots': slot_list})
    except Exception as e:
        logger.error(f"Slot fetch error: {e}")
        return JsonResponse({'slots': [], 'error': str(e)})


# =========================================================
# AJAX: GET DOCTORS BY DEPARTMENT
# =========================================================

def get_doctors_by_dept(request):
    dept_id = request.GET.get('dept_id')
    if not dept_id:
        doctors = Doctor.objects.filter(available=True).values('id', 'name', 'specialization', 'consultation_fee')
    else:
        doctors = Doctor.objects.filter(available=True, department_id=dept_id).values('id', 'name', 'specialization', 'consultation_fee')
    return JsonResponse({'doctors': list(doctors)})


# =========================================================
# CANCEL APPOINTMENT (Patient)
# =========================================================

@login_required
def cancel_appointment(request, appointment_id):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    appointment = get_object_or_404(Appointment, id=appointment_id, patient=patient)

    if appointment.status in ['Completed', 'Cancelled']:
        messages.error(request, "Cannot cancel this appointment.")
        return redirect("patient_dashboard")

    if request.method == "POST":
        appointment.status = 'Cancelled'
        appointment.save()
        notification_service.notify_appointment_cancelled(appointment)
        try:
            email_service.send_appointment_status_email(appointment)
        except Exception as e:
            logger.error(f"Cancel email error: {e}")
        messages.success(request, "Appointment cancelled.")

    return redirect("patient_dashboard")


# =========================================================
# APPOINTMENT DETAIL (Patient)
# =========================================================

@login_required
def appointment_detail(request, appointment_id):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    appointment = get_object_or_404(Appointment, id=appointment_id, patient=patient)
    bill = getattr(appointment, 'bill', None)
    prescriptions = Prescription.objects.filter(appointment=appointment)
    test_reports = TestReport.objects.filter(appointment=appointment)
    medical_record = getattr(appointment, 'medical_record', None)

    return render(request, "appointment_detail.html", {
        "appointment": appointment,
        "bill": bill,
        "prescriptions": prescriptions,
        "test_reports": test_reports,
        "medical_record": medical_record,
    })


# =========================================================
# VIEW BILL (Patient)
# =========================================================

@login_required
def view_bill(request, bill_id):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    bill = get_object_or_404(Bill, id=bill_id, patient=patient)
    payment = getattr(bill, 'payment', None)
    razorpay_key = settings.RAZORPAY_KEY_ID
    razorpay_configured = payment_service.is_razorpay_configured()

    return render(request, "view_bill.html", {
        "bill": bill,
        "payment": payment,
        "razorpay_key": razorpay_key,
        "razorpay_configured": razorpay_configured,
    })


# =========================================================
# INITIATE ONLINE PAYMENT (Razorpay)
# =========================================================

@login_required
def initiate_payment(request, bill_id):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    bill = get_object_or_404(Bill, id=bill_id, patient=patient)

    if bill.payment_status == 'Paid':
        messages.info(request, "This bill is already paid.")
        return redirect("view_bill", bill_id=bill_id)

    if not payment_service.is_razorpay_configured():
        messages.error(request, "Online payment is not configured. Please pay at the hospital reception or contact admin.")
        return redirect("view_bill", bill_id=bill_id)

    order, error = payment_service.create_razorpay_order(bill.total_amount, bill.bill_number)

    if error:
        messages.error(request, f"Could not create payment order: {error}")
        return redirect("view_bill", bill_id=bill_id)

    # Create/update payment record
    payment, _ = Payment.objects.get_or_create(
        bill=bill,
        defaults={
            'patient': patient,
            'appointment': bill.appointment,
            'amount': bill.total_amount,
            'payment_method': 'Online',
            'payment_status': 'Processing',
        }
    )
    payment.razorpay_order_id = order['id']
    payment.payment_method = 'Online'
    payment.payment_status = 'Processing'
    payment.save()

    return render(request, "pay_bill.html", {
        "bill": bill,
        "payment": payment,
        "order": order,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "patient": patient,
    })


# =========================================================
# PAYMENT SUCCESS (Razorpay callback)
# =========================================================

@login_required
def payment_success(request):
    if request.method == "POST":
        razorpay_order_id = request.POST.get("razorpay_order_id", "")
        razorpay_payment_id = request.POST.get("razorpay_payment_id", "")
        razorpay_signature = request.POST.get("razorpay_signature", "")

        # Verify signature
        if not payment_service.verify_razorpay_payment(
            razorpay_order_id, razorpay_payment_id, razorpay_signature
        ):
            messages.error(request, "Payment verification failed. Please contact support.")
            return redirect("patient_dashboard")

        # Update payment
        payment = Payment.objects.filter(razorpay_order_id=razorpay_order_id).first()
        if not payment:
            messages.error(request, "Payment record not found.")
            return redirect("patient_dashboard")

        payment_service.mark_payment_success(
            payment, razorpay_payment_id, razorpay_order_id, razorpay_signature
        )

        notification_service.notify_payment_success(payment)
        try:
            email_service.send_payment_confirmation_email(payment)
        except Exception as e:
            logger.error(f"Payment email error: {e}")

        messages.success(request, "Payment successful!")
        return redirect("payment_receipt", payment_id=payment.id)

    return redirect("patient_dashboard")


# =========================================================
# CASH PAYMENT SELECTION
# =========================================================

@login_required
def cash_payment(request, bill_id):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    bill = get_object_or_404(Bill, id=bill_id, patient=patient)

    if bill.payment_status == 'Paid':
        messages.info(request, "This bill is already paid.")
        return redirect("view_bill", bill_id=bill_id)

    if request.method == "POST":
        payment, created = Payment.objects.get_or_create(
            bill=bill,
            defaults={
                'patient': patient,
                'appointment': bill.appointment,
                'amount': bill.total_amount,
                'payment_method': 'Cash',
                'payment_status': 'Pending',
            }
        )
        if not created:
            payment.payment_method = 'Cash'
            payment.payment_status = 'Pending'
            payment.save()
            bill.payment_status = 'Pending'
            bill.save()

        messages.success(request, "Cash payment registered. Please pay at Patil Hospital reception.")
        return redirect("patient_dashboard")

    return render(request, "cash_payment.html", {"bill": bill})


# =========================================================
# PAYMENT RECEIPT
# =========================================================

@login_required
def payment_receipt(request, payment_id):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    payment = get_object_or_404(Payment, id=payment_id, patient=patient)

    return render(request, "payment_receipt.html", {
        "payment": payment,
        "bill": payment.bill,
        "appointment": payment.appointment,
        "patient": patient,
    })


@login_required
def process_direct_payment(request, bill_id):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    bill = get_object_or_404(Bill, id=bill_id, patient=patient)

    if request.method == "POST":
        payment_method_input = request.POST.get("payment_method", "UPI")
        upi_id_used = request.POST.get("upi_id", "9022328691@superyes").strip() or "9022328691@superyes"
        import uuid
        receipt_no = f"PAY-{uuid.uuid4().hex[:8].upper()}"

        if payment_method_input == "UPI":
            display_method = f"UPI ({upi_id_used})"
        elif payment_method_input == "Card":
            display_method = "Card Payment"
        elif payment_method_input == "NetBanking":
            display_method = "Net Banking"
        else:
            display_method = "Cash"

        payment, created = Payment.objects.get_or_create(
            bill=bill,
            defaults={
                'patient': patient,
                'appointment': bill.appointment,
                'amount': bill.total_amount,
                'payment_method': display_method,
                'payment_status': 'Paid',
                'receipt_number': receipt_no,
                'payment_date': timezone.now(),
            }
        )

        payment.payment_status = 'Paid'
        payment.payment_method = display_method
        payment.receipt_number = receipt_no
        payment.payment_date = timezone.now()
        payment.save()

        bill.payment_status = 'Paid'
        bill.paid_amount = bill.total_amount
        bill.save()

        if bill.appointment and bill.appointment.status == 'Pending':
            bill.appointment.status = 'Confirmed'
            bill.appointment.save()

        try:
            email_service.send_payment_confirmation_email(payment)
        except Exception as e:
            logger.error(f"Payment email error: {e}")

        doc_name = bill.appointment.doctor.name if bill.appointment and bill.appointment.doctor else "Doctor"
        messages.success(
            request, 
            f"🎉 Payment of ₹{bill.total_amount} for Dr. {doc_name} was successful via {payment_method_input}! Receipt No: {receipt_no} (Confirmation Email Sent)"
        )
        return redirect("patient_dashboard")

    return redirect("patient_dashboard")


@login_required
def pay_appointment_fee(request, appointment_id):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    appointment = get_object_or_404(Appointment, id=appointment_id, patient=patient)

    bill = getattr(appointment, 'bill', None)
    if not bill:
        fee = appointment.doctor.consultation_fee if appointment.doctor else 500
        import uuid
        bill = Bill.objects.create(
            patient=patient,
            appointment=appointment,
            bill_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
            total_amount=fee,
            paid_amount=0,
            payment_status='Pending'
        )

    return process_direct_payment(request, bill.id)


# =========================================================
# NOTIFICATIONS (Patient)
# =========================================================

@login_required
def notifications(request):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    all_notifications = Notification.objects.filter(patient=patient).order_by('-created_at')
    # Mark all as read
    all_notifications.update(is_read=True)

    return render(request, "notifications.html", {
        "patient": patient,
        "notifications": all_notifications,
    })


@login_required
def mark_notification_read(request, notif_id):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    notif = get_object_or_404(Notification, id=notif_id, patient=patient)
    notif.is_read = True
    notif.save()
    return redirect("notifications")


# =========================================================
# TEST REPORTS (Patient)
# =========================================================

@login_required
def patient_test_reports(request):
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect("login")

    reports = TestReport.objects.filter(patient=patient).select_related('doctor').order_by('-created_at')
    return render(request, "test_reports.html", {
        "patient": patient,
        "reports": reports,
    })


# =========================================================
# REVENUE & PAYMENT RECORDS (ADMIN)
# =========================================================

@login_required
def admin_revenue_records(request):
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Admin access required.")
        return redirect("login")

    today = timezone.localdate()

    # Department-wise Revenue Collection Breakdown
    departments = Department.objects.all().annotate(
        doctor_count=Count('doctors', distinct=True)
    )

    dept_revenue_list = []
    for dept in departments:
        total_dept_rev = Payment.objects.filter(
            payment_status='Paid',
            appointment__doctor__department=dept
        ).aggregate(total=Sum('amount'))['total'] or 0

        today_dept_rev = Payment.objects.filter(
            payment_status='Paid',
            created_at__date=today,
            appointment__doctor__department=dept
        ).aggregate(total=Sum('amount'))['total'] or 0

        dept_txns_count = Payment.objects.filter(
            payment_status='Paid',
            appointment__doctor__department=dept
        ).count()

        dept_revenue_list.append({
            'department': dept,
            'total_revenue': total_dept_rev,
            'today_revenue': today_dept_rev,
            'txns_count': dept_txns_count,
        })

    dept_revenue_list.sort(key=lambda x: x['total_revenue'], reverse=True)

    # Search & Filter for Payments
    search_q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    method_filter = request.GET.get('method', '').strip()
    dept_filter = request.GET.get('department', '').strip()

    payments_qs = Payment.objects.all().select_related('patient', 'bill', 'appointment', 'appointment__doctor', 'appointment__doctor__department').order_by('-created_at')

    if search_q:
        payments_qs = payments_qs.filter(
            Q(receipt_number__icontains=search_q) |
            Q(patient__name__icontains=search_q) |
            Q(patient__email__icontains=search_q) |
            Q(appointment__doctor__name__icontains=search_q)
        )
    if status_filter:
        payments_qs = payments_qs.filter(payment_status=status_filter)
    if method_filter:
        payments_qs = payments_qs.filter(payment_method__icontains=method_filter)
    if dept_filter:
        payments_qs = payments_qs.filter(appointment__doctor__department_id=dept_filter)

    paginator = Paginator(payments_qs, 10)
    page = request.GET.get('page', 1)
    payments = paginator.get_page(page)

    today_revenue = Payment.objects.filter(payment_status='Paid', created_at__date=today).aggregate(total=Sum('amount'))['total'] or 0
    total_revenue = Payment.objects.filter(payment_status='Paid').aggregate(total=Sum('amount'))['total'] or 0
    online_revenue = Payment.objects.filter(payment_status='Paid').filter(Q(payment_method__icontains='Online') | Q(payment_method__icontains='UPI')).aggregate(total=Sum('amount'))['total'] or 0
    cash_revenue = Payment.objects.filter(payment_status='Paid', payment_method__icontains='Cash').aggregate(total=Sum('amount'))['total'] or 0

    stats = {
        'today_revenue': today_revenue,
        'total_revenue': total_revenue,
        'online_revenue': online_revenue,
        'cash_revenue': cash_revenue,
        'total_transactions': Payment.objects.count(),
        'paid_transactions': Payment.objects.filter(payment_status='Paid').count(),
    }

    return render(request, "admin_revenue.html", {
        "payments": payments,
        "dept_revenue_list": dept_revenue_list,
        "all_departments": departments,
        "stats": stats,
        "search_q": search_q,
        "status_filter": status_filter,
        "method_filter": method_filter,
        "dept_filter": dept_filter,
        "today": today,
    })
