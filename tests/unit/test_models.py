"""
Unit tests for the database models.
"""
import pytest
from datetime import datetime

from backend.models.player import Player, PlayerRanking
from backend.models.injury import InjuryReport, InjuryStatus, StatusChange
from backend.models.user import User, NotificationSetting, Team


def test_player_model(db_session):
    """Test the Player model."""
    # Create a player
    player = Player(
        name="LeBron James",
        team="LAL",
        position="F",
        jersey_number="23",
        current_rank=1,
        is_top_100=True,
        nba_id="2544",
        espn_id="1966"
    )
    
    db_session.add(player)
    db_session.commit()
    
    # Query the player
    queried_player = db_session.query(Player).filter(Player.name == "LeBron James").first()
    
    # Assert that the player was created correctly
    assert queried_player is not None
    assert queried_player.name == "LeBron James"
    assert queried_player.team == "LAL"
    assert queried_player.position == "F"
    assert queried_player.jersey_number == "23"
    assert queried_player.current_rank == 1
    assert queried_player.is_top_100 is True
    assert queried_player.nba_id == "2544"
    assert queried_player.espn_id == "1966"


def test_injury_report_model(db_session):
    """Test the InjuryReport model."""
    # Create an injury report
    report = InjuryReport(
        report_date=datetime.now(),
        source_url="https://example.com/injury-report",
        report_hash="abc123"
    )
    
    db_session.add(report)
    db_session.commit()
    
    # Query the report
    queried_report = db_session.query(InjuryReport).first()
    
    # Assert that the report was created correctly
    assert queried_report is not None
    assert queried_report.source_url == "https://example.com/injury-report"
    assert queried_report.report_hash == "abc123"


def test_injury_status_model(db_session):
    """Test the InjuryStatus model."""
    # Create a player
    player = Player(
        name="LeBron James",
        team="LAL",
        position="F",
        jersey_number="23",
        current_rank=1,
        is_top_100=True
    )
    
    # Create an injury report
    report = InjuryReport(
        report_date=datetime.now(),
        source_url="https://example.com/injury-report",
        report_hash="abc123"
    )
    
    db_session.add(player)
    db_session.add(report)
    db_session.commit()
    
    # Create an injury status
    status = InjuryStatus(
        player_id=player.id,
        report_id=report.id,
        status="OUT",
        reason="Ankle",
        details="Left ankle sprain",
        game_date=datetime.now(),
        opponent="BOS",
        is_status_change=True,
        previous_status="QUESTIONABLE"
    )
    
    db_session.add(status)
    db_session.commit()
    
    # Query the status
    queried_status = db_session.query(InjuryStatus).first()
    
    # Assert that the status was created correctly
    assert queried_status is not None
    assert queried_status.player_id == player.id
    assert queried_status.report_id == report.id
    assert queried_status.status == "OUT"
    assert queried_status.reason == "Ankle"
    assert queried_status.details == "Left ankle sprain"
    assert queried_status.opponent == "BOS"
    assert queried_status.is_status_change is True
    assert queried_status.previous_status == "QUESTIONABLE"


def test_user_model(db_session):
    """Test the User model."""
    # Create a user
    user = User(
        email="user@example.com",
        username="testuser",
        hashed_password="hashedpassword",
        email_notifications=True,
        push_notifications=False,
        web_notifications=True,
        is_active=True,
        is_verified=False
    )
    
    db_session.add(user)
    db_session.commit()
    
    # Query the user
    queried_user = db_session.query(User).filter(User.email == "user@example.com").first()
    
    # Assert that the user was created correctly
    assert queried_user is not None
    assert queried_user.email == "user@example.com"
    assert queried_user.username == "testuser"
    assert queried_user.hashed_password == "hashedpassword"
    assert queried_user.email_notifications is True
    assert queried_user.push_notifications is False
    assert queried_user.web_notifications is True
    assert queried_user.is_active is True
    assert queried_user.is_verified is False


def test_notification_setting_model(db_session):
    """Test the NotificationSetting model."""
    # Create a user
    user = User(
        email="user@example.com",
        username="testuser",
        hashed_password="hashedpassword"
    )
    
    # Create a player
    player = Player(
        name="LeBron James",
        team="LAL",
        position="F",
        jersey_number="23",
        current_rank=1,
        is_top_100=True
    )
    
    db_session.add(user)
    db_session.add(player)
    db_session.commit()
    
    # Create a notification setting
    setting = NotificationSetting(
        user_id=user.id,
        player_id=player.id,
        email_enabled=True,
        push_enabled=False,
        web_enabled=True,
        min_importance=3
    )
    
    db_session.add(setting)
    db_session.commit()
    
    # Query the setting
    queried_setting = db_session.query(NotificationSetting).first()
    
    # Assert that the setting was created correctly
    assert queried_setting is not None
    assert queried_setting.user_id == user.id
    assert queried_setting.player_id == player.id
    assert queried_setting.email_enabled is True
    assert queried_setting.push_enabled is False
    assert queried_setting.web_enabled is True
    assert queried_setting.min_importance == 3


def test_team_model(db_session):
    """Test the Team model."""
    # Create a team
    team = Team(
        name="Los Angeles Lakers",
        abbreviation="LAL",
        city="Los Angeles",
        conference="Western",
        division="Pacific"
    )
    
    db_session.add(team)
    db_session.commit()
    
    # Query the team
    queried_team = db_session.query(Team).filter(Team.abbreviation == "LAL").first()
    
    # Assert that the team was created correctly
    assert queried_team is not None
    assert queried_team.name == "Los Angeles Lakers"
    assert queried_team.abbreviation == "LAL"
    assert queried_team.city == "Los Angeles"
    assert queried_team.conference == "Western"
    assert queried_team.division == "Pacific"
