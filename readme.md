with open('README.md', 'w', encoding='utf-8') as f:
  f.write('''# Smart Timetable Generator

A Python-based web application for educational institutions to automatically generate, manage, and visualize optimal class timetables using AI-powered constraint programming.

---

## ✨ Features

- **Role-Based Access Control:** Admin, faculty, and department heads can log in, add/manage data, and view schedules.
- **Comprehensive Data Management:** Add and view departments, faculty, classrooms, subjects, batches, and lunch breaks.
- **Constraint Programming:** Leverages Google’s OR-Tools CP-SAT solver for automatic, conflict-free timetable generation.
- **Lunch Break Handling:** Enforces no-class periods for specific batches, ensuring realistic schedules.
- **Responsive UI:** Built with Flask, SQLAlchemy, and Bootstrap-like CSS for desktop and mobile.
- **Data Visualization:** View all entered data and generated timetables in clean, sortable tables.
- **Modern Styling:** Dark theme with cyan accents for a sleek, professional look.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Flask, Flask-SQLAlchemy, Flask-Login, OR-Tools
- Basic SQLite (no external DB needed for dev)

### Installation

1. Clone the repository:
