"""
Management command to create demo data for Patil Hospital.
Usage: python manage.py create_demo_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main.models import Department, Doctor, Patient, Appointment
from datetime import date, time


DEMO_DEPARTMENTS = [
    {"name": "General Medicine", "icon": "fa-stethoscope", "description": "Comprehensive primary care and general health services."},
    {"name": "Cardiology", "icon": "fa-heart", "description": "Diagnosis and treatment of heart and cardiovascular conditions."},
    {"name": "Orthopedics", "icon": "fa-bone", "description": "Bone, joint, muscle and skeletal system care."},
    {"name": "Pediatrics", "icon": "fa-child", "description": "Healthcare for infants, children and adolescents."},
    {"name": "Dermatology", "icon": "fa-user-md", "description": "Skin, hair and nail conditions."},
    {"name": "Neurology", "icon": "fa-brain", "description": "Disorders of the nervous system."},
    {"name": "Gynecology", "icon": "fa-venus", "description": "Women's reproductive health."},
    {"name": "ENT", "icon": "fa-ear-listen", "description": "Ear, Nose and Throat specialist care."},
    {"name": "Dental", "icon": "fa-tooth", "description": "Comprehensive dental care and oral health."},
]


class Command(BaseCommand):
    help = "Create demo data for Patil Hospital (admin, doctor, patient)"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Creating Patil Hospital demo data..."))

        # ── Departments ──────────────────────────────────────────
        self.stdout.write("Creating departments...")
        dept_map = {}
        for d in DEMO_DEPARTMENTS:
            dept, created = Department.objects.get_or_create(
                name=d["name"],
                defaults={"icon": d["icon"], "description": d["description"], "is_active": True}
            )
            dept_map[d["name"]] = dept
            if created:
                self.stdout.write(f"  [+] Department: {d['name']}")

        # ── Admin ────────────────────────────────────────────────
        if not User.objects.filter(email="admin@patilhospital.com").exists():
            admin_user = User.objects.create_superuser(
                username="admin@patilhospital.com",
                email="admin@patilhospital.com",
                password="Admin@12345",
                first_name="Hospital",
                last_name="Admin"
            )
            self.stdout.write(self.style.SUCCESS("  [+] Admin: admin@patilhospital.com / Admin@12345"))
        else:
            admin_user = User.objects.filter(email="admin@patilhospital.com").first()
            self.stdout.write("  [-] Admin already exists")

        # ── Demo Doctors ─────────────────────────────────────────
        doctors_data = [
            {
                "name": "Dr. Rahul Patil",
                "email": "doctor@patilhospital.com",
                "phone": "9876543210",
                "specialization": "Cardiologist",
                "qualification": "MBBS, MD (Cardiology)",
                "experience": 12,
                "consultation_fee": 500,
                "department": "Cardiology",
                "bio": "Senior cardiologist with 12 years of experience.",
                "password": "Doctor@12345",
            },
            {
                "name": "Dr. Priya Sharma",
                "email": "drpriya@patilhospital.com",
                "phone": "9876543211",
                "specialization": "General Physician",
                "qualification": "MBBS, MD",
                "experience": 8,
                "consultation_fee": 300,
                "department": "General Medicine",
                "bio": "Experienced general physician.",
                "password": "Doctor@12345",
            },
            {
                "name": "Dr. Amit Kumar",
                "email": "dramit@patilhospital.com",
                "phone": "9876543212",
                "specialization": "Orthopedic Surgeon",
                "qualification": "MBBS, MS (Ortho)",
                "experience": 15,
                "consultation_fee": 600,
                "department": "Orthopedics",
                "bio": "Specialist in bone and joint conditions.",
                "password": "Doctor@12345",
            },
        ]

        demo_doctor = None
        for d in doctors_data:
            if not User.objects.filter(email=d["email"]).exists():
                u = User.objects.create_user(
                    username=d["email"], email=d["email"],
                    password=d["password"], first_name=d["name"]
                )
                doctor = Doctor.objects.create(
                    user=u, name=d["name"], email=d["email"],
                    phone=d["phone"], specialization=d["specialization"],
                    qualification=d["qualification"], experience=d["experience"],
                    consultation_fee=d["consultation_fee"],
                    department=dept_map.get(d["department"]),
                    bio=d["bio"], available=True,
                    available_days="Mon-Sat",
                    available_time_start=time(9, 0),
                    available_time_end=time(17, 0),
                )
                if demo_doctor is None:
                    demo_doctor = doctor
                self.stdout.write(self.style.SUCCESS(f"  [+] Doctor: {d['email']} / {d['password']}"))
            else:
                if demo_doctor is None:
                    demo_doctor = Doctor.objects.filter(email=d["email"]).first()
                self.stdout.write(f"  [-] Doctor {d['email']} already exists")

        # ── Demo Patient ─────────────────────────────────────────
        if not User.objects.filter(email="patient@patilhospital.com").exists():
            p_user = User.objects.create_user(
                username="patient@patilhospital.com",
                email="patient@patilhospital.com",
                password="Patient@12345",
                first_name="Demo",
                last_name="Patient"
            )
            patient = Patient.objects.create(
                user=p_user,
                name="Demo Patient",
                email="patient@patilhospital.com",
                phone="9000000001",
                age=30,
                gender="Male",
                blood_group="O+",
                address="123, Main Street, Pune, Maharashtra"
            )
            self.stdout.write(self.style.SUCCESS("  [+] Patient: patient@patilhospital.com / Patient@12345"))
        else:
            patient = Patient.objects.filter(email="patient@patilhospital.com").first()
            self.stdout.write("  [-] Patient already exists")

        # ── Demo Appointment ─────────────────────────────────────
        if patient and demo_doctor:
            from datetime import timedelta
            from django.utils import timezone
            apt_date = timezone.localdate() + timedelta(days=2)

            if not Appointment.objects.filter(patient=patient, doctor=demo_doctor, appointment_date=apt_date).exists():
                from main.services.appointment_service import generate_bill_for_appointment
                apt = Appointment.objects.create(
                    patient=patient,
                    doctor=demo_doctor,
                    department=demo_doctor.department,
                    appointment_date=apt_date,
                    appointment_time=time(10, 0),
                    reason="Routine checkup",
                    status="Pending"
                )
                try:
                    generate_bill_for_appointment(apt)
                except Exception:
                    pass
                self.stdout.write(self.style.SUCCESS(f"  [+] Demo appointment on {apt_date} at 10:00 AM"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 55))
        self.stdout.write(self.style.SUCCESS("  PATIL HOSPITAL DEMO DATA CREATED SUCCESSFULLY!"))
        self.stdout.write(self.style.SUCCESS("=" * 55))
        self.stdout.write("")
        self.stdout.write("  Login Accounts:")
        self.stdout.write("  ---------------------------------------------")
        self.stdout.write("  Admin  : admin@patilhospital.com / Admin@12345")
        self.stdout.write("  Doctor : doctor@patilhospital.com / Doctor@12345")
        self.stdout.write("  Patient: patient@patilhospital.com / Patient@12345")
        self.stdout.write("")
        self.stdout.write("  NOTE: Change all passwords before going live!")
        self.stdout.write("")
