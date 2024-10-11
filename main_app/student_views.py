import json
import math
from datetime import datetime
from django.utils import timezone

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *


def student_home(request):
    student = get_object_or_404(Student, admin=request.user)
    subjects = Subject.objects.filter(course=student.course)
    
    subject_attendance = []
    data_present = []
    data_absent = []
    data_name = []
    
    for subject in subjects:
        attendance = AttendanceReport.objects.filter(student=student, attendance__subject=subject)
        total_present = attendance.filter(status=True).count()
        total_absent = attendance.filter(status=False).count()
        total = total_present + total_absent
        
        if total > 0:
            percent_present = round((total_present / total) * 100, 2)
        else:
            percent_present = 0
        
        subject_attendance.append({
            'subject': subject.name,
            'percent_present': percent_present,
        })
        
        data_name.append(subject.name)
        data_present.append(total_present)
        data_absent.append(total_absent)
    
    total_attendance = sum(data_present) + sum(data_absent)
    
    context = {
        'page_title': 'Student Homepage',
        'subject_attendance': subject_attendance,
        'data_name': json.dumps(data_name),
        'data_present': data_present,
        'data_absent': data_absent,
        'percent_present': round((sum(data_present) / total_attendance * 100), 2) if total_attendance > 0 else 0,
        'percent_absent': round((sum(data_absent) / total_attendance * 100), 2) if total_attendance > 0 else 0,
    }
    return render(request, 'student_template/home_content.html', context)


@ csrf_exempt
def student_view_attendance(request):
    student = get_object_or_404(Student, admin=request.user)
    if request.method != 'POST':
        course = get_object_or_404(Course, id=student.course.id)
        context = {
            'subjects': Subject.objects.filter(course=course),
            'page_title': 'View Attendance'
        }
        return render(request, 'student_template/student_view_attendance.html', context)
    else:
        subject_id = request.POST.get('subject')
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        try:
            subject = get_object_or_404(Subject, id=subject_id)
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            attendance = Attendance.objects.filter(
                date__range=(start_date, end_date), subject=subject)
            attendance_reports = AttendanceReport.objects.filter(
                attendance__in=attendance, student=student)
            json_data = []
            for report in attendance_reports:
                data = {
                    "date":  str(report.attendance.date),
                    "status": report.status
                }
                json_data.append(data)
            return JsonResponse(json.dumps(json_data), safe=False)
        except Exception as e:
            return None
        
def student_check_noc(request):
    student = get_object_or_404(Student, admin=request.user)
    results = []
    
    subjects = Subject.objects.filter(course=student.course)
    for subject in subjects:
        attendance = AttendanceReport.objects.filter(student=student, attendance__subject=subject)
        total_classes = attendance.count()
        present_classes = attendance.filter(status=True).count()
        if total_classes > 0:
            attendance_percent = (present_classes / total_classes) * 100
        else:
            attendance_percent = 0
        
        results.append({
            'id': subject.id,
            'subject': subject.name,
            'staff': f"{subject.staff.admin.first_name} {subject.staff.admin.last_name}",
            'attendance': f"{attendance_percent:.2f}%",
            'submission': False,  # Default value, you'll need to implement a way to track submissions
            'signature_of_staff': ''  # You may want to implement this feature later
        })
    
    context = {
        'results': results,
        'page_title': 'Check NOC'
    }
    return render(request, "student_template/student_view_noc.html", context)


def check_noc_status(request):
    student = get_object_or_404(Student, admin=request.user)
    nocs = NOC.objects.filter(student=student)
    context = {
        'nocs': nocs,
        'page_title': 'Check NOC Status'
    }
    return render(request, 'student_template/check_noc_status.html', context)


def student_apply_leave(request):
    form = LeaveReportStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStudent.objects.filter(student=student),
        'page_title': 'Apply for leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('student_apply_leave'))
            except Exception:
                messages.error(request, "Could not submit")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_apply_leave.html", context)


def student_feedback(request):
    form = FeedbackStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStudent.objects.filter(student=student),
        'page_title': 'Student Feedback'

    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Feedback submitted for review")
                return redirect(reverse('student_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_feedback.html", context)


def student_view_profile(request):
    student = get_object_or_404(Student, admin=request.user)
    form = StudentEditForm(request.POST or None, request.FILES or None,
                           instance=student)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = student.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                student.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('student_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(request, "Error Occured While Updating Profile " + str(e))

    return render(request, "student_template/student_view_profile.html", context)


@csrf_exempt
def student_fcmtoken(request):
    token = request.POST.get('token')
    student_user = get_object_or_404(CustomUser, id=request.user.id)
    try:
        student_user.fcm_token = token
        student_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def student_view_notification(request):
    student = get_object_or_404(Student, admin=request.user)
    notifications = NotificationStudent.objects.filter(student=student)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "student_template/student_view_notification.html", context)


def student_view_noc(request):
    student = get_object_or_404(Student, admin=request.user)
    nocs = NOC.objects.filter(student=student)
    context = {
        'results': nocs,
        'page_title': 'View NOC Status'
    }
    return render(request, "student_template/student_view_noc.html", context)




def student_view_subjects(request):
    student = request.user.student
    subjects = Subject.objects.filter(course=student.course)
    
    context = {
        'subjects': subjects,
        'page_title': 'View Subjects and Assignments'
    }
    return render(request, 'student_template/student_view_subjects.html', context)

@csrf_exempt
def submit_assignment(request):
    if request.method == 'POST':
        subject_id = request.POST.get('subject_id')
        student = request.user.student
        
        # Create or update the assignment submission
        submission, created = AssignmentSubmission.objects.update_or_create(
            student=student,
            subject_id=subject_id,
            defaults={'submitted': True, 'submission_date': timezone.now()}
        )
        
        if created:
            message = 'Assignment submitted successfully!'
        else:
            message = 'Assignment submission updated!'

        return JsonResponse({'message': message})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)

