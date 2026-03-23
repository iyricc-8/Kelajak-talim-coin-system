from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Transaction

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/transactions')
@login_required
def transactions():
    page = request.args.get('page', 1, type=int)
    txn_type = request.args.get('type', '')

    query = Transaction.query.filter_by(user_id=current_user.id)
    if txn_type:
        query = query.filter_by(type=txn_type)

    txns = query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=25)
    return render_template('student/transactions.html', txns=txns, txn_type=txn_type)
