"""
Manager Revenue Days Tests
=========================

Unit tests for Manager Revenue Days module functionality.
"""

import os
import tempfile
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
import pandas as pd
from io import BytesIO

from .services import ManagerRevenueDaysService
from .utils import extract_revenue_days_sheet, validate_revenue_days_data, format_file_size


class ManagerRevenueDaysServiceTests(TestCase):
    """Test cases for ManagerRevenueDaysService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = ManagerRevenueDaysService()
    
    def test_service_initialization(self):
        """Test service initializes correctly."""
        self.assertIsInstance(self.service, ManagerRevenueDaysService)
        self.assertTrue(hasattr(self.service, 'media_folder'))
    
    @patch('core_dashboard.modules.manager_revenue_days.services.extract_revenue_days_sheet')
    def test_process_uploaded_file_success(self, mock_extract):
        """Test successful file processing."""
        # Mock the extraction function
        mock_df = pd.DataFrame({'Manager': ['Test'], 'Revenue Days': [10]})
        mock_extract.return_value = mock_df
        
        # Create a mock uploaded file
        mock_file = MagicMock()
        mock_file.name = 'test_file.xlsx'
        
        with patch('os.path.exists'), patch('os.makedirs'), patch.object(mock_df, 'to_excel'):
            result = self.service.process_uploaded_file(mock_file)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['output_file'], 'Revenue Days Manager.xlsx')
    
    @patch('core_dashboard.modules.manager_revenue_days.services.extract_revenue_days_sheet')
    def test_process_uploaded_file_failure(self, mock_extract):
        """Test file processing failure."""
        # Mock extraction failure
        mock_extract.return_value = None
        
        mock_file = MagicMock()
        mock_file.name = 'test_file.xlsx'
        
        result = self.service.process_uploaded_file(mock_file)
        
        self.assertFalse(result['success'])
        self.assertIn('Could not extract RevenueDays sheet', result['error'])


class ManagerRevenueDaysUtilsTests(TestCase):
    """Test cases for utility functions."""
    
    def test_format_file_size(self):
        """Test file size formatting."""
        self.assertEqual(format_file_size(0), "0 B")
        self.assertEqual(format_file_size(1024), "1.0 KB")
        self.assertEqual(format_file_size(1048576), "1.0 MB")
    
    def test_validate_revenue_days_data_empty(self):
        """Test validation with empty data."""
        result = validate_revenue_days_data(None)
        self.assertFalse(result['valid'])
        self.assertIn('empty', result['error'].lower())
    
    def test_validate_revenue_days_data_valid(self):
        """Test validation with valid data."""
        df = pd.DataFrame({
            'Manager': ['John Doe', 'Jane Smith'],
            'Client': ['Client A', 'Client B'],
            'Revenue Days': [10, 15]
        })
        
        result = validate_revenue_days_data(df)
        self.assertTrue(result['valid'])
        self.assertEqual(result['rows'], 2)
        self.assertEqual(result['columns'], 3)


class ManagerRevenueDaysViewTests(TestCase):
    """Test cases for Manager Revenue Days views."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
    
    def test_upload_no_file(self):
        """Test upload endpoint with no file."""
        response = self.client.post('/manager-revenue-days/upload/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('No file uploaded', data['error'])
    
    def test_upload_invalid_file_type(self):
        """Test upload with invalid file type."""
        test_file = SimpleUploadedFile(
            "test.txt", 
            b"file_content", 
            content_type="text/plain"
        )
        
        response = self.client.post(
            '/manager-revenue-days/upload/',
            {'manager_revenue_days_file': test_file}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Invalid file type', data['error'])
    
    def test_status_endpoint(self):
        """Test status endpoint."""
        response = self.client.get('/manager-revenue-days/status/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('file_exists', data)


class ManagerRevenueDaysIntegrationTests(TestCase):
    """Integration tests for the complete module."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.client = Client()
    
    @patch('core_dashboard.modules.manager_revenue_days.services.extract_revenue_days_sheet')
    def test_full_upload_workflow(self, mock_extract):
        """Test the complete upload workflow."""
        # Mock successful extraction
        mock_df = pd.DataFrame({
            'Manager': ['John Doe'],
            'Client': ['Test Client'],
            'Revenue Days': [20]
        })
        mock_extract.return_value = mock_df
        
        # Create test Excel file
        test_file = SimpleUploadedFile(
            "test_manager_revenue.xlsx",
            b"fake_excel_content",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        with patch('os.path.exists'), patch('os.makedirs'), patch.object(mock_df, 'to_excel'):
            response = self.client.post(
                '/manager-revenue-days/upload/',
                {'manager_revenue_days_file': test_file}
            )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('file_info', data)
