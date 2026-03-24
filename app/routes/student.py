from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, logout_user
from app import db
from app.models import Transaction, Order, Achievement, UserAchievement, Notification, User, Quest
from app.forms import EditProfileForm
from app.services.user_service import delete_user_account
from app.services.quest_service import process_daily_activity, get_user_quests
from app.services.economy_service import get_next_level_xp
from app.utils.helpers import save_upload
import os

student_bp = Blueprint('student', __name__)


@student_bp.route('/dashboard')
@login_required
def dashboard():
    # Process daily streak
    streak_updated, bonus_coins = process_daily_activity(current_user)
    if streak_updated and bonus_coins:
        flash(f'Tabriklaymiz! {current_user.streak} kunlik streak uchun sizga {bonus_coins} Coin berildi!', 'success')
    elif streak_updated:
        pass # Just updated without bonus
        
    # Get active quests
    user_quests = get_user_quests(current_user)

    current_xp = current_user.xp or 0
    next_level_xp = get_next_level_xp(current_user.level or 1)
    progress_pct = 100 if not next_level_xp else int(min(100, (current_xp / next_level_xp) * 100))
    remaining_xp = None if not next_level_xp else max(0, next_level_xp - current_xp)

    from app.models import Product
    # Recent transactions
    recent_txns = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.created_at.desc()).limit(5).all()
    # Recent orders
    recent_orders = Order.query.filter_by(user_id=current_user.id)\
        .order_by(Order.created_at.desc()).limit(3).all()
    # Popular products
    popular_products = Product.query.filter_by(is_active=True)\
        .order_by(Product.price_coin.asc()).limit(4).all()
    # User achievements
    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id)\
        .order_by(UserAchievement.received_at.desc()).limit(4).all()
    # Unread notifications
    unread_notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .order_by(Notification.created_at.desc()).limit(5).all()

    # Leaderboard rank
    from sqlalchemy import func
    from app.models import Wallet
    ranked = db.session.query(User.id, Wallet.balance)\
        .join(Wallet, User.id == Wallet.user_id)\
        .filter(User.role == 'student', User.is_active == True)\
        .order_by(Wallet.balance.desc()).all()
    rank = next((i + 1 for i, (uid, _) in enumerate(ranked) if uid == current_user.id), None)

    return render_template('student/dashboard.html',
                           recent_txns=recent_txns,
                           recent_orders=recent_orders,
                           popular_products=popular_products,
                           user_achievements=user_achievements,
                           unread_notifs=unread_notifs,
                           user_quests=user_quests,
                           current_xp=current_xp,
                           progress_pct=progress_pct,
                           next_level_xp=next_level_xp,
                           remaining_xp=remaining_xp,
                           rank=rank)


@student_bp.route('/quest/<int:quest_id>/complete', methods=['POST'])
@login_required
def complete_user_quest(quest_id):
    from app.services.quest_service import complete_quest
    success, msg = complete_quest(current_user, quest_id)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('student.dashboard'))


@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = EditProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data

        if form.avatar.data and form.avatar.data.filename:
            avatar_path = save_upload(form.avatar.data, 'avatars')
            if avatar_path:
                current_user.avatar = avatar_path

        db.session.commit()
        flash("Profil muvaffaqiyatli yangilandi!", 'success')
        return redirect(url_for('student.profile'))

    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id)\
        .order_by(UserAchievement.received_at.desc()).all()
    purchase_history = Order.query.filter_by(user_id=current_user.id)\
        .order_by(Order.created_at.desc()).limit(10).all()

    return render_template('student/profile.html',
                           form=form,
                           user_achievements=user_achievements,
                           purchase_history=purchase_history)


@student_bp.route('/profile/delete', methods=['POST'])
@login_required
def delete_profile():
    if current_user.role == 'admin':
        flash("Administrator akkaunti o'chirilmaydi.", 'danger')
        return redirect(url_for('student.profile'))

    user = current_user._get_current_object()
    delete_user_account(user)
    logout_user()
    flash("Akkauntingiz o'chirildi.", 'success')
    return redirect(url_for('auth.login'))


@student_bp.route('/coins')
@login_required
def coins():
    page = request.args.get('page', 1, type=int)
    txns = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.created_at.desc())\
        .paginate(page=page, per_page=20)

    # Stats
    from sqlalchemy import func
    earned = db.session.query(func.sum(Transaction.amount))\
        .filter(Transaction.user_id == current_user.id, Transaction.type == 'earn').scalar() or 0
    spent = db.session.query(func.sum(Transaction.amount))\
        .filter(Transaction.user_id == current_user.id, Transaction.type == 'spend').scalar() or 0

    return render_template('student/coins.html', txns=txns, earned=earned, spent=spent)


@student_bp.route('/orders')
@login_required
def orders():
    page = request.args.get('page', 1, type=int)
    orders_list = Order.query.filter_by(user_id=current_user.id)\
        .order_by(Order.created_at.desc())\
        .paginate(page=page, per_page=20)
    return render_template('student/orders.html', orders=orders_list)


@student_bp.route('/achievements')
@login_required
def achievements():
    all_achievements = Achievement.query.filter_by(is_active=True).all()
    user_ach_ids = {ua.achievement_id for ua in current_user.achievements.all()}
    user_ach_map = {ua.achievement_id: ua for ua in current_user.achievements.all()}
    return render_template('student/achievements.html',
                           all_achievements=all_achievements,
                           user_ach_ids=user_ach_ids,
                           user_ach_map=user_ach_map)


@student_bp.route('/leaderboard')
@login_required
def leaderboard():
    from app.models import Wallet
    from sqlalchemy import func

    top_users = db.session.query(User, Wallet.balance)\
        .join(Wallet, User.id == Wallet.user_id)\
        .filter(User.role == 'student', User.is_active == True)\
        .order_by(Wallet.balance.desc()).limit(50).all()

    return render_template('student/leaderboard.html', top_users=top_users)


@student_bp.route('/notifications')
@login_required
def notifications():
    # Mark all as read
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()

    page = request.args.get('page', 1, type=int)
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=20)
    return render_template('student/notifications.html', notifs=notifs)
