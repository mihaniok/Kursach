from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from .forms import RegistrationForm, EmailAuthenticationForm, ProfileForm
from .models import User, Group, Grade, GroupSubject, StudyMaterial, Subject
from django.db.models import Avg
from django import forms
from datetime import datetime 

import requests
import json
from django.conf import settings


# Функция регистрации
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

# Кастомный класс для входа
class CustomLoginView(LoginView):
    form_class = EmailAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        remember_me = self.request.POST.get('remember_me')
        if not remember_me:
            # Установим время жизни сессии на 0 (закроется при закрытии браузера)
            self.request.session.set_expiry(0)
            self.request.session.modified = True
        return super(CustomLoginView, self).form_valid(form)

def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required
def home(request):
    if hasattr(request.user, 'is_teacher') and request.user.is_teacher:
        return redirect('teacher-dashboard')
    return render(request, 'core/home.html', {'user': request.user})

# Декоратор для проверки роли преподавателя
def teacher_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_teacher and not request.user.is_superuser:
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# страница преподавателя
@login_required
@teacher_required
def teacher_dashboard(request):
    teacher = request.user
    
    # Получаем группы и предметы, которые ведет преподаватель
    teaching_subjects = GroupSubject.objects.filter(teacher=teacher).select_related('group', 'subject')
    
    # Группируем по семестрам
    semesters_data = {}
    for subject in teaching_subjects:
        semester_key = subject.semester
        if semester_key not in semesters_data:
            semesters_data[semester_key] = []
        semesters_data[semester_key].append(subject)
    
    # Получаем учебные материалы преподавателя
    teacher_materials = StudyMaterial.objects.filter(author=teacher).order_by('-upload_date')[:5]
    
    # Получаем последние выставленные оценки
    recent_grades = Grade.objects.filter(group_subject__teacher=teacher).select_related('student', 'group_subject').order_by('-date')[:10]
    
    context = {
        'teacher': teacher,
        'semesters_data': sorted(semesters_data.items()),
        'total_groups': teaching_subjects.values('group').distinct().count(),
        'total_subjects': teaching_subjects.values('subject').distinct().count(),
        'teacher_materials': teacher_materials,
        'recent_grades': recent_grades,
    }
    return render(request, 'accounts/teacher_dashboard.html', context)

# Страница для управления оценками (список предметов)
@login_required
@teacher_required
def teacher_grades(request):
    teacher = request.user
    
    # Получаем все предметы, которые ведет преподаватель
    teaching_subjects = GroupSubject.objects.filter(teacher=teacher).select_related('group', 'subject')
    
    context = {
        'teaching_subjects': teaching_subjects,
    }
    return render(request, 'accounts/teacher_grades.html', context)


# Страница для выставления оценок для конкретного предмета
@login_required
@teacher_required
def teacher_grades_edit(request, group_subject_id):
    teacher = request.user
    
    group_subject = get_object_or_404(GroupSubject, id=group_subject_id, teacher=teacher)
    students = User.objects.filter(group=group_subject.group, role='student').order_by('last_name', 'first_name')
    
    # Получаем существующие оценки
    existing_grades = Grade.objects.filter(
        group_subject=group_subject
    ).select_related('student')
    
    # Создаем словарь оценок для быстрого доступа
    grades_dict = {grade.student.id: grade for grade in existing_grades}
    
    # Создаем список студентов с их оценками для удобного доступа в шаблоне
    students_with_grades = []
    for student in students:
        grade = grades_dict.get(student.id)
        students_with_grades.append({
            'student': student,
            'grade': grade,
        })
    
    if request.method == 'POST':
        # Обработка выставления/изменения оценок
        for student in students:
            grade_value = request.POST.get(f'grade_{student.id}')
            date_str = request.POST.get(f'date_{student.id}')
            
            if grade_value and date_str:
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    grade_int = int(grade_value)
                    
                    # Проверяем, что оценка от 1 до 5
                    if 1 <= grade_int <= 5:
                        # Проверяем существующую оценку
                        if student.id in grades_dict:
                            # Обновляем существующую оценку
                            existing_grade = grades_dict[student.id]
                            existing_grade.grade = grade_int
                            existing_grade.date = date
                            existing_grade.save()
                            messages.success(request, f'Оценка для {student.get_full_name()} обновлена')
                        else:
                            # Создаем новую оценку
                            Grade.objects.create(
                                student=student,
                                group_subject=group_subject,
                                grade=grade_int,
                                grade_type='exam',
                                date=date
                            )
                            messages.success(request, f'Оценка для {student.get_full_name()} добавлена')
                    else:
                        messages.error(request, f'Оценка должна быть от 1 до 5 для {student.get_full_name()}')
                        
                except ValueError:
                    messages.error(request, f'Ошибка в данных для {student.get_full_name()}')
        
        # После сохранения обновляем данные
        return redirect('teacher-grades-edit', group_subject_id=group_subject_id)
    
    context = {
        'group_subject': group_subject,
        'students_with_grades': students_with_grades,  # Используем новый формат
        'today': datetime.now().date(),
    }
    return render(request, 'accounts/teacher_grades_edit.html', context)

# Страница для управления учебными материалами
@login_required
@teacher_required
def teacher_materials(request):
    teacher = request.user
    
    # Получаем предметы, которые ведет преподаватель
    teaching_subjects = GroupSubject.objects.filter(teacher=teacher).select_related('subject')
    
    if request.method == 'POST':
        form = StudyMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.author = teacher
            material.save()
            form.save_m2m()
            messages.success(request, 'Материал успешно добавлен')
            return redirect('teacher-materials')
    else:
        form = StudyMaterialForm()
        # Фильтруем доступные группы по предметам преподавателя
        form.fields['groups'].queryset = Group.objects.filter(
            groupsubject__teacher=teacher
        ).distinct()
        form.fields['subject'].queryset = Subject.objects.filter(
            groupsubject__teacher=teacher
        ).distinct()
    
    # Получаем материалы преподавателя
    materials = StudyMaterial.objects.filter(author=teacher).order_by('-upload_date')
    
    context = {
        'form': form,
        'materials': materials,
        'teaching_subjects': teaching_subjects,
    }
    return render(request, 'accounts/teacher_materials.html', context)

# Форма для учебных материалов
class StudyMaterialForm(forms.ModelForm):
    class Meta:
        model = StudyMaterial
        fields = ['title', 'description', 'subject', 'file', 'groups']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'groups': forms.CheckboxSelectMultiple,
        }
        
@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()
            print(f"Avatar saved: {user.avatar}")
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})

@login_required
def group_view(request):
    if not request.user.group:
        return render(request, 'accounts/no_group.html')
    
    group_members = User.objects.filter(
        group=request.user.group
    ).order_by('last_name', 'first_name', 'middle_name')
    
    context = {
        'group': request.user.group,
        'members': group_members,
        'total_members': group_members.count()
    }
    return render(request, 'accounts/group.html', context)

@login_required
def performance_view(request):
    semester = request.GET.get('semester', None)
    
    # Параметры для Go сервиса
    payload = {
        'student_id': request.user.id,
        'auth_token': settings.GO_SERVICE_SECRET
    }
    
    if semester:
        payload['semester'] = int(semester)
    
    try:
        # Вызов Go микросервиса
        response = requests.post(
            f'{settings.GO_SERVICE_URL}/api/performance',
            json=payload,
            timeout=5 
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data['success']:
                semesters_data = []
                for semester_num, subjects in data['semesters'].items():
                    semester_data = (int(semester_num), subjects)
                    semesters_data.append(semester_data)
                
                # Сортируем по семестрам
                semesters_data.sort(key=lambda x: x[0])
                
                context = {
                    'semesters_data': semesters_data,
                    'avg_grade': data['avg_grade'],
                    'selected_semester': int(semester) if semester else None,
                    'all_semesters': get_all_semesters(request.user),
                    'source': 'go_service'  # Для отладки
                }
                return render(request, 'accounts/performance.html', context)
        else:
            print(f"Go service returned status: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Go service connection error: {e}")
    except json.JSONDecodeError as e:
        print(f"Go service JSON decode error: {e}")
    except Exception as e:
        print(f"Unexpected error with Go service: {e}")
    return performance_view_fallback(request, semester)

def performance_view_fallback(request, semester):
    grades_qs = Grade.objects.filter(student=request.user).select_related(
        'group_subject__subject', 'group_subject'
    ).order_by('group_subject__semester', 'group_subject__subject__name', 'date')
    
    if semester:
        grades_qs = grades_qs.filter(group_subject__semester=semester)
    
    # Преобразуем в список для обработки
    grades = list(grades_qs)
    avg_grade = grades_qs.aggregate(avg=Avg('grade'))['avg'] if grades_qs.exists() else None
    
    # Группируем оценки по семестрам и предметам
    semesters_data = {}
    for grade in grades:
        semester_key = grade.group_subject.semester
        subject_key = grade.group_subject.subject.name
        
        if semester_key not in semesters_data:
            semesters_data[semester_key] = {}
            
        if subject_key not in semesters_data[semester_key]:
            semesters_data[semester_key][subject_key] = {
                'teacher': grade.group_subject.teacher,
                'grades': [],
                'avg': None
            }
            
        semesters_data[semester_key][subject_key]['grades'].append(grade)
    
    for semester, subjects in semesters_data.items():
        for subject_name, data in subjects.items():
            subject_grades = data['grades']
            if subject_grades:
                data['avg'] = sum(g.grade for g in subject_grades) / len(subject_grades)
    
    context = {
        'semesters_data': sorted(semesters_data.items()),
        'all_semesters': get_all_semesters(request.user),
        'selected_semester': int(semester) if semester else None,
        'avg_grade': round(avg_grade, 2) if avg_grade else None,
        'source': 'django_fallback'
    }
    return render(request, 'accounts/performance.html', context)

def get_all_semesters(user):
    """Получаем список всех семестров для студента"""
    return Grade.objects.filter(
        student=user
    ).values_list(
        'group_subject__semester', flat=True
    ).distinct().order_by('group_subject__semester')


@login_required
def study_materials_view(request):
    # Материалы для группы студента, сгруппированные по предметам
    materials_by_subject = {}
    
    # Получаем все материалы для группы студента
    materials = StudyMaterial.objects.filter(
        groups=request.user.group
    ).select_related('subject').order_by('subject__name', '-upload_date')
    
    # Группируем по предметам
    for material in materials:
        if material.subject not in materials_by_subject:
            materials_by_subject[material.subject] = []
        materials_by_subject[material.subject].append(material)
    
    context = {
        'materials_by_subject': sorted(materials_by_subject.items(), key=lambda x: x[0].name),
        'total_materials': materials.count()
    }
    return render(request, 'accounts/study_materials.html', context)