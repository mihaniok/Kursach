from django.contrib import admin
from django.urls import path
from accounts.views import register, CustomLoginView, custom_logout, home
from accounts.views import profile_view
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import group_view, performance_view, study_materials_view
from accounts.views import teacher_dashboard, teacher_grades, teacher_materials, teacher_grades_edit

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('register/', register, name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('my-group/', group_view, name='my-group'),
    path('performance/', performance_view, name='performance'),
    path('materials/', study_materials_view, name='study-materials'),
    
    # Преподавательские маршруты
    path('teacher/dashboard/', teacher_dashboard, name='teacher-dashboard'),
    path('teacher/grades/', teacher_grades, name='teacher-grades'),  # Список предметов
    path('teacher/grades/<int:group_subject_id>/', teacher_grades_edit, name='teacher-grades-edit'),  # Конкретный предмет
    path('teacher/materials/', teacher_materials, name='teacher-materials'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)