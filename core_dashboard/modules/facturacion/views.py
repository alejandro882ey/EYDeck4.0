import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .services import FacturacionService


@csrf_exempt
def upload_view(request):
    if request.method == 'POST':
        f = request.FILES.get('facturacion_file')
        if not f:
            return JsonResponse({'success': False, 'error': 'No file provided'})
        service = FacturacionService()
        result = service.process_uploaded_file(f, original_filename=f.name)
        return JsonResponse(result)
    return JsonResponse({'success': False, 'error': 'Invalid method'})


def status_view(request):
    service = FacturacionService()
    info = service.get_latest_file_info()
    if not info:
        return JsonResponse({'success': True, 'file_exists': False, 'message': 'No Facturacion file found'})
    billed = service.get_totals_from_file(info['path'])
    return JsonResponse({'success': True, 'file_exists': True, 'file_info': info, 'billed_total': billed})


@csrf_exempt
def clear_view(request):
    service = FacturacionService()
    info = service.get_latest_file_info()
    if not info:
        return JsonResponse({'success': True, 'message': 'No files to clear'})
    try:
        os.remove(info['path'])
    except Exception:
        pass
    # clear persistent cache if any
    try:
        if os.path.exists(service._cache_file):
            os.remove(service._cache_file)
    except Exception:
        pass
    return JsonResponse({'success': True, 'message': 'Facturacion files cleared'})
