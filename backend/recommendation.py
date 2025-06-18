import json
import re
from typing import Dict, List

def parse_reward_rate(reward_rate: str, spending_category: str) -> float:
    """Parse reward rate to extract percentage or points for a specific category."""
    try:
        # Extract percentage or points from reward_rate (e.g., "5% on online spends, 1% on others")
        patterns = [
            r"(\d+\.?\d*)\s*(?:%|points|NeuCoins|miles)\s*on\s*(\w+)",  # Matches "5% on online" or "5 points on travel"
            r"(\d+\.?\d*)\s*(?:%|points|NeuCoins|miles)"  # Fallback for general rate
        ]
        for pattern in patterns:
            matches = re.findall(pattern, reward_rate)
            for match in matches:
                rate, category = (float(match[0]), match[1]) if len(match) == 2 else (float(match[0]), "others")
                if category.lower() in spending_category.lower() or category == "others":
                    return rate / 100 if "%" in reward_rate else rate
        return 0.01  # Default to 1% or 1 point if no match
    except:
        return 0.01  # Fallback for unparsable rates

def calculate_reward_simulation(spending: Dict, card: Dict) -> float:
    """Calculate estimated annual rewards based on user spending and card reward rate."""
    reward_type = card["reward_type"].lower()
    total_rewards = 0
    spending_categories = {
        "spending_fuel": "fuel",
        "spending_travel": "travel",
        "spending_groceries": "groceries",
        "spending_dining": "dining"
    }
    for spend_key, category in spending_categories.items():
        spend_amount = float(spending.get(spend_key, 0))
        reward_rate = parse_reward_rate(card["reward_rate"], category)
        if reward_type in ["cashback", "discount"]:
            total_rewards += spend_amount * 12 * reward_rate  # Cashback as INR
        elif reward_type in ["points", "miles", "neucoins", "fuel points"]:
            total_rewards += spend_amount * 12 / 100 * reward_rate  # Points per ₹100 spent
        else:  # Custom or other
            total_rewards += spend_amount * 12 * 0.01  # Default 1% equivalent
    return total_rewards

def calculate_score(user_data: Dict, card: Dict) -> float:
    """Calculate a score for the card based on user preferences."""
    score = 0
    # Eligibility match
    if float(user_data.get("income", 0)) >= card["min_income"]:
        score += 30
    if user_data.get("credit_score", "unknown") == "unknown" or (user_data.get("credit_score") and int(user_data["credit_score"]) >= card["min_credit_score"]):
        score += 30
    # Spending match
    spending = {k: float(user_data.get(k, 0)) for k in ["spending_fuel", "spending_travel", "spending_groceries", "spending_dining"]}
    max_spend_category = max(spending, key=spending.get, default="spending_dining").replace("spending_", "")
    if any(max_spend_category in perk.lower() for perk in json.loads(card["perks"])):
        score += 30
    # Benefits match
    if user_data.get("benefits", "").lower() in [p.lower() for p in json.loads(card["perks"])] or \
       user_data.get("benefits", "").lower() == card["reward_type"].lower():
        score += 20
    # Fee affordability
    if card["annual_fee"] < float(user_data.get("income", 0)) * 0.1:
        score += 10
    return score

def recommend_cards(user_data: Dict, cards: List[Dict]) -> List[Dict]:
    """Generate top 5 card recommendations based on user data."""
    recommendations = []
    for card in cards:
        if user_data.get("existing_cards", "none").lower() != "none" and card["name"].lower() in user_data["existing_cards"].lower():
            continue
        score = calculate_score(user_data, card)
        reward = calculate_reward_simulation(user_data, card)
        reward_label = "cashback" if card["reward_type"] in ["cashback", "discount"] else card["reward_type"]
        recommendations.append({
            "name": card["name"],
            "issuer": card["issuer"],
            "annual_fee": card["annual_fee"],
            "reward_type": card["reward_type"],
            "reward_rate": card["reward_rate"],
            "perks": json.loads(card["perks"]),
            "apply_link": card["apply_link"],
            "img_url": card["img_url"],
            "score": score,
            "reward_simulation": f"You could earn ₹{int(reward)}/year in {reward_label}" if card["reward_type"] in ["cashback", "discount"] else f"You could earn {int(reward)}/year {reward_label}",
            "reasons": [
                f"Matches your preference for {user_data.get('benefits', 'benefits')}",
                f"Suitable for your {max([k for k in user_data if k.startswith('spending_')], key=lambda x: float(user_data.get(x, 0))).replace('spending_', '')} spending"
            ]
        })
    return sorted(recommendations, key=lambda x: x["score"], reverse=True)[:5]