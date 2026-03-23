import os
from flask import current_app
from app import db
from app.models import Transaction, Order, UserAchievement, Notification, Wallet


def delete_user_account(user):
    """Delete user and all related data safely."""
    # Detach creator references to avoid FK issues
    Transaction.query.filter_by(created_by=user.id).update({'created_by': None}, synchronize_session=False)

    # Remove user-owned records
    Transaction.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Order.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    UserAchievement.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Notification.query.filter_by(user_id=user.id).delete(synchronize_session=False)

    # Remove wallet
    if user.wallet:
        db.session.delete(user.wallet)

    # Remove avatar file if exists
    if user.avatar:
        try:
            file_path = os.path.join(current_app.root_path, 'static', user.avatar)
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass

    db.session.delete(user)
    db.session.commit()
