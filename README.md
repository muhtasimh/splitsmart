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
