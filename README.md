# SplitSmart

SplitSmart is a full-stack shared-expense management application for tracking expenses between groups of users, calculating balances, and generating simplified repayment suggestions.

## Features

- Token-based user authentication
- Create and track shared group expenses
- MySQL relational database for users, groups, expenses, and settlements
- REST API built with Django REST Framework
- Expense search and filtering
- Validation for expense amounts, participants, and group membership
- Automatic calculation of each member's net balance
- Greedy debt simplification that generates repayment suggestions from group balances
- Dashboard displaying expenses, balances, groups, and suggested repayments
- Responsive web interface
- Automated API tests for authentication, expense validation, balance calculations, and debt simplification
- Dockerized Django and MySQL development environment using Docker Compose
- GitHub Actions CI workflow that automatically runs the test suite on pushes and pull requests
- Sign-in and sign-out functionality

## Tech Stack

### Backend
- Python
- Django
- Django REST Framework
- MySQL

### Frontend
- JavaScript
- HTML/CSS

### Development
- Git
- GitHub
- Docker
- Docker Compose
- GitHub Actions
- Django REST Framework APITestCase

## How It Works

Each expense records a payer, a group, an amount, and the users participating in the expense.

SplitSmart calculates each participant's share and determines the resulting net balance for each group member. Positive balances represent money owed to a member, while negative balances represent money that member owes.

The application then uses a greedy debt-simplification algorithm to match debtors with creditors and generate straightforward repayment suggestions.

## API

The backend exposes REST endpoints for:

- Users
- Groups
- Expenses
- Settlements
- Group balances
- Suggested repayments
- Authentication

Protected endpoints require token authentication.

## Validation

The API validates expense data before it is stored, including:

- Expense amounts must be valid and greater than zero
- Payers must belong to the selected group
- Participants must belong to the selected group
- Expenses must contain valid participants

## Local Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd SplitSmart
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure MySQL

Create a MySQL database and database user for SplitSmart.

Create a `.env` file in the project root containing your local database configuration:

```env
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=3306
```

Do not commit the `.env` file.

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Start the application

```bash
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```
## Docker Setup

SplitSmart can also be run with Docker Compose, which starts both the Django application and MySQL database in containers.

```bash
docker compose up -d
```

Apply migrations:

```bash
docker compose exec web python manage.py migrate
```

Run the automated test suite:

```bash
docker compose exec web python manage.py test
```

Stop the containers:

```bash
docker compose down
```

The MySQL service includes a health check so the Django container waits for the database to become available before starting.

## Continuous Integration

GitHub Actions runs the automated test suite on every push and pull request.

The CI workflow:

- Starts a MySQL 8.0 service
- Installs the Python dependencies
- Configures the test database
- Runs the Django test suite
- Fails the workflow if any test fails

## Project Structure

```text
SplitSmart/
├── expenses/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── ...
├── splitsmart/
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Security

Database credentials are stored in environment variables rather than directly in the source code. The `.env` file and local virtual environment are excluded from version control.

Protected API endpoints use token authentication.