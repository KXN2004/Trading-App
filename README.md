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
├── .dockerignore          # Specifies files to ignore when building Docker images
├── .env                   # Environment variables configuration file
├── .gitignore             # Specifies files to ignore in Git version control
├── api.py                 # FastAPI application and route definitions
├── close_tab.html         # HTML template for closing a tab
├── config.py              # Configuration settings for the application
├── docker-compose.yml     # Docker Compose configuration for multi-container applications
├── Dockerfile             # Instructions to build the Docker image
├── enums.py               # Enumerations used in the application
├── main.py                # Main script to run the application
├── models.py              # SQLAlchemy models for database tables
├── pyproject.toml         # Project metadata and dependencies
├── README.md              # Project documentation
├── requirements.txt       # Python dependencies
├── Token.py               # Token management for authentication
├── unknown_user.html      # HTML template for unknown user page
└── utils.py               # Utility functions used across the application
```

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Docker (optional, for containerized deployment)

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/trading-app.git
    cd trading-app
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

4. Set up the environment variables:
    ```sh
    cp .env.example .env
    # Edit the .env file to include your database path and API keys
    ```

### Running the Application

1. Start the FastAPI server:
    ```sh
    uvicorn api:app --reload
    ```

2. Access the application at `http://localhost:8000`.

### Using Docker

1. Build the Docker image:
    ```sh
    docker build -t trading-app .
    ```

2. Run the Docker container:
    ```sh
    docker run -p 80:80 trading-app
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
