from flask import Flask, request, jsonify
from agent import CreditCardAgent
from recommendation import recommend_cards
import sqlite3
import json
import os

app = Flask(__name__)

# Initialize Groq agent
agent = CreditCardAgent()

# SQLite database connection
def get_db_connection():
    # Use relative path for local dev, override with DB_PATH for Render
    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_db_path = os.path.join(base_dir, "data", "credit_cards.db")
    db_path = os.getenv("DB_PATH", default_db_path)
    # Ensure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database with sample data
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credit_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            issuer TEXT,
            annual_fee INTEGER,
            reward_type TEXT,
            reward_rate TEXT,
            min_income INTEGER,
            min_credit_score INTEGER,
            perks TEXT,
            apply_link TEXT,
            img_url TEXT
        )
    ''')
    # Load sample data from JSON
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cards.json")
    with open(json_path, 'r') as f:
        cards = json.load(f)
    cursor.executemany('''
        INSERT OR IGNORE INTO credit_cards (name, issuer, annual_fee, reward_type, reward_rate, min_income, min_credit_score, perks, apply_link, img_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [(c['name'], c['issuer'], c['annual_fee'], c['reward_type'], c['reward_rate'], 
           c['eligibility']['min_income'], c['eligibility']['min_credit_score'], 
           json.dumps(c['perks']), c['apply_link'], c['img_url']) for c in cards])
    conn.commit()
    conn.close()

@app.route('/start_session', methods=['POST'])
def start_session():
    session_id = agent.start_session()
    question = agent.get_next_question(session_id)
    return jsonify({"session_id": session_id, "question": question})

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.json
    session_id = data['session_id']
    answer = data['answer']
    next_question = agent.process_answer(session_id, answer)
    return jsonify({"question": next_question})

@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    session_id = request.json['session_id']
    user_data = agent.get_user_data(session_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM credit_cards')
    cards = [dict(row) for row in cursor.fetchall()]
    conn.close()
    recommendations = recommend_cards(user_data, cards)
    return jsonify({"recommendations": recommendations})

if __name__ == '__main__':
    init_db()
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)