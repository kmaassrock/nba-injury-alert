# NBA Injury Alert System

A real-time notification system for NBA player injury status changes.

## Overview

The NBA Injury Alert System monitors official NBA injury reports and notifies users when there are changes to the injury status of their favorite players or teams. The system is designed to provide timely updates to fantasy basketball players, sports bettors, and NBA fans.

## Features

- **Real-time Monitoring**: Automatically polls NBA injury reports for updates
- **Status Change Detection**: Identifies when a player's injury status changes
- **User Preferences**: Users can follow specific players or teams
- **Multiple Notification Channels**: Email, web, and push notifications
- **Top Player Focus**: Prioritizes notifications for top-ranked players
- **Customizable Alerts**: Users can set quiet hours and notification preferences

## Architecture

The system consists of the following components:

- **Backend API**: FastAPI-based REST API and WebSocket server
- **Database**: SQLAlchemy ORM with PostgreSQL
- **Fetcher**: Retrieves injury reports from NBA data sources
- **Processor**: Analyzes reports and detects status changes
- **Notifier**: Sends notifications through various channels

## Setup

### Prerequisites

- Python 3.9+
- PostgreSQL
- SMTP server for email notifications (optional)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nba-injury-alert.git
   cd nba-injury-alert
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following variables:
   ```
   # Database
   DATABASE_URL=postgresql://username:password@localhost/nba_injury_alert
   
   # API
   API_HOST=0.0.0.0
   API_PORT=8000
   
   # Fetcher
   NBA_API_BASE_URL=https://stats.nba.com
   INJURY_REPORT_ENDPOINT=/stats/injuries
   POLL_INTERVAL_SECONDS=3600
   
   # Notification
   EMAIL_ENABLED=true
   EMAIL_SMTP_SERVER=smtp.example.com
   EMAIL_SMTP_PORT=587
   EMAIL_SMTP_USERNAME=your_username
   EMAIL_SMTP_PASSWORD=your_password
   EMAIL_FROM_ADDRESS=noreply@example.com
   
   # Debug
   DEBUG=true
   ```

5. Initialize the database:
   ```bash
   alembic upgrade head
   ```

### Running the Application

Start the backend API server:

```bash
python -m backend.main
```

The API will be available at `http://localhost:8000`.

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Project Structure

```
nba-injury-alert/
├── backend/
│   ├── api/                # FastAPI application and routers
│   ├── fetcher/            # Data retrieval components
│   ├── models/             # Database models
│   ├── notifier/           # Notification components
│   ├── processor/          # Data processing components
│   └── utils/              # Utility modules
├── alembic/                # Database migrations
├── tests/                  # Test suite
└── frontend/               # Frontend application (future)
```

### Running Tests

```bash
pytest
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
