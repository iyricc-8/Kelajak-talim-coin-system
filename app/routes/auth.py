from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Wallet
from app.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_token()
            reset_url = url_for('auth.reset_token', token=token, _external=True)
            flash("Agar email ro'yxatdan o'tgan bo'lsa, parolni tiklash havolasi yuborildi.", 'info')
            flash(f'Tiklash havolasi (test uchun): {reset_url}', 'warning')
        else:
            flash("Agar email ro'yxatdan o'tgan bo'lsa, parolni tiklash havolasi yuborildi.", 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_request.html', form=form)


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    user = User.verify_reset_token(token)
    if user is None:
        flash("Havola yaroqsiz yoki muddati o'tgan. Yangi havola so'rang.", 'danger')
        return redirect(url_for('auth.reset_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Parol muvaffaqiyatli yangilandi. Endi kirishingiz mumkin.", 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.username.data)
        ).first()

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash("Akkauntingiz bloklangan. Administratorga murojaat qiling.", 'danger')
                return redirect(url_for('auth.login'))
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash(f'Xush kelibsiz, {user.first_name}!', 'success')
            if next_page:
                return redirect(next_page)
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('student.dashboard'))
        else:
            flash("Login yoki parol noto'g'ri.", 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            username=form.username.data,
            email=form.email.data,
            role='student',
            is_active=True
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        wallet = Wallet(user_id=user.id, balance=0)
        db.session.add(wallet)
        db.session.commit()

        flash("Ro'yxatdan o'tish muvaffaqiyatli! Endi kirishingiz mumkin.", 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Siz tizimdan chiqdingiz.', 'info')
    return redirect(url_for('auth.login'))
