# Varsh's Personal AI 🤖✨

> A production-quality, secure, reusable AI assistant powered by **Google Gemini**.  
> Features secure authentication with **JWT tokens**, in-memory fallback, and persistent **MongoDB sessions**.

---

## 🔒 Security & Authentication
To protect the Gemini API key and maintain privacy, the system is guarded by user authentication:
* **Credentials are stored securely as bcrypt hashes** in the `.env` file (never hardcoded in source code).
* **JWT Access Tokens** are issued upon successful authentication and stored in secure, `HttpOnly`, `SameSite` cookies to prevent XSS/CSRF attacks.
* **MongoDB integration** stores session state, logs, and enables token revocation on logout.

---

## 📁 Project Structure

```
chatbot/
│
├── app/
│   ├── api/
│   │   └── routes.py          ← API route handlers (login, chat, health, models)
│   ├── services/
│   │   ├── chatbot_service.py ← GeminiChatbot core class
│   │   └── auth_service.py    ← Bcrypt verification & JWT token management
│   ├── models/
│   │   └── schemas.py         ← Pydantic validation models
│   ├── config/
│   │   ├── settings.py        ← Environment configuration singleton
│   │   └── database.py        ← Async Motor MongoDB client
│   ├── utils/
│   │   ├── logger.py          ← Colored logging utility
│   │   └── session_manager.py ← Session memory storage
│   └── main.py                ← FastAPI app factory
│
├── frontend/
│   ├── index.html             ← Secure Chat UI (HTML)
│   └── static/
│       ├── style.css          ← Dark-mode glassmorphism styles with login overlay
│       └── app.js             ← Frontend authentication and API handler
│
├── chatbot.py                 ← Public module interface
├── main.py                    ← Standalone server entry point
├── hash_tool.py               ← Password hashing generator
├── integration_example.py     ← Plug-and-play example
├── .env                       ← Secret configurations
├── requirements.txt           ← Dependencies list
└── README.md
```

---

## 🚀 Quick Start

### 1. Set Up Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Ensure MongoDB is Running
Make sure MongoDB is running on your machine (default port `27017`). You can check with:
```bash
mongod --version
```

### 4. Configure `.env`
Create a `.env` file based on `.env.example`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
MODEL=gemini-2.5-flash
TEMPERATURE=0.7
MAX_OUTPUT_TOKENS=2048

# Authentication (Securely mapped from .env)
AUTH_USER_ID=24ADR172
AUTH_PASSWORD_HASH=$2b$12$.hJDv27i50EMtPUot5smbeI8wbwmHW/yF7/Dq.aKx51TOxhDh/AU.
JWT_SECRET=vp-ai-jwt-secret-x9k2p7q4n8m3r1s5t6u0w
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=8

# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=vp_ai_db
```

### 5. Running the Application
To start the standalone application:
```bash
python main.py
```
Open **http://localhost:8000** in your browser. You will be greeted with a stunning glassmorphic login screen.

---

## 🔑 Customizing Credentials
To change the password without editing source code:
1. Run the hashing tool:
   ```bash
   python hash_tool.py
   ```
2. Enter your new password.
3. Copy the outputted `AUTH_PASSWORD_HASH` line and paste it into your `.env` file.
4. Update `AUTH_USER_ID` in `.env` if you wish to change the username.

---

## 🔌 API Reference

### Auth Endpoints
* **`POST /api/auth/login`**: Validate credentials, issue token, and set HttpOnly cookie.
* **`POST /api/auth/logout`**: Revoke the session in MongoDB and delete the authentication cookie.
* **`GET /api/auth/session`**: Check the current user's session validity.

### Chat Endpoints (Require Authentication)
* **`POST /api/chat`**: Send user prompt and receive Gemini's reply.
* **`POST /api/new-chat`**: Reset current conversation history.
* **`GET /api/models`**: Get available Gemini models.

### Public Endpoints
* **`GET /api/health`**: System status report.

---

## 📄 License
MIT License. Free to use and integrate.
