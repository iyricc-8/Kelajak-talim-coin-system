from datetime import datetime, timedelta
from app import db
from app.models import Order, Product, Notification
from app.services.coin_service import deduct_coins, check_and_award_achievements
from app.services.economy_service import get_required_level, is_store_open


def purchase_product(user, product_id):
    """
    Full purchase flow:
    1. Check product is active and in stock
    2. Check user balance
    3. Deduct coins
    4. Create order
    5. Update stock
    6. Send notification
    Returns (success: bool, message: str, order: Order|None)
    """
    product = Product.query.get(product_id)

    if not product:
        return False, 'Mahsulot topilmadi.', None

    if not is_store_open():
        return False, "Do'kon faqat chorshanba va shanba kunlari ochiq.", None

    if not product.is_active:
        return False, 'Bu mahsulotni sotib olish mumkin emas.', None

    if product.stock <= 0:
        return False, 'Mahsulot tugagan.', None

    required_level = get_required_level(product.price_coin)
    if (user.level or 1) < required_level:
        return False, f"Bu mahsulot uchun {required_level}-daraja kerak. Sizning darajangiz: {user.level or 1}.", None

    balance = user.coin_balance
    if balance < product.price_coin:
        shortage = product.price_coin - balance
        return False, f'Bu xarid uchun {shortage} Coin yetmaydi.', None

    # Check Purchase Limits to preserve Gamification Budget
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    
    # 1. 1 purchase per week limit
    recent_order = Order.query.filter(Order.user_id == user.id, Order.created_at >= seven_days_ago).first()
    if recent_order:
        return False, "Siz haftasiga faqat 1 ta mahsulot xarid qila olasiz. Keyingi haftani kuting!", None

    # 2. Level category limits (monthly)
    orders_last_month = Order.query.filter(Order.user_id == user.id, Order.created_at >= thirty_days_ago).all()
    
    cheap_count = 0
    expensive_count = 0
    
    for o in orders_last_month:
        if o.product:
            req_lvl = get_required_level(o.product.price_coin)
            if req_lvl == 1:
                cheap_count += 1
            if req_lvl >= 4:
                expensive_count += 1

    if required_level == 1 and cheap_count >= 2:
        return False, "Siz bu oy uchun arzon (Level 1) mahsulotlar limitini (2 ta) tugatdingiz.", None
        
    if required_level >= 4 and expensive_count >= 1:
        return False, "Siz bu oy uchun qimmat (Level 4+) mahsulot limitini (1 ta) tugatdingiz.", None

    # Deduct coins
    txn = deduct_coins(
        user=user,
        amount=product.price_coin,
        reason=f'Xarid: {product.title}',
        created_by_id=user.id
    )
    if txn is False:
        return False, 'Hisobda Coin yetarli emas.', None

    # Create order
    order = Order(
        user_id=user.id,
        product_id=product.id,
        price_at_purchase=product.price_coin,
        status='new'
    )
    db.session.add(order)

    # Reduce stock (but not for infinite stock items like digital bonuses)
    if product.stock < 999:
        product.stock -= 1

    # Notification
    notif = Notification(
        user_id=user.id,
        title='Buyurtma rasmiylashtirildi!',
        message=f'Siz "{product.title}" ni {product.price_coin} Coin ga buyurtma qildingiz. Holat: tasdiqlanishi kutilmoqda.'
    )
    db.session.add(notif)
    db.session.commit()

    # Check achievements after purchase
    check_and_award_achievements(user)

    return True, "Mahsulot muvaffaqiyatli buyurtma qilindi! Tasdiqlashni kuting.", order


def update_order_status(order_id, new_status, comment=None):
    """Update order status (admin/teacher action)."""
    order = Order.query.get(order_id)
    if not order:
        return False, 'Buyurtma topilmadi.'

    valid_statuses = ['new', 'confirmed', 'delivered', 'cancelled']
    if new_status not in valid_statuses:
        return False, "Noto'g'ri holat."

    from datetime import datetime
    order.status = new_status
    order.updated_at = datetime.utcnow()
    if comment:
        order.comment = comment

    status_labels = {
        'confirmed': 'tasdiqlandi',
        'delivered': 'berildi',
        'cancelled': 'bekor qilindi'
    }

    if new_status in status_labels:
        notif = Notification(
            user_id=order.user_id,
            title="Buyurtma holati o'zgardi",
            message=f'Buyurtmangiz "{order.product.title}" {status_labels[new_status]}.'
        )
        db.session.add(notif)

    db.session.commit()
    return True, f'Buyurtma holati "{new_status}" ga yangilandi.'
