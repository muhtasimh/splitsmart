# SplitSmart

SplitSmart is a full-stack shared-expense application for organizing group expenses, tracking personal balances, and simplifying repayments.

## Live Demo

**[Open SplitSmart](https://splitsmart-muhtasimh-hndbbtaegzcxe9ge.canadacentral-01.azurewebsites.net/)**

The application is deployed on Microsoft Azure App Service with a MySQL database hosted on Aiven.

## Features

- Create and manage shared-expense groups and members
- Add, edit, search, and delete expenses
- Select who paid and who participated in each expense
- Track how much you owe and how much you are owed
- Calculate per-member balances and simplified repayments
- Account registration, authentication, and private user data
- Persistent MySQL storage
- Responsive dashboard for expenses, balances, and active groups

## Development

- REST API built with Django REST Framework
- Automated API testing covering authentication, account isolation, expense CRUD, group management, and balance calculations
- CI/CD with GitHub Actions
- Production deployment on Microsoft Azure App Service
- Cloud database integration with Aiven MySQL

## Tech Stack

### Frontend

- JavaScript
- HTML
- CSS

### Backend

- Python
- Django
- Django REST Framework
- MySQL

### Testing & Deployment

- Django REST Framework APITestCase
- GitHub Actions
- Microsoft Azure App Service
- Aiven MySQL
