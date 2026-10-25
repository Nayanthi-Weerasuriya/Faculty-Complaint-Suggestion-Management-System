from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User, UserRole
from authorities.models import Authority
from categories.models import Category
from cases.models import Case, CaseType, CasePriority, CaseStatus, CaseComment
from audit.utils import log_audit
from notifications.utils import create_notification


class Command(BaseCommand):
    help = "Populate database with comprehensive faculty test data for ITC 3380 presentation"

    def handle(self, *args, **options):
        self.stdout.write("Seeding FMSC test data...")

        # 1. Authorities (Section 6, Appendix A)
        maint_auth, _ = Authority.objects.get_or_create(
            name="Maintenance Division",
            defaults={
                'officer_name': "Eng. Sunil Jayasinghe",
                'designation': "Faculty Works Engineer",
                'email': "maintenance@mgt.sjp.ac.lk",
                'phone': "011-2803120",
                'unit': "Civil & Physical Works",
                'is_active': True,
            }
        )
        it_auth, _ = Authority.objects.get_or_create(
            name="IT Unit",
            defaults={
                'officer_name': "Mrs. Nilmini Fernando",
                'designation': "Senior Network Administrator",
                'email': "ithelpdesk@mgt.sjp.ac.lk",
                'phone': "011-2803145",
                'unit': "Computer & Network Infrastructure",
                'is_active': True,
            }
        )
        exam_auth, _ = Authority.objects.get_or_create(
            name="Examination Unit",
            defaults={
                'officer_name': "Mr. Asanka Weerasinghe",
                'designation': "Assistant Registrar (Examinations)",
                'email': "exams@mgt.sjp.ac.lk",
                'phone': "011-2803110",
                'unit': "Academic & Exam Affairs",
                'is_active': True,
            }
        )
        dean_auth, _ = Authority.objects.get_or_create(
            name="Dean's Office",
            defaults={
                'officer_name': "Senior Asst. Registrar",
                'designation': "Faculty Administration",
                'email': "dean@mgt.sjp.ac.lk",
                'phone': "011-2803100",
                'unit': "Deanery Administration",
                'is_active': True,
            }
        )
        dept_it_auth, _ = Authority.objects.get_or_create(
            name="Department of Information Technology",
            defaults={
                'officer_name': "Dr. K. Wickramasinghe",
                'designation': "Head of Department",
                'email': "headit@mgt.sjp.ac.lk",
                'phone': "011-2803200",
                'unit': "Academic Department",
                'is_active': True,
            }
        )

        # 2. Categories (Section 10 & 11)
        cat_class, _ = Category.objects.get_or_create(
            name="Classroom Facilities",
            defaults={'description': 'Lecture halls, desks, whiteboards, air conditioning, podiums'}
        )
        cat_it, _ = Category.objects.get_or_create(
            name="IT Systems & Equipment",
            defaults={'description': 'Projectors, campus Wi-Fi, lab computers, LMS connectivity, smart boards'}
        )
        cat_maint, _ = Category.objects.get_or_create(
            name="Maintenance & Infrastructure",
            defaults={'description': 'Water leakages, lighting, cleanliness, washrooms, lifts, doors/windows'}
        )
        cat_exam, _ = Category.objects.get_or_create(
            name="Examination Services",
            defaults={'description': 'Exam hall seating, admission tickets, timetable scheduling'}
        )
        cat_student, _ = Category.objects.get_or_create(
            name="Student Support Services",
            defaults={'description': 'Library seating, cafeteria services, student common rooms'}
        )

        # 3. Users for all 6 Roles
        # Superuser / Sysadmin
        admin_user = User.objects.filter(username="admin").first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                username="admin",
                email="sysadmin@mgt.sjp.ac.lk",
                password="password123",
                role=UserRole.SYSTEM_ADMIN,
                first_name="System",
                last_name="Administrator",
                reg_or_staff_id="SYS-001",
                department_or_unit="Faculty IT & Systems"
            )
        else:
            admin_user.set_password("password123")
            admin_user.save()

        # Faculty Administrator
        admin_officer, _ = User.objects.get_or_create(
            username="admin_officer",
            defaults={
                'email': "admin_officer@mgt.sjp.ac.lk",
                'first_name': "Ruwan",
                'last_name': "Senanayake",
                'role': UserRole.ADMINISTRATOR,
                'reg_or_staff_id': "ADMIN-FMSC-01",
                'department_or_unit': "Faculty General Office",
                'is_staff': True,
            }
        )
        admin_officer.set_password("password123")
        admin_officer.save()

        # Student 1
        student1, _ = User.objects.get_or_create(
            username="student1",
            defaults={
                'email': "kasun.p@mgt.sjp.ac.lk",
                'first_name': "Kasun",
                'last_name': "Perera",
                'role': UserRole.STUDENT,
                'reg_or_staff_id': "FMSC/2023/1042",
                'department_or_unit': "Department of Accounting",
                'contact_number': "077-1234567",
            }
        )
        student1.set_password("password123")
        student1.save()

        # Student 2
        student2, _ = User.objects.get_or_create(
            username="student2",
            defaults={
                'email': "nayanthi.s@mgt.sjp.ac.lk",
                'first_name': "Nayanthi",
                'last_name': "Silva",
                'role': UserRole.STUDENT,
                'reg_or_staff_id': "FMSC/2023/2180",
                'department_or_unit': "Department of Finance",
                'contact_number': "071-9876543",
            }
        )
        student2.set_password("password123")
        student2.save()

        # Lecturer 1
        lecturer1, _ = User.objects.get_or_create(
            username="lecturer1",
            defaults={
                'email': "wickramasinghe@mgt.sjp.ac.lk",
                'first_name': "Dr. K.",
                'last_name': "Wickramasinghe",
                'role': UserRole.LECTURER,
                'reg_or_staff_id': "EMP-FMSC-089",
                'department_or_unit': "Department of Information Technology",
                'contact_number': "077-4455667",
            }
        )
        lecturer1.set_password("password123")
        lecturer1.save()

        # Maintenance Authority Officer
        maint_head, _ = User.objects.get_or_create(
            username="maint_head",
            defaults={
                'email': "maint.officer@mgt.sjp.ac.lk",
                'first_name': "Sunil",
                'last_name': "Jayasinghe",
                'role': UserRole.AUTHORITY,
                'assigned_authority': maint_auth,
                'reg_or_staff_id': "MAINT-ENG-01",
                'department_or_unit': "Maintenance Division",
                'is_staff': True,
            }
        )
        maint_head.set_password("password123")
        maint_head.save()

        # IT Authority Officer
        it_head, _ = User.objects.get_or_create(
            username="it_head",
            defaults={
                'email': "it.admin@mgt.sjp.ac.lk",
                'first_name': "Nilmini",
                'last_name': "Fernando",
                'role': UserRole.AUTHORITY,
                'assigned_authority': it_auth,
                'reg_or_staff_id': "IT-ADMIN-02",
                'department_or_unit': "IT Unit",
                'is_staff': True,
            }
        )
        it_head.set_password("password123")
        it_head.save()

        # Faculty Management / Dean
        dean_user, _ = User.objects.get_or_create(
            username="dean_management",
            defaults={
                'email': "dean.fmsc@sjp.ac.lk",
                'first_name': "Prof.",
                'last_name': "P. D. Nimal",
                'role': UserRole.FACULTY_MANAGEMENT,
                'reg_or_staff_id': "DEAN-FMSC-001",
                'department_or_unit': "Dean's Office",
                'is_staff': True,
            }
        )
        dean_user.set_password("password123")
        dean_user.save()

        # 4. Realistic Cases matching Proposal examples & Ageing Scenarios
        now = timezone.now()

        test_cases_data = [
            {
                'case_number': 'FMSC-2026-0001',
                'title': 'Projector not working in Hall A',
                'case_type': CaseType.COMPLAINT,
                'priority': CasePriority.URGENT,
                'category': cat_it,
                'location': 'Main Building, Lecture Hall A',
                'description': 'HDMI display cable is broken and projector lamp is flashing red, preventing afternoon lectures from proceeding.',
                'status': CaseStatus.IN_PROGRESS,
                'submitted_by': lecturer1,
                'assigned_authority': it_auth,
                'days_ago': 2,
                'admin_notes': 'Please send an IT technician immediately as lecture starts at 1:00 PM.',
            },
            {
                'case_number': 'FMSC-2026-0002',
                'title': 'Add more seating near the library veranda',
                'case_type': CaseType.SUGGESTION,
                'priority': CasePriority.NORMAL,
                'category': cat_student,
                'location': 'Faculty Library Ground Floor Veranda',
                'description': 'During peak study hours between 11 AM and 2 PM, many students do not have benches to sit and collaborate on group work.',
                'status': CaseStatus.SUBMITTED,
                'submitted_by': student1,
                'assigned_authority': None,
                'days_ago': 1,
            },
            {
                'case_number': 'FMSC-2026-0011',
                'title': 'Broken chair in lecture hall 3',
                'case_type': CaseType.COMPLAINT,
                'priority': CasePriority.NORMAL,
                'category': cat_class,
                'location': 'Hall 3, Row 4 Desk 12',
                'description': 'Arm rest and writing flap are detached and sharp screws are exposed.',
                'status': CaseStatus.NOT_STARTED,
                'submitted_by': student2,
                'assigned_authority': maint_auth,
                'days_ago': 6,
                'admin_notes': 'Assigned to carpentry workshop for repair.',
            },
            {
                'case_number': 'FMSC-2026-0015',
                'title': 'Water leak near corridor',
                'case_type': CaseType.COMPLAINT,
                'priority': CasePriority.URGENT,
                'category': cat_maint,
                'location': 'Accounting Dept Corridor 2nd Floor',
                'description': 'Water pipe joint above corridor ceiling tile is leaking water onto the floor, causing slipping hazard.',
                'status': CaseStatus.IN_PROGRESS,
                'submitted_by': student1,
                'assigned_authority': maint_auth,
                'days_ago': 3,
                'admin_notes': 'Plumber dispatched with caution signboards.',
            },
            {
                'case_number': 'FMSC-2026-0018',
                'title': 'Slow Wi-Fi connection in New Computer Lab 02',
                'case_type': CaseType.COMPLAINT,
                'priority': CasePriority.NORMAL,
                'category': cat_it,
                'location': 'IT Building 3rd Floor Lab 02',
                'description': 'Wi-Fi access point frequent disconnects during online lab evaluations.',
                'status': CaseStatus.SOLVED,
                'submitted_by': lecturer1,
                'assigned_authority': it_auth,
                'days_ago': 5,
                'admin_notes': 'Check access point firmware and channel interference.',
                'resolution_notes': 'Replaced damaged POE injector and reconfigured access point channel to 5GHz with updated firmware. Connection tested with 45 simultaneous client connections at 80Mbps.',
                'solved_at': now - timedelta(days=1),
            },
            {
                'case_number': 'FMSC-2026-0021',
                'title': 'Digital notice board installation near main faculty entrance',
                'case_type': CaseType.SUGGESTION,
                'priority': CasePriority.NORMAL,
                'category': cat_student,
                'location': 'Faculty Main Entrance Foyer',
                'description': 'Replace paper posters with an interactive TV display showing lecture notices, exam timetables, and career fairs.',
                'status': CaseStatus.SOLVED,
                'submitted_by': student1,
                'assigned_authority': it_auth,
                'days_ago': 10,
                'resolution_notes': 'Proposal approved and 55-inch faculty announcement digital display installed and connected to faculty digital signage server.',
                'solved_at': now - timedelta(days=3),
            },
            {
                'case_number': 'FMSC-2026-0025',
                'title': 'Air conditioner leaking in Room 204',
                'case_type': CaseType.COMPLAINT,
                'priority': CasePriority.URGENT,
                'category': cat_class,
                'location': 'Postgraduate Wing Room 204',
                'description': 'Air conditioner condenser line blocked; water dripping near audio visual switchboard.',
                'status': CaseStatus.WAITING_FOR_INFO,
                'submitted_by': lecturer1,
                'assigned_authority': maint_auth,
                'days_ago': 4,
                'admin_notes': 'AC technician inspected; waiting for specialized replacement pipe from supplier.',
            },
            {
                'case_number': 'FMSC-2026-0029',
                'title': 'Exam timetable clash for Year 3 Semester 1 subjects',
                'case_type': CaseType.COMPLAINT,
                'priority': CasePriority.URGENT,
                'category': cat_exam,
                'location': 'Examination Unit / Online Portal',
                'description': 'ITC 3380 and FIN 3320 are scheduled simultaneously on Thursday June 18th morning.',
                'status': CaseStatus.UNDER_REVIEW,
                'submitted_by': student2,
                'assigned_authority': exam_auth,
                'days_ago': 2,
                'admin_notes': 'Exam division verifying subject registration lists.',
            },
            {
                'case_number': 'FMSC-2026-0033',
                'title': 'Install sanitary napkin vending machine in female rest rooms',
                'case_type': CaseType.SUGGESTION,
                'priority': CasePriority.NORMAL,
                'category': cat_student,
                'location': 'Ground Floor & 2nd Floor Student Washrooms',
                'description': 'Essential health and hygiene enhancement for female students and staff across the faculty.',
                'status': CaseStatus.CLOSED,
                'submitted_by': student2,
                'assigned_authority': dean_auth,
                'days_ago': 15,
                'resolution_notes': 'Procurement completed via university welfare fund; two automatic vending machines installed and operational.',
                'solved_at': now - timedelta(days=5),
                'closed_at': now - timedelta(days=4),
            },
            {
                'case_number': 'FMSC-2026-0040',
                'title': 'Spam / promotional leaflet on faculty boards',
                'case_type': CaseType.COMPLAINT,
                'priority': CasePriority.NORMAL,
                'category': cat_student,
                'location': 'Old Management Building Staircase',
                'description': 'Commercial advertising poster pasted without dean office stamp.',
                'status': CaseStatus.REJECTED,
                'submitted_by': student1,
                'assigned_authority': None,
                'days_ago': 7,
                'admin_notes': 'Rejected: Handled directly by faculty security squad under standard cleaning protocols.',
            },
            {
                'case_number': 'FMSC-2026-0044',
                'title': 'Burnt light fixture outside Lab 05 corridor',
                'case_type': CaseType.COMPLAINT,
                'priority': CasePriority.NORMAL,
                'category': cat_maint,
                'location': 'IT Block 2nd Floor Corridor',
                'description': 'Tube light flickering and emitting burning plastic smell.',
                'status': CaseStatus.NOT_STARTED,
                'submitted_by': lecturer1,
                'assigned_authority': maint_auth,
                'days_ago': 5,
                'admin_notes': 'Electrical unit to replace ballast.',
            },
            {
                'case_number': 'FMSC-2026-0050',
                'title': 'LMS Server timeout during quiz submissions',
                'case_type': CaseType.COMPLAINT,
                'priority': CasePriority.URGENT,
                'category': cat_it,
                'location': 'Faculty Moodle LMS',
                'description': 'HTTP 504 Gateway Timeout error occurring when more than 300 students submit midterm assignments at the same time.',
                'status': CaseStatus.IN_PROGRESS,
                'submitted_by': student1,
                'assigned_authority': it_auth,
                'days_ago': 1,
                'admin_notes': 'IT Unit analyzing server PHP-FPM process pools and database connection limits.',
            }
        ]

        for data in test_cases_data:
            days_ago = data.pop('days_ago')
            sub_time = now - timedelta(days=days_ago)
            case_num = data.pop('case_number')

            case, created = Case.objects.get_or_create(
                case_number=case_num,
                defaults={
                    'title': data['title'],
                    'case_type': data['case_type'],
                    'priority': data['priority'],
                    'category': data['category'],
                    'location': data['location'],
                    'description': data['description'],
                    'declaration': True,
                    'status': data['status'],
                    'submitted_by': data['submitted_by'],
                    'assigned_authority': data.get('assigned_authority'),
                    'admin_notes': data.get('admin_notes', ''),
                    'resolution_notes': data.get('resolution_notes', ''),
                    'submitted_at': sub_time,
                    'solved_at': data.get('solved_at'),
                    'closed_at': data.get('closed_at'),
                }
            )

            if created:
                log_audit(
                    case=case,
                    user=case.submitted_by,
                    action_type="Case Submitted",
                    new_value=f"{case.get_case_type_display()} - {case.get_priority_display()}"
                )
                if case.status in [CaseStatus.IN_PROGRESS, CaseStatus.SOLVED, CaseStatus.CLOSED]:
                    CaseComment.objects.create(
                        case=case,
                        author=admin_user,
                        comment_type='progress',
                        comment_text=f"Initial inspection completed by {case.assigned_authority.name if case.assigned_authority else 'Team'}."
                    )
                if case.status in [CaseStatus.SOLVED, CaseStatus.CLOSED]:
                    create_notification(
                        recipient=case.submitted_by,
                        case=case,
                        title=f"Case Solved: {case.case_number}",
                        message=f"Your case '{case.title}' has been resolved. Notes: {case.resolution_notes}",
                        notification_type='solved'
                    )

        self.stdout.write(self.style.SUCCESS("FMSC Portal successfully seeded with realistic test data!"))
