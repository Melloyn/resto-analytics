import pytest
from unittest.mock import patch, MagicMock
from infrastructure.messaging.telegram_provider import TelegramProvider

@pytest.fixture
def provider():
    return TelegramProvider()

@patch('requests.post')
def test_send_message_success(mock_post, provider):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp
    
    success, msg = provider.send_message("fake_token", "12345", "Test message")
    
    assert success is True
    assert "✅" in msg

@patch('requests.post')
def test_send_message_api_error(mock_post, provider):
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"
    mock_post.return_value = mock_resp
    
    success, msg = provider.send_message("fake_token", "12345", "Test message")
    
    assert success is False
    assert "Ошибка Telegram" in msg
    assert "Bad Request" in msg

@patch('requests.post')
def test_send_message_network_error(mock_post, provider):
    mock_post.side_effect = Exception("Connection Refused")
    
    success, msg = provider.send_message("fake_token", "12345", "Test message")
    
    assert success is False
    assert "Ошибка сети" in msg

def test_send_message_missing_credentials(provider):
    success, msg = provider.send_message("", "12345", "Test message")
    assert success is False
    assert "❌" in msg
    
    success, msg = provider.send_message("token", "", "Test message")
    assert success is False
    assert "❌" in msg
