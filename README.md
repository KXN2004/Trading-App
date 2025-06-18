# Trading App

![Python](https://img.shields.io/badge/Python-3.10-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.68.0-green.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-1.4.23-red.svg)

## Overview

Trading App is a Python-based application designed for algorithmic trading using the Upstox REST API. It leverages FastAPI for the web interface, SQLAlchemy for database interactions, and various other libraries to facilitate trading strategies.

## Features

- **Algorithmic Trading**: Automate trading strategies with ease.
- **FastAPI Integration**: Provides a robust and fast web interface.
- **Database Management**: Uses SQLAlchemy for efficient database operations.
- **Upstox API**: Seamless integration with Upstox for trading operations.
- **Responsive UI**: Includes HTML templates for user interactions.

## Project Structure

```
.
├── app/                       # The directory containing the main application
│   ├── api.py                 # FastAPI application and route definitions
│   ├── config.py              # Configuration settings for the application
│   ├── database.py            # File containeing the database connection
│   ├── enums.py               # Enumerations used in the application
│   ├── logger.py              # File containing the app logger
│   ├── main.py                # Main script to run the application
│   ├── models.py              # SQLAlchemy models for database tables
│   └── utils.py               # Utility functions used across the application
├── templates/                 # The directory containing the html templates
│   ├── close_tab.html         # HTML template for closing a tab
│   ├── internal_error.html    # HTML template for internal errors
│   └── unknown_user.html      # HTML template for unknown user page
├── .dockerignore              # Specifies files to ignore when building Docker images
├── .gitignore                 # Specifies files to ignore in Git version control
├── .env                       # Environment variables configuration file
├── .env.example               # Environment variables configuration Examples
├── Dockerfile                 # Instructions to build the Docker image
├── compose.yml                # Docker Compose configuration for multi-container applications
├── favicon.ico                # Favicon for the frontend web page
├── pyproject.toml             # Project metadata and dependencies
├── README.md                  # Project documentation
└── uv.lock                    # UV Lock File
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker (optional, for containerized deployment)

### Setting up the Application

0. Download and install [uv](https://docs.astral.sh/uv/getting-started/installation/) onto your system

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/trading-app.git
    cd trading-app
    ```

2. Set up the environment variables:
    ```sh
    cp .env.example .env
    # Edit the .env file to include your database path and API keys
    ```

### Running the Application

1. Start the FastAPI server:
    ```sh
    uv run fastapi run app/api.py
    ```
    > Note: Make sure you're in the root of the project directory when running the above command

2. Access the application at `http://localhost:8000` or at `http://127.0.0.1:8000`.

### Using Docker

1. Start the Docker Compose:
    ```sh
    docker compose up
    ```

2. Stop the Docker Compose:
    ```sh
    docker compose down
    ```

## Usage

- **Login**: Navigate to `/login/{client_id}` to initiate the login process.
- **Callback**: The callback endpoint `/callback` handles the OAuth2 flow.
- **Trading Operations**: The application automates trading strategies based on predefined rules.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Upstox API](https://upstox.com/developer/api/)

---

*Happy Trading!*
