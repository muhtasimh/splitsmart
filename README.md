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
- Debt simplification that generates repayment suggestions from group balances
- Dashboard displaying expenses, balances, groups, and repayments
- Responsive web interface
- Sign-in and sign-out functionality

## Tech Stack

- Python
- Django
- Django REST Framework
- MySQL
- JavaScript
- HTML/CSS
- Git & GitHub

## How It Works

Each expense records a payer, a group, an amount, and the users participating in the expense. SplitSmart calculates each participant's share and maintains net balances for group members.

The application then matches debtors with creditors using a greedy debt-simplification algorithm to generate straightforward repayment suggestions.

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

## Local Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt