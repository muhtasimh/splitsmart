# SplitSmart

SplitSmart is a full-stack shared-expense web application for organizing group expenses, calculating each person's net balance, and producing simplified repayment suggestions.

**Live app:** https://splitsmart-muhtasimh-hndbbtaegzcxe9ge.canadacentral-01.azurewebsites.net/

## What it does

- Account registration and token-based authentication
- Private, account-isolated groups and expenses
- Groups can contain people who do not have SplitSmart accounts
- Group owners can identify which member represents them, or manage a group without participating
- Create, edit, search, and delete shared expenses
- Choose the payer and participants for each expense
- Dashboard totals for expenses, money owed to you, money you owe, and active groups
- Per-member balance calculation and simplified repayment suggestions
- Persistent MySQL storage
- API validation and automated regression tests
- Continuous integration with GitHub Actions
- Production deployment on Azure App Service

## Tech stack

**Backend:** Python, Django, Django REST Framework, MySQL  
**Frontend:** JavaScript, HTML, CSS  
**Infrastructure:** Azure App Service, Aiven MySQL, GitHub Actions  
**Development:** Git, GitHub, Docker, Docker Compose, Django REST Framework APITestCase

## Architecture

The browser UI communicates with a Django REST Framework API. Django owns authentication, authorization, validation, balance calculations, and settlement logic. MySQL stores users, groups, members, expenses, participants, and recorded settlements.

A group is owned by one SplitSmart account but its members are independent records, so names inside a group do not have to match account usernames. When the owner participates in a group, an explicit account-to-member link lets the dashboard calculate that user's personal balance correctly.

Each expense stores:

- the group
- a description and amount
- the member who paid
- the members who participated

For an expense, SplitSmart credits the payer with the full amount and subtracts an equal share from each participant. Recorded settlements are then applied to those balances. Positive balances mean a member should receive money; negative balances mean they owe money.

The settlement view uses a greedy matching algorithm to pair debtors with creditors and produce a smaller, straightforward set of repayments.

## Main API capabilities

The REST API supports:

- authentication and registration
- groups and group membership
- expenses
- settlements
- group details and balances
- personal dashboard balance
- simplified debts/repayments
- search and filtering

Protected resources are scoped to the authenticated account so one account cannot access another account's groups or expenses.

## Validation and testing

The API validates that expense amounts are positive, participants are present, and payers/participants belong to the selected group.

The automated test suite covers authentication, registration, account isolation, expense CRUD, invalid cross-group members, group editing/deletion, balance and debt calculations, explicit account-to-member identity, owners who are not group members, and changing/removing member identity.

GitHub Actions runs the test suite on pushes and pull requests against a MySQL 8 service.

## Local development

Create environment variables for Django and MySQL:

```text
SECRET_KEY=your-development-secret
DB_NAME=splitsmart
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

Install dependencies and run migrations:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then open the local Django server in your browser.

## Deployment

The production application is deployed to Azure App Service. Production database credentials are supplied through environment variables and are not stored in the repository. Pushes to the deployment branch trigger the configured GitHub Actions workflow.
