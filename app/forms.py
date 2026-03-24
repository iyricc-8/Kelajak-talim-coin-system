from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, Optional
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Login yoki Email', validators=[DataRequired()])
    password = PasswordField('Parol', validators=[DataRequired()])
    remember_me = BooleanField('Meni eslab qol')
    submit = SubmitField('Kirish')


class RegistrationForm(FlaskForm):
    first_name = StringField('Ism', validators=[DataRequired(), Length(min=2, max=64)])
    last_name = StringField('Familiya', validators=[DataRequired(), Length(min=2, max=64)])
    username = StringField('Login', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Parol', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Parolni tasdiqlang', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField("Ro'yxatdan o'tish")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Bu login band.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Bu email allaqachon ishlatilgan.')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField("Parolni tiklash havolasini yuborish")


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Yangi parol', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Parolni tasdiqlang', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Parolni yangilash')


class EditProfileForm(FlaskForm):
    first_name = StringField('Ism', validators=[DataRequired(), Length(min=2, max=64)])
    last_name = StringField('Familiya', validators=[DataRequired(), Length(min=2, max=64)])
    avatar = FileField('Avatar', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Faqat rasm fayllari!')])
    submit = SubmitField('Saqlash')


class AwardCoinsForm(FlaskForm):
    user_id = SelectField("O'quvchi", coerce=int, validators=[DataRequired()])
    amount = IntegerField('Coin miqdori', validators=[DataRequired(), NumberRange(min=1, max=10000)])
    reason = StringField('Sabab', validators=[DataRequired(), Length(max=256)])
    comment = TextAreaField('Izoh', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Hisoblash')


class DeductCoinsForm(FlaskForm):
    user_id = SelectField("O'quvchi", coerce=int, validators=[DataRequired()])
    amount = IntegerField('Coin miqdori', validators=[DataRequired(), NumberRange(min=1, max=10000)])
    reason = StringField('Sabab', validators=[DataRequired(), Length(max=256)])
    comment = TextAreaField('Izoh', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Hisobdan yechish')


class QuestForm(FlaskForm):
    title = StringField('Kvest Nomi', validators=[DataRequired(), Length(max=256)])
    description = TextAreaField('Tavsif', validators=[Optional()])
    reward_coins = IntegerField('Mukofot (Coin)', validators=[Optional(), NumberRange(min=0)])
    reward_xp = IntegerField('Mukofot (XP)', validators=[Optional(), NumberRange(min=0)])
    quest_type = SelectField('Kvest Turi', choices=[('daily', 'Kunlik (Daily)'), ('weekly', 'Haftalik (Weekly)')])
    is_active = BooleanField('Faol', default=True)
    submit = SubmitField('Saqlash')



class ProductForm(FlaskForm):
    title = StringField('Nomi', validators=[DataRequired(), Length(max=256)])
    description = TextAreaField('Tavsif', validators=[Optional()])
    price_coin = IntegerField('Narx (Coin)', validators=[DataRequired(), NumberRange(min=1)])
    stock = IntegerField('Qolgan', validators=[DataRequired(), NumberRange(min=0)])
    category_id = SelectField('Kategoriya', coerce=int, validators=[Optional()])
    image = FileField('Rasm', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Faqat rasm fayllari!')])
    is_active = BooleanField('Faol')
    submit = SubmitField('Saqlash')


class CategoryForm(FlaskForm):
    name = StringField('Nomi', validators=[DataRequired(), Length(max=128)])
    description = TextAreaField('Tavsif', validators=[Optional()])
    submit = SubmitField('Saqlash')


class AchievementForm(FlaskForm):
    title = StringField('Nomi', validators=[DataRequired(), Length(max=256)])
    description = TextAreaField('Tavsif', validators=[Optional()])
    icon = StringField('Belgi (emoji)', validators=[DataRequired(), Length(max=10)], default='🏅')
    condition_type = SelectField('Shart turi', choices=[
        ('total_earned', 'Jami ishlangan Coin'),
        ('purchases', 'Xaridlar soni'),
        ('leaderboard_top1', 'Reytingda Top-1'),
    ])
    condition_value = IntegerField('Shart qiymati', validators=[DataRequired(), NumberRange(min=1)])
    is_active = BooleanField('Faol')
    submit = SubmitField('Saqlash')


class EditUserForm(FlaskForm):
    user_id = HiddenField()
    first_name = StringField('Ism', validators=[DataRequired(), Length(min=2, max=64)])
    last_name = StringField('Familiya', validators=[DataRequired(), Length(min=2, max=64)])
    username = StringField('Login', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Yangi parol', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Parolni tasdiqlang', validators=[Optional(), EqualTo('password', message='Parollar mos emas.')])
    role = SelectField('Rol', choices=[('student', "O'quvchi"), ('teacher', "O'qituvchi"), ('admin', 'Administrator')])
    is_active = BooleanField('Faol')
    submit = SubmitField('Saqlash')

    def _current_user_id(self):
        try:
            return int(self.user_id.data) if self.user_id.data else None
        except (TypeError, ValueError):
            return None

    def validate_username(self, field):
        existing = User.query.filter_by(username=field.data).first()
        current_id = self._current_user_id()
        if existing and existing.id != current_id:
            raise ValidationError('Bu login band.')

    def validate_email(self, field):
        existing = User.query.filter_by(email=field.data).first()
        current_id = self._current_user_id()
        if existing and existing.id != current_id:
            raise ValidationError('Bu email allaqachon ishlatilgan.')

    def validate_confirm_password(self, field):
        if self.password.data and not field.data:
            raise ValidationError('Parolni tasdiqlang.')


class EconomySettingsForm(FlaskForm):
    xp_per_coin = IntegerField('1 Coin uchun XP', validators=[Optional(), NumberRange(min=0, max=1000)])
    level_2_xp = IntegerField('Level 2 XP', validators=[DataRequired(), NumberRange(min=0, max=100000)])
    level_3_xp = IntegerField('Level 3 XP', validators=[DataRequired(), NumberRange(min=0, max=100000)])
    level_2_min_price = IntegerField('Level 2 uchun min narx (Coin)', validators=[DataRequired(), NumberRange(min=0, max=1000000)])
    level_3_min_price = IntegerField('Level 3 uchun min narx (Coin)', validators=[DataRequired(), NumberRange(min=0, max=1000000)])

    open_mon = BooleanField('Dushanba')
    open_tue = BooleanField('Seshanba')
    open_wed = BooleanField('Chorshanba')
    open_thu = BooleanField('Payshanba')
    open_fri = BooleanField('Juma')
    open_sat = BooleanField('Shanba')
    open_sun = BooleanField('Yakshanba')

    submit = SubmitField('Saqlash')

    def validate_level_3_xp(self, field):
        if self.level_3_xp.data < self.level_2_xp.data:
            raise ValidationError("Level 3 XP Level 2 XP dan kichik bo'lmasligi kerak.")

    def validate_level_3_min_price(self, field):
        if self.level_3_min_price.data < self.level_2_min_price.data:
            raise ValidationError("Level 3 narxi Level 2 narxidan kichik bo'lmasligi kerak.")

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False
        if not any([self.open_mon.data, self.open_tue.data, self.open_wed.data,
                    self.open_thu.data, self.open_fri.data, self.open_sat.data, self.open_sun.data]):
            self.open_mon.errors.append("Kamida bitta kunni tanlang.")
            return False
        return True
