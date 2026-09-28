# FITBUDDY – AI Fitness Plan Generator

**FitBuddy** is a production-grade, AI-driven full-stack fitness planning web application built with **FastAPI**, **SQLite/SQLAlchemy**, **Jinja2**, and **Google Gemini AI**. It creates personalized, safety-conscious 7-day workout routines and evidence-based nutrition/recovery advice, featuring an adaptive user-feedback revision loop that permanently preserves original plan history.

---

## Table of Contents

- [Overview & Objectives](#overview--objectives)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Directory Structure](#project-directory-structure)
- [Prerequisites](#prerequisites)
- [Installation & Virtual Environment Setup](#installation--virtual-environment-setup)
- [Environment Configuration](#environment-configuration)
- [Google Gemini Model Configuration](#google-gemini-model-configuration)
- [Running the Application](#running-the-application)
- [Application URLs](#application-urls)
- [Admin & Coach Portal](#admin--coach-portal)
- [Database Design & Operations](#database-design--operations)
- [REST API Endpoints & Documentation](#rest-api-endpoints--documentation)
- [Automated Testing](#automated-testing)
- [Fitness Safety & Ethical AI Principles](#fitness-safety--ethical-ai-principles)
- [Troubleshooting & FAQ](#troubleshooting--faq)

---

## Overview & Objectives

FitBuddy empowers fitness enthusiasts and coaches by generating structured, progressive 7-day workout routines tailored to individual biometric targets, experience levels, and specific goals.

### Core Capabilities:
1. **Biometric Input & Validation**: Collects name, unique user ID, age (13–100), body weight, primary goal, and intensity level.
2. **AI-Powered 7-Day Routine Generation**: Leverages Google Gemini to formulate structured daily workouts including targeted focus, dynamic warm-up, exercises with sets/reps/duration/rest intervals, and cool-down routines.
3. **Targeted Nutrition & Recovery Guidance**: Employs Gemini Flash to deliver concise, non-extreme dietary and recovery tips.
4. **Adaptive Feedback Loop**: Users submit qualitative feedback (e.g., *"add more cardio intervals"*, *"include two rest days"*, *"make workouts under 30 minutes"*), triggering AI regeneration of a complete 7-day routine.
5. **Permanent Plan History**: The SQLite database permanently preserves the client's `original_plan` and stores the revised regimen in `updated_plan`, allowing easy version toggling in the user interface.
6. **Coach / Admin Dashboard**: Session-authenticated management interface providing metrics, live user search, detailed plan review, and deletion with cascading cleanup.
7. **Complete REST API**: JSON endpoints for programmatic integration alongside interactive OpenAPI Swagger documentation.

---

## Key Features

- **Modern Athletic Dark UI**: High-contrast, responsive interface styled with emerald and cyan neon accents, card layouts, accessible controls, and mobile-first responsiveness.
- **Official Google GenAI SDK**: Uses the new official `google-genai` SDK (`from google import genai`) with JSON schema enforcement.
- **Configurable Models**: Model identifiers (`GEMINI_WORKOUT_MODEL`, `GEMINI_TIP_MODEL`) are decoupled into environment variables with modern defaults (`gemini-2.5-flash`).
- **Resilient Fallback System**: Never crashes if the Gemini API is unreachable, unconfigured, or rate-limited. Automatically supplies evidence-based exercise routines in demo mode.
- **Strict Pydantic Validation**: Comprehensive boundary and type validation on all user submissions.
- **Database Cascade Integrity**: Deleting an athlete safely cascades to remove all associated workout plans.

---

## System Architecture

```
               ┌────────────────────────────────────────────────────────┐
               │                     Web Browser                        │
               │         (HTML5 / CSS3 / Jinja2 / JavaScript)           │
               └───────────▲────────────────────────────────▲───────────┘
                           │ (HTML Forms / GET)             │ (REST JSON API)
                           ▼                                ▼
               ┌────────────────────────────────────────────────────────┐
               │                   FastAPI Application                  │
               │   - SessionMiddleware (Admin Auth)                     │
               │   - Jinja2Templates / StaticFiles                      │
               │   - Global Exception Handlers                          │
               └───────┬────────────────────────┬───────────────┬───────┘
                       │                        │               │
                       ▼                        ▼               ▼
           ┌──────────────────────┐  ┌──────────────────┐  ┌─────────────┐
           │ Pydantic Validation  │  │ Google GenAI SDK │  │ SQLAlchemy  │
           │ (schemas.py)         │  │ (Gemini Models)  │  │ ORM (models)│
           └──────────────────────┘  └──────────┬───────┘  └──────┬──────┘
                                                │                 │
                                                ▼                 ▼
                                     ┌──────────────────┐  ┌─────────────┐
                                     │  Google Gemini   │  │   SQLite    │
                                     │  Flash / Pro API │  │ fitbuddy.db │
                                     └──────────────────┘  └─────────────┘
```

---

## Technology Stack

| Layer | Component | Version / Specification |
|---|---|---|
| **Language** | Python | 3.11+ (Tested on Python 3.12) |
| **Framework** | FastAPI | >= 0.110.0 (Modern ASGI Web Framework) |
| **Server** | Uvicorn | >= 0.28.0 (High-performance ASGI Server) |
| **Database** | SQLite + SQLAlchemy | 2.0+ ORM with connection pooling |
| **AI SDK** | Google GenAI SDK | `google-genai >= 1.0.0` (Official Google GenAI SDK) |
| **Templating** | Jinja2 | >= 3.1.3 |
| **Validation** | Pydantic v2 | >= 2.6.0 |
| **Session Auth** | Starlette Sessions | Signed cookies with configurable secret |
| **Testing** | Pytest + HTTPX | 23 isolated test cases with mocked AI services |

---

## Project Directory Structure

```
fitbuddy/
│
├── app/
│   ├── __init__.py               # Package marker and version identifier
│   ├── main.py                   # FastAPI initialization, middleware, exception handlers
│   ├── routes.py                 # HTML view handlers and REST API endpoints
│   ├── database.py               # Database engine, session lifecycle, and CRUD functions
│   ├── models.py                 # SQLAlchemy ORM models (User, WorkoutPlan)
│   ├── schemas.py                # Pydantic schemas, field validators, response models
│   ├── gemini_generator.py       # 7-day workout generator using Google GenAI SDK
│   ├── gemini_flash_generator.py # Concise nutrition/recovery tip generator
│   ├── updated_plan.py           # Feedback-driven workout regeneration
│   ├── config.py                 # Environment settings loader using python-dotenv
│   └── utils.py                  # JSON extractor, fallback generator, safety constants
│
├── templates/
│   ├── base.html                 # Master HTML template (navigation, footer, disclaimer)
│   ├── index.html                # Questionnaire landing page with feature cards
│   ├── result.html               # 7-day plan display, nutrition card, version toggle
│   ├── feedback.html             # User feedback submission with suggestion chips
│   ├── all_users.html            # Admin dashboard with live search and table view
│   ├── user_detail.html          # Detailed athlete profile and plan history comparison
│   ├── login.html                # Admin authentication portal
│   ├── error.html                # User-friendly technical error page
│   └── 404.html                  # Custom 404 not found page
│
├── static/
│   ├── css/
│   │   └── style.css             # Athletic dark-mode stylesheet with neon accents
│   ├── js/
│   │   └── app.js                # Dynamic UI helpers, loading states, live search
│   └── images/                   # Static graphics and icons
│
├── tests/
│   ├── __init__.py               # Test package initialization
│   ├── test_routes.py            # Route, web view, and REST API tests with mocked AI
│   ├── test_database.py          # SQLAlchemy CRUD and cascade delete tests
│   └── test_schemas.py           # Pydantic validation and boundary check tests
│
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git ignore file for secrets, venv, and SQLite files
├── requirements.txt              # Production dependency specifications
├── README.md                     # Comprehensive project documentation
└── run.py                        # Direct application launch script
```

---

## Prerequisites

- **Python 3.11** or **Python 3.12** installed on your system.
- Git (optional, for version control).
- Google Gemini API key (optional for local testing; demo mode provides built-in fallback routines if omitted).

---

## Installation & Virtual Environment Setup

### 1. Clone or Open the Repository
```bash
cd d:/fitbuddy
```

### 2. Create a Virtual Environment

#### On Windows (PowerShell or Command Prompt):
```powershell
python -m venv venv
venv\Scripts\activate
```

#### On Linux or macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Environment Configuration

1. Copy `.env.example` to create your local `.env` file:
   ```bash
   cp .env.example .env
   ```
   *(On Windows PowerShell: `Copy-Item .env.example .env`)*

2. Open `.env` and configure your settings:
   ```env
   # Google Gemini API Key (https://aistudio.google.com/)
   GEMINI_API_KEY=your_gemini_api_key_here

   # Configurable Gemini Models
   GEMINI_WORKOUT_MODEL=gemini-2.5-flash
   GEMINI_TIP_MODEL=gemini-2.5-flash

   # SQLite Database Connection String
   DATABASE_URL=sqlite:///./fitbuddy.db

   # Admin / Coach Dashboard Authentication
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=change_me_to_a_secure_password

   # Session Secret Key
   SECRET_KEY=fitbuddy-super-secret-key-replace-in-production

   # Environment Mode
   APP_ENV=development
   ```

> **Security Note:** Never commit your `.env` file to version control. `.env` is listed in `.gitignore`.

---

## Google Gemini Model Configuration

FitBuddy relies on the official **Google GenAI Python SDK** (`google-genai`). Model identifiers are completely decoupled from application logic:

- `GEMINI_WORKOUT_MODEL`: Used for complex, structured 7-day routine generation and feedback adaptation.
  - Recommended: `gemini-2.5-flash` or `gemini-1.5-pro`
- `GEMINI_TIP_MODEL`: Used for quick, concise nutrition and recovery guidance.
  - Recommended: `gemini-2.5-flash` or `gemini-1.5-flash`

To switch models, simply change the identifier in your `.env` file without modifying any Python code.

If `GEMINI_API_KEY` is not supplied, the application automatically enters **Demo Mode**, serving balanced evidence-based routines so you can test all features without an external network dependency.

---

## Running the Application

You can launch FitBuddy using either method below:

### Option A: Using the Launcher Script
```bash
python run.py
```

### Option B: Using Uvicorn CLI
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## Application URLs

Once running, navigate to:

- **Web Application Home**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Coach / Admin Dashboard**: [http://127.0.0.1:8000/view-all-users](http://127.0.0.1:8000/view-all-users)
- **Admin Login**: [http://127.0.0.1:8000/admin/login](http://127.0.0.1:8000/admin/login)

---

## Admin & Coach Portal

To access `/view-all-users`, you must authenticate through the coach portal:

1. Navigate to [http://127.0.0.1:8000/admin/login](http://127.0.0.1:8000/admin/login)
2. Enter credentials configured in your `.env`:
   - **Default Username:** `admin`
   - **Default Password:** `admin123` (or whatever you set in `.env`)
3. The dashboard features:
   - Total athlete count metrics.
   - Live client-side search across names, user IDs, and goals.
   - Direct links to inspect full athlete plan history (`/user/{user_id}`).
   - Safe one-click deletion with confirmation dialog.

---

## Database Design & Operations

FitBuddy uses **SQLite** through **SQLAlchemy 2.0 ORM**. Tables are created automatically on startup:

### 1. `users` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | Primary Key, Auto-increment | Internal numeric identifier |
| `user_id` | String(50) | Unique, Indexed, Not Null | Alphanumeric handle (e.g. `alex_24`) |
| `username` | String(100) | Not Null | Athlete full name or nickname |
| `age` | Integer | Not Null | Age in years (13–100) |
| `weight` | Float | Not Null | Body weight in kilograms (20–300) |
| `goal` | String(100) | Not Null | Primary fitness goal |
| `intensity` | String(50) | Not Null | Workout intensity (low, medium, high) |
| `created_at`| DateTime | Not Null | Registration timestamp |

### 2. `workout_plans` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | Primary Key, Auto-increment | Plan identifier |
| `user_id` | String(50) | ForeignKey(`users.user_id`, CASCADE), Indexed | Foreign key linking to user |
| `original_plan` | Text (JSON) | Not Null | Permanently preserved baseline plan |
| `updated_plan` | Text (JSON) | Nullable | Revised plan incorporating user feedback |
| `nutrition_tip` | Text | Nullable | Goal-aligned nutrition/recovery advice |
| `feedback` | Text | Nullable | User-submitted adjustment requests |
| `created_at`| DateTime | Not Null | Creation timestamp |
| `updated_at`| DateTime | Not Null | Last update timestamp |

---

## REST API Endpoints & Documentation

All API endpoints return standard JSON responses and status codes:

### 1. Generate Workout Plan
- **Endpoint**: `POST /api/generate-workout`
- **Status Code**: `201 Created`
- **Request Body**:
  ```json
  {
    "username": "Diana Prince",
    "user_id": "diana_p",
    "age": 28,
    "weight": 65.0,
    "goal": "strength",
    "intensity": "high"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "user": { ... },
    "workout_plan": { "days": [ ... ], "safety_note": "..." },
    "nutrition_tip": "...",
    "message": "Workout plan generated successfully"
  }
  ```

### 2. Submit Feedback & Update Plan
- **Endpoint**: `POST /api/submit-feedback`
- **Status Code**: `200 OK`
- **Request Body**:
  ```json
  {
    "user_id": "diana_p",
    "feedback": "Add more shoulder mobility and dedicated yoga stretching on rest days."
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "user_id": "diana_p",
    "updated_plan": { "days": [ ... ] },
    "message": "Workout plan updated successfully based on feedback"
  }
  ```

### 3. List All Registered Users
- **Endpoint**: `GET /api/users`
- **Status Code**: `200 OK`

### 4. Get User & Plan Details
- **Endpoint**: `GET /api/users/{user_id}`
- **Status Code**: `200 OK`

---

## Automated Testing

FitBuddy comes with a comprehensive **Pytest** test suite covering:
- Web route loading and HTML form submissions.
- Pydantic schema validation (age boundaries, weight constraints, intensity whitelist, character checks).
- In-memory database CRUD, duplicate handling, plan permanence, and cascading deletes.
- Feedback plan updates and version toggle rendering.
- Session-based admin login, logout, and access protection.
- REST API endpoint serialization and HTTP status codes.

### Running Tests:
```bash
pytest -v
```

All 23 unit and integration tests execute in ~1 second using an in-memory database with external AI calls strictly mocked.

---

## Fitness Safety & Ethical AI Principles

FitBuddy enforces strict safety constraints in all AI system prompts and user interfaces:
- **No Medical Diagnoses**: Prompts instruct Gemini never to diagnose medical conditions or issue clinical prescriptions.
- **No Extreme Regimens**: AI is explicitly instructed against recommending dangerous exercises, extreme training volumes, or restrictive crash diets.
- **Appropriate Recovery**: 7-day plans mandate at least 1–2 rest or active mobility days.
- **Prominent Medical Disclaimer**: Displayed on the homepage banner, plan result page, and in plan metadata:
  > *"FitBuddy provides general fitness and wellness information and is not a substitute for professional medical advice. Consult a qualified healthcare professional or fitness professional if you have an injury, medical condition, or concerns about exercising."*

---

## Troubleshooting & FAQ

### 1. `google.genai.errors.APIError` or Quota Exceeded
FitBuddy catches all Gemini API exceptions gracefully. In the event of an outage or invalid credentials, the system serves structured, balanced fallback routines so user workflows are never interrupted. Check your API key at [Google AI Studio](https://aistudio.google.com/).

### 2. Can't Log In to Admin Dashboard
Verify `ADMIN_USERNAME` and `ADMIN_PASSWORD` in your `.env` file. Restart the application if you modified `.env`.

### 3. Database Reset
If you want a clean database:
1. Stop the server (`Ctrl+C`).
2. Delete `fitbuddy.db`.
3. Restart the server (`python run.py`). SQLite tables will automatically re-initialize.

---

## License

FitBuddy is open-source software provided under the MIT License.
