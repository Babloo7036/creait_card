import streamlit as st
import requests
import json
import os

st.set_page_config(page_title="Credit Card Advisor", layout="wide")

# Use environment variable for backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")

if "session_id" not in st.session_state:
    st.session_state.session_id = None
    st.session_state.conversation = []
    st.session_state.current_question = None
    st.session_state.recommendations = None

def start_session():
    response = requests.post(f"{BACKEND_URL}/start_session")
    data = response.json()
    st.session_state.session_id = data["session_id"]
    st.session_state.current_question = data["question"]
    st.session_state.conversation.append({"role": "Assistant", "message": data["question"]})

def submit_answer(answer):
    response = requests.post(f"{BACKEND_URL}/submit_answer", json={"session_id": st.session_state.session_id, "answer": answer})
    data = response.json()
    st.session_state.conversation.append({"role": "User", "message": answer})
    st.session_state.current_question = data["question"]
    st.session_state.conversation.append({"role": "Assistant", "message": data["question"]})
    if "recommend cards" in data["question"].lower():
        get_recommendations()

def get_recommendations():
    response = requests.post(f"{BACKEND_URL}/get_recommendations", json={"session_id": st.session_state.session_id})
    st.session_state.recommendations = response.json()["recommendations"]

st.title("Credit Card Advisor")

# Chat interface
if not st.session_state.session_id:
    if st.button("Start"):
        start_session()

if st.session_state.current_question:
    st.subheader("Conversation")
    for msg in st.session_state.conversation:
        if msg["role"] == "Assistant":
            st.write(f"**Assistant**: {msg['message']}")
        else:
            st.write(f"**You**: {msg['message']}")
    
    if "recommend cards" not in st.session_state.current_question.lower():
        answer = st.text_input("Your answer:", key="answer_input")
        if st.button("Submit"):
            if answer:
                submit_answer(answer)

# Recommendations
if st.session_state.recommendations:
    st.subheader("Recommended Credit Cards")
    for rec in st.session_state.recommendations:
        with st.expander(f"{rec['name']} ({rec['issuer']})"):
            if rec["img_url"]:
                st.image(rec["img_url"], width=200)
            st.write(f"**Annual Fee**: ₹{rec['annual_fee']}")
            st.write(f"**Reward Type**: {rec['reward_type']} ({rec['reward_rate']})")
            st.write(f"**Perks**: {', '.join(rec['perks'])}")
            st.write(f"**Estimated Rewards**: {rec['reward_simulation']}")
            st.write(f"**Why Recommended**: {', '.join(rec['reasons'])}")
            st.write(f"[Apply Now]({rec['apply_link']})")
    
    if st.button("Compare Cards"):
        st.subheader("Card Comparison")
        st.table([
            {
                "Name": rec["name"],
                "Issuer": rec["issuer"],
                "Annual Fee": rec["annual_fee"],
                "Reward Rate": rec["reward_rate"],
                "Perks": ", ".join(rec["perks"])
            } for rec in st.session_state.recommendations
        ])
    
    if st.button("Restart"):
        st.session_state.session_id = None
        st.session_state.conversation = []
        st.session_state.current_question = None
        st.session_state.recommendations = None