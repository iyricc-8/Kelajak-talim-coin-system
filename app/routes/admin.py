from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from app import db
from app.models import User, Wallet, Transaction, Product, Category, Order, Achievement, UserAchievement, Notification, EconomySetting, Quest
from app.forms import AwardCoinsForm, DeductCoinsForm, ProductForm, CategoryForm, AchievementForm, EditUserForm, EconomySettingsForm, QuestForm
from app.services.coin_service import award_coins, deduct_coins
from app.services.order_service import update_order_status
from app.services.user_service import delete_user_account
from app.utils.helpers import save_upload, role_required
import os
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin() and not current_user.is_teacher():
            abort(403)
        return f(*args, **kwargs)
    return decorated


def strict_admin(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    from sqlalchemy import func
    total_users = User.query.filter_by(role='student').count()
    total_coins_in_circulation = db.session.query(func.sum(Wallet.balance)).scalar() or 0
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='new').count()
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_coins=total_coins_in_circulation,
                           total_orders=total_orders,
                           pending_orders=pending_orders,
                           recent_transactions=recent_transactions,
                           recent_users=recent_users)


# -- Users --------------------------------------------------
@admin_bp.route('/users')
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')
    role_filter = request.args.get('role', '')

    query = User.query
    if search:
        query = query.filter(
            (User.first_name.ilike(f'%{search}%')) |
            (User.last_name.ilike(f'%{search}%')) |
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    if role_filter:
        query = query.filter_by(role=role_filter)

    users_list = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/users.html', users=users_list, search=search, role_filter=role_filter)


@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    form = EditUserForm(obj=user)
    form.user_id.data = user.id

    if form.validate_on_submit() and current_user.is_admin():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash("Foydalanuvchi ma'lumotlari yangilandi.", 'success')
        return redirect(url_for('admin.user_detail', user_id=user_id))

    recent_txns = Transaction.query.filter_by(user_id=user_id)\
        .order_by(Transaction.created_at.desc()).limit(10).all()
    user_orders = Order.query.filter_by(user_id=user_id)\
        .order_by(Order.created_at.desc()).limit(5).all()
    user_achievements = UserAchievement.query.filter_by(user_id=user_id).all()

    # Award/Deduct forms
    award_form = AwardCoinsForm()
    award_form.user_id.choices = [(user.id, user.full_name)]

    return render_template('admin/user_detail.html',
                           user=user, form=form,
                           award_form=award_form,
                           recent_txns=recent_txns,
                           user_orders=user_orders,
                           user_achievements=user_achievements)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@strict_admin
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("O'zingizni admin paneldan o'chira olmaysiz. Profil orqali o'chiring.", 'warning')
        return redirect(url_for('admin.user_detail', user_id=user_id))

    if user.role == 'admin':
        flash("Administrator akkaunti o'chirilmaydi.", 'danger')
        return redirect(url_for('admin.user_detail', user_id=user_id))

    delete_user_account(user)
    flash("Foydalanuvchi o'chirildi.", 'success')
    return redirect(url_for('admin.users'))


# -- Coins Management -------------------------------------
@admin_bp.route('/coins', methods=['GET', 'POST'])
@admin_required
def coins():
    students = User.query.filter(User.role.in_(['student', 'teacher'])).order_by(User.first_name).all()
    award_form = AwardCoinsForm()
    award_form.user_id.choices = [(u.id, f'{u.full_name} (@{u.username})') for u in students]
    deduct_form = DeductCoinsForm()
    deduct_form.user_id.choices = [(u.id, f'{u.full_name} (@{u.username})') for u in students]

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'award' and award_form.validate_on_submit():
            target = User.query.get(award_form.user_id.data)
            if target:
                award_coins(target, award_form.amount.data, award_form.reason.data,
                            award_form.comment.data, current_user.id)
                flash(f"{target.full_name} foydalanuvchisiga {award_form.amount.data} Coin hisoblandi.", 'success')
            return redirect(url_for('admin.coins'))

        elif action == 'deduct' and deduct_form.validate_on_submit():
            target = User.query.get(deduct_form.user_id.data)
            if target:
                result = deduct_coins(target, deduct_form.amount.data, deduct_form.reason.data,
                                      deduct_form.comment.data, current_user.id, txn_type='penalty')
                if result:
                    flash(f"{target.full_name} foydalanuvchisidan {deduct_form.amount.data} Coin yechildi.", 'success')
                else:
                    flash(f"{target.full_name} foydalanuvchisida Coin yetarli emas.", 'danger')
            return redirect(url_for('admin.coins'))

    return render_template('admin/coins.html', award_form=award_form, deduct_form=deduct_form)


# -- Transactions ------------------------------------------
@admin_bp.route('/transactions')
@admin_required
def transactions():
    page = request.args.get('page', 1, type=int)
    user_id = request.args.get('user_id', type=int)
    txn_type = request.args.get('type', '')

    query = Transaction.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    if txn_type:
        query = query.filter_by(type=txn_type)

    txns = query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=25)
    all_users = User.query.order_by(User.first_name).all()
    return render_template('admin/transactions.html', txns=txns, all_users=all_users,
                           selected_user=user_id, txn_type=txn_type)


# -- Store --------------------------------------------------
@admin_bp.route('/store')
@admin_required
def store():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '', type=str)
    category_id = request.args.get('category', type=int)
    status = request.args.get('status', '', type=str)
    stock = request.args.get('stock', '', type=str)

    query = Product.query
    if search:
        like = f'%{search}%'
        query = query.filter(
            (Product.title.ilike(like)) | (Product.description.ilike(like))
        )
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if status == 'active':
        query = query.filter(Product.is_active == True)
    elif status == 'inactive':
        query = query.filter(Product.is_active == False)
    if stock == 'out':
        query = query.filter(Product.stock == 0)
    elif stock == 'low':
        query = query.filter(Product.stock > 0, Product.stock <= 5)

    products = query.order_by(Product.created_at.desc()).paginate(page=page, per_page=20)
    categories = Category.query.order_by(Category.name).all()

    stats = {
        'total': Product.query.count(),
        'active': Product.query.filter_by(is_active=True).count(),
        'inactive': Product.query.filter_by(is_active=False).count(),
        'out': Product.query.filter_by(stock=0).count(),
        'low': Product.query.filter(Product.stock > 0, Product.stock <= 5).count(),
    }

    return render_template(
        'admin/store.html',
        products=products,
        categories=categories,
        search=search,
        selected_category=category_id,
        status=status,
        stock=stock,
        stats=stats
    )


@admin_bp.route('/store/create', methods=['GET', 'POST'])
@admin_required
def create_product():
    form = ProductForm()
    form.category_id.choices = [(0, '-- Kategoriyasiz --')] + \
        [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        image_path = None
        if form.image.data and form.image.data.filename:
            image_path = save_upload(form.image.data, 'products')

        product = Product(
            title=form.title.data,
            description=form.description.data,
            price_coin=form.price_coin.data,
            stock=form.stock.data,
            category_id=form.category_id.data if form.category_id.data != 0 else None,
            image=image_path,
            is_active=form.is_active.data
        )
        db.session.add(product)
        db.session.commit()
        flash('Mahsulot yaratildi!', 'success')
        return redirect(url_for('admin.store'))

    return render_template('admin/product_form.html', form=form, title='Yangi mahsulot')


@admin_bp.route('/store/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    form.category_id.choices = [(0, '-- Kategoriyasiz --')] + \
        [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        product.title = form.title.data
        product.description = form.description.data
        product.price_coin = form.price_coin.data
        product.stock = form.stock.data
        product.category_id = form.category_id.data if form.category_id.data != 0 else None
        product.is_active = form.is_active.data

        if form.image.data and form.image.data.filename:
            image_path = save_upload(form.image.data, 'products')
            if image_path:
                product.image = image_path

        db.session.commit()
        flash('Mahsulot yangilandi!', 'success')
        return redirect(url_for('admin.store'))

    return render_template('admin/product_form.html', form=form, product=product, title="Mahsulotni tahrirlash")


@admin_bp.route('/store/<int:product_id>/toggle', methods=['POST'])
@admin_required
def toggle_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    status = 'faollashtirildi' if product.is_active else 'faolsizlantirildi'
    flash(f'Mahsulot "{product.title}" {status}.', 'info')
    return redirect(url_for('admin.store'))


@admin_bp.route('/store/<int:product_id>/delete', methods=['POST'])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.orders.count() > 0:
        flash('Ushbu mahsulot bo-yicha buyurtmalar bor. Avval buyurtmalarni yakunlang yoki mahsulotni faolsizlantiring.', 'danger')
        return redirect(url_for('admin.store'))

    if product.image:
        try:
            file_path = os.path.join(current_app.root_path, 'static', product.image)
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass

    db.session.delete(product)
    db.session.commit()
    flash('Mahsulot o-chirildi.', 'success')
    return redirect(url_for('admin.store'))


# -- Orders ------------------------------------------------
@admin_bp.route('/orders')
@admin_required
def orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    orders_list = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=25)
    return render_template('admin/orders.html', orders=orders_list, status_filter=status_filter)


@admin_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def update_order(order_id):
    new_status = request.form.get('status')
    comment = request.form.get('comment', '')
    success, message = update_order_status(order_id, new_status, comment)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('admin.orders'))


# -- Achievements ------------------------------------------
@admin_bp.route('/achievements')
@admin_required
def achievements():
    achievements_list = Achievement.query.all()
    return render_template('admin/achievements.html', achievements=achievements_list)


@admin_bp.route('/achievements/create', methods=['GET', 'POST'])
@strict_admin
def create_achievement():
    form = AchievementForm()
    if form.validate_on_submit():
        ach = Achievement(
            title=form.title.data,
            description=form.description.data,
            icon=form.icon.data,
            condition_type=form.condition_type.data,
            condition_value=form.condition_value.data,
            is_active=form.is_active.data
        )
        db.session.add(ach)
        db.session.commit()
        flash('Yutuq yaratildi!', 'success')
        return redirect(url_for('admin.achievements'))
    return render_template('admin/achievement_form.html', form=form, title='Yangi yutuq')


@admin_bp.route('/achievements/<int:ach_id>/edit', methods=['GET', 'POST'])
@strict_admin
def edit_achievement(ach_id):
    ach = Achievement.query.get_or_404(ach_id)
    form = AchievementForm(obj=ach)
    if form.validate_on_submit():
        ach.title = form.title.data
        ach.description = form.description.data
        ach.icon = form.icon.data
        ach.condition_type = form.condition_type.data
        ach.condition_value = form.condition_value.data
        ach.is_active = form.is_active.data
        db.session.commit()
        flash('Yutuq yangilandi!', 'success')
        return redirect(url_for('admin.achievements'))
    return render_template('admin/achievement_form.html', form=form, title="Yutuqni tahrirlash", achievement=ach)


@admin_bp.route('/achievements/<int:ach_id>/toggle', methods=['POST'])
@strict_admin
def toggle_achievement(ach_id):
    ach = Achievement.query.get_or_404(ach_id)
    ach.is_active = not ach.is_active
    db.session.commit()
    flash(f'Yutuq "{ach.title}" yangilandi.', 'info')
    return redirect(url_for('admin.achievements'))


@admin_bp.route('/achievements/<int:ach_id>/delete', methods=['POST'])
@strict_admin
def delete_achievement(ach_id):
    ach = Achievement.query.get_or_404(ach_id)
    UserAchievement.query.filter_by(achievement_id=ach.id).delete(synchronize_session=False)
    db.session.delete(ach)
    db.session.commit()
    flash('Yutuq o-chirildi.', 'success')
    return redirect(url_for('admin.achievements'))


# -- Categories --------------------------------------------
@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        cat = Category(name=form.name.data, description=form.description.data)
        db.session.add(cat)
        db.session.commit()
        flash('Kategoriya yaratildi!', 'success')
        return redirect(url_for('admin.categories'))
    cats = Category.query.all()
    return render_template('admin/categories.html', categories=cats, form=form)


@admin_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    cat = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=cat)
    if form.validate_on_submit():
        cat.name = form.name.data
        cat.description = form.description.data
        db.session.commit()
        flash('Kategoriya yangilandi!', 'success')
        return redirect(url_for('admin.categories'))
    return render_template('admin/category_form.html', form=form, title="Kategoriyani tahrirlash", category=cat)


@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@admin_required
def delete_category(category_id):
    cat = Category.query.get_or_404(category_id)
    if cat.products.count() > 0:
        flash('Bu kategoriyada mahsulotlar bor. Avval mahsulotlarni boshqa kategoriyaga o-tkazing.', 'danger')
        return redirect(url_for('admin.categories'))
    db.session.delete(cat)
    db.session.commit()
    flash('Kategoriya o-chirildi.', 'success')
    return redirect(url_for('admin.categories'))


# -- Reports -----------------------------------------------
@admin_bp.route('/reports')
@admin_required
def reports():
    from sqlalchemy import func
    from datetime import datetime, timedelta

    # Top students by balance
    top_by_balance = db.session.query(User, Wallet.balance)\
        .join(Wallet, User.id == Wallet.user_id)\
        .filter(User.role == 'student')\
        .order_by(Wallet.balance.desc()).limit(10).all()

    # Total coins distributed
    total_earned = db.session.query(func.sum(Transaction.amount))\
        .filter(Transaction.type == 'earn').scalar() or 0
    total_spent = db.session.query(func.sum(Transaction.amount))\
        .filter(Transaction.type == 'spend').scalar() or 0

    # Orders by status
    orders_by_status = db.session.query(Order.status, func.count(Order.id))\
        .group_by(Order.status).all()

    # Most purchased products
    top_products = db.session.query(Product.title, func.count(Order.id).label('cnt'))\
        .join(Order, Product.id == Order.product_id)\
        .group_by(Product.id).order_by(func.count(Order.id).desc()).limit(5).all()

    return render_template('admin/reports.html',
                           top_by_balance=top_by_balance,
                           total_earned=total_earned,
                           total_spent=total_spent,
                           orders_by_status=orders_by_status,
                           top_products=top_products)


# -- Settings ----------------------------------------------
@admin_bp.route('/settings', methods=['GET', 'POST'])
@strict_admin
def settings():
    total_users = User.query.count()
    total_products = Product.query.count()
    total_txns = Transaction.query.count()

    setting = EconomySetting.query.first()
    if not setting:
        setting = EconomySetting()
        db.session.add(setting)
        db.session.commit()

    form = EconomySettingsForm(obj=setting)

    if request.method == 'GET':
        open_days = []
        if setting.store_open_days:
            for part in setting.store_open_days.split(','):
                part = part.strip()
                if part.isdigit():
                    open_days.append(int(part))
        form.open_mon.data = 0 in open_days
        form.open_tue.data = 1 in open_days
        form.open_wed.data = 2 in open_days
        form.open_thu.data = 3 in open_days
        form.open_fri.data = 4 in open_days
        form.open_sat.data = 5 in open_days
        form.open_sun.data = 6 in open_days

    if form.validate_on_submit():
        setting.xp_per_coin = form.xp_per_coin.data
        setting.level_2_xp = form.level_2_xp.data
        setting.level_3_xp = form.level_3_xp.data
        setting.level_2_min_price = form.level_2_min_price.data
        setting.level_3_min_price = form.level_3_min_price.data

        days = []
        if form.open_mon.data: days.append(0)
        if form.open_tue.data: days.append(1)
        if form.open_wed.data: days.append(2)
        if form.open_thu.data: days.append(3)
        if form.open_fri.data: days.append(4)
        if form.open_sat.data: days.append(5)
        if form.open_sun.data: days.append(6)
        setting.store_open_days = ','.join(str(d) for d in days)

        db.session.commit()
        flash("Economy sozlamalari saqlandi.", 'success')
        return redirect(url_for('admin.settings'))

    return render_template('admin/settings.html',
                           total_users=total_users,
                           total_products=total_products,
                           total_txns=total_txns,
                           form=form)

# -- Quests ------------------------------------------------
@admin_bp.route('/quests')
@admin_required
def quests():
    quests_list = Quest.query.all()
    return render_template('admin/quests.html', quests=quests_list)

@admin_bp.route('/quests/create', methods=['GET', 'POST'])
@strict_admin
def create_quest():
    form = QuestForm()
    if form.validate_on_submit():
        q = Quest(
            title=form.title.data,
            description=form.description.data,
            reward_coins=form.reward_coins.data or 0,
            reward_xp=form.reward_xp.data or 0,
            quest_type=form.quest_type.data,
            is_active=form.is_active.data
        )
        db.session.add(q)
        db.session.commit()
        flash('Kvest yaratildi!', 'success')
        return redirect(url_for('admin.quests'))
    return render_template('admin/quest_form.html', form=form, title='Yangi kvest')

@admin_bp.route('/quests/<int:id>/edit', methods=['GET', 'POST'])
@strict_admin
def edit_quest(id):
    q = Quest.query.get_or_404(id)
    form = QuestForm(obj=q)
    if form.validate_on_submit():
        q.title = form.title.data
        q.description = form.description.data
        q.reward_coins = form.reward_coins.data or 0
        q.reward_xp = form.reward_xp.data or 0
        q.quest_type = form.quest_type.data
        q.is_active = form.is_active.data
        db.session.commit()
        flash('Kvest yangilandi!', 'success')
        return redirect(url_for('admin.quests'))
    return render_template('admin/quest_form.html', form=form, title="Kvestni tahrirlash", quest=q)

@admin_bp.route('/quests/<int:id>/toggle', methods=['POST'])
@strict_admin
def toggle_quest(id):
    q = Quest.query.get_or_404(id)
    q.is_active = not q.is_active
    db.session.commit()
    flash(f'Kvest yangilandi.', 'info')
    return redirect(url_for('admin.quests'))
