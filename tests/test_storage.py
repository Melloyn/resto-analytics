import pytest
from unittest.mock import patch, MagicMock
from infrastructure.storage.yandex_disk_storage import YandexDiskStorage

@pytest.fixture
def storage():
    return YandexDiskStorage()

@patch('requests.get')
def test_download_file_success(mock_get, storage, tmp_path):
    mock_resp1 = MagicMock()
    mock_resp1.status_code = 200
    mock_resp1.json.return_value = {"href": "http://fake-url.com/download"}
    
    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200
    mock_resp2.content = b"fake db content"
    
    mock_get.side_effect = [mock_resp1, mock_resp2]
    
    local_path = tmp_path / "test.db"
    result = storage.download_file("remote/path", str(local_path), "fake_token", force=True)
    
    assert result is True
    assert local_path.read_bytes() == b"fake db content"

@patch('requests.get')
def test_download_file_failure(mock_get, storage, tmp_path):
    mock_get.side_effect = Exception("Network Error")
    
    local_path = tmp_path / "test.db"
    result = storage.download_file("remote/path", str(local_path), "fake_token", force=True)
    
    assert result is False

@patch('requests.get')
@patch('requests.put')
def test_upload_file_success(mock_put, mock_get, storage, tmp_path):
    mock_resp1 = MagicMock()
    mock_resp1.status_code = 200
    mock_resp1.json.return_value = {"href": "http://fake-url.com/upload"}
    mock_get.return_value = mock_resp1
    
    mock_resp2 = MagicMock()
    mock_resp2.status_code = 201
    mock_put.return_value = mock_resp2
    
    local_path = tmp_path / "test.db"
    local_path.write_bytes(b"fake db content")
    
    result = storage.upload_file(str(local_path), "remote/path", "fake_token")
    
    assert result is True

@patch('requests.get')
def test_upload_file_failure(mock_get, storage, tmp_path):
    mock_get.side_effect = Exception("Network Error")
    
    local_path = tmp_path / "test.db"
    local_path.write_bytes(b"fake db content")
    
    result = storage.upload_file(str(local_path), "remote/path", "fake_token")
    
    assert result is False

@patch('requests.get')
def test_list_directory_success(mock_get, storage):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "_embedded": {
            "items": [{"name": "file1.txt"}, {"name": "file2.txt"}]
        }
    }
    mock_get.return_value = mock_resp
    
    items = storage.list_directory("remote/path", "fake_token", limit=10)
    
    assert len(items) == 2
    assert items[0]["name"] == "file1.txt"

@patch('requests.get')
def test_list_directory_failure(mock_get, storage):
    mock_get.side_effect = Exception("Network Error")
    
    items = storage.list_directory("remote/path", "fake_token")
    
    assert items == []

@patch('requests.get')
def test_download_file_stream_success(mock_get, storage):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"fake bytes content"
    mock_get.return_value = mock_resp
    
    data = storage.download_file_stream("http://fake-url.com", "fake_token")
    
    assert data == b"fake bytes content"

@patch('requests.get')
def test_download_file_stream_failure(mock_get, storage):
    mock_get.side_effect = Exception("Network Error")
    
    data = storage.download_file_stream("http://fake-url.com", "fake_token")
    
    assert data is None

@patch('requests.get')
def test_list_directory_uses_requests_mock(mock_get, storage):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "_embedded": {
            "items": [{"name": "file1.txt", "type": "file"}]
        }
    }
    mock_get.return_value = mock_resp
    
    items = storage.list_directory("remote/path", "fake_token")
    
    mock_get.assert_called_once()
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0]["name"] == "file1.txt"

@patch('requests.get')
def test_download_file_stream_yields_bytes(mock_get, storage):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"fake byte stream generator output"
    mock_get.return_value = mock_resp
    
    data = storage.download_file_stream("http://fake-url.com", "fake_token")
    
    mock_get.assert_called_once()
    assert isinstance(data, bytes)
    assert len(data) > 0
    assert data == b"fake byte stream generator output"
