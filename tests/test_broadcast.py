"""
Unit Tests for Broadcast System
Run with: pytest tests/test_broadcast.py -v
"""
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.app.services.csv_handler import clean_phone_number, parse_csv_content, CSVValidationError
from bot.app.services.broadcast_manager import BroadcastManager

class TestPhoneCleaning:
    """Test phone number cleaning and validation"""
    
    def test_clean_indonesian_local_format(self):
        """Test cleaning Indonesian local number (08xxx)"""
        assert clean_phone_number('081234567890') == '6281234567890'
        assert clean_phone_number('085678901234') == '6285678901234'
    
    def test_clean_international_format(self):
        """Test already correct international format"""
        assert clean_phone_number('6281234567890') == '6281234567890'
        assert clean_phone_number('+6281234567890') == '6281234567890'
    
    def test_clean_with_separators(self):
        """Test numbers with dashes, spaces, etc"""
        assert clean_phone_number('0812-3456-7890') == '6281234567890'
        assert clean_phone_number('0812 3456 7890') == '6281234567890'
        assert clean_phone_number('+62-812-3456-7890') == '6281234567890'
    
    def test_invalid_numbers(self):
        """Test invalid phone numbers"""
        assert clean_phone_number('') is None
        assert clean_phone_number('123') is None  # Too short
        assert clean_phone_number('12345678901234567890') is None  # Too long
        assert clean_phone_number('0212345678') is None  # Not mobile (starts with 021)
        assert clean_phone_number('invalid') is None

class TestCSVParsing:
    """Test CSV parsing and validation"""
    
    def test_parse_csv_with_header(self):
        """Test CSV with header row"""
        csv = "phone,name\n081234567890,John\n085678901234,Jane"
        targets = parse_csv_content(csv)
        assert len(targets) == 2
        # Correctly check dict values
        phones = [t['phone'] for t in targets]
        assert '6281234567890' in phones
        assert '6285678901234' in phones
    
    def test_parse_csv_without_header(self):
        """Test CSV without header (raw numbers)"""
        csv = "081234567890\n085678901234\n0819876543210"
        targets = parse_csv_content(csv)
        assert len(targets) == 3
        assert targets[0]['phone'] == '6281234567890'
    
    def test_parse_csv_deduplication(self):
        """Test that duplicate numbers are removed"""
        csv = "phone\n081234567890\n081234567890\n6281234567890"
        targets = parse_csv_content(csv)
        assert len(targets) == 1  # All are same number
    
    def test_parse_csv_mixed_valid_invalid(self):
        """Test CSV with mix of valid and invalid"""
        csv = "phone\n081234567890\ninvalid\n085678901234\n123"
        targets = parse_csv_content(csv)
        assert len(targets) == 2  # Only 2 valid

    def test_parse_empty_csv(self):
        """Test empty CSV raises error"""
        with pytest.raises(CSVValidationError):
            parse_csv_content("")

    def test_parse_csv_too_large(self):
        """Test CSV size limit"""
        large_csv = "phone\n" + ("081234567890\n" * 100000)  # Over limit
        with pytest.raises(CSVValidationError):
            parse_csv_content(large_csv)

    def test_parse_csv_max_rows(self):
        """Test maximum row limit"""
        csv = "phone\n" + ("081234567890\n" * 11000)  # Over 10K limit
        with pytest.raises(CSVValidationError):
            parse_csv_content(csv, max_rows=10000)

class TestBroadcastManager:
    """Test Broadcast Manager functions"""

    @pytest.fixture(autouse=True)
    def app_context(self):
        """Provide app context for DB tests"""
        from bot.app import create_app
        app = create_app()
        with app.app_context():
            yield
    
    def test_segment_map(self):
        """Test that segment map has expected keys"""
        segments = BroadcastManager.get_available_segments()
        expected_keys = ['all_merchants', 'active', 'expired', 'trial', 'starter', 'business', 'pro']
        
        for key in expected_keys:
            assert key in segments
            # Since we are in app context, this should work now
    
    def test_format_menu(self):
        """Test menu formatting"""
        menu = BroadcastManager.format_segment_menu()
        
        assert 'PILIH TARGET BROADCAST' in menu
        assert 'Semua Merchant' in menu
        assert 'CSV' in menu

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, '-v'])
