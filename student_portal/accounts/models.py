from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.contrib.auth.models import BaseUserManager


class Group(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Название группы')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class UserManager(BaseUserManager):
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user
    
class User(AbstractUser):
    # Убираем username
    username = None
    email = models.EmailField(unique=True)
    
    USER_ROLES = [
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
        ('admin', 'Администратор'),
    ]
    role = models.CharField(
        max_length=10,
        choices=USER_ROLES,
        default='student',
        verbose_name='Роль'
    )
    
    # Основные поля
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$')
    first_name = models.CharField(max_length=150, verbose_name='Имя')
    last_name = models.CharField(max_length=150, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=150, blank=True, verbose_name='Отчество')
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        verbose_name='Номер телефона'
    )
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/%d/',  # Добавим дату в путь
        blank=True,
        null=True,
        verbose_name='Аватар'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Группа'
    )
    
    objects = UserManager() 
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    @property
    def avg_grade(self):
        from django.db.models import Avg
        avg = Grade.objects.filter(student=self).aggregate(avg=Avg('grade'))['avg']
        return round(avg, 2) if avg else None
    
    @property
    def is_teacher(self):
        return self.role == 'teacher'
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return self.get_full_name()
    
    def get_full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()

class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название предмета')
    description = models.TextField(blank=True, verbose_name='Описание')
    
    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class GroupSubject(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name='Группа')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name='Предмет')
    semester = models.PositiveSmallIntegerField(verbose_name='Семестр')
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Преподаватель',
        limit_choices_to={'role': 'teacher'},
        related_name='teaching_subjects'
    )
    
    class Meta:
        verbose_name = 'Предмет группы'
        verbose_name_plural = 'Предметы групп'
        unique_together = ('group', 'subject', 'semester')
    
    def __str__(self):
        return f"{self.subject} ({self.group}, {self.semester} семестр)"

class Grade(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Студент')
    group_subject = models.ForeignKey(GroupSubject, on_delete=models.CASCADE, verbose_name='Предмет группы')
    date = models.DateField(verbose_name='Дата оценки')
    grade = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка'
    )
    grade_type = models.CharField(
        max_length=20,
        choices=[('exam', 'Экзамен')],  # Оставляем только экзамен
        default='exam',
        verbose_name='Тип оценки'
    )
    
    class Meta:
        verbose_name = 'Оценка'
        verbose_name_plural = 'Оценки'
        ordering = ['-date']
        unique_together = ('student', 'group_subject') 
    
    def __str__(self):
        return f"{self.student}: {self.group_subject} - {self.grade}"

class Meta:
    permissions = [
        ('manage_grades', 'Может управлять оценками'),
        ('manage_subjects', 'Может управлять предметами'),
    ]


class StudyMaterial(models.Model):
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    file = models.FileField(
        upload_to='study_materials/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'txt'])
        ],
        verbose_name='Файл'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        verbose_name='Предмет',
        related_name='materials',
    )
    groups = models.ManyToManyField(Group, verbose_name='Для групп')
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')
    author = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name='Автор',
        limit_choices_to={'is_staff': True}  # Только преподаватели
    )

    class Meta:
        verbose_name = 'Учебный материал'
        verbose_name_plural = 'Учебные материалы'
        ordering = ['-upload_date']

    def __str__(self):
        return self.title

    def get_file_icon(self):
        ext = self.file.name.split('.')[-1].lower()
        if ext == 'pdf':
            return 'fa-file-pdf text-danger'
        elif ext == 'docx':
            return 'fa-file-word text-primary'
        elif ext == 'txt':
            return 'fa-file-alt text-secondary'
        return 'fa-file'