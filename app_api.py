import streamlit as st
import pandas as pd
import sqlite3
import requests
import json
import datetime
import os
# from dotenv import load_dotenv

# Load environment variables
# load_dotenv()

# Read the Gemini API key from environment variable
def get_api_key():
    """
    Retrieve Gemini API key from Streamlit secrets or fallback methods.
    """
    # Retrieve from secrets, ensuring it's a clean string
    try:
        api_key = st.secrets["gemini"] if "gemini" in st.secrets else None
    except Exception as e:
        st.error(f"Error retrieving API key from secrets: {e}")
        api_key = None
    
    # # User input fallback
    # if not api_key:
    #     api_key = st.text_input("Enter your Gemini API Key", type="password")
    
    return api_key


# Gemini API endpoint
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("dtl_data.db")
    cursor = conn.cursor()
    # Create tables if not exists (existing table creation code)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            knows_autonomous TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            response TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user_id INTEGER,
            parent_comment_id INTEGER,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(post_id) REFERENCES posts(id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(parent_comment_id) REFERENCES comments(id)
        )
    ''')
    # Add regulations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_posts():
    conn = sqlite3.connect("dtl_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT posts.id, users.name, posts.content, posts.created_at
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.created_at DESC
    """)
    posts = cursor.fetchall()
    conn.close()
    return posts

def insert_comment(post_id, user_id, content, parent_comment_id=None):
    conn = sqlite3.connect("dtl_data.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO comments (post_id, user_id, content, parent_comment_id) VALUES (?, ?, ?, ?)",
        (post_id, user_id, content, parent_comment_id)
    )
    conn.commit()
    conn.close()


def call_gemini_api(prompt, api_key):
    api_key=str(api_key)
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

    payload = {
        "prompt": {
            "text": prompt
        },
        "temperature": 0.7,
        "maxOutputTokens": 1024
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        response_data = response.json()
        generated_text = response_data['candidates'][0]['output']
        
        return generated_text
    
    except requests.exceptions.RequestException as e:
        st.error(f"API Request Error: {e}")
        return None
    except (KeyError, IndexError) as e:
        st.error(f"Response Parsing Error: {e}")
        return None

# Regulation Generation Function
def generate_regulation(users, responses, api_key):
    """
    Generate comprehensive regulations using Gemini API
    """
    prompt = """
    As an expert AI ethics consultant, create comprehensive ethical guidelines 
    for autonomous vehicle development based on the following user perspectives.

    Analyze the collected insights considering:
    - Ethical decision-making frameworks
    - Human life prioritization
    - Transparency in AI decision processes
    - Balancing individual and collective safety

    User Perspectives Compilation:
    """
    
    # Add user responses to the prompt
    for user in users:
        user_id, name, age, gender, knows_autonomous, timestamp = user
        prompt += f"\n- User Profile: {age} y/o {gender}, Autonomous Vehicle Knowledge: {knows_autonomous}"
    
    # Add detailed response information
    for response in responses:
        user_id, question, answer = response
        prompt += f"\n- Critical Question: {question}\n  User Response: {answer}"
    
    prompt += """

    Deliverable Guidelines Requirements:
    1. Provide clear, actionable recommendations
    2. Address potential moral and ethical conflicts
    3. Ensure transparency in autonomous vehicle decision-making
    4. Consider diverse perspectives and edge cases
    5. Create a robust ethical framework for AI developers

    Format your response using markdown, with clear sections and bullet points.
    """

    # Call Gemini API
    try:
        regulation = call_gemini_api(prompt, api_key)
        
        if regulation:
            store_regulation(regulation)
        
        return regulation
    except Exception as e:
        st.error(f"Regulation generation error: {e}")
        return None

# Store Regulation Function
def store_regulation(regulation):
    """
    Store generated regulation in SQLite database
    """
    conn = sqlite3.connect("dtl_data.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO regulations (content) VALUES (?)", 
        (regulation,)
    )
    
    conn.commit()
    conn.close()

# Existing functions for user and forum interactions remain the same
def insert_user(name, age, gender, knows_autonomous):
    conn = sqlite3.connect("dtl_data.db")
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO users (name, age, gender, knows_autonomous, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (name, age, gender, knows_autonomous, timestamp))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id

def insert_responses(user_id, responses):
    conn = sqlite3.connect("dtl_data.db")
    cursor = conn.cursor()
    for question, response in responses.items():
        cursor.execute("""
            INSERT INTO responses (user_id, question, response)
            VALUES (?, ?, ?)
        """, (user_id, question, response))
    conn.commit()
    conn.close()

# Functions to handle posts and comments
def insert_post(user_id, content):
    conn = sqlite3.connect("dtl_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO posts (user_id, content) VALUES (?, ?)", (user_id, content))
    conn.commit()
    conn.close()

def get_comments(post_id):
    conn = sqlite3.connect("dtl_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT comments.id, comments.post_id, comments.user_id, comments.content, comments.created_at,
               comments.parent_comment_id, users.name
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.post_id = ?
        ORDER BY comments.created_at ASC
    """, (post_id,))
    comments = cursor.fetchall()
    conn.close()
    return comments

# Main Streamlit Application
def main():
    questions=[]
    # Page configuration
    st.set_page_config(page_title="Autonomous Vehicles Ethics App", page_icon="🚗")

    # Get API Key
    api_key = get_api_key()
    
    if not api_key:
        st.error("Please provide a valid Gemini API Key")
        return

    # Initialize database
    init_db()

    # Navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Go to", ["Home", "User Details", "Questionnaire", "Forum", "Regulation Generator", "Download Data"])

    # Home Page
    if page == "Home":
        st.title("Welcome to the Autonomous Vehicles Ethics App")
        st.write("""
            This app collects user opinions on ethical considerations for autonomous vehicles.
        Your DATA is being used for generation of regulations for ai makers to give guidelines to developers.
        Please proceed through the pages to provide your input.
        Answer All the Questions Carefully and then feel free to chat on our forum page and interact with other users.
             








             Created BY:
                Nischal R E(1RV23CS157)
                Niranjan R N(1RV23CS156)
                Pavan V(1RV23CS165)
        """)

    # Existing pages (User Details, Questionnaire) remain the same
    # 2. User Details Page
    elif page == "User Details":
        st.title("Your Details")
        st.subheader("Please provide your information:")

        name = st.text_input("Name")
        age = st.number_input("Age", min_value=0, max_value=120, step=1)
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        knows_autonomous = st.selectbox("Do you know about autonomous vehicles?", ["Yes", "No"])

        if st.button("Submit"):
            if name.strip():
                user_id = insert_user(name.strip(), age, gender, knows_autonomous)
                st.session_state['user_id'] = user_id
                st.success("Information saved!")
            else:
                st.error("Name cannot be empty.")

# 3. Questionnaire Page
    elif page == "Questionnaire":
        st.title("Ethical Questionnaire")

        questions = [
            {
                "question": "Should autonomous vehicles prioritize saving passengers over pedestrians, or should every life be treated equally?",
                "input_type": "selectbox",
                "options": ["Prioritize Passengers", "Treat Every Life Equally", "Prioritize Pedestrians"]
            },
            {
                "question": "In a situation where only one life can be saved, should age (e.g., child vs. elderly) influence the decision?",
                "input_type": "selectbox",
                "options": ["Yes, prioritize the younger", "No, every life is equal", "Not Sure"]
            },
            {
                "question": "How should autonomous vehicles handle situations involving animals on the road? Should they prioritize human safety over animal lives?",
                "input_type": "text_area"
            },
            {
                "question": "Would you feel comfortable knowing an autonomous vehicle might sacrifice your safety to save a larger group of people?",
                "input_type": "radio",
                "options": ["Yes", "No", "Maybe"]
            },
            {
                "question": "What ethical principles should guide the decisions of autonomous vehicles during accidents?",
                "input_type": "text_area"
            },
            {
                "question": "Should autonomous vehicles be programmed to follow traffic rules strictly, even if it means a higher risk of accidents?",
                "input_type": "radio",
                "options": ["Yes", "No", "Depends on the situation"]
            },
        ]

        responses = {}

        for idx, item in enumerate(questions, 1):
            st.write(f"**{idx}. {item['question']}**")
            if item["input_type"] == "radio":
                responses[f"Q{idx}"] = st.radio("", item["options"], key=f"q{idx}")
            elif item["input_type"] == "selectbox":
                responses[f"Q{idx}"] = st.selectbox("", item["options"], key=f"q{idx}")
            elif item["input_type"] == "text_area":
                responses[f"Q{idx}"] = st.text_area("", key=f"q{idx}")
            else:
                st.error("Unknown input type.")

            st.write("---")

        if st.button("Submit Answers"):
            if 'user_id' in st.session_state:
                insert_responses(st.session_state['user_id'], responses)
                st.success("Responses saved!")
            else:
                st.error("Please submit your details first.")

# 4. Forum Page
    elif page == "Forum":
        st.title("Community Forum")
        st.subheader("Interact with other users!")

        if 'user_id' in st.session_state:
            st.write("### Create a New Post")
            new_post = st.text_area("What's on your mind?", key="new_post")
            if st.button("Post", key="post_button"):
                if new_post.strip():
                    insert_post(st.session_state['user_id'], new_post.strip())
                    st.success("Post created!")
                    st.experimental_rerun()  # Refresh the page to show the new post
                else:
                    st.error("Post content cannot be empty.")
        else:
            st.warning("Please submit your details on the User Details page to post.")

        st.write("---")
        st.write("### Recent Posts")
        posts = get_posts()
        if posts:
            for post in posts:
                post_id, author_name, post_content, post_created_at = post
                st.markdown(f"**{author_name}** posted at {post_created_at}")
                st.write(post_content)

                # Display comments
                comments = get_comments(post_id)

                # Function to display comments recursively
                def display_comments(comments_list, parent_id=None, level=0):
                    for comment in comments_list:
                        comment_id = comment[0]
                        comment_post_id = comment[1]
                        comment_user_id = comment[2]
                        comment_content = comment[3]
                        comment_created_at = comment[4]
                        comment_parent_id = comment[5]
                        commenter_name = comment[6]

                        if comment_parent_id == parent_id:
                            indent = "&nbsp;" * 4 * level
                            st.markdown(f"{indent}**{commenter_name}** replied at {comment_created_at}")
                            st.markdown(f"{indent}{comment_content}")

                            # Reply to comment
                            if 'user_id' in st.session_state:
                                with st.expander(f"{indent}Reply", expanded=False):
                                    reply_content = st.text_area(f"Reply to {commenter_name}", key=f"reply_{comment_id}")
                                    if st.button(f"Submit Reply to Comment {comment_id}", key=f"submit_reply_{comment_id}"):
                                        if reply_content.strip():
                                            insert_comment(post_id, st.session_state['user_id'], reply_content.strip(), parent_comment_id=comment_id)
                                            st.success("Reply added!")
                                            st.experimental_rerun()  # Refresh to show the new reply
                                        else:
                                            st.error("Reply cannot be empty.")
                            # Recursive call to display nested comments
                            display_comments(comments_list, parent_id=comment_id, level=level+1)

                display_comments(comments)

                # Add a comment to the post
                if 'user_id' in st.session_state:
                    st.write("**Add a comment:**")
                    comment_content = st.text_input(f"Your comment on post {post_id}", key=f"comment_{post_id}")
                    if st.button(f"Submit Comment to Post {post_id}", key=f"submit_comment_{post_id}"):
                        if comment_content.strip():
                            insert_comment(post_id, st.session_state['user_id'], comment_content.strip())
                            st.success("Comment added!")
                            st.experimental_rerun()  # Refresh to show the new comment
                        else:
                            st.error("Comment cannot be empty.")
                else:
                    st.warning("Please submit your details to comment.")

                st.write("---")
        else:
            st.write("No posts yet. Be the first to post!")

    # Regulation Generator Page
    elif page == "Regulation Generator":
        st.title("Ethical Guidelines for Autonomous Vehicles")
        
        # Fetch users and responses
        conn = sqlite3.connect("dtl_data.db")
        cursor = conn.cursor()
        
        # Fetch users
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        
        # Fetch responses with questions
        cursor.execute("""
            SELECT r.user_id, 
                   CASE 
                     WHEN r.question LIKE '%prioritize%' THEN 'Should autonomous vehicles prioritize saving passengers over pedestrians?'
                     WHEN r.question LIKE '%age%' THEN 'How should age influence life-saving decisions?'
                     WHEN r.question LIKE '%animals%' THEN 'Handling situations involving animals on the road'
                     WHEN r.question LIKE '%sacrifice%' THEN 'Comfort with potential self-sacrifice for group safety'
                   END AS normalized_question, 
                   r.response 
            FROM responses r
        """)
        responses = cursor.fetchall()
        conn.close()
        
        # Check if there are enough responses
        if users and responses:
            # Button to generate regulations
            if st.button("Generate Ethical Guidelines"):
                with st.spinner("Generating comprehensive guidelines..."):
                    regulation = generate_regulation(users, responses, api_key)
                    
                    if regulation:
                        st.success("Guidelines Generated Successfully!")
                        st.markdown("### Generated Ethical Guidelines")
                        st.write(regulation)
                        
                        # Option to save to file
                        if st.button("Save Guidelines to File"):
                            with open("autonomous_vehicle_ethics_guidelines.txt", "w") as f:
                                f.write(regulation)
                            st.success("Guidelines saved to 'autonomous_vehicle_ethics_guidelines.txt'")
                    else:
                        st.error("Failed to generate guidelines.")
        else:
            st.warning("Insufficient data to generate regulations.")

        # Display recent stored regulations
        st.subheader("Previous Generated Guidelines")
        conn = sqlite3.connect("dtl_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT content, created_at FROM regulations ORDER BY created_at DESC LIMIT 3")
        previous_regulations = cursor.fetchall()
        conn.close()
        
        for regulation, timestamp in previous_regulations:
            with st.expander(f"Guidelines - {timestamp}"):
                st.write(regulation)

    # Rest of the pages (Forum, Download Data) remain the same

if __name__ == "__main__":
    main()
