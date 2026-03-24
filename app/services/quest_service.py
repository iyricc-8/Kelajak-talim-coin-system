from datetime import datetime, date, timedelta
from app import db
from app.models import User, Quest, UserQuest, Notification
from app.services.coin_service import award_coins, award_xp


def process_daily_activity(user):
    """
    Called when a user logs in or completes an activity to update their streak.
    Streak logic:
    - If last_active_date is today -> do nothing
    - If last_active_date is yesterday -> increment streak
    - If last_active_date is older -> reset streak to 1
    
    Milestones: 3 days -> +5 coins, 7 days -> +10 coins, 14+ days -> +20 coins
    """
    today = date.today()
    
    if user.last_active_date == today:
        return False, None
        
    yesterday = today - timedelta(days=1)
    
    if user.last_active_date == yesterday:
        user.streak = (user.streak or 0) + 1
    else:
        user.streak = 1
        
    user.last_active_date = today
    
    # Check milestones
    bonus_coins = 0
    if user.streak == 3:
        bonus_coins = 5
    elif user.streak == 7:
        bonus_coins = 10
    elif user.streak >= 14 and user.streak % 7 == 0:  # Every 7 days after 14? User requested "14 days -> 20 coins", assume every subsequent week or just once.
        bonus_coins = 20
        
    if bonus_coins > 0:
        award_coins(
            user=user,
            amount=bonus_coins,
            reason=f'{user.streak} kunlik streak bonusi!',
            created_by_id=None
        )
        
    db.session.commit()
    return True, bonus_coins


def get_user_quests(user):
    """Get active quests for the user."""
    # This can be expanded to automatically assign random quests daily
    now = datetime.utcnow()
    quests = db.session.query(Quest, UserQuest).outerjoin(
        UserQuest, (UserQuest.quest_id == Quest.id) & (UserQuest.user_id == user.id)
    ).filter(Quest.is_active == True).all()
    
    result = []
    for quest, uq in quests:
        if uq and uq.is_completed:
            status = 'completed'
        else:
            status = 'active'
        result.append({
            'quest': quest,
            'status': status,
            'user_quest': uq
        })
    return result


def complete_quest(user, quest_id):
    """Mark a quest as completed and give rewards."""
    quest = Quest.query.get(quest_id)
    if not quest or not quest.is_active:
        return False, "Kvest topilmadi yoki nofaol."
        
    uq = UserQuest.query.filter_by(user_id=user.id, quest_id=quest_id).first()
    if uq and uq.is_completed:
        return False, "Siz bu kvestni allaqachon bajargansiz."
        
    if not uq:
        uq = UserQuest(user_id=user.id, quest_id=quest.id)
        db.session.add(uq)
        
    uq.is_completed = True
    uq.completed_at = datetime.utcnow()
    
    # Give rewards
    if quest.reward_coins > 0:
        award_coins(user, quest.reward_coins, f"Kvest: {quest.title}")
    if quest.reward_xp > 0:
        award_xp(user, quest.reward_xp, f"Kvest: {quest.title}")
        
    db.session.commit()
    return True, f"Kvest muvaffaqiyatli bajarildi! +{quest.reward_coins} Coin, +{quest.reward_xp} XP."
