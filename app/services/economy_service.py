from datetime import datetime
from flask import current_app
from app.models import EconomySetting


def _get_settings():
    settings = EconomySetting.query.first()
    if not settings:
        return {
            'xp_per_coin': current_app.config.get('XP_PER_COIN', 3),
            'level_2_xp': current_app.config.get('LEVEL_2_XP', 300),
            'level_3_xp': current_app.config.get('LEVEL_3_XP', 800),
            'level_2_min_price': current_app.config.get('LEVEL_2_MIN_PRICE', 100),
            'level_3_min_price': current_app.config.get('LEVEL_3_MIN_PRICE', 250),
            'store_open_days': current_app.config.get('STORE_OPEN_DAYS', (2, 5)),
        }

    days = []
    if settings.store_open_days:
        for part in settings.store_open_days.split(','):
            part = part.strip()
            if part.isdigit():
                days.append(int(part))
    if not days:
        days = list(current_app.config.get('STORE_OPEN_DAYS', (2, 5)))

    return {
        'xp_per_coin': settings.xp_per_coin,
        'level_2_xp': settings.level_2_xp,
        'level_3_xp': settings.level_3_xp,
        'level_2_min_price': settings.level_2_min_price,
        'level_3_min_price': settings.level_3_min_price,
        'store_open_days': days,
    }


def get_level_thresholds():
    settings = _get_settings()
    return (
        settings.get('level_2_xp', 300),
        settings.get('level_3_xp', 800)
    )


def resolve_level(xp):
    l2, l3 = get_level_thresholds()
    level = 1
    if xp >= l2: level = 2
    if xp >= l3: level = 3
    return level


def get_next_level_xp(level):
    l2, l3 = get_level_thresholds()
    if level < 2: return l2
    if level == 2: return l3
    return None


def add_xp(user, amount):
    """Directly add XP to user, separate from coins."""
    gained = max(0, amount)
    user.xp = (user.xp or 0) + gained
    user.level = resolve_level(user.xp)
    return gained


def get_xp_per_coin():
    settings = _get_settings()
    value = settings.get('xp_per_coin', 0)
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 0
    return max(0, value)


def get_required_level(price_coin):
    settings = _get_settings()
    # Simple logic for determining what level is required based on price
    # Based on user request: cheap < 200 (lvl 1), medium 200-700 (lvl 2), expensive 700+ (lvl 3)
    if price_coin >= 700:
        return 3
    if price_coin >= 200:
        return 2
    return 1


def is_store_open(now=None):
    now = now or datetime.now()
    open_days = _get_settings()['store_open_days']
    return now.weekday() in open_days
