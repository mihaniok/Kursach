from django.contrib import admin
from .models import Subject, GroupSubject, Grade, StudyMaterial, User

class GroupSubjectInline(admin.TabularInline):
    model = GroupSubject
    extra = 1

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [GroupSubjectInline]

@admin.register(GroupSubject)
class GroupSubjectAdmin(admin.ModelAdmin):
    list_display = ('subject', 'group', 'semester', 'teacher')
    list_filter = ('group', 'semester', 'teacher')
    search_fields = ('subject__name', 'teacher__last_name', 'teacher__first_name')
    list_editable = ('teacher',)
    autocomplete_fields = ['teacher']
    list_select_related = ('subject', 'group', 'teacher')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'last_name', 'first_name', 'role', 'group', 'is_active')
    list_filter = ('role', 'group', 'is_active')
    search_fields = ('email', 'last_name', 'first_name', 'middle_name')
    list_editable = ('role', 'is_active')
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Персональная информация', {
            'fields': ('last_name', 'first_name', 'middle_name', 'phone_number', 'avatar')
        }),
        ('Учебная информация', {
            'fields': ('role', 'group')
        }),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions')
        }),
        ('Важные даты', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Для преподавателей скрываем поле группы
        if obj and obj.role == 'teacher':
            form.base_fields['group'].widget.attrs['disabled'] = True
        return form

class GradeInline(admin.TabularInline):
    model = Grade
    extra = 1
    fields = ('student', 'grade', 'grade_type', 'date')
    autocomplete_fields = ['student']

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'group_subject', 'grade', 'grade_type', 'date')
    list_filter = ('group_subject__group', 'group_subject__subject', 'grade_type')
    search_fields = ('student__last_name', 'student__first_name')
    date_hierarchy = 'date'
    
@admin.register(StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'author', 'upload_date')
    list_filter = ('subject', 'groups', 'upload_date')
    search_fields = ('title', 'description', 'subject__name')
    filter_horizontal = ('groups',)
    autocomplete_fields = ['subject']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'subject')
        }),
        ('Файл', {
            'fields': ('file',)
        }),
        ('Доступ', {
            'fields': ('groups',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.author = request.user
        super().save_model(request, obj, form, change)