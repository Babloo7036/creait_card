from groq import Groq
import os
from typing import Dict, Optional
import re

class CreditCardAgent:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.sessions: Dict[str, Dict] = {}
        self.questions = [
            {"key": "income", "text": "What is your monthly income in INR?", "validation": self.validate_income},
            {"key": "spending_fuel", "text": "How much do you spend monthly on fuel (in INR)?", "validation": self.validate_amount},
            {"key": "spending_travel", "text": "How much do you spend monthly on travel (in INR)?", "validation": self.validate_amount},
            {"key": "spending_groceries", "text": "How much do you spend monthly on groceries (in INR)?", "validation": self.validate_amount},
            {"key": "spending_dining", "text": "How much do you spend monthly on dining (in INR)?", "validation": self.validate_amount},
            {"key": "benefits", "text": "Which benefit do you prefer? (cashback, travel points, lounge access)", "validation": self.validate_benefits},
            {"key": "existing_cards", "text": "Do you have any credit cards? If yes, list them (or say 'none').", "validation": lambda x: x},
            {"key": "credit_score", "text": "What’s your approximate credit score? (300-900, or 'unknown')", "validation": self.validate_credit_score}
        ]

    def start_session(self) -> str:
        session_id = str(len(self.sessions) + 1)
        self.sessions[session_id] = {"step": 0, "data": {}, "history": []}
        return session_id

    def get_next_question(self, session_id: str) -> str:
        session = self.sessions.get(session_id)
        if not session or session["step"] >= len(self.questions):
            return "All questions answered. Ready to recommend cards?"
        return self.questions[session["step"]]["text"]

    def validate_income(self, answer: str) -> Optional[str]:
        try:
            income = float(answer)
            if income < 0:
                return "Income cannot be negative. Please provide a valid monthly income."
            return None
        except ValueError:
            return "Please enter a valid number for your income."

    def validate_amount(self, answer: str) -> Optional[str]:
        try:
            amount = float(answer)
            if amount < 0:
                return "Amount cannot be negative. Please provide a valid amount."
            return None
        except ValueError:
            return "Please enter a valid number for your spending."

    def validate_benefits(self, answer: str) -> Optional[str]:
        benefits = ["cashback", "travel points", "lounge access"]
        if answer.lower() not in benefits:
            return f"Please choose one of: {', '.join(benefits)}."
        return None

    def validate_credit_score(self, answer: str) -> Optional[str]:
        if answer.lower() == "unknown":
            return None
        try:
            score = int(answer)
            if 300 <= score <= 900:
                return None
            return "Credit score must be between 300 and 900, or 'unknown'."
        except ValueError:
            return "Please enter a valid credit score (300-900) or 'unknown'."

    def process_answer(self, session_id: str, answer: str) -> str:
        session = self.sessions.get(session_id)
        if not session or session["step"] >= len(self.questions):
            return "All questions answered. Ready to recommend cards?"
        
        current_question = self.questions[session["step"]]
        validation_error = current_question["validation"](answer)
        if validation_error:
            # Use Groq to generate a polite re-ask message
            prompt = f"The user provided an invalid answer: '{answer}' for the question: '{current_question['text']}'. The error is: '{validation_error}'. Politely explain the error and re-ask the question."
            response = self.client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            return response.choices[0].message.content
        
        session["data"][current_question["key"]] = answer
        session["history"].append({"role": "user", "content": answer})
        session["step"] += 1
        
        next_question = self.get_next_question(session_id)
        if "recommend cards" in next_question.lower():
            return next_question
        
        # Use Groq to generate a context-aware next question
        history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in session["history"]])
        prompt = f"You are a friendly credit card recommendation assistant. Based on the conversation history:\n{history}\nAsk this question: {next_question}. Keep the tone concise and professional."
        response = self.client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        return response.choices[0].message.content

    def get_user_data(self, session_id: str) -> Dict:
        return self.sessions.get(session_id, {}).get("data", {})