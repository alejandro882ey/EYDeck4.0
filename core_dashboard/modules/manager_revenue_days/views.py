"""
Manager Revenue Days Views
=========================

Views for handling Manager Revenue Days file uploads and processing.
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from .services import ManagerRevenueDaysService
from .utils import format_file_size

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def upload_manager_revenue_days(request):
    """
    Handle Manager Revenue Days file upload.
    
    This view processes the uploaded Excel file, extracts the RevenueDays sheet,
    and saves it as 'Revenue Days Manager.xlsx' in the media folder.
    """
    try:
        if 'manager_revenue_days_file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No file uploaded. Please select a Manager Revenue Days file.'
            })
        
        uploaded_file = request.FILES['manager_revenue_days_file']
        
        # Validate file type
        if not uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
            return JsonResponse({
                'success': False,
                'error': 'Invalid file type. Please upload an Excel file (.xlsx or .xls).'
            })
        
        # Process the file
        service = ManagerRevenueDaysService()
        result = service.process_uploaded_file(uploaded_file, uploaded_file.name)
        
        if result['success']:
            logger.info(f"Manager Revenue Days upload successful: {result['message']}")
            
            # Add additional info for the response
            result['file_info'] = {
                'original_name': uploaded_file.name,
                'size': format_file_size(uploaded_file.size),
                'output_name': result['output_file']
            }
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in upload_manager_revenue_days: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error occurred: {str(e)}'
        })


@require_http_methods(["GET"])
def get_manager_revenue_days_status(request):
    """
    Get the status of the latest Manager Revenue Days file.
    """
    try:
        service = ManagerRevenueDaysService()
        file_info = service.get_latest_file_info()
        
        if file_info:
            # Convert timestamp to readable format
            from datetime import datetime
            modified_time = datetime.fromtimestamp(file_info['modified'])
            
            return JsonResponse({
                'success': True,
                'file_exists': True,
                'file_info': {
                    'filename': file_info['filename'],
                    'size': format_file_size(file_info['size']),
                    'last_modified': modified_time.strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        else:
            return JsonResponse({
                'success': True,
                'file_exists': False,
                'message': 'No Manager Revenue Days file has been processed yet.'
            })
            
    except Exception as e:
        logger.error(f"Error getting Manager Revenue Days status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error retrieving file status: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def clear_manager_revenue_days(request):
    """
    Clear all processed Manager Revenue Days files.
    """
    try:
        service = ManagerRevenueDaysService()
        result = service.clear_processed_files()
        
        logger.info(f"Manager Revenue Days clear operation: {result['message']}")
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error clearing Manager Revenue Days: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error clearing files: {str(e)}'
        })
