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
            {"key": "existing_cards", "text": "Do you have any credit cards? If yes, list them (or say 'none').", "validation": self.validate_existing_cards},
            {"key": "credit_score", "text": "What’s your approximate credit score? (300-900, or 'unknown')", "validation": self.validate_credit_score}
        ]

    def start_session(self) -> str:
        session_id = str(len(self.sessions) + 1)
        self.sessions[session_id] = {"step": 0, "data": {}, "history": []}
        return session_id

    def get_next_question(self, session_id: str) -> str:
        session = self.sessions.get(session_id)
        if not session:
            return "Error: Invalid session ID."
        if session["step"] >= len(self.questions):
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

    def validate_existing_cards(self, answer: str) -> Optional[str]:
        if not answer.strip():
            return "Please provide a response (e.g., 'none' or list your cards)."
        if answer.lower() == "none" or len(answer.strip()) > 0:
            return None
        return "Please say 'none' or list your credit cards."

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
        if not session:
            return "Error: Invalid session ID."
        if session["step"] >= len(self.questions):
            return "All questions answered. Ready to recommend cards?"
        
        current_question = self.questions[session["step"]]
        validation_error = current_question["validation"](answer)
        if validation_error:
            try:
                prompt = (
                    f"The user provided an invalid answer: '{answer}' for the question: '{current_question['text']}'. "
                    f"The error is: '{validation_error}'. Politely explain the error in one sentence and re-ask the question in another sentence. "
                    f"Keep the tone friendly and concise."
                )
                response = self.client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"Error processing answer: {str(e)}. Please try again: {current_question['text']}"
        
        session["data"][current_question["key"]] = answer
        session["history"].append({"role": "user", "content": answer})
        session["history"].append({"role": "assistant", "content": current_question["text"]})
        session["step"] += 1
        
        next_question = self.get_next_question(session_id)
        if "recommend cards" in next_question.lower():
            return next_question
        
        try:
            history_summary = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in session["history"]])
            prompt = (
                f"You are a friendly credit card recommendation assistant. The user has provided the following information:\n{history_summary}\n"
                f"Based on this, ask the next question: '{next_question}'. If relevant, reference the user's previous answers to make the question more personalized. "
                f"Keep the tone concise, professional, and friendly. Respond with only the question."
            )
            response = self.client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                    max_tokens=100
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating question: {str(e)}. Please answer: {next_question}"

    def get_user_data(self, session_id: str) -> Dict:
        return self.sessions.get(session_id, {}).get("data", {})

    def end_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]