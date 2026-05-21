# EndoScan AI v2 - Medical Imaging Analysis

EndoScan AI is a sophisticated web application designed for the medical field, specifically for gastroenterology. It leverages the power of Google Gemini (via LangChain) to provide zero-shot AI analysis of endoscopic images (gastroscopy and colonoscopy), assisting medical professionals in identifying potential abnormalities.

## 🚀 Key Features
- **AI Analysis**: Real-time zero-shot analysis of endoscopic images using `gemini-2.5-flash`.
- **User Authentication**: Secure login and registration system using SHA-256 hashing and JWT (JSON Web Tokens).
- **History Tracking**: Automatically saves every analysis to a SQLite database, allowing users to review past findings.
- **Modern UI**: A responsive, iOS-inspired glassmorphism design with Light/Dark mode support.
- **Data Privacy**: Local storage of uploaded images and structured results in a private SQLite database.

## 🛠️ Technology Stack
- **Backend**: FastAPI (Python), LangChain, Google Generative AI API.
- **Database**: SQLite3 with a specialized Data Access Layer in `database.py`.
- **Frontend**: Vanilla JavaScript, HTML5, CSS3 (Glassmorphism), Jinja2 Templates.
- **Security**: JWT for session management, SHA-256 for password protection.

---

## 📂 Project Structure

```text
D:\codes\sessiya-loyiha\v2\
├── main.py            # Core FastAPI application & protected routes
├── auth.py            # Authentication logic (Login, Register, JWT)
├── database.py        # Centralized Database Abstraction Layer (DAL)
├── config.py          # Configuration & specialized medical prompts
├── requirements.txt   # Project dependencies
├── endoscan.db        # SQLite database (auto-generated)
├── uploads/           # Storage for uploaded endoscopy images
└── frontend/          # Static assets and UI templates
    ├── home.html      # Main application dashboard
    ├── login.html     # Dedicated login page
    ├── register.html  # Dedicated registration page
    ├── auth.css       # Styling for authentication pages
    ├── endoscan-ai.css# Main application styles
    └── endoscan-ai.js # Frontend logic & API interactions
```

---

## ⚙️ Setup and Installation

### 1. Prerequisites
- Python 3.10+
- Google Gemini API Key

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
python database.py
```

### 4. Run the Application
```bash
fastapi dev main.py
```
Access the app at `http://127.0.0.1:8000`.

---

## 📝 Development Conventions

### Authentication
- **Hashing**: Passwords are saved as SHA-256 hex digests.
- **Tokens**: JWT is used for session persistence, stored in a secure `access_token` cookie.
- **Protection**: All core routes (`/`, `/predict`, `/history`) require a valid JWT.

### Database (Data Access Layer)
All database interactions MUST happen through `database.py`. Do not write raw SQL in `main.py` or `auth.py`.
- Use `get_user_by_username()` for auth checks.
- Use `add_history_item()` to persist AI results.
- Use `get_user_history()` to retrieve user-specific records.

### AI Prompting
The `SYSTEM_PROMPT` in `config.py` is fine-tuned for clinical accuracy. It enforces a strict JSON output format in Uzbek to ensure the frontend can parse and display results correctly.

---

## 🚧 Roadmap / Future Improvements
- [ ] Implement DICOM file parsing for professional medical images.
- [ ] Add PDF report generation for analysis results.
- [ ] Integrate environment variables (`.env`) for API keys and secret keys.
- [ ] Unit testing for the Database Abstraction Layer.
