from datetime import datetime
from app import db
from app.models import Wallet, Transaction, Notification, Achievement, UserAchievement
from app.services.economy_service import add_xp, get_active_event_multiplier


def award_coins(user, amount, reason, comment=None, created_by_id=None):
    """Award coins to a user. Creates transaction, updates wallet, checks achievements."""
    if amount <= 0:
        raise ValueError("Amount must be positive")

    multiplier = get_active_event_multiplier()
    amount = int(amount * multiplier)
    
    wallet = user.wallet
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0)
        db.session.add(wallet)
        db.session.flush()

    wallet.balance += amount
    balance_after = wallet.balance

    txn = Transaction(
        user_id=user.id,
        type='earn',
        amount=amount,
        reason=reason,
        comment=comment,
        created_by=created_by_id,
        balance_after=balance_after
    )
    db.session.add(txn)

    notif = Notification(
        user_id=user.id,
        title='Coin hisoblandi!',
        message=f'Sizga {amount} Coin hisoblandi. Sabab: {reason}'
    )
    db.session.add(notif)
    db.session.commit()

    # Check achievements after awarding
    check_and_award_achievements(user)

    return txn

def award_xp(user, amount, reason=None):
    """Award XP separately. Does not affect coins."""
    if amount <= 0:
        return 0
    gained = add_xp(user, amount)
    
    if reason:
        notif = Notification(
            user_id=user.id,
            title='+XP Tajriba Olishi!',
            message=f'Sizga {amount} XP berildi. Sabab: {reason}'
        )
        db.session.add(notif)
        
    db.session.commit()
    check_and_award_achievements(user)
    return gained


def deduct_coins(user, amount, reason, comment=None, created_by_id=None, txn_type='spend'):
    """Deduct coins from a user. Returns False if insufficient balance."""
    if amount <= 0:
        raise ValueError("Amount must be positive")

    wallet = user.wallet
    if not wallet or wallet.balance < amount:
        return False

    wallet.balance -= amount
    balance_after = wallet.balance

    txn = Transaction(
        user_id=user.id,
        type=txn_type,
        amount=amount,
        reason=reason,
        comment=comment,
        created_by=created_by_id,
        balance_after=balance_after
    )
    db.session.add(txn)

    notif = Notification(
        user_id=user.id,
        title='Coin yechildi',
        message=f'Hisobingizdan {amount} Coin yechildi. Sabab: {reason}'
    )
    db.session.add(notif)
    db.session.commit()

    return txn


def adjust_coins(user, amount, reason, comment=None, created_by_id=None):
    """Manual adjustment (can be positive or negative)."""
    if amount == 0:
        raise ValueError("Amount cannot be zero")

    wallet = user.wallet
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0)
        db.session.add(wallet)
        db.session.flush()

    if amount < 0 and wallet.balance < abs(amount):
        return False

    wallet.balance += amount
    balance_after = wallet.balance

    txn = Transaction(
        user_id=user.id,
        type='adjustment',
        amount=amount,
        reason=reason,
        comment=comment,
        created_by=created_by_id,
        balance_after=balance_after
    )
    db.session.add(txn)

    msg = f'Sizga {amount} Coin hisoblandi (tuzatish).' if amount > 0 else f'Hisobingizdan {abs(amount)} Coin tuzatish qilindi.'
    notif = Notification(
        user_id=user.id,
        title='Coin tuzatish',
        message=f'{msg} Sabab: {reason}'
    )
    db.session.add(notif)
    db.session.commit()

    return txn


def get_total_earned(user):
    """Get total coins ever earned by a user."""
    result = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == user.id,
        Transaction.type == 'earn'
    ).scalar()
    return result or 0


def get_purchase_count(user):
    """Get number of purchases by a user."""
    from app.models import Order
    return Order.query.filter_by(user_id=user.id).count()


def check_and_award_achievements(user):
    """Check and award any newly unlocked achievements."""
    active_achievements = Achievement.query.filter_by(is_active=True).all()
    user_achievement_ids = {ua.achievement_id for ua in user.achievements.all()}

    total_earned = get_total_earned(user)
    purchase_count = get_purchase_count(user)

    for achievement in active_achievements:
        if achievement.id in user_achievement_ids:
            continue

        unlocked = False
        if achievement.condition_type == 'total_earned' and total_earned >= achievement.condition_value:
            unlocked = True
        elif achievement.condition_type == 'purchases' and purchase_count >= achievement.condition_value:
            unlocked = True

        if unlocked:
            ua = UserAchievement(user_id=user.id, achievement_id=achievement.id)
            db.session.add(ua)
            notif = Notification(
                user_id=user.id,
                title='Yangi yutuq!',
                message=f'Siz "{achievement.icon} {achievement.title}" yutug\'ini oldingiz!'
            )
            db.session.add(notif)

    db.session.commit()
