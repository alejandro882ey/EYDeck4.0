"""
Manager Revenue Days Services
============================

Business logic layer for Manager Revenue Days functionality.
Handles file processing, sheet extraction, and file storage operations.
"""

import os
import logging
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .utils import extract_revenue_days_sheet

logger = logging.getLogger(__name__)


class ManagerRevenueDaysService:
    """
    Service class for handling Manager Revenue Days operations.
    
    This service provides isolated functionality for processing Manager Revenue Days
    Excel files without affecting the main revenue tracking system.
    """
    
    def __init__(self):
        """Initialize the Manager Revenue Days service."""
        self.media_folder = os.path.join(settings.MEDIA_ROOT, 'manager_revenue_days')
        self.ensure_media_folder()
    
    def ensure_media_folder(self):
        """Ensure the media folder exists for storing processed files."""
        if not os.path.exists(self.media_folder):
            os.makedirs(self.media_folder, exist_ok=True)
            logger.info(f"Created media folder: {self.media_folder}")
    
    def process_uploaded_file(self, uploaded_file, original_filename=None):
        """
        Process an uploaded Manager Revenue Days Excel file.
        
        Args:
            uploaded_file: The uploaded file object
            original_filename (str, optional): Original filename for reference
            
        Returns:
            dict: Processing result with status and details
        """
        try:
            # Extract filename
            filename = original_filename or uploaded_file.name
            logger.info(f"Processing Manager Revenue Days file: {filename}")
            
            # Extract RevenueDays sheet
            extracted_data = extract_revenue_days_sheet(uploaded_file)
            
            if extracted_data is None or extracted_data.empty:
                return {
                    'success': False,
                    'error': 'Could not extract RevenueDays sheet from the uploaded file'
                }
            
            # Save extracted sheet with dated filename or default
            if original_filename and original_filename.startswith('Revenue Days Manager_'):
                output_filename = original_filename
            else:
                output_filename = 'Revenue Days Manager.xlsx'
            output_path = os.path.join(self.media_folder, output_filename)
            
            # Save the extracted data to the media folder
            extracted_data.to_excel(output_path, index=False, sheet_name='RevenueDays')
            
            logger.info(f"Successfully saved extracted sheet to: {output_path}")
            
            return {
                'success': True,
                'message': f'Manager Revenue Days processed successfully',
                'output_file': output_filename,
                'output_path': output_path,
                'rows_processed': len(extracted_data)
            }
            
        except Exception as e:
            logger.error(f"Error processing Manager Revenue Days file: {str(e)}")
            return {
                'success': False,
                'error': f'Error processing file: {str(e)}'
            }
    
    def get_latest_file_info(self):
        """
        Get information about the latest processed Manager Revenue Days file.
        
        Returns:
            dict: File information or None if no file exists
        """
        try:
            output_filename = 'Revenue Days Manager.xlsx'
            output_path = os.path.join(self.media_folder, output_filename)
            
            if os.path.exists(output_path):
                stat = os.stat(output_path)
                return {
                    'filename': output_filename,
                    'path': output_path,
                    'size': stat.st_size,
                    'modified': stat.st_mtime
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return None
    
    def clear_processed_files(self):
        """
        Clear all processed Manager Revenue Days files.
        
        Returns:
            dict: Operation result
        """
        try:
            cleared_files = []
            if os.path.exists(self.media_folder):
                for filename in os.listdir(self.media_folder):
                    file_path = os.path.join(self.media_folder, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        cleared_files.append(filename)
            
            logger.info(f"Cleared {len(cleared_files)} Manager Revenue Days files")
            
            return {
                'success': True,
                'message': f'Cleared {len(cleared_files)} files',
                'cleared_files': cleared_files
            }
            
        except Exception as e:
            logger.error(f"Error clearing files: {str(e)}")
            return {
                'success': False,
                'error': f'Error clearing files: {str(e)}'
            }
