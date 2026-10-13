# CampusFlow

A mini Google Classroom-style web application built with **Streamlit** and **MongoDB Atlas**, created as a NoSQL course project.

CampusFlow lets teachers manage courses, assignments, and grades, while students can see their enrolled courses, upcoming deadlines, and feedback — all connected to a real MongoDB Atlas database.

---

## What CampusFlow does

| Role | Capabilities |
|---|---|
| **Teacher** | Create courses, enroll students, create/edit/delete assignments, grade submissions, view analytics |
| **Student** | View enrolled courses, see assignments and deadlines, record submission status, view marks and feedback |

---

## Technologies used (in plain English)

| Technology | What it is |
|---|---|
| **Python** | The programming language everything is written in |
| **Streamlit** | A Python library that turns Python scripts into web apps — no HTML needed |
| **MongoDB Atlas** | A cloud-hosted NoSQL database where all course/student data is stored |
| **PyMongo** | The Python library that talks to MongoDB |
| **python-dotenv** | Loads your secret database credentials from a private `.env` file |
| **Pandas** | Organises data into tables for display |
| **Plotly** | Creates interactive charts on the Analytics page |

---

## Folder structure

```
NOSQL PROJECT/
├── app.py                  ← Main entry point (Dashboard page)
├── config.py               ← Loads environment variables
├── database.py             ← MongoDB connection (single reusable client)
├── auth.py                 ← Demo identity selector
├── requirements.txt        ← Python package list
├── README.md               ← This file
├── .env.example            ← Template for your private credentials
├── .gitignore              ← Files Git will not track (includes .env)
│
├── assets/                 ← Vector brand assets (logo.svg, favicon.svg)
├── .streamlit/
│   └── config.toml         ← App theme and port settings
│
├── services/               ← All database query logic lives here
│   ├── courses.py
│   ├── assignments.py
│   ├── submissions.py
│   └── analytics.py
│
├── components/             ← Reusable UI building blocks
│   ├── layout.py           ← Page headers, CSS, sidebar, metric cards
│   ├── tables.py           ← Data table renderers
│   └── feedback.py         ← Success/error/warning message helpers
│
├── pages/                  ← Streamlit multipage navigation
│   ├── 1_Courses.py
│   ├── 2_Assignments.py
│   ├── 3_Submissions.py
│   └── 4_Analytics.py
│
└── tests/
    └── test_campusflow.py  ← 43 unit tests (no live database required)
```

---

## How the app connects to MongoDB Atlas

1. When you start the app, `database.py` reads `MONGODB_URI` from your `.env` file.
2. It creates a single MongoDB client (cached with `st.cache_resource` so it is reused across reruns).
3. It pings MongoDB Atlas to verify the connection.
4. The connection status (green dot = connected, red dot = failed) appears in the sidebar.
5. All database reads and writes go through the `services/` modules — never scattered across UI code.

---

## Setup instructions (Windows PowerShell)

### Step 1 — Create a virtual environment

Open PowerShell in the project folder and run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> If you get a script execution error, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Step 2 — Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 3 — Create your `.env` file

```powershell
Copy-Item .env.example .env
```

Then open `.env` in Notepad and fill in your real values:

```
MONGODB_URI=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@YOUR_CLUSTER.mongodb.net/?appName=ClassFlowCluster
MONGODB_DB_NAME=classflow
```

**Never share this file or commit it to Git.** It contains your database password.

---

## Where to get MongoDB credentials

1. Go to [MongoDB Atlas](https://cloud.mongodb.com) and log in.
2. Open your project and click **Database Access** in the left sidebar.
3. Find your database user (or create one if needed).
4. The **username** goes into `MONGODB_URI` where it says `YOUR_USERNAME`.
5. The **password** you set goes where it says `YOUR_PASSWORD`. If the password contains special characters (like `@`, `#`, `$`), URL-encode them (for example, `#` becomes `%23`).
6. Click **Clusters**, then **Connect** on your cluster to find the connection string.

---

## Configure Atlas Network Access

MongoDB Atlas blocks connections from unknown IP addresses by default.

1. In Atlas, click **Network Access** in the left sidebar.
2. Click **Add IP Address**.
3. For development, you can click **Allow Access From Anywhere** (`0.0.0.0/0`).
4. For production, add only your specific IP address.

---

## Database user permissions

Your Atlas database user needs at least **readWrite** access to the `classflow` database.

1. Go to **Database Access** → click **Edit** on your user.
2. Under **Database User Privileges**, select **Read and write to any database**, or add a specific rule for `classflow`.

---

## How to run the app

Make sure your virtual environment is active, then:

```powershell
python -m streamlit run app.py
```

The app will open at `http://localhost:8501` in your browser.

> **Note:** If `streamlit` is not on your PATH, always use `python -m streamlit run app.py`.

---

## How to switch between demo identities

The app does not use passwords. Instead, you choose a user from the real `users` collection in your database using the **"Switch user"** dropdown in the left sidebar.

- Selecting a **teacher** (e.g., Priya Sharma) shows teacher features: course management, grading, analytics.
- Selecting a **student** (e.g., Aarav Mehta) shows student features: enrolled courses, assignments, grades.

> ⚠️ **This is for demonstration only.** The identity selector is not secure login — anyone can select any user. Do not use this application for real student data in a production environment.

---

## What each page does

| Page | What it shows |
|---|---|
| **Dashboard** (app.py) | Summary metrics, upcoming deadlines, recent activity — tailored to your selected role |
| **Courses** | List of courses; teachers can create courses and manage enrollment; students see their enrolled courses |
| **Assignments** | All assignments with deadline and status; teachers can create, edit, and delete assignments; students can filter and record submission status |
| **Submissions** | All submission records; teachers can filter and grade; students see their marks and feedback |
| **Analytics** | Real charts from MongoDB data: submission status distribution, marks histogram, average marks by assignment, submission counts |

---

## Which operations write to MongoDB

| Action | Collection modified | Fields written |
|---|---|---|
| Create course | `courses` | `title`, `description`, `teacher_id`, `student_ids`, `created_at` |
| Add student to course | `courses` | `student_ids` (appended) |
| Remove student from course | `courses` | `student_ids` (removed) |
| Create assignment | `assignments` | `course_id`, `title`, `description`, `deadline`, `max_marks` |
| Edit assignment | `assignments` | `title`, `description`, `deadline`, `max_marks` |
| Delete assignment | `assignments` | Document deleted (related submissions are NOT deleted) |
| Grade submission | `submissions` | `marks`, `feedback`, `status` |
| Mark as submitted (student) | `submissions` | New document: `assignment_id`, `student_id`, `submitted_at`, `status`, `marks`, `feedback` |

All write operations verify role and ownership before touching the database. Teachers can only modify their own courses.

---

## Limitation — assignment answers and file uploads

The `submissions` collection in this database does not contain an answer-text or file-upload field.

This means:
- Students **cannot** submit assignment answers or upload files through CampusFlow.
- The **"Mark as submitted"** button on the Assignments page records a status only — it tells the teacher you have acknowledged the assignment, but stores no answer.
- If you want to store actual answers, the `submissions` schema would need a new field (e.g., `answer_text`), and this application would need to be updated to use it.

This limitation is clearly labelled in the interface wherever the submit button appears.

---

## Limitation — identity selector is not real authentication

The "Switch user" selector in the sidebar is a demo convenience, not a login system. It:
- Does not check any password.
- Does not use sessions, tokens, or cookies in a secure way.
- Allows switching to any user in the database instantly.

**Do not deploy this application to the public internet for real student use without implementing proper authentication.**

---

## Troubleshooting

### "Cannot reach MongoDB Atlas"
- Check that your `.env` file has a correct, complete `MONGODB_URI`.
- Go to Atlas → Network Access and make sure your current IP is allowed.
- Check your internet connection.

### "Database access denied"
- Go to Atlas → Database Access and make sure your user has readWrite permissions.
- Make sure the password in the URI is URL-encoded if it contains special characters.

### "No module named streamlit" or similar
- Make sure your virtual environment is active: `.venv\Scripts\Activate.ps1`
- Run `pip install -r requirements.txt` again.

### "streamlit is not recognized"
- Use `python -m streamlit run app.py` instead of `streamlit run app.py`.

### The app shows "No users found"
- Check that the `users` collection in your Atlas database is not empty.
- Verify `MONGODB_DB_NAME=classflow` in your `.env`.

---

## How to stop the application

Press `Ctrl + C` in the PowerShell window where the app is running.

---

## Running the tests

The test suite does not require a database connection:

```powershell
python -m pytest tests/test_campusflow.py -v
```

Expected result: **43 passed**.
