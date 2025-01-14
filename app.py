import streamlit as st
import os
import sqlite3
from datetime import date
import random
from langchain.agents import load_tools, initialize_agent, AgentType
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Database functions (moved to a separate module is recommended for larger projects)
def init_db():
    conn = sqlite3.connect("health_tracker.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            task TEXT,
            points INTEGER,
            badge TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_progress(task, points, badge=None):
    conn = sqlite3.connect("health_tracker.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_progress (date, task, points, badge) VALUES (?, ?, ?, ?)",
                   (date.today(), task, points, badge))
    conn.commit()
    conn.close()

def fetch_progress():
    conn = sqlite3.connect("health_tracker.db")
    cursor = conn.cursor()
    cursor.execute("SELECT date, task, points, badge FROM user_progress")
    data = cursor.fetchall()
    conn.close()
    return data

def generate_daily_challenge():
    challenges = [
        "Drink 2L of water today",
        "Do 15 minutes of meditation",
        "Take a 30-minute walk",
        "Eat at least 2 servings of vegetables",
    ]
    return random.choice(challenges)

# Langchain functions
def get_conversational_chain():
    llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    tools = load_tools(["serpapi", "llm-math"], llm=llm)
    agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=False) #Verbose set to false to reduce output
    prompt_template = """
        You are a helpful medical assistant. Based on the symptoms provided, give possible diagnoses and advice, fetching information from the web if needed.
        Be cautious and always recommend consulting a medical professional for definitive diagnosis and treatment.
        Additionally, recommend healthy activities such as appropriate foods to eat, whether to exercise or not, and other general wellness tips based on the symptoms.
        Always include a bold disclaimer that this information is sourced online and users should consult a doctor for definitive advice.

        Symptoms:
        {question}

        Answer:
        """
    prompt = PromptTemplate(template=prompt_template, input_variables=["question"])
    return agent, prompt

# Streamlit app
def main():
    st.set_page_config(page_title="Health Hub", layout="wide")
    st.title("Health Hub 🩺🎮")

    init_db()

    # Tabs for Symptom Checker and Health Tracker
    tabs = ["Symptom Checker", "Health Tracker"]
    selected_tab = st.sidebar.radio("Select a feature:", tabs)

    if selected_tab == "Symptom Checker":
        st.markdown(
            """
            <style>
            .header-text {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            .warning-text {
                color: red;
                font-weight: bold;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.markdown('<div class="header-text">Describe your symptoms below, and receive helpful insights!</div>', unsafe_allow_html=True)

        user_symptoms = st.text_area("Enter your symptoms:", placeholder="E.g., I have a fever and a sore throat.")

        if st.button("Analyze Symptoms"):
            if user_symptoms:
                with st.spinner("Analyzing your symptoms and providing recommendations..."):
                    try:
                        agent, prompt = get_conversational_chain()
                        response = agent.run(prompt.format(question=user_symptoms))

                        st.subheader("AI Diagnosis and Advice")
                        st.write(response)

                        st.markdown('<div class="warning-text"><b>Disclaimer:</b> The information provided is sourced online and may not be accurate. Always consult a qualified medical professional for definitive diagnosis and treatment.</div>', unsafe_allow_html=True)
                    except ValueError as ve:
                        st.error(f"Parsing error: {ve}")
                        st.info("The system encountered an issue processing the output. Please try again or rephrase your symptoms.")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                        st.info("There was an error processing your request. Please try again or consult a doctor.")
            else:
                st.warning("Please enter your symptoms.")

        st.markdown(
            """
            <div style="margin-top: 20px;">
                <h3>Important Note:</h3>
                <ul>
                    <li>The advice provided by this application is based on general online information.</li>
                    <li>It is not a substitute for professional medical diagnosis or treatment.</li>
                    <li>If you experience severe symptoms, please seek medical attention immediately.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    elif selected_tab == "Health Tracker":
        st.subheader("Today's Challenge")
        daily_challenge = generate_daily_challenge()
        st.info(f"Challenge: {daily_challenge}")
        if st.button("Complete Challenge"):
            log_progress(task=daily_challenge, points=10, badge="Challenger")
            st.success("Challenge completed! You earned 10 points and a 'Challenger' badge!")

        st.subheader("Health Trivia")
        trivia_question = "How much water should an average adult drink daily?"
        trivia_options = ["1L", "2L", "3L", "4L"]
        correct_answer = "2L"

        user_answer = st.radio("Choose your answer:", trivia_options)
        if st.button("Submit Answer"):
            if user_answer == correct_answer:
                st.success("Correct! You earned 5 points.")
                log_progress(task="Answered trivia correctly", points=5)
            else:
                st.error("Incorrect. Try again next time.")

        st.subheader("Your Progress")
        progress_data = fetch_progress()
        if progress_data:
            for entry in progress_data:
                st.write(f"- Date: {entry[0]}, Task: {entry[1]}, Points: {entry[2]}, Badge: {entry[3]}")
        else:
            st.info("No progress logged yet. Start completing tasks!")

        st.sidebar.title("Leaderboard")
        st.sidebar.write("Top performers coming soon!")


if __name__ == "__main__":
    main()