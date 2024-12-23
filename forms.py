# forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, IntegerField
from wtforms.validators import DataRequired, Length, Email, Optional, EqualTo, Regexp, NumberRange

class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=3, max=100)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    display_name = StringField('Отображаемое имя', validators=[DataRequired(), Length(min=1, max=100)])
    group_name = StringField('Группа', validators=[DataRequired(), Length(min=1, max=100)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=255)])
    phone = StringField('Номер телефона', validators=[
        Optional(),
        Regexp(r'^\+?\d{7,15}$', message="Номер телефона должен содержать от 7 до 15 цифр и может начинаться с +.")
    ])
    city = StringField('Город', validators=[Optional(), Length(max=100)])
    date_of_birth = DateField('Дата рождения', format='%Y-%m-%d', validators=[Optional()])
    admission_year = IntegerField('Год поступления', validators=[
        Optional(),
        NumberRange(min=1900, max=2100, message="Введите корректный год.")
    ])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=3, max=100)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Войти')

class ProfileForm(FlaskForm):
    display_name = StringField('Отображаемое имя', validators=[DataRequired(), Length(min=1, max=100)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=255)])
    phone = StringField('Номер телефона', validators=[
        Optional(),
        Regexp(r'^\+?\d{7,15}$', message="Номер телефона должен содержать от 7 до 15 цифр и может начинаться с +.")
    ])
    city = StringField('Город', validators=[Optional(), Length(max=100)])
    date_of_birth = DateField('Дата рождения', format='%Y-%m-%d', validators=[Optional()])
    admission_year = IntegerField('Год поступления', validators=[
        Optional(),
        NumberRange(min=1900, max=2100, message="Введите корректный год.")
    ])
    current_password = PasswordField('Текущий пароль', validators=[Optional(), Length(min=6)])
    new_password = PasswordField('Новый пароль', validators=[Optional(), Length(min=6), EqualTo('confirm_new_password', message='Пароли должны совпадать')])
    confirm_new_password = PasswordField('Подтвердите новый пароль', validators=[Optional(), Length(min=6)])
    submit = SubmitField('Обновить профиль')

class UpdateStudentForm(FlaskForm):
    display_name = StringField('Отображаемое имя', validators=[DataRequired(), Length(min=1, max=100)])
    phone = StringField('Номер телефона', validators=[
        Optional(),
        Regexp(r'^\+?\d{7,15}$', message="Номер телефона должен содержать от 7 до 15 цифр и может начинаться с +.")
    ])
    city = StringField('Город', validators=[Optional(), Length(max=100)])
    date_of_birth = DateField('Дата рождения', format='%Y-%m-%d', validators=[Optional()])
    admission_year = IntegerField('Год поступления', validators=[
        Optional(),
        NumberRange(min=1900, max=2100, message="Введите корректный год.")
    ])
    submit = SubmitField('Обновить данные')
