import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import sync_data

@patch('sync_data.YandexDiskStorage')
@patch('sync_data.data_loader')
def test_sync_from_yandex_uses_storage_adapter(mock_data_loader, mock_storage_class):
    # Prepare the mock storage instance
    mock_storage = MagicMock()
    mock_storage_class.return_value = mock_storage
    
    # Mock list_directory to return a predictable structure
    mock_storage.list_directory.side_effect = [
        # Call 1: Root folder items
        [
            {"type": "dir", "name": "Venue1", "path": "root/Venue1"},
            {"type": "file", "name": "root_data.xlsx", "file": "url/root"}
        ],
        # Call 2: Venue1 subfolder items
        [
            {"type": "file", "name": "venue1_data.csv", "file": "url/venue1"}
        ]
    ]
    
    # Mock download_file_stream to return fake byte stream
    mock_storage.download_file_stream.return_value = b"fake bytes content"
    
    # Mock data loader to return a valid DataFrame tuple
    # Tuple: (df, error, warnings, dropped_stats)
    mock_df = pd.DataFrame({"Data": [1, 2, 3]})
    mock_data_loader.process_single_file.return_value = (mock_df, None, [], None)
    
    # Inject a fake token to avoid the early exit condition
    sync_data.YANDEX_TOKEN = "fake_token_for_test"
    
    # Catch parquet writes to prevent modifying actual files
    with patch('pandas.DataFrame.to_parquet') as mock_to_parquet:
        sync_data.sync_from_yandex()
        
        # 1. Assert we used the Storage Adapter properly
        assert mock_storage.list_directory.call_count == 2
        assert mock_storage.download_file_stream.call_count == 2
        
        # 2. Prevent requests from being used
        assert not hasattr(sync_data, "requests"), "sync_data should not import or use 'requests'"
        
        # 3. Assert successful completion resulting in disk write
        mock_to_parquet.assert_called_once()
