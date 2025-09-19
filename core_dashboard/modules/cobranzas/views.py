import logging
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .services import CobranzasService
import json
from .utils import format_file_size
from django.shortcuts import render
import pandas as pd

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def upload_cobranzas(request):
    try:
        if 'cobranzas_file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No file uploaded. Please select a Cobranzas file.'})

        uploaded_file = request.FILES['cobranzas_file']
        if not uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
            return JsonResponse({'success': False, 'error': 'Invalid file type. Please upload an Excel file (.xlsx or .xls).'})

        service = CobranzasService()
        result = service.process_uploaded_file(uploaded_file, uploaded_file.name)

        if result.get('success'):
            result['file_info'] = {
                'original_name': uploaded_file.name,
                'size': format_file_size(getattr(uploaded_file, 'size', 0)),
                'output_name': result.get('output_file')
            }

        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error in upload_cobranzas: {e}")
        return JsonResponse({'success': False, 'error': f'Unexpected error occurred: {e}'})


@require_http_methods(["GET"])
def get_cobranzas_status(request):
    try:
        service = CobranzasService()
        info = service.get_latest_file_info()
        if info:
            from datetime import datetime
            modified_time = datetime.fromtimestamp(info['modified'])
            return JsonResponse({'success': True, 'file_exists': True, 'file_info': {
                'filename': info['filename'], 'size': format_file_size(info['size']), 'last_modified': modified_time.strftime('%Y-%m-%d %H:%M:%S')
            }})

        return JsonResponse({'success': True, 'file_exists': False, 'message': 'No Cobranzas file has been processed yet.'})
    except Exception as e:
        logger.error(f"Error getting Cobranzas status: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def clear_cobranzas(request):
    try:
        service = CobranzasService()
        result = service.clear_processed_files()
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error clearing Cobranzas files: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["GET"])
def preview_cobranzas(request):
    """Render a focused analysis window for Cobranzas with USD/VES breakdowns."""
    try:
        svc = CobranzasService()
        info = svc.get_latest_file_info()
        # If there is no single latest processed file, we may still have a combined cached DataFrame
        # (e.g., when files were processed previously and only the persistent cache exists). In that
        # case, allow rendering using the combined DataFrame.
        combined_df = svc.get_all_processed_df()
        if not info and (combined_df is None or combined_df.empty):
            context = {'message': 'No processed Cobranzas file available.'}
            return render(request, 'core_dashboard/cobranzas_preview.html', context)

        # cumulative across all processed files (used for Total Collected shown in preview)
        cumulative_collected = svc.get_cumulative_collected_total()
        usd_total, ves_equiv_total, ves_bolivares_total = svc.get_cumulative_breakdown()

        # Do not try to prefer per-file breakdowns here; rely on service totals
        # NOTE: Do NOT override MTD cards with per-file snapshot totals here.
        # MTD values should come from service.get_mtd_breakdown_for_date and
        # not be forced to the latest file totals. This preserves consistent
        # fiscal month-to-date semantics across combined data.

        # provide a list of available processed report dates so the template can show a filter
        available_reports = svc.get_available_report_dates()

        # If a report_date query param is provided (YYYY-MM-DD), compute cumulative up to that date
        selected_report_date = request.GET.get('report_date')
        cumulative_up_to = None
        if selected_report_date:
            try:
                cumulative_up_to = svc.get_cumulative_collected_up_to(selected_report_date)
            except Exception:
                cumulative_up_to = None

        # MTD (fiscal month-to-date) breakdown based on latest available date.
        latest_date = None
        try:
            import pandas as _pd
            if info and info.get('path'):
                try:
                    latest_df = _pd.read_excel(info['path'], sheet_name='Cobranzas')
                except Exception:
                    try:
                        latest_df = _pd.read_excel(info['path'])
                    except Exception:
                        latest_df = None
                if latest_df is not None and not latest_df.empty:
                    date_cols = [c for c in latest_df.columns if 'fecha' in str(c).lower() or 'cobro' in str(c).lower()]
                    if date_cols:
                        try:
                            latest_date = _pd.to_datetime(latest_df[date_cols[0]], errors='coerce').max()
                        except Exception:
                            latest_date = None
            # If latest_date still None, try to infer from combined_df
            if latest_date is None and combined_df is not None and not combined_df.empty:
                try:
                    # combined_df already has 'fecha_day' as 'YYYY-MM-DD'
                    combined_df['_dt'] = _pd.to_datetime(combined_df['fecha_day'], errors='coerce')
                    latest_date = combined_df['_dt'].max()
                except Exception:
                    latest_date = None
        except Exception:
            latest_date = None

        usd_mtd, ves_equiv_mtd, ves_bolivares_mtd = svc.get_mtd_breakdown_for_date(latest_date or pd.Timestamp.today())

        # For backward compatibility get totals from latest file as well
        collected, billed = svc.get_totals_from_file(info['path'])
        total_split = (usd_total or 0.0) + (ves_equiv_total or 0.0)
        if total_split > 0:
            usd_pct = round((usd_total / total_split) * 100)
            ves_pct = round((ves_equiv_total / total_split) * 100)
        else:
            usd_pct = ves_pct = 0

        # compute daily series once to avoid double work
        daily_series = svc.get_daily_collections_and_rates()

        context = {
            'collected_total': cumulative_collected,
            'cumulative_up_to': cumulative_up_to,
            'billed_total': billed,
            'usd_total': usd_total,
            'ves_equiv_total': ves_equiv_total,
            'ves_bolivares_total': ves_bolivares_total,
            'usd_pct': usd_pct,
            'ves_pct': ves_pct,
            'usd_mtd': usd_mtd,
            'ves_equiv_mtd': ves_equiv_mtd,
            'ves_bolivares_mtd': ves_bolivares_mtd,
            'file_info': info,
            # daily series for charts
            'cobranzas_series': daily_series,
            'cobranzas_series_json': json.dumps(daily_series, default=str)
            ,
            'available_reports': available_reports,
            'selected_report_date': selected_report_date
            }
        # Debugging via file inspection removed from this endpoint to keep preview simple.
        # If needed, a dedicated debug endpoint can be added later.
        return render(request, 'core_dashboard/cobranzas_preview.html', context)
    except Exception as e:
        logger.error(f"Error rendering cobranzas preview: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["GET"])
def preview_cobranzas_data(request):
    """AJAX endpoint: given report_date=YYYY-MM-DD return computed aggregates for that cutoff.

    Returns JSON: { success: True, cumulative_up_to, usd_mtd, ves_equiv_mtd, ves_bolivares_mtd, usd_total, ves_equiv_total, ves_bolivares_total }
    """
    try:
        svc = CobranzasService()
        report_date = request.GET.get('report_date')
        if not report_date:
            return JsonResponse({'success': False, 'error': 'report_date parameter required (YYYY-MM-DD)'} )

        # cumulative up to the date
        cumulative_up_to = svc.get_cumulative_collected_up_to(report_date)

        # Determine list of processed files for cumulative computation
        import re
        files = [f for f in os.listdir(svc.media_folder) if f.lower().endswith(('.xlsx', '.xls'))]
        pattern = re.compile(r'cobranzas[_-](\d{4}-\d{2}-\d{2})', re.IGNORECASE)

        # For MTD breakdown compute for the report_date
        from pandas import to_datetime
        try:
            dt = to_datetime(report_date)
        except Exception:
            dt = None
        usd_mtd = ves_equiv_mtd = ves_bolivares_mtd = 0.0
        if dt is not None:
            usd_mtd, ves_equiv_mtd, ves_bolivares_mtd = svc.get_mtd_breakdown_for_date(dt)

        # NOTE: Do NOT override MTD values with per-file totals here. The MTD
        # breakdown should come from svc.get_mtd_breakdown_for_date to maintain
        # consistent fiscal month semantics.
        # Also return cumulative overall breakdowns
        usd_total, ves_equiv_total, ves_bolivares_total = svc.get_cumulative_breakdown()

        # Compute cumulative breakdown up to the cutoff (sum per-file breakdowns)
        cumulative_usd_up_to = 0.0
        cumulative_ves_equiv_up_to = 0.0
        cumulative_ves_bolivares_up_to = 0.0
        try:
            from datetime import datetime
            cutoff_date = datetime.strptime(report_date, '%Y-%m-%d').date()
            for fn in files:
                # try filename pattern first
                m = pattern.search(fn)
                file_date = None
                if m:
                    try:
                        file_date = datetime.strptime(m.group(1), '%Y-%m-%d').date()
                    except Exception:
                        file_date = None
                if file_date is None:
                    # infer from contents
                    try:
                        p = os.path.join(svc.media_folder, fn)
                        inferred = svc.get_processed_file_date(p)
                        if inferred:
                            file_date = datetime.strptime(inferred, '%Y-%m-%d').date()
                    except Exception:
                        file_date = None

                if file_date and file_date <= cutoff_date:
                    try:
                        p = os.path.join(svc.media_folder, fn)
                        u, ve, vb = svc.get_breakdown_from_file(p)
                        cumulative_usd_up_to += float(u or 0.0)
                        cumulative_ves_equiv_up_to += float(ve or 0.0)
                        cumulative_ves_bolivares_up_to += float(vb or 0.0)
                    except Exception:
                        continue
        except Exception:
            pass

        return JsonResponse({
            'success': True,
            'report_date': report_date,
            'cumulative_up_to': cumulative_up_to,
            'cumulative_usd_up_to': cumulative_usd_up_to,
            'cumulative_ves_equiv_up_to': cumulative_ves_equiv_up_to,
            'cumulative_ves_bolivares_up_to': cumulative_ves_bolivares_up_to,
            # per-file fields intentionally omitted; use svc methods to inspect files separately
            'usd_mtd': usd_mtd,
            'ves_equiv_mtd': ves_equiv_mtd,
            'ves_bolivares_mtd': ves_bolivares_mtd,
            'usd_total': usd_total,
            'ves_equiv_total': ves_equiv_total,
            'ves_bolivares_total': ves_bolivares_total
        })
    except Exception as e:
        logger.error(f"Error in preview_cobranzas_data: {e}")
        return JsonResponse({'success': False, 'error': str(e)})
