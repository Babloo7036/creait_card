import json
from typing import Dict, List

def calculate_reward_simulation(spending: Dict, card: Dict) -> float:
    reward_rate = float(card["reward_rate"].split()[0]) / 100 if card["reward_type"] == "cashback" else 0
    total_spending = sum(float(spending.get(key, 0)) for key in ["spending_fuel", "spending_travel", "spending_groceries", "spending_dining"])
    return total_spending * 12 * reward_rate

def calculate_score(user_data: Dict, card: Dict) -> float:
    score = 0
    # Eligibility match
    if float(user_data.get("income", 0)) >= card["min_income"]:
        score += 30
    if user_data.get("credit_score", "unknown") == "unknown" or (user_data.get("credit_score") and int(user_data["credit_score"]) >= card["min_credit_score"]):
        score += 30
    # Spending match
    spending = {k: float(user_data.get(k, 0)) for k in ["spending_fuel", "spending_travel", "spending_groceries", "spending_dining"]}
    max_spend_category = max(spending, key=spending.get, default="spending_dining")
    if any(max_spend_category.replace("spending_", "") in perk.lower() for perk in json.loads(card["perks"])):
        score += 30
    # Benefits match
    if user_data.get("benefits", "").lower() in [p.lower() for p in json.loads(card["perks"])]:
        score += 20
    # Fee affordability
    if card["annual_fee"] < float(user_data.get("income", 0)) * 0.1:
        score += 10
    return score

def recommend_cards(user_data: Dict, cards: List[Dict]) -> List[Dict]:
    recommendations = []
    for card in cards:
        if user_data.get("existing_cards", "none").lower() != "none" and card["name"].lower() in user_data["existing_cards"].lower():
            continue
        score = calculate_score(user_data, card)
        reward = calculate_reward_simulation(user_data, card)
        recommendations.append({
            "name": card["name"],
            "issuer": card["issuer"],
            "annual_fee": card["annual_fee"],
            "reward_type": card["reward_type"],
            "reward_rate": card["reward_rate"],
            "perks": json.loads(card["perks"]),
            "apply_link": card["apply_link"],
            "score": score,
            "reward_simulation": f"You could earn ₹{int(reward)}/year {card['reward_type']}",
            "reasons": [
                f"Matches your {user_data.get('benefits', 'preferred benefits')}",
                f"Suitable for your {max([k for k in user_data if k.startswith('spending_')], key=lambda x: float(user_data.get(x, 0))).replace('spending_', '')} spending"
            ]
        })
    return sorted(recommendations, key=lambda x: x["score"], reverse=True)[:5]