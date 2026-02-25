import pytest
import auth

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_users.db"
    original_db = auth.USERS_DB
    auth.USERS_DB = str(db_file)
    auth.init_auth_db()
    yield str(db_file)
    auth.USERS_DB = original_db

def test_successful_login(test_db):
    auth.create_user("Test User", "testuser", "test@test.com", "12345", "password123", status="approved")
    user = auth.authenticate_user("testuser", "password123")
    assert user is not None
    assert user["role"] == "user"

def test_unapproved_login(test_db):
    auth.create_user("Test User", "testuser", "test@test.com", "12345", "password123", status="pending")
    with pytest.raises(auth.InvalidCredentialsError) as excinfo:
        auth.authenticate_user("testuser", "password123")
    assert "не одобрен" in str(excinfo.value)

def test_invalid_credentials(test_db):
    auth.create_user("Test User", "testuser", "test@test.com", "12345", "password123", status="approved")
    with pytest.raises(auth.InvalidCredentialsError) as excinfo:
        auth.authenticate_user("testuser", "wrongpassword")
    assert "Неверный логин" in str(excinfo.value)

def test_user_already_exists(test_db):
    auth.create_user("Test User", "testuser", "test@test.com", "12345", "password123")
    with pytest.raises(auth.UserAlreadyExistsError):
        auth.create_user("Clone User", "testuser", "clone@test.com", "12345", "password123")
    with pytest.raises(auth.UserAlreadyExistsError):
        auth.create_user("Clone User2", "testuser2", "test@test.com", "12345", "password123")

def test_brute_force_lockout(test_db):
    auth.create_user("Test User", "bruteuser", "brute@test.com", "12345", "password123", status="approved")
    
    # Fail 5 times
    for _ in range(5):
        with pytest.raises(auth.InvalidCredentialsError) as excinfo:
            auth.authenticate_user("bruteuser", "wrong_pass")
        assert "Неверный логин" in str(excinfo.value)
            
    # The 6th attempt should return a specific lockout message
    with pytest.raises(auth.InvalidCredentialsError) as excinfo:
        auth.authenticate_user("bruteuser", "wrong_pass")
        
    assert "Слишком много попыток входа" in str(excinfo.value)
