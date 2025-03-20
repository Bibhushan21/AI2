from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from mistralai import Mistral  # Import Mistral library
import PyPDF2
import os

# Initialize Flask app
MultiverzAI = Flask(__name__)

# MySQL Configuration 
MultiverzAI.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:NewSecurePassword2024@127.0.0.1:3306/Multiverz_AI_Chat"
MultiverzAI.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the Database
db = SQLAlchemy(MultiverzAI)

# Define Chat Model (Table Structure)
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(255), nullable=False)  
    user_message = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# Create Database Tables
with MultiverzAI.app_context():
    db.create_all()

# Function to extract system prompt from a PDF
def extract_prompt_from_pdf(pdf_path):
    try:
        with open(pdf_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            prompt_text = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    prompt_text.append(page_text.replace("\n", " "))  
            return " ".join(prompt_text).strip()
    except Exception as e:
        return f"Error reading system prompt: {str(e)}"

# Load system prompt from the PDF
pdf_path = "Brainstorming Agent - System Prompt.pdf"  
system_prompt = extract_prompt_from_pdf(pdf_path)

if not system_prompt or "Error" in system_prompt:
    print("⚠️ Warning: System prompt not loaded correctly.")
else:
    print("✅ System prompt loaded successfully.")

system_message = {
    "role": "system",
    "content": system_prompt
}

# Initialize chat memory 
memory = []

@MultiverzAI.route("/")
def home():
    return render_template("index.html")

@MultiverzAI.route("/chat", methods=["POST"])
def chat():
    global memory
    data = request.json
    user_name = data.get("user_name", "").strip()
    user_input = data.get("message", "").strip()

    if not user_name or not user_input:
        return jsonify({"error": "User name and message are required"}), 400

    memory.append({"role": "user", "content": user_input})

    try:
        # Initialize Mistral client
        api_key = "N2VeTffMFqGYvyVS3D8ZJKgjmlvn7VKZ"  # Set your Mistral API key here
        model = "mistral-large-latest"  # Choose your model (adjust as needed)

        client = Mistral(api_key=api_key)
        # Send the chat request to Mistral
        response = client.chat.complete(
            model=model,
            messages=[system_message] + memory  # Keep system prompt + chat history
        )
        ai_response = response.choices[0].message.content
        memory.append({"role": "assistant", "content": ai_response})

        # Save chat to MySQL database
        new_chat = Chat(user_name=user_name, user_message=user_input, ai_response=ai_response)
        db.session.add(new_chat)
        db.session.commit()

    except Exception as e:
        ai_response = f"Error: {str(e)}"

    return jsonify({"user_name": user_name, "user_message": user_input, "ai_response": ai_response})

@MultiverzAI.route("/chat-history", methods=["GET"])
def get_chat_history():
    chats = Chat.query.order_by(Chat.timestamp.desc()).all()
    chat_list = [
        {
            "id": chat.id,
            "user_name": chat.user_name,
            "user_message": chat.user_message,
            "ai_response": chat.ai_response,
            "timestamp": chat.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for chat in chats
    ]
    return jsonify(chat_list)

if __name__ == "__main__":
    MultiverzAI.run(host="0.0.0.0", port=5000, debug=True)
