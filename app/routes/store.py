from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Product, Category, Event
from app.services.order_service import purchase_product
from app.services.economy_service import is_store_open, get_required_level, get_next_level_xp
from datetime import date

store_bp = Blueprint('store', __name__)


@store_bp.route('/store')
@login_required
def store():
    category_id = request.args.get('category', type=int)
    sort = request.args.get('sort', 'price_asc')
    search = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)

    query = Product.query.filter_by(is_active=True)

    if search:
        query = query.filter(Product.title.ilike(f'%{search}%'))

    if category_id:
        query = query.filter_by(category_id=category_id)

    if sort == 'price_asc':
        query = query.order_by(Product.price_coin.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price_coin.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.paginate(page=page, per_page=12)
    categories = Category.query.all()

    store_open = is_store_open()
    required_levels = {p.id: get_required_level(p.price_coin) for p in products.items}
    next_level_xp = get_next_level_xp(current_user.level or 1)
    current_xp = current_user.xp or 0
    progress_pct = 100 if not next_level_xp else int(min(100, (current_xp / next_level_xp) * 100))
    remaining_xp = None if not next_level_xp else max(0, next_level_xp - current_xp)

    today = date.today()
    active_events = Event.query.filter(
        Event.is_active == True,
        (Event.start_date == None) | (Event.start_date <= today),
        (Event.end_date == None) | (Event.end_date >= today)
    ).all()

    return render_template('store/store.html',
                           products=products,
                           categories=categories,
                           selected_category=category_id,
                           sort=sort,
                           search=search,
                           store_open=store_open,
                           required_levels=required_levels,
                           next_level_xp=next_level_xp,
                           current_xp=current_xp,
                           progress_pct=progress_pct,
                           remaining_xp=remaining_xp,
                           active_events=active_events)


@store_bp.route('/store/<int:product_id>')
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    can_afford = current_user.coin_balance >= product.price_coin
    shortage = max(0, product.price_coin - current_user.coin_balance)
    store_open = is_store_open()
    required_level = get_required_level(product.price_coin)
    has_level = (current_user.level or 1) >= required_level
    return render_template('store/product_detail.html',
                           product=product,
                           can_afford=can_afford,
                           shortage=shortage,
                           store_open=store_open,
                           required_level=required_level,
                           has_level=has_level)


@store_bp.route('/store/<int:product_id>/buy', methods=['POST'])
@login_required
def buy_product(product_id):
    success, message, order = purchase_product(current_user, product_id)
    if success:
        flash(message, 'success')
        return redirect(url_for('student.orders'))
    else:
        flash(message, 'danger')
        return redirect(url_for('store.product_detail', product_id=product_id))
