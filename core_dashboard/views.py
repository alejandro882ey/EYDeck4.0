

# # Create users if they don't exist
# if not User.objects.filter(username='admin').exists():
#     User.objects.create_user('admin', password='admin')
# if not User.objects.filter(username='dev').exists():
#     User.objects.create_user('dev', password='dev')

from django.shortcuts import render, redirect
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField, FloatField
from django.db.models.functions import TruncWeek, Coalesce
from django.utils import timezone
import datetime
import json
import logging
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from ey_analytics_engine import fetch_all_data, generate_dashboard_analytics
import plotly.graph_objects as go
from django.conf import settings
import os
import traceback
import subprocess

from .data_processor import process_uploaded_files
from .models import UploadHistory, RevenueEntry, Client, Area, SubArea, Contract, ExchangeRate
from .utils import get_fiscal_month_year
from core_dashboard.modules import ranking_module
from core_dashboard.modules.exchange_rate_module import get_exchange_rate_data
try:
    # Import programmatic IMAP fetcher; safe import if module exists
    from core_dashboard.management.commands.fetch_exchange_emails import fetch_and_update
except Exception:
    fetch_and_update = None


# Helper: compute cumulative goal from fiscal year start up to report date
def compute_cumulative_goal(metas_df, label_col, label_value, current_report_date, goal_col, mes_col='Mes', match_contains=False, label_eq=False):
    """
    Sum monthly goals from fiscal year start (July) up to the fiscal month that contains current_report_date.

    metas_df: pandas DataFrame with a column 'Mes' containing strings like 'Julio 25', 'Agosto 25', ... or 'Total'
    label_col: column name to match (e.g., 'Partner', 'Manager', 'SL')
    label_value: value to match for label_col (string)
    current_report_date: datetime.date indicating the reporting date
    goal_col: column name containing the numeric monthly goal (e.g., 'ANSR Goal')
    match_contains: if True, match label_col using case-insensitive contains; else equality (after strip/lower)
    label_eq: if True, match label_col with exact equality (case-sensitive strip), used for SL rows like 'Total general'
    """
    try:
        import calendar
        if current_report_date is None:
            return 0

        # Determine fiscal year start (July of fiscal year)
        if current_report_date.month >= 7:
            fy_start_year = current_report_date.year
        else:
            fy_start_year = current_report_date.year - 1

        # Build months from July (7) of fy_start_year up to the fiscal month for current_report_date
        months = []
        # fiscal target month and year
        target_month = None
        target_year = None
        # compute fiscal month name/year string for target using existing helper
        target_label = get_fiscal_month_year(current_report_date)

        # iterate months starting July
        m = 7
        y = fy_start_year
        while True:
            month_name = calendar.month_name[m]
            # Spanish month names mapping in get_fiscal_month_year uses Spanish names; try to map English->Spanish
            # Create a simple map to Spanish short names used in metas files
            es_map = {
                'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril', 'May': 'Mayo', 'June': 'Junio',
                'July': 'Julio', 'August': 'Agosto', 'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
            }
            es_month = es_map.get(month_name, month_name)
            mes_label = f"{es_month} {y % 100}"
            months.append(mes_label)
            if mes_label == target_label:
                break
            # advance month
            m += 1
            if m > 12:
                m = 1
                y += 1
            # safety: avoid infinite loop
            if len(months) > 12:
                break

        # Sum goal_col for all matching rows across the months list
        total = 0
        for mes in months:
            try:
                if label_col and not label_eq:
                    if match_contains:
                        rows = metas_df[metas_df[label_col].astype(str).str.strip().str.lower().str.contains(str(label_value).strip().lower(), na=False) & (metas_df[mes_col] == mes)]
                    else:
                        rows = metas_df[(metas_df[label_col].astype(str).str.strip().str.lower() == str(label_value).strip().lower()) & (metas_df[mes_col] == mes)]
                elif label_col and label_eq:
                    rows = metas_df[(metas_df[label_col].astype(str).str.strip() == str(label_value).strip()) & (metas_df[mes_col] == mes)]
                else:
                    rows = metas_df[metas_df[mes_col] == mes]
                if not rows.empty and goal_col in rows.columns:
                    s = rows[goal_col].astype(float).sum()
                    total += float(s or 0)
            except Exception:
                continue
        return float(total)
    except Exception:
        return 0
from core_dashboard.modules.manager_revenue_days import ManagerRevenueDaysService, ManagerAnalyticsService
# Optional Cobranzas module
try:
    from core_dashboard.modules.cobranzas.services import CobranzasService
except Exception:
    CobranzasService = None
# Service Line cards module (provides four SL-specific KPI cards)
try:
    from core_dashboard.modules.service_line_cards.services import ServiceLineCardsService
except Exception:
    ServiceLineCardsService = None
# Sub Service Line (SSL) cards module
try:
    from core_dashboard.modules.sub_service_line_cards.services import SubServiceLineCardsService
except Exception:
    SubServiceLineCardsService = None


def upload_file_view(request):
    history = UploadHistory.objects.all().order_by('-uploaded_at')
    if request.method == 'POST':
        try:
            upload_date_str = request.POST.get('upload_date')
            if not upload_date_str:
                raise ValueError("Upload date is required.")
            upload_date = datetime.datetime.strptime(upload_date_str, '%Y-%m-%d').date()

            engagement_file = request.FILES.get('engagement_df_file')
            dif_file = request.FILES.get('dif_df_file')
            revenue_days_file = request.FILES.get('revenue_days_file')
            manager_revenue_days_file = request.FILES.get('manager_revenue_days_file')  # Optional
            cobranzas_file = request.FILES.get('cobranzas_file')  # Optional
            facturacion_file = request.FILES.get('facturacion_file')  # Optional

            if not all([engagement_file, dif_file, revenue_days_file]):
                raise ValueError("Engagement, Dif, and Revenue Days files are required.")

            # Validate file extensions
            ALLOWED_EXTENSIONS = {'.csv', '.xls', '.xlsx', '.xlsb'}
            files_to_validate = [engagement_file, dif_file, revenue_days_file]
                
            for f in files_to_validate:
                ext = os.path.splitext(f.name)[1]
                if ext.lower() not in ALLOWED_EXTENSIONS:
                    raise ValueError(f"File type {ext} is not allowed.")

            # Create history directory for the given date
            history_dir = os.path.join(settings.MEDIA_ROOT, 'historico_de_final_database', upload_date.strftime('%Y-%m-%d'))
            os.makedirs(history_dir, exist_ok=True)

            from django.core.files.storage import FileSystemStorage
            fs = FileSystemStorage(location=history_dir)

            # Save files with new names
            engagement_ext = os.path.splitext(engagement_file.name)[1]
            dif_ext = os.path.splitext(dif_file.name)[1]
            revenue_ext = os.path.splitext(revenue_days_file.name)[1]
            cobranzas_ext = None
            if cobranzas_file:
                cobranzas_ext = os.path.splitext(cobranzas_file.name)[1]
            facturacion_ext = None
            if facturacion_file:
                facturacion_ext = os.path.splitext(facturacion_file.name)[1]

            engagement_filename = fs.save(f"Engagement_df_{upload_date_str}{engagement_ext}", engagement_file)
            dif_filename = fs.save(f"Dif_df_{upload_date_str}{dif_ext}", dif_file)
            revenue_filename = fs.save(f"Revenue_days_{upload_date_str}{revenue_ext}", revenue_days_file)
            cobranzas_filename = None
            if cobranzas_file:
                cobranzas_filename = fs.save(f"Cobranzas_{upload_date_str}{cobranzas_ext}", cobranzas_file)
            facturacion_filename = None
            if facturacion_file:
                facturacion_filename = fs.save(f"Facturacion_{upload_date_str}{facturacion_ext}", facturacion_file)

            engagement_path = fs.path(engagement_filename)
            dif_path = fs.path(dif_filename)
            revenue_path = fs.path(revenue_filename)
            cobranzas_path = fs.path(cobranzas_filename) if cobranzas_filename else None
            facturacion_path = fs.path(facturacion_filename) if facturacion_filename else None
            
            # --- NEW: Call process_uploaded_data.py as a subprocess ---
            process_script_path = os.path.join(settings.BASE_DIR, 'process_uploaded_data.py')
            command = [
                'python',
                process_script_path,
                engagement_path,
                dif_path,
                revenue_path,
                upload_date_str
            ]
            print(f"Executing command: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, check=False)

            print(f"Subprocess Return Code: {result.returncode}")
            print(f"Subprocess STDOUT: {result.stdout}")
            print(f"Subprocess STDERR: {result.stderr}")

            if result.returncode != 0:
                error_message = f"Error processing files: {result.stderr}"
                print(f"Subprocess Error: {error_message}")
                raise Exception(error_message)

            # --- END NEW ---

            # The legacy Final_Database CSV is no longer produced. Files were processed
            # in-memory by process_uploaded_data.py and imported into the database.
            # Instead of attempting to read a Final_Database CSV, proceed to record
            # the upload and redirect to the main dashboard where the new data will
            # be visible. If something went wrong during processing the subprocess
            # would have returned a non-zero exit code and we would have already
            # raised an Exception above.

            # Process Manager Revenue Days file if provided (optional)
            manager_revenue_days_result = None
            if manager_revenue_days_file:
                try:
                    print(f"Processing Manager Revenue Days file: {manager_revenue_days_file.name}")
                    manager_service = ManagerRevenueDaysService()
                    
                    # Create dated filename to match the upload date
                    original_name = manager_revenue_days_file.name
                    dated_filename = f"Revenue Days Manager_{upload_date_str}.xlsx"
                    
                    manager_revenue_days_result = manager_service.process_uploaded_file(
                        manager_revenue_days_file, 
                        dated_filename
                    )
                    
                    if manager_revenue_days_result['success']:
                        print(f"Successfully processed Manager Revenue Days: {manager_revenue_days_result['message']}")
                    else:
                        print(f"Warning: Manager Revenue Days processing failed: {manager_revenue_days_result['error']}")
                        
                except Exception as e:
                    print(f"Warning: Error processing Manager Revenue Days file: {str(e)}")
                    # Don't fail the entire upload if Manager Revenue Days processing fails
                    manager_revenue_days_result = {'success': False, 'error': str(e)}

            # Record the upload in history
            file_names = f"Engagement_df_{upload_date_str}, Dif_df_{upload_date_str}, Revenue_days_{upload_date_str}"
            if manager_revenue_days_file:
                file_names += f", Manager_Revenue_Days_{upload_date_str}"
            # Process Cobranzas if provided (optional)
            cobranzas_result = None
            if cobranzas_file:
                try:
                    from core_dashboard.modules.cobranzas.services import CobranzasService
                    cobr_service = CobranzasService()
                    original_name = cobranzas_file.name
                    dated_filename = f"Cobranzas_{upload_date_str}.xlsx"
                    cobranzas_result = cobr_service.process_uploaded_file(cobranzas_file, dated_filename)
                    if cobranzas_result.get('success'):
                        file_names += f", Cobranzas_{upload_date_str}"
                        print(f"Successfully processed Cobranzas: {cobranzas_result.get('message')}")
                    else:
                        print(f"Warning: Cobranzas processing failed: {cobranzas_result.get('error')}")
                except Exception as e:
                    print(f"Warning: Error processing Cobranzas file: {str(e)}")
                    cobranzas_result = {'success': False, 'error': str(e)}
                
            # Process Facturacion if provided (optional)
            facturacion_result = None
            if facturacion_file:
                try:
                    from core_dashboard.modules.facturacion.services import FacturacionService
                    fact_service = FacturacionService()
                    original_name = facturacion_file.name
                    dated_filename = f"Facturacion_{upload_date_str}.xlsx"
                    facturacion_result = fact_service.process_uploaded_file(facturacion_file, dated_filename)
                    if facturacion_result.get('success'):
                        file_names += f", Facturacion_{upload_date_str}"
                        print(f"Successfully processed Facturacion: {facturacion_result.get('message')}")
                    else:
                        print(f"Warning: Facturacion processing failed: {facturacion_result.get('error')}")
                except Exception as e:
                    print(f"Warning: Error processing Facturacion file: {str(e)}")
                    facturacion_result = {'success': False, 'error': str(e)}
                
            UploadHistory.objects.create(
                file_name=file_names,
                uploaded_by=None
            )

            # Redirect to main dashboard so the newly processed data (imported into DB)
            # is visible. Provide a success message via Django messages or query param.
            from django.contrib import messages
            messages.success(request, 'Files uploaded and processed successfully!')
            return redirect('dashboard')

        except Exception as e:
            print(f"Error during file upload or processing: {e}")
            traceback.print_exc()
            context = {'history': history, 'error_message': f'Error: {e}'}
            return render(request, 'core_dashboard/upload.html', context)

    return render(request, 'core_dashboard/upload.html', {'history': history})


def delete_data_and_cache_view(request):
    """Handle the delete data and cache operation with password protection."""
    from django.http import JsonResponse
    from django.views.decorators.csrf import csrf_exempt
    import shutil
    from pathlib import Path
    
    print(f"Delete request received: method={request.method}")
    
    if request.method == 'POST':
        password = request.POST.get('password', '')
        print(f"Password received: {'YES' if password else 'NO'}")
        
        # Check password
        if password != '69420':
            print("Invalid password provided")
            return JsonResponse({'success': False, 'message': 'Invalid password.'})
        
        print("Password validated successfully")
        
        try:
            print("Starting data and cache deletion...")
            
            # Clear all database data with counts
            revenue_count = RevenueEntry.objects.count()
            RevenueEntry.objects.all().delete()
            print(f"✓ Cleared {revenue_count} RevenueEntry records")
            
            upload_count = UploadHistory.objects.count()
            UploadHistory.objects.all().delete()
            print(f"✓ Cleared {upload_count} UploadHistory records")
            
            exchange_count = ExchangeRate.objects.count()
            ExchangeRate.objects.all().delete()
            print(f"✓ Cleared {exchange_count} ExchangeRate records")
            
            # Clear foreign key related data
            contract_count = Contract.objects.count()
            Contract.objects.all().delete()
            print(f"✓ Cleared {contract_count} Contract records")
            
            subarea_count = SubArea.objects.count()
            SubArea.objects.all().delete()
            print(f"✓ Cleared {subarea_count} SubArea records")
            
            area_count = Area.objects.count()
            Area.objects.all().delete()
            print(f"✓ Cleared {area_count} Area records")
            
            client_count = Client.objects.count()
            Client.objects.all().delete()
            print(f"✓ Cleared {client_count} Client records")
            
            # Clear media files (uploaded files and processed data)
            media_root = Path(settings.MEDIA_ROOT)
            print(f"Media root path: {media_root}")
            if media_root.exists():
                try:
                    shutil.rmtree(media_root)
                    print("✓ Cleared media directory")
                except Exception as e:
                    print(f"✗ Error clearing media directory: {e}")
                    # Don't fail the entire operation for this
            else:
                print("Media directory doesn't exist, skipping")
            
            # Clear __pycache__ directories
            base_dir = Path(settings.BASE_DIR)
            print(f"Base directory: {base_dir}")
            cache_dirs_cleared = 0
            
            for root, dirs, files in os.walk(base_dir):
                for dir_name in dirs:
                    if dir_name == "__pycache__":
                        cache_path = os.path.join(root, dir_name)
                        try:
                            shutil.rmtree(cache_path)
                            cache_dirs_cleared += 1
                            print(f"✓ Cleared cache: {cache_path}")
                        except Exception as e:
                            print(f"✗ Error clearing cache {cache_path}: {e}")
            
            print(f"✓ Cleared {cache_dirs_cleared} __pycache__ directories")
            
            # Clear specific cache files
            cache_files = [
                "historical_data.csv",
                "*.pyc"
            ]
            
            files_cleared = 0
            for pattern in cache_files:
                for file_path in base_dir.glob(f"**/{pattern}"):
                    try:
                        file_path.unlink()
                        files_cleared += 1
                        print(f"✓ Cleared cache file: {file_path}")
                    except Exception as e:
                        print(f"✗ Error clearing cache file {file_path}: {e}")
            
            print(f"✓ Cleared {files_cleared} cache files")
            print("🎉 All data and cache cleared successfully!")
            
            return JsonResponse({
                'success': True, 
                'message': f'Successfully deleted: {revenue_count + upload_count + exchange_count + contract_count + subarea_count + area_count + client_count} database records, {cache_dirs_cleared} cache directories, and {files_cleared} cache files.'
            })
            
        except Exception as e:
            error_msg = f"Error during deletion: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': error_msg})
    
    print("Non-POST request, redirecting to upload page")
    # For non-POST requests, redirect to upload page
    return redirect('upload_file')


def tables_view(request):
    return render(request, 'core_dashboard/tables.html')


def analysis_view(request):
    try:
        # 1. Fetch the data using the new engine
        master_df = fetch_all_data(historical_csv_path='historical_data.csv')
        print(f"Length of master_df: {len(master_df)}")

        # 2. Generate the analytics and charts
        if len(master_df) > 20:
            final_dashboard_data = generate_dashboard_analytics(master_df)

            # 3. Process the output for the template
            # Trends
            trends_html = ""
            if 'moving_averages_chart' in final_dashboard_data['Trends'] and isinstance(final_dashboard_data['Trends']['moving_averages_chart'], go.Figure):
                trends_html += final_dashboard_data['Trends']['moving_averages_chart'].to_html(full_html=False, include_plotlyjs='cdn')
            else:
                trends_html += "<p>Moving Averages chart not available.</p>"

            if 'hp_filter_chart' in final_dashboard_data['Trends'] and isinstance(final_dashboard_data['Trends']['hp_filter_chart'], go.Figure):
                trends_html += final_dashboard_data['Trends']['hp_filter_chart'].to_html(full_html=False, include_plotlyjs='cdn')
            else:
                trends_html += "<p>HP Filter chart not available.</p>"

            if 'garch_volatility_chart' in final_dashboard_data['Trends'] and isinstance(final_dashboard_data['Trends']['garch_volatility_chart'], go.Figure):
                trends_html += final_dashboard_data['Trends']['garch_volatility_chart'].to_html(full_html=False, include_plotlyjs='cdn')
            else:
                trends_html += "<p>GARCH Volatility chart not available.</p>"

            if 'latest_volatility' in final_dashboard_data['Trends']:
                trends_html += f"<h5>Latest Volatility: {final_dashboard_data['Trends']['latest_volatility']:.4f}</h5>"

            # Projections
            projections_html = ""
            if 'arima_forecast_chart' in final_dashboard_data['Projections'] and isinstance(final_dashboard_data['Projections']['arima_forecast_chart'], go.Figure):
                projections_html += final_dashboard_data['Projections']['arima_forecast_chart'].to_html(full_html=False, include_plotlyjs='cdn')
            else:
                projections_html += "<p>ARIMA Forecast chart not available.</p>"

            if 'holt_winters_chart' in final_dashboard_data['Projections'] and isinstance(final_dashboard_data['Projections']['holt_winters_chart'], go.Figure):
                projections_html += final_dashboard_data['Projections']['holt_winters_chart'].to_html(full_html=False, include_plotlyjs='cdn')
            else:
                projections_html += "<p>Holt-Winters Forecast chart not available.</p>"

            # Estimates
            estimations_html = ""
            if 'spread_chart' in final_dashboard_data['Estimates'] and isinstance(final_dashboard_data['Estimates']['spread_chart'], go.Figure):
                estimations_html += final_dashboard_data['Estimates']['spread_chart'].to_html(full_html=False, include_plotlyjs='cdn')
            else:
                estimations_html += "<p>Spread chart not available.</p>"

            if 'var_irf_chart' in final_dashboard_data['Estimates'] and isinstance(final_dashboard_data['Estimates']['var_irf_chart'], go.Figure):
                estimations_html += final_dashboard_data['Estimates']['var_irf_chart'].to_html(full_html=False, include_plotlyjs='cdn')
            else:
                estimations_html += "<p>VAR IRF chart not available.</p>"

            if 'latest_spread' in final_dashboard_data['Estimates']:
                estimations_html += f"<h5>Latest Spread: {final_dashboard_data['Estimates']['latest_spread']:.2f}%</h5>"

            # Benchmarking
            benchmarking_html = ""
            if 'benchmark_chart' in final_dashboard_data['Benchmarking'] and isinstance(final_dashboard_data['Benchmarking']['benchmark_chart'], go.Figure):
                benchmarking_html += final_dashboard_data['Benchmarking']['benchmark_chart'].to_html(full_html=False, include_plotlyjs='cdn')
            else:
                benchmarking_html += "<p>Benchmark chart not available.</p>"

            if 'forecast_surprise' in final_dashboard_data['Benchmarking']:
                benchmarking_html += f"<h5>Forecast Surprise: {final_dashboard_data['Benchmarking']['forecast_surprise']:.4f}</h5>"

            # Competitive Landscape
            competitive_landscape_html = ""
            if 'share_of_voice_chart' in final_dashboard_data['Competitive_Landscape'] and isinstance(final_dashboard_data['Competitive_Landscape']['share_of_voice_chart'], go.Figure):
                competitive_landscape_html += final_dashboard_data['Competitive_Landscape']['share_of_voice_chart'].to_html(full_html=False, include_plotlyjs='cdn')
            else:
                competitive_landscape_html += "<p>Share of Voice chart not available.</p>"

            if 'brand_interest_chart' in final_dashboard_data['Competitive_Landscape'] and isinstance(final_dashboard_data['Competitive_Landscape']['brand_interest_chart'], go.Figure):
                competitive_landscape_html += final_dashboard_data['Competitive_Landscape']['brand_interest_chart'].to_html(full_html=False, include_plotlyjs='cdn')
            else:
                competitive_landscape_html += "<p>Brand Interest chart not available.</p>"

            if 'talent_acquisition_chart' in final_dashboard_data['Competitive_Landscape'] and isinstance(final_dashboard_data['Competitive_Landscape']['talent_acquisition_chart'], go.Figure):
                competitive_landscape_html += final_dashboard_data['Competitive_Landscape']['talent_acquisition_chart'].to_html(full_html=False, include_plotlyjs='cdn')
            else:
                competitive_landscape_html += "<p>Talent Acquisition chart not available.</p>"

            context = {
                'trends': trends_html,
                'projections': projections_html,
                'estimations': estimations_html,
                'expected_data': benchmarking_html,
                'competitive_landscape': competitive_landscape_html, # Added new context variable
            }
        else:
            context = {
                'trends': "<p>Not enough historical data for analysis. Need at least 20 data points.</p>",
                'projections': "",
                'estimations': "",
                'expected_data': "",
                'competitive_landscape': "", # Added new context variable
            }
        print(f"Context keys: {context.keys()}")
        for key, value in context.items():
            if isinstance(value, str):
                print(f"Context['{key}'] length: {len(value)}")
                if len(value) < 500: # Print short values for inspection
                    print(f"Context['{key}'] content: {value[:200]}...")
            else:
                print(f"Context['{key}'] type: {type(value)}")

    except Exception as e:
        print(f"Error in analysis_view: {e}")
        traceback.print_exc()
        context = {
            'trends': f"<p>An error occurred during analysis: {e}</p>",
            'projections': "",
            'estimations': "",
            'expected_data': "",
            'competitive_landscape': "", # Added new context variable
        }

    return render(request, 'core_dashboard/analysis.html', context)


def messaging_view(request):
    # Get distinct partners, managers, and areas for messaging
    partners = RevenueEntry.objects.values_list('engagement_partner', flat=True).distinct().exclude(engagement_partner__isnull=True).exclude(Q(engagement_partner__exact='')).order_by('engagement_partner')
    managers = RevenueEntry.objects.values_list('engagement_manager', flat=True).distinct().exclude(engagement_manager__isnull=True).exclude(Q(engagement_manager__exact='')).order_by('engagement_manager')
    areas = Area.objects.values_list('name', flat=True).distinct().exclude(name__isnull=True).exclude(Q(name__exact='')).order_by('name')
    context = {
        'partners': partners,
        'managers': managers,
        'areas': areas
    }
    return render(request, 'core_dashboard/messaging.html', context)


def dashboard_view(request):
    # Get filter parameters from request
    selected_partner = request.GET.get('partner')
    selected_manager = request.GET.get('manager')
    selected_area = request.GET.get('service_line')
    selected_sub_area = request.GET.get('sub_service_line')
    selected_client = request.GET.get('client')
    selected_week_filter = request.GET.get('week') # Renamed to avoid conflict

    print(f"DEBUG: selected_partner: {selected_partner}")
    print(f"DEBUG: selected_manager: {selected_manager}")
    print(f"DEBUG: selected_area: {selected_area}")
    print(f"DEBUG: selected_sub_area: {selected_sub_area}")
    print(f"DEBUG: selected_client: {selected_client}")
    print(f"DEBUG: selected_week_filter: {selected_week_filter}")
    print(f"DEBUG: selected_partner: {selected_partner}")
    print(f"DEBUG: selected_manager: {selected_manager}")
    print(f"DEBUG: selected_area: {selected_area}")
    print(f"DEBUG: selected_sub_area: {selected_sub_area}")
    print(f"DEBUG: selected_client: {selected_client}")
    print(f"DEBUG: selected_week_filter: {selected_week_filter}")

    # Ensure context dict exists early so any code path that sets context[...] won't fail
    context = {}

    # Queryset for historical trend (uses all data)
    all_revenue_entries = RevenueEntry.objects.all()

    # Base queryset for KPIs. Start with all entries.
    base_revenue_entries = RevenueEntry.objects.all()

    # Get distinct weeks for filtering, formatted to Friday's date
    available_weeks_raw = RevenueEntry.objects.annotate(calculated_week=TruncWeek('date')).values_list('calculated_week', flat=True).distinct().order_by('calculated_week')
    available_weeks = []
    for week_start_date in available_weeks_raw:
        if week_start_date:
            # Calculate Friday's date for the week (assuming week starts on Monday)
            # Monday (0) to Sunday (6). Friday is 4.
            # If week_start_date is Monday, add 4 days to get Friday.
            friday_date = week_start_date + datetime.timedelta(days=4)
            available_weeks.append(friday_date.strftime('%Y-%m-%d'))

    # Date filtering logic for the entire page
    if selected_week_filter:
        friday_date = datetime.datetime.strptime(selected_week_filter, '%Y-%m-%d').date()
        start_of_week = friday_date - datetime.timedelta(days=friday_date.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=6)
        base_revenue_entries = base_revenue_entries.filter(date__range=[start_of_week, end_of_week])
    elif available_weeks:
        # Default to the most recent week if no week is selected
        most_recent_week = available_weeks[-1]
        friday_date = datetime.datetime.strptime(most_recent_week, '%Y-%m-%d').date()
        print(f"DEBUG: base_revenue_entries count after week filter: {base_revenue_entries.count()}")
        start_of_week = friday_date - datetime.timedelta(days=friday_date.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=6)
        base_revenue_entries = base_revenue_entries.filter(date__range=[start_of_week, end_of_week])
    else:
        base_revenue_entries = RevenueEntry.objects.none()
    print(f"DEBUG: base_revenue_entries count after week filter: {base_revenue_entries.count()}")

    # --- Macro Section Calculations (always on the full dataset for the selected date) ---
    macro_revenue_entries = base_revenue_entries
    if selected_area:
        macro_revenue_entries = macro_revenue_entries.filter(area__name=selected_area)
    if selected_sub_area:
        macro_revenue_entries = macro_revenue_entries.filter(sub_area__name=selected_sub_area)
    if selected_client:
        macro_revenue_entries = macro_revenue_entries.filter(client__name=selected_client)
    
    macro_total_clients = macro_revenue_entries.values('client').distinct().count()
    # ANSR YTD should be computed from the synthetic field (fytd_ansr_sintetico)
    macro_ansr_fytd = macro_revenue_entries.aggregate(Sum('fytd_ansr_sintetico'))['fytd_ansr_sintetico__sum'] or 0
    macro_total_direct_cost = macro_revenue_entries.aggregate(Sum('fytd_direct_cost_amt'))['fytd_direct_cost_amt__sum'] or 0
    macro_margin = macro_ansr_fytd - macro_total_direct_cost
    macro_margin_percentage = (macro_margin / macro_ansr_fytd * 100) if macro_ansr_fytd else 0
    macro_total_charged_hours = macro_revenue_entries.aggregate(Sum('fytd_charged_hours'))['fytd_charged_hours__sum'] or 0
    macro_rph = (macro_ansr_fytd / macro_total_charged_hours) if macro_total_charged_hours else 0
    macro_mtd_charged_hours = macro_revenue_entries.aggregate(Sum('mtd_charged_hours'))['mtd_charged_hours__sum'] or 0
    macro_monthly_tracker = macro_mtd_charged_hours * macro_rph
    total_mtd_charged_hours = macro_revenue_entries.aggregate(Sum('mtd_charged_hours'))['mtd_charged_hours__sum'] or 0
    total_fytd_charged_hours = macro_revenue_entries.aggregate(Sum('fytd_charged_hours'))['fytd_charged_hours__sum'] or 0
    macro_diferencial_final = macro_revenue_entries.aggregate(Sum('fytd_diferencial_final'))['fytd_diferencial_final__sum'] or 0
    # Sum for new Diferencial Final MTD column and convert to absolute value
    # Use abs() for display since we want to show the magnitude of the difference
    macro_diferencial_mtd = abs(macro_revenue_entries.aggregate(Sum('diferencial_mtd'))['diferencial_mtd__sum'] or 0)

    # --- New MTD direct cost and MTD margin/RPH calculations ---
    # Sum of MTD direct cost (per row field mtd_direct_cost_amt)
    macro_mtd_direct_cost = macro_revenue_entries.aggregate(Sum('mtd_direct_cost_amt'))['mtd_direct_cost_amt__sum'] or 0

    # RPH MTD: ANSR MTD (macro_monthly_tracker) / total MTD charged hours
    macro_rph_mtd = (macro_monthly_tracker / total_mtd_charged_hours) if total_mtd_charged_hours else 0

    # Margin MTD: ANSR MTD minus sum(MTD_DirectCostAmt)
    macro_mtd_margin_value = (macro_monthly_tracker - macro_mtd_direct_cost)
    macro_mtd_margin_percentage = (macro_mtd_margin_value / macro_monthly_tracker * 100) if macro_monthly_tracker else 0

    # Calculate collection metrics for Cobranzas (Collected YTD) card
    # Prefer processed Cobranzas module totals exclusively when available; otherwise default to 0
    macro_collected_total = 0.0
    macro_billed_total = 0.0
    try:
        if CobranzasService is not None:
            cobr_service = CobranzasService()
            # If a week filter is selected, compute cumulative collected up to that date
            try:
                if selected_week_filter:
                    try:
                        macro_collected_total = float(cobr_service.get_cumulative_collected_up_to(selected_week_filter) or 0.0)
                    except Exception:
                        macro_collected_total = float(cobr_service.get_cumulative_collected_total() or 0.0)
                else:
                    # Use cumulative collected total across all processed reports for the Macro card
                    macro_collected_total = float(cobr_service.get_cumulative_collected_total() or 0.0)
            except Exception:
                # fallback to latest file collected
                latest_info = cobr_service.get_latest_file_info()
                if latest_info:
                    try:
                        macro_collected_total, _ = cobr_service.get_totals_from_file(latest_info['path'])
                    except Exception:
                        macro_collected_total = cobr_service.get_collected_total_from_latest()
            # keep billed at zero until Facturacion module exists
            # Try to get billed total from Facturacion module if available
            try:
                from core_dashboard.modules.facturacion.services import FacturacionService
                fact_service = FacturacionService()
                latest_info = fact_service.get_latest_file_info()
                if latest_info:
                    if selected_week_filter:
                        # Use the computed friday_date (a date object) to sum up to the filter date
                        try:
                            macro_billed_total = float(fact_service.get_totals_from_file(latest_info['path'], up_to_date=friday_date) or 0.0)
                        except Exception:
                            macro_billed_total = float(fact_service.get_totals_from_file(latest_info['path']) or 0.0)
                    else:
                        macro_billed_total = float(fact_service.get_totals_from_file(latest_info['path']) or 0.0)
                else:
                    macro_billed_total = 0.0
            except Exception as e:
                print(f"DEBUG: Error getting Facturacion totals: {e}")
                macro_billed_total = 0.0
    except Exception as e:
        print(f"DEBUG: Error getting Cobranzas totals: {e}")

    print(f"DEBUG: macro_collected_total = {macro_collected_total}")
    print(f"DEBUG: macro_billed_total = {macro_billed_total}")

    # Sum of 'fytd_diferencial_final' per partner
    diferencial_final_by_partner = base_revenue_entries.values('engagement_partner').annotate(
        total_diferencial_final=Coalesce(Sum('fytd_diferencial_final'), 0.0)
    ).order_by('-total_diferencial_final')

    # --- Filtered Section (for partner/manager specific views) ---
    revenue_entries_for_kpis = base_revenue_entries
    if selected_partner:
        revenue_entries_for_kpis = revenue_entries_for_kpis.filter(engagement_partner=selected_partner)
    if selected_manager:
        revenue_entries_for_kpis = revenue_entries_for_kpis.filter(engagement_manager=selected_manager)
    if selected_area:
        revenue_entries_for_kpis = revenue_entries_for_kpis.filter(area__name=selected_area)
    if selected_sub_area:
        revenue_entries_for_kpis = revenue_entries_for_kpis.filter(sub_area__name=selected_sub_area)
    if selected_client:
        revenue_entries_for_kpis = revenue_entries_for_kpis.filter(client__name=selected_client)
    print(f"DEBUG: revenue_entries_for_kpis count after all filters: {revenue_entries_for_kpis.count()}")
    print(f"DEBUG: revenue_entries_for_kpis first entry: {revenue_entries_for_kpis.first()}")

    # KPIs for the filtered view
    ansr_sintetico = "${:,.2f}".format(revenue_entries_for_kpis.aggregate(Sum('fytd_ansr_sintetico'))['fytd_ansr_sintetico__sum'] or 0)
    total_clients = "{:,.0f}".format(revenue_entries_for_kpis.values('client').distinct().count())
    total_engagements = "{:,.0f}".format(revenue_entries_for_kpis.values('contract').distinct().count())

    # Charged hours by partner and manager (based on the filtered data)
    fytd_charged_hours_by_partner = revenue_entries_for_kpis.values('engagement_partner').annotate(
        total_fytd_charged_hours=Sum('fytd_charged_hours')
    ).order_by('-total_fytd_charged_hours')

    mtd_charged_hours_by_partner = revenue_entries_for_kpis.values('engagement_partner').annotate(
        total_mtd_charged_hours=Sum('mtd_charged_hours')
    ).order_by('-total_mtd_charged_hours')

    fytd_charged_hours_by_manager = revenue_entries_for_kpis.values('engagement_manager').annotate(
        total_fytd_charged_hours=Sum('fytd_charged_hours')
    ).order_by('-total_fytd_charged_hours')

    mtd_charged_hours_by_manager = revenue_entries_for_kpis.values('engagement_manager').annotate(
        total_mtd_charged_hours=Sum('mtd_charged_hours')
    ).order_by('-total_mtd_charged_hours')

    # Add FYTD_ChargedHours and MTD_Charged to the partner filter
    # This will be used in the template to display the data
    fytd_charged_hours_by_partner_with_labels = []
    mtd_charged_hours_by_partner_with_labels = []

    for partner in fytd_charged_hours_by_partner:
        fytd_charged_hours_by_partner_with_labels.append({
            'engagement_partner': partner['engagement_partner'],
            'total_fytd_charged_hours': partner['total_fytd_charged_hours'],
            'label': 'Horas Cargadas (FYTD)'
        })

    for partner in mtd_charged_hours_by_partner:
        mtd_charged_hours_by_partner_with_labels.append({
            'engagement_partner': partner['engagement_partner'],
            'total_mtd_charged_hours': partner['total_mtd_charged_hours'],
            'label': 'Horas Cargadas (MTD)'
        })

    # --- All Partners Ranked (for flip card) ---
    all_partners_ranked = base_revenue_entries.values('engagement_partner').annotate(
        total_revenue=Sum('fytd_ansr_sintetico')
    ).order_by('-total_revenue').exclude(engagement_partner__isnull=True).exclude(engagement_partner__exact='')
    for p in all_partners_ranked:
        p['total_revenue'] = "${:,.2f}".format(p['total_revenue'] or 0)

    # Get all FYTD charged hours by partner to merge with the ranked list
    all_fytd_charged_hours_by_partner = base_revenue_entries.values('engagement_partner').annotate(
        total_fytd_charged_hours=Sum('fytd_charged_hours')
    ).order_by('engagement_partner')

    # Calculate FYTD, MTD, and Daily Revenue
    today = timezone.now().date()
    current_month_start = today.replace(day=1)
    current_year_start = today.replace(month=1, day=1) # Assuming fiscal year starts Jan 1

    fytd_revenue = "${:,.2f}".format(revenue_entries_for_kpis.filter(date__gte=current_year_start).aggregate(Sum('fytd_ansr_sintetico'))['fytd_ansr_sintetico__sum'] or 0)
    mtd_revenue = "${:,.2f}".format(revenue_entries_for_kpis.filter(date__gte=current_month_start).aggregate(Sum('fytd_ansr_sintetico'))['fytd_ansr_sintetico__sum'] or 0)
    daily_revenue = "${:,.2f}".format(revenue_entries_for_kpis.filter(date=today).aggregate(Sum('fytd_ansr_sintetico'))['fytd_ansr_sintetico__sum'] or 0)

    # Placeholder for Collections and Billing (assuming fields exist in RevenueEntry)
    total_collections = "${:,.2f}".format(revenue_entries_for_kpis.aggregate(Sum('collections'))['collections__sum'] or 0)
    total_billing = "${:,.2f}".format(revenue_entries_for_kpis.aggregate(Sum('billing'))['billing__sum'] or 0)

    # Placeholder for Active Employees in Venezuela
    active_employees_venezuela = "{:,.0f}".format(150) # Static placeholder value

    # Top Partners by Revenue
    top_partners = revenue_entries_for_kpis.values('engagement_partner').annotate(
        total_revenue=Sum('fytd_ansr_sintetico')
    ).order_by('-total_revenue').exclude(engagement_partner__isnull=True).exclude(engagement_partner__exact='')[:5]
    # Format revenue for top_partners
    for p in top_partners:
        p['total_revenue'] = "${:,.2f}".format(p['total_revenue'] or 0)

    # Top 5 Clients by Revenue (for table display)
    top_clients_table = revenue_entries_for_kpis.values('client__name').annotate(total_revenue=Sum('fytd_ansr_sintetico')).order_by('-total_revenue')[:5]
    # Format revenue for top_clients_table
    for c in top_clients_table:
        c['total_revenue'] = "${:,.2f}".format(c['total_revenue'] or 0)

    # Calculate "Loss per differential"
    # Assuming 'bcv_rate' and 'monitor_rate' are fields in RevenueEntry
    # Loss = (BCV Rate - Monitor Rate) * Revenue
    loss_per_differential = "${:,.2f}".format(revenue_entries_for_kpis.annotate(
        differential_loss=ExpressionWrapper((F('bcv_rate') - F('monitor_rate')) * F('fytd_ansr_sintetico'), output_field=DecimalField())
    ).aggregate(Sum('differential_loss'))['differential_loss__sum'] or 0)

    # Revenue by Area
    revenue_by_area = revenue_entries_for_kpis.values('area__name').annotate(total_revenue=Sum('fytd_ansr_sintetico')).order_by('-total_revenue')
    area_labels = [item['area__name'] for item in revenue_by_area]
    area_data = [float(item['total_revenue'] or 0) for item in revenue_by_area]

    # Top 5 Clients by Revenue (for chart)
    top_clients_chart = revenue_entries_for_kpis.values('client__name').annotate(total_revenue=Sum('fytd_ansr_sintetico')).order_by('-total_revenue')[:5]
    client_labels = [item['client__name'] for item in top_clients_chart]
    client_data = [float(item['total_revenue'] or 0) for item in top_clients_chart]

    # Rankings (managers, clients, engagements)
    top_managers, all_managers_ranked = ranking_module.compute_ranking(revenue_entries_for_kpis, 'engagement_manager', revenue_field='fytd_ansr_sintetico')
    top_clients_rank, all_clients_ranked = ranking_module.compute_ranking(revenue_entries_for_kpis, 'client__name', revenue_field='fytd_ansr_sintetico')
    # use contract__name (existing field) for engagement/contract labels
    top_engagements, all_engagements_ranked = ranking_module.compute_ranking(revenue_entries_for_kpis, 'contract__name', revenue_field='fytd_ansr_sintetico')

    # --- New: Build detailed ranking lists for Partners, Managers, Service Lines and Sub Service Lines ---
    partners_ranking = []
    managers_ranking = []
    service_lines_ranking = []
    sub_service_lines_ranking = []

    # Helper to compute avg and goal per group
    def build_ranking(group_field, label_field=None):
        grouped = revenue_entries_for_kpis.values(group_field).annotate(
            ansr_fytd=Coalesce(Sum('fytd_ansr_sintetico'), 0.0),
            hours_fytd=Coalesce(Sum('fytd_charged_hours'), 0.0)
        ).order_by('-ansr_fytd')

        results = []
        # Compute global averages to compare against
        total_groups = 0
        total_ansr = 0.0
        total_hours = 0.0
        for g in grouped:
            total_groups += 1
            total_ansr += float(g.get('ansr_fytd') or 0)
            total_hours += float(g.get('hours_fytd') or 0)
        avg_ansr = (total_ansr / total_groups) if total_groups else 0
        avg_hours = (total_hours / total_groups) if total_groups else 0

        for g in grouped:
            label = g.get(group_field) or '-'
            ansr_value = float(g.get('ansr_fytd') or 0)
            hours_value = float(g.get('hours_fytd') or 0)
            rph = (ansr_value / hours_value) if hours_value else 0
            # Default goal resolution: keep the displayed `goal` as the monthly goal (MTD)
            # while computing completion % against the cumulative FYTD goal.
            goal = None            # this remains the displayed column (monthly/MTD)
            goal_mtd = None        # monthly goal value fetched from metas (used to set `goal`)
            goal_fytd = None       # cumulative FYTD goal (sum of months up to report date)
            goal_completion_percentage = None
            goal_color = 'grey'
            # Try to resolve goals depending on the grouping
            try:
                normalized_label = str(label).strip() if label else ''
                # Determine the current report date for monthly goals
                current_report_date = None
                if selected_week_filter:
                    current_report_date = datetime.datetime.strptime(selected_week_filter, '%Y-%m-%d').date()
                elif available_weeks:
                    current_report_date = datetime.datetime.strptime(available_weeks[-1], '%Y-%m-%d').date()

                # Partners: metas_PPED.csv
                if group_field == 'engagement_partner':
                    metas_pped_path = os.path.join(settings.BASE_DIR, 'metas_PPED.csv')
                    if os.path.exists(metas_pped_path):
                        metas_pped_df = pd.read_csv(metas_pped_path)
                        metas_pped_df['Partner'] = metas_pped_df['Partner'].astype(str).str.strip().str.lower()
                        norm = normalized_label.lower()
                        # Compute cumulative FYTD goal from monthly rows; also fetch the monthly (MTD) row
                        try:
                            goal_fytd = compute_cumulative_goal(metas_pped_df, 'Partner', norm, current_report_date, 'ANSR Goal PPED', mes_col='Mes', match_contains=True)
                            # monthly (MTD) goal
                            target_label = get_fiscal_month_year(current_report_date) if current_report_date else None
                            if target_label is not None:
                                mrows = metas_pped_df[metas_pped_df['Partner'].astype(str).str.strip().str.lower().str.contains(norm, na=False) & (metas_pped_df['Mes'] == target_label)]
                                if not mrows.empty and 'ANSR Goal PPED' in mrows.columns:
                                    goal_mtd = float(mrows['ANSR Goal PPED'].sum())
                            # fallback to yearly Total for FYTD if cumulative not found
                            if not goal_fytd:
                                yearly_rows = metas_pped_df[(metas_pped_df['Partner'].str.contains(norm, case=False, na=False)) & (metas_pped_df['Mes'] == 'Total')]
                                if not yearly_rows.empty:
                                    goal_fytd = float(yearly_rows['ANSR Goal PPED'].sum())
                        except Exception:
                            goal_mtd = None
                            goal_fytd = None

                # Managers: metas_MANAGERS.csv
                elif group_field == 'engagement_manager':
                    metas_managers_path = os.path.join(settings.BASE_DIR, 'metas_MANAGERS.csv')
                    if os.path.exists(metas_managers_path):
                        metas_managers_df = pd.read_csv(metas_managers_path)
                        metas_managers_df['Manager'] = metas_managers_df['Manager'].astype(str).str.strip().str.lower()
                        norm = normalized_label.lower()
                        # Compute cumulative FYTD goal for manager from monthly metas; also fetch monthly MTD goal
                        try:
                            goal_fytd = compute_cumulative_goal(metas_managers_df, 'Manager', norm, current_report_date, 'ANSR Goal', mes_col='Mes', match_contains=True)
                            target_label = get_fiscal_month_year(current_report_date) if current_report_date else None
                            if target_label is not None:
                                mrows = metas_managers_df[metas_managers_df['Manager'].astype(str).str.strip().str.lower().str.contains(norm, na=False) & (metas_managers_df['Mes'] == target_label)]
                                if not mrows.empty and 'ANSR Goal' in mrows.columns:
                                    goal_mtd = float(mrows['ANSR Goal'].sum())
                            if not goal_fytd:
                                yearly_rows = metas_managers_df[(metas_managers_df['Manager'].str.contains(norm, case=False, na=False)) & (metas_managers_df['Mes'] == 'Total')]
                                if not yearly_rows.empty:
                                    goal_fytd = float(yearly_rows['ANSR Goal'].sum())
                        except Exception:
                            goal_mtd = None
                            goal_fytd = None

                # Service Lines: metas_SL.csv
                elif group_field == 'area__name' or group_field == 'engagement_service_line':
                    metas_sl_path = os.path.join(settings.BASE_DIR, 'metas_SL.csv')
                    if os.path.exists(metas_sl_path):
                        metas_sl_df = pd.read_csv(metas_sl_path)
                        normalized_label_sl = normalized_label
                        # Compute cumulative FYTD goal for the service line using monthly metas; also fetch monthly MTD goal
                        try:
                            goal_fytd = compute_cumulative_goal(metas_sl_df, 'SL', normalized_label_sl, current_report_date, 'ANSR Goal', mes_col='Mes', match_contains=False, label_eq=True)
                            target_label = get_fiscal_month_year(current_report_date) if current_report_date else None
                            if target_label is not None:
                                mrows = metas_sl_df[(metas_sl_df['SL'].astype(str).str.strip() == normalized_label_sl) & (metas_sl_df['Mes'] == target_label)]
                                if not mrows.empty and 'ANSR Goal' in mrows.columns:
                                    goal_mtd = float(mrows['ANSR Goal'].sum())
                            if not goal_fytd:
                                row = metas_sl_df[(metas_sl_df['SL'].str.strip() == normalized_label_sl) & (metas_sl_df['Mes'] == 'Total')]
                                if not row.empty:
                                    goal_fytd = float(row['ANSR Goal'].sum())
                        except Exception:
                            goal_mtd = None
                            goal_fytd = None

                # Sub service lines: attempt metas_SL as fallback (no dedicated metas file)
                elif group_field == 'sub_area__name' or group_field == 'engagement_sub_service_line':
                    # Try to use metas_SL as a fallback (match by SL name); if not found leave goal as None
                    metas_sl_path = os.path.join(settings.BASE_DIR, 'metas_SL.csv')
                    if os.path.exists(metas_sl_path):
                        metas_sl_df = pd.read_csv(metas_sl_path)
                        normalized_label_sl = normalized_label
                        try:
                            goal_fytd = compute_cumulative_goal(metas_sl_df, 'SL', normalized_label_sl, current_report_date, 'ANSR Goal', mes_col='Mes', match_contains=False, label_eq=True)
                            target_label = get_fiscal_month_year(current_report_date) if current_report_date else None
                            if target_label is not None:
                                mrows = metas_sl_df[(metas_sl_df['SL'].astype(str).str.strip() == normalized_label_sl) & (metas_sl_df['Mes'] == target_label)]
                                if not mrows.empty and 'ANSR Goal' in mrows.columns:
                                    goal_mtd = float(mrows['ANSR Goal'].sum())
                            if not goal_fytd:
                                goal_fytd = None
                        except Exception:
                            goal_mtd = None
                            goal_fytd = None
                    else:
                        goal = None
            except Exception:
                goal = None

            # Normalize goals and compute completion percentage for ANSR using the cumulative FYTD goal
            try:
                # Displayed goal should remain the monthly MTD goal if available
                if goal_mtd is not None:
                    goal = float(goal_mtd)
                else:
                    # fallback: if no monthly goal, keep goal as None (don't override with FYTD)
                    goal = None

                # Compute completion percentage using the FYTD cumulative goal when available
                if goal_fytd is not None and float(goal_fytd) > 0:
                    goal_completion_percentage = (ansr_value / float(goal_fytd)) * 100
                else:
                    goal_completion_percentage = None
            except Exception:
                goal = None
                goal_completion_percentage = None

            # Color classification function
            def classify_color(pct):
                try:
                    p = float(pct)
                except Exception:
                    return 'grey'
                if p < 50:
                    return 'red'
                if p < 95:
                    return 'yellow'
                return 'green'

            goal_color = classify_color(goal_completion_percentage) if goal_completion_percentage is not None else 'grey'

            # Average comparison
            comparison_pct = None
            comparison_color = 'grey'
            try:
                if avg_ansr and avg_ansr > 0:
                    comparison_pct = (ansr_value / avg_ansr) * 100
                    comparison_color = classify_color(comparison_pct)
            except Exception:
                comparison_pct = None

            results.append({
                'label': label,
                'ansr_fytd': ansr_value,
                'hours_fytd': hours_value,
                'rph': rph,
                'goal': goal,
                'goal_completion_percentage': goal_completion_percentage,
                'goal_color': goal_color,
                'avg_ansr': avg_ansr,
                'comparison_pct': comparison_pct,
                'comparison_color': comparison_color,
            })

        return results

    # Build partners ranking grouped by engagement_partner
    partners_ranking = build_ranking('engagement_partner')

    # Managers ranking grouped by engagement_manager
    managers_ranking = build_ranking('engagement_manager')

    # Service Lines grouped by area__name (or engagement_service_line)
    # Some rows use 'area__name' and some legacy entries use 'engagement_service_line'
    service_lines_ranking = build_ranking('area__name')

    # Sub Service Lines grouped by sub_area__name (or engagement_sub_service_line)
    sub_service_lines_ranking = build_ranking('sub_area__name')

    # Add these to context so template tables can render them
    context['partners_ranking'] = partners_ranking
    context['managers_ranking'] = managers_ranking
    context['service_lines_ranking'] = service_lines_ranking
    context['sub_service_lines_ranking'] = sub_service_lines_ranking

    # Temporary debug: print top rows for partners and managers when in DEBUG mode
    try:
        if getattr(settings, 'DEBUG', False):
            print('\n=== DEBUG: Top partners_ranking (label, ansr_fytd, goal (MTD), goal_fytd, pct) ===')
            for p in (partners_ranking or [])[:8]:
                print(f"Partner: {p.get('label')} | ANSR_FYTD: {p.get('ansr_fytd')} | goal(MTD): {p.get('goal')} | goal_FYTD: {p.get('goal_fytd') if 'goal_fytd' in p else 'N/A'} | pct: {p.get('goal_completion_percentage')}")
            print('\n=== DEBUG: Top managers_ranking (label, ansr_fytd, goal (MTD), goal_fytd, pct) ===')
            for m in (managers_ranking or [])[:8]:
                print(f"Manager: {m.get('label')} | ANSR_FYTD: {m.get('ansr_fytd')} | goal(MTD): {m.get('goal')} | goal_FYTD: {m.get('goal_fytd') if 'goal_fytd' in m else 'N/A'} | pct: {m.get('goal_completion_percentage')}")
    except Exception:
        pass

    # Revenue Trend by Date (calculating daily revenue in Python)
    import pandas as pd

    all_entries = list(all_revenue_entries.order_by('engagement_id', 'date').values('engagement_id', 'date', 'revenue'))

    daily_revenues = []
    prev_engagement_id = None
    prev_revenue = 0

    for entry in all_entries:
        current_engagement_id = entry['engagement_id']
        current_revenue = entry['revenue'] or 0

        if current_engagement_id != prev_engagement_id:
            # New engagement, so the daily revenue is the current revenue
            daily_revenue = current_revenue
        else:
            # Same engagement, calculate the difference
            daily_revenue = current_revenue - prev_revenue

        daily_revenues.append({
            'date': entry['date'],
            'daily_revenue': daily_revenue
        })

        prev_engagement_id = current_engagement_id
        prev_revenue = current_revenue

    # Sum up daily revenues by date
    df = pd.DataFrame(daily_revenues)
    if not df.empty:
        # Ensure 'daily_revenue' is numeric before summing
        df['daily_revenue'] = pd.to_numeric(df['daily_revenue'], errors='coerce').fillna(0)
        daily_totals = df.groupby('date')['daily_revenue'].sum().reset_index()
        # Ensure the 'date' column is in datetime format before using .dt accessor
        daily_totals['date'] = pd.to_datetime(daily_totals['date'])
        trend_labels = daily_totals['date'].dt.strftime('%Y-%m-%d').tolist()
        trend_data = [float(x) for x in daily_totals['daily_revenue']]
    else:
        trend_labels = []
        trend_data = []

    # Recent Revenue Entries (uses all_revenue_entries, but limited to 10)
    recent_entries = all_revenue_entries.select_related('client', 'area').order_by('-date')[:10] # Get last 10 entries
    # Format revenue for recent_entries
    for entry in recent_entries:
        entry.revenue_formatted = "${:,.2f}".format(entry.revenue or 0)

    # Get distinct values for filters, excluding None and empty strings
    partners = RevenueEntry.objects.values_list('engagement_partner', flat=True).distinct().exclude(engagement_partner__isnull=True).exclude(Q(engagement_partner__exact='')).order_by('engagement_partner')
    db_managers = RevenueEntry.objects.values_list('engagement_manager', flat=True).distinct().exclude(engagement_manager__isnull=True).exclude(Q(engagement_manager__exact='')).order_by('engagement_manager')
    
    # Get managers from Manager Revenue Days file
    try:
        manager_analytics = ManagerAnalyticsService()
        revenue_days_managers = manager_analytics.get_available_managers()
    except Exception as e:
        print(f"DEBUG: Error getting Revenue Days managers: {str(e)}")
        revenue_days_managers = []
    
    # Combine both manager sources and remove duplicates
    all_managers = list(set(list(db_managers) + revenue_days_managers))
    managers = sorted([m for m in all_managers if m])  # Remove any None/empty values and sort
    
    areas = Area.objects.values_list('name', flat=True).distinct().exclude(name__isnull=True).exclude(Q(name__exact='')).order_by('name')
    sub_areas = SubArea.objects.values_list('name', flat=True).distinct().exclude(name__isnull=True).exclude(Q(name__exact='')).order_by('name')
    clients = Client.objects.values_list('name', flat=True).distinct().exclude(name__isnull=True).exclude(Q(name__exact='')).order_by('name')

    # Placeholder for highlights/news ticker
    highlights = [
        "EY Global: Janet Truncale elected Global Chair and CEO, effective July 1, 2024.",
        "EY US acquired IT consulting firm Nuvalence, expanding its tech capabilities.",
        "EY Venezuela: Achieved record revenue in Q2 2025, driven by new client acquisitions.",
        "EY Global: New solutions for risk management launched on EY.ai Agentic Platform.",
        "EY Venezuela: Successfully completed major audit for a leading financial institution.",
        "EY Global: EY and ACCA issue new guidance urging stronger AI checks.",
    ]

    # --- Macro Section Calculations ---
    macro_total_clients = revenue_entries_for_kpis.values('client').distinct().count()
    # Use the synthetic ANSR field for the Macro ANSR YTD metric
    macro_total_ansr_sintetico = revenue_entries_for_kpis.aggregate(Sum('fytd_ansr_sintetico'))['fytd_ansr_sintetico__sum'] or 0
    macro_total_direct_cost = revenue_entries_for_kpis.aggregate(Sum('fytd_direct_cost_amt'))['fytd_direct_cost_amt__sum'] or 0
    macro_margin = macro_total_ansr_sintetico - macro_total_direct_cost
    macro_margin_percentage = (macro_margin / macro_total_ansr_sintetico * 100) if macro_total_ansr_sintetico else 0
    macro_total_charged_hours = revenue_entries_for_kpis.aggregate(Sum('fytd_charged_hours'))['fytd_charged_hours__sum'] or 0
    macro_rph = (macro_total_ansr_sintetico / macro_total_charged_hours) if macro_total_charged_hours else 0
    macro_mtd_charged_hours = revenue_entries_for_kpis.aggregate(Sum('mtd_charged_hours'))['mtd_charged_hours__sum'] or 0
    macro_monthly_tracker = macro_mtd_charged_hours * macro_rph


    # --- Nuevas métricas y datos para gráficos ---

    # 1. Distribución de clientes por partner
    clients_by_partner = revenue_entries_for_kpis.values('engagement_partner').annotate(
        num_clients=Count('client', distinct=True)
    ).order_by('-num_clients').exclude(engagement_partner__isnull=True).exclude(engagement_partner__exact='')

    partner_distribution_labels = [item['engagement_partner'] for item in clients_by_partner]
    partner_distribution_data = [item['num_clients'] for item in clients_by_partner]

    # 2. Cartera en moneda extranjera (usando fytd_diferencial_final)
    cartera_moneda_extranjera = "${:,.2f}".format(revenue_entries_for_kpis.aggregate(Sum('fytd_diferencial_final'))['fytd_diferencial_final__sum'] or 0)

    # 3. Cartera local ajustada (usando fytd_ansr_sintetico)
    cartera_local_ajustada = "${:,.2f}".format(revenue_entries_for_kpis.aggregate(Sum('fytd_ansr_sintetico'))['fytd_ansr_sintetico__sum'] or 0)

    # 4. Total CXC (asumiendo que es la suma de billing - collections, o solo billing si no hay un campo de CXC explícito)
    # Si tienes un campo de CXC directo, por favor, indícalo.
    total_cxc = "${:,.2f}".format(revenue_entries_for_kpis.aggregate(Sum('billing'))['billing__sum'] or 0) # Usando billing como proxy

    # 5. Promedio de antigüedad (requiere un campo de fecha de inicio de contrato/cliente y fecha actual)
    # Por ahora, es un placeholder. Necesito más información sobre cómo calcularlo.
    promedio_antiguedad = "N/A" # Placeholder

    # 6. Unbilled Inventory por Service Line
    # Asumiendo que Unbilled Inventory = FYTD_ANSRAmt - Collections
    unbilled_inventory_by_service_line = revenue_entries_for_kpis.values('engagement_service_line').annotate(
    unbilled_amount=Sum(ExpressionWrapper(F('fytd_ansr_sintetico') - F('collections'), output_field=FloatField()))
    ).order_by('-unbilled_amount').exclude(engagement_service_line__isnull=True).exclude(engagement_service_line__exact='')

    # Normalize labels by stripping whitespace to avoid display mismatches
    unbilled_labels = [item['engagement_service_line'].strip() if isinstance(item['engagement_service_line'], str) else item['engagement_service_line'] for item in unbilled_inventory_by_service_line]
    unbilled_data = [float(item['unbilled_amount'] or 0) for item in unbilled_inventory_by_service_line]

    # 7. Anticipos (requiere un campo específico para anticipos)
    # Por ahora, es un placeholder. Necesito más información sobre cómo calcularlo.
    total_anticipos = "N/A" # Placeholder

    # --- Partner Specification Section ---
    partner_spec_data = None
    # Initialize variables to avoid UnboundLocalError
    partner_fytd_charged_hours = 0
    partner_mtd_charged_hours = 0
    partner_fytd_hours_goal = 0
    partner_mtd_hours_goal = 0
    partner_fytd_hours_completion_percentage = 0
    partner_mtd_hours_completion_percentage = 0

    if selected_partner:
        print(f"DEBUG: Entering partner_spec_data block for partner: {selected_partner}")
        partner_revenue_entries = revenue_entries_for_kpis
        print(f"DEBUG: partner_revenue_entries count: {partner_revenue_entries.count()}")
        print(f"DEBUG: partner_revenue_entries first entry: {partner_revenue_entries.first()}")

        partner_spec_num_engagements = partner_revenue_entries.values('contract').distinct().count()
        partner_spec_num_clients = partner_revenue_entries.values('client').distinct().count()

        # Get client list with their revenue for the selected partner
        client_list_with_revenue = partner_revenue_entries.values('client__name').annotate(
            total_revenue=Sum('fytd_ansr_sintetico')
        ).order_by('-total_revenue')

        # Format revenue for the client list
        formatted_client_list = [
            {
                'name': item['client__name'],
                'revenue': "${:,.2f}".format(item['total_revenue'] or 0)
            }
            for item in client_list_with_revenue
        ]

        first_entry = partner_revenue_entries.first()
        revenue_days_val = first_entry.total_revenue_days_p_cp if first_entry else 0

        # Partner-specific ANSR FYTD and MTD
        # Partner-level ANSR YTD should also use the synthetic ANSR field
        partner_fytd_ansr_value = partner_revenue_entries.aggregate(Sum('fytd_ansr_sintetico'))['fytd_ansr_sintetico__sum'] or 0
        partner_mtd_ansr_value = partner_revenue_entries.aggregate(Sum('mtd_ansr_amt'))['mtd_ansr_amt__sum'] or 0

        # Goals for partner-specific ANSR
        partner_fytd_ansr_goal = 0
        partner_mtd_ansr_goal = 0
        partner_fytd_ansr_completion_percentage = 0
        partner_mtd_ansr_completion_percentage = 0

        try:
            metas_pped_path = os.path.join(settings.BASE_DIR, 'metas_PPED.csv')
            if os.path.exists(metas_pped_path):
                metas_pped_df = pd.read_csv(metas_pped_path)
                # Normalize partner names in DataFrame
                metas_pped_df['Partner'] = metas_pped_df['Partner'].str.strip().str.lower()

                # Normalize selected_partner for comparison
                normalized_selected_partner = selected_partner.strip().lower() if selected_partner else ''

                # Debug: Print available partners in CSV
                print(f"DEBUG: Available partners in CSV: {metas_pped_df['Partner'].unique()}")
                print(f"DEBUG: Looking for partner: {normalized_selected_partner}")

                # Compute cumulative FYTD goal for the selected partner by summing monthly goals from fiscal year start
                current_report_date = None
                if selected_week_filter:
                    current_report_date = datetime.datetime.strptime(selected_week_filter, '%Y-%m-%d').date()
                elif available_weeks:
                    current_report_date = datetime.datetime.strptime(available_weeks[-1], '%Y-%m-%d').date()

                # Use compute_cumulative_goal to sum monthly ANSR goals for the partner; fallback to 'Total' yearly if not found
                try:
                    partner_fytd_ansr_goal = compute_cumulative_goal(metas_pped_df, 'Partner', normalized_selected_partner, current_report_date, 'ANSR Goal PPED', mes_col='Mes', match_contains=True)
                    partner_fytd_hours_goal = compute_cumulative_goal(metas_pped_df, 'Partner', normalized_selected_partner, current_report_date, 'Horas Goal PPED', mes_col='Mes', match_contains=True)
                    # If cumulative returned 0, fallback to any 'Total' yearly row
                    if partner_fytd_ansr_goal == 0:
                        partner_yearly_goal_rows = metas_pped_df[
                            (metas_pped_df['Partner'].str.contains(normalized_selected_partner, case=False, na=False)) & (metas_pped_df['Mes'] == 'Total')
                        ]
                        if not partner_yearly_goal_rows.empty:
                            partner_fytd_ansr_goal = float(partner_yearly_goal_rows['ANSR Goal PPED'].sum())
                            partner_fytd_hours_goal = float(partner_yearly_goal_rows['Horas Goal PPED'].sum())
                    print(f"DEBUG: Computed cumulative FYTD goal for {normalized_selected_partner}: {partner_fytd_ansr_goal}")
                except Exception as e:
                    print(f"DEBUG: Error computing cumulative partner goals: {e}")

                # Get monthly goal for the selected partner based on fiscal month (kept for MTD display)
                if current_report_date:
                    fiscal_month_name_for_goal = get_fiscal_month_year(current_report_date)
                    partner_monthly_goal_rows = metas_pped_df[
                        (metas_pped_df['Partner'].str.contains(normalized_selected_partner, case=False, na=False)) & (metas_pped_df['Mes'] == fiscal_month_name_for_goal)
                    ]
                    if not partner_monthly_goal_rows.empty:
                        partner_mtd_ansr_goal = float(partner_monthly_goal_rows['ANSR Goal PPED'].sum())
                        partner_mtd_hours_goal = float(partner_monthly_goal_rows['Horas Goal PPED'].sum())
                        print(f"DEBUG: Found MTD goal for {normalized_selected_partner} in {fiscal_month_name_for_goal}: {partner_mtd_ansr_goal}")
                    else:
                        partner_mtd_hours_goal = 0
                        print(f"DEBUG: No MTD goal found for {normalized_selected_partner} in {fiscal_month_name_for_goal}")

            # Calculate completion percentages for partner
            if partner_fytd_ansr_goal > 0:
                partner_fytd_ansr_completion_percentage = (partner_fytd_ansr_value / partner_fytd_ansr_goal) * 100
            if partner_mtd_ansr_goal > 0:
                partner_mtd_ansr_completion_percentage = (partner_mtd_ansr_value / partner_mtd_ansr_goal) * 100

            # Calculate charged hours completion percentages
            # Get partner's actual charged hours
            partner_fytd_charged_hours = partner_revenue_entries.aggregate(Sum('fytd_charged_hours'))['fytd_charged_hours__sum'] or 0
            partner_mtd_charged_hours = partner_revenue_entries.aggregate(Sum('mtd_charged_hours'))['mtd_charged_hours__sum'] or 0

            if partner_fytd_hours_goal > 0:
                partner_fytd_hours_completion_percentage = (partner_fytd_charged_hours / partner_fytd_hours_goal) * 100
            if partner_mtd_hours_goal > 0:
                partner_mtd_hours_completion_percentage = (partner_mtd_charged_hours / partner_mtd_hours_goal) * 100

        except Exception as e:
            print(f"Error processing partner goals: {e}")
            traceback.print_exc()

        partner_spec_data = {
            'num_engagements': partner_spec_num_engagements,
            'num_clients': partner_spec_num_clients,
            'client_list': formatted_client_list, # Use the new formatted list
            'revenue_days': f"{revenue_days_val:,.2f}",
            'partner_fytd_ansr_value': partner_fytd_ansr_value,
            'partner_fytd_ansr_goal': partner_fytd_ansr_goal,
            'partner_fytd_ansr_completion_percentage': partner_fytd_ansr_completion_percentage,
            'partner_mtd_ansr_value': partner_mtd_ansr_value,
            'partner_mtd_ansr_goal': partner_mtd_ansr_goal,
            'partner_mtd_ansr_completion_percentage': partner_mtd_ansr_completion_percentage,
            'partner_fytd_charged_hours': partner_fytd_charged_hours,
            'partner_fytd_hours_goal': partner_fytd_hours_goal,
            'partner_fytd_hours_completion_percentage': partner_fytd_hours_completion_percentage,
            'partner_mtd_charged_hours': partner_mtd_charged_hours,
            'partner_mtd_hours_goal': partner_mtd_hours_goal,
            'partner_mtd_hours_completion_percentage': partner_mtd_hours_completion_percentage,
        }

        if selected_client:
            client_revenue_entries = partner_revenue_entries.filter(client__name=selected_client)
            current_month_start = timezone.now().date().replace(day=1)
            mtd_ansr_amt = client_revenue_entries.filter(date__gte=current_month_start).aggregate(
                Sum('mtd_ansr_amt')
            )['mtd_ansr_amt__sum'] or 0
            partner_spec_data['mtd_ansr_amt'] = "${:,.2f}".format(mtd_ansr_amt)

        # --- New Perdida Diferencial Calculations for Partner View ---
        # 1. Total Perdida Diferencial for the partner
        partner_perdida_diferencial = partner_revenue_entries.aggregate(
            total_perdida=Sum('fytd_diferencial_final')
        )['total_perdida'] or 0
        # Keep numeric value in context so templates can format consistently
        partner_spec_data['total_perdida_diferencial'] = partner_perdida_diferencial

        # 2. Perdida Diferencial per Client for the partner
        perdida_per_client = partner_revenue_entries.values('client__name').annotate(
            perdida=Sum('fytd_diferencial_final')
        ).order_by('-perdida')
        partner_spec_data['perdida_per_client'] = [
            {'client_name': item['client__name'], 'perdida': item['perdida'] or 0}
            for item in perdida_per_client
        ]

        # 3. Top 5 Engagements by Perdida Diferencial for the partner
        top_engagements_perdida = partner_revenue_entries.values('contract__name').annotate(
            perdida=Sum('fytd_diferencial_final')
        ).order_by('-perdida')[:5]
        partner_spec_data['top_engagements_perdida'] = [
            {'engagement_name': item['contract__name'], 'perdida': item['perdida'] or 0}
            for item in top_engagements_perdida
        ]

    # --- Manager Specification Section ---
    manager_spec_data = None
    if selected_manager:
        print(f"DEBUG: Calculating Manager specification data for manager: {selected_manager}")
        
        # Determine selected date for MTD calculations
        selected_date = None
        if selected_week_filter:
            selected_date = datetime.datetime.strptime(selected_week_filter, '%Y-%m-%d').date()
        elif available_weeks:
            selected_date = datetime.datetime.strptime(available_weeks[-1], '%Y-%m-%d').date()
        
        # Get manager specification data using the new analytics service
        try:
            manager_analytics = ManagerAnalyticsService()
            manager_spec_data = manager_analytics.get_manager_kpis(selected_manager, selected_date)
            
            if manager_spec_data:
                print(f"DEBUG: Manager specification data generated successfully for {selected_manager}")
                print(f"DEBUG: Manager FYTD ANSR: ${manager_spec_data['manager_fytd_ansr_value']:,.2f}")
                print(f"DEBUG: Manager MTD ANSR: ${manager_spec_data['manager_mtd_ansr_value']:,.2f}")
                print(f"DEBUG: Manager Revenue Days: {manager_spec_data['revenue_days']}")
            else:
                print(f"DEBUG: Failed to generate manager specification data for {selected_manager}")
                
        except Exception as e:
            print(f"ERROR: Exception in manager analytics: {str(e)}")
            manager_spec_data = None

        # Add Manager Goals functionality
        if manager_spec_data:
            manager_fytd_ansr_goal = 0
            manager_mtd_ansr_goal = 0
            manager_fytd_hours_goal = 0
            manager_mtd_hours_goal = 0
            manager_fytd_ansr_completion_percentage = 0
            manager_mtd_ansr_completion_percentage = 0
            manager_fytd_hours_completion_percentage = 0
            manager_mtd_hours_completion_percentage = 0

            try:
                metas_managers_path = os.path.join(settings.BASE_DIR, 'metas_MANAGERS.csv')
                if os.path.exists(metas_managers_path):
                    metas_managers_df = pd.read_csv(metas_managers_path)
                    # Normalize manager names in DataFrame
                    metas_managers_df['Manager'] = metas_managers_df['Manager'].str.strip().str.lower()

                    # Normalize selected_manager for comparison
                    normalized_selected_manager = selected_manager.strip().lower() if selected_manager else ''

                    # Debug: Print available managers in CSV
                    print(f"DEBUG: Available managers in CSV: {metas_managers_df['Manager'].unique()}")
                    print(f"DEBUG: Looking for manager: {normalized_selected_manager}")

                    # Compute cumulative FYTD goal for the selected manager by summing monthly goals
                    try:
                        manager_fytd_ansr_goal = compute_cumulative_goal(metas_managers_df, 'Manager', normalized_selected_manager, selected_date, 'ANSR Goal', mes_col='Mes', match_contains=True)
                        manager_fytd_hours_goal = compute_cumulative_goal(metas_managers_df, 'Manager', normalized_selected_manager, selected_date, 'Horas Goal', mes_col='Mes', match_contains=True)
                        # fallback to yearly Total if cumulative returns 0
                        if manager_fytd_ansr_goal == 0:
                            manager_yearly_goal_rows = metas_managers_df[(metas_managers_df['Manager'].str.contains(normalized_selected_manager, case=False, na=False)) & (metas_managers_df['Mes'] == 'Total')]
                            if not manager_yearly_goal_rows.empty:
                                manager_fytd_ansr_goal = float(manager_yearly_goal_rows['ANSR Goal'].sum())
                                manager_fytd_hours_goal = float(manager_yearly_goal_rows['Horas Goal'].sum())
                        print(f"DEBUG: Computed cumulative FYTD manager goal for {normalized_selected_manager}: {manager_fytd_ansr_goal}")
                    except Exception as e:
                        print(f"DEBUG: Error computing cumulative manager goals: {e}")

                    # Get monthly goal for the selected manager based on fiscal month (kept for MTD display)
                    if selected_date:
                        fiscal_month_name_for_goal = get_fiscal_month_year(selected_date)
                        manager_monthly_goal_rows = metas_managers_df[(metas_managers_df['Manager'].str.contains(normalized_selected_manager, case=False, na=False)) & (metas_managers_df['Mes'] == fiscal_month_name_for_goal)]
                        if not manager_monthly_goal_rows.empty:
                            manager_mtd_ansr_goal = float(manager_monthly_goal_rows['ANSR Goal'].sum())
                            manager_mtd_hours_goal = float(manager_monthly_goal_rows['Horas Goal'].sum())
                            print(f"DEBUG: Found MTD goal for {normalized_selected_manager} in {fiscal_month_name_for_goal}: {manager_mtd_ansr_goal}")
                        else:
                            print(f"DEBUG: No MTD goal found for {normalized_selected_manager} in {fiscal_month_name_for_goal}")

                # Calculate completion percentages for manager
                if manager_fytd_ansr_goal > 0:
                    manager_fytd_ansr_completion_percentage = (manager_spec_data['manager_fytd_ansr_value'] / manager_fytd_ansr_goal) * 100
                if manager_mtd_ansr_goal > 0:
                    manager_mtd_ansr_completion_percentage = (manager_spec_data['manager_mtd_ansr_value'] / manager_mtd_ansr_goal) * 100
                if manager_fytd_hours_goal > 0:
                    manager_fytd_hours_completion_percentage = (manager_spec_data['manager_fytd_charged_hours'] / manager_fytd_hours_goal) * 100
                if manager_mtd_hours_goal > 0:
                    manager_mtd_hours_completion_percentage = (manager_spec_data['manager_mtd_charged_hours'] / manager_mtd_hours_goal) * 100

                # Add goals to manager_spec_data
                manager_spec_data.update({
                    'manager_fytd_ansr_goal': manager_fytd_ansr_goal,
                    'manager_mtd_ansr_goal': manager_mtd_ansr_goal,
                    'manager_fytd_hours_goal': manager_fytd_hours_goal,
                    'manager_mtd_hours_goal': manager_mtd_hours_goal,
                    'manager_fytd_ansr_completion_percentage': manager_fytd_ansr_completion_percentage,
                    'manager_mtd_ansr_completion_percentage': manager_mtd_ansr_completion_percentage,
                    'manager_fytd_hours_completion_percentage': manager_fytd_hours_completion_percentage,
                    'manager_mtd_hours_completion_percentage': manager_mtd_hours_completion_percentage,
                })

                print(f"DEBUG: Manager goals added - FYTD ANSR Goal: {manager_fytd_ansr_goal}, MTD ANSR Goal: {manager_mtd_ansr_goal}")
                print(f"DEBUG: Manager goals added - FYTD Hours Goal: {manager_fytd_hours_goal}, MTD Hours Goal: {manager_mtd_hours_goal}")

            except Exception as e:
                print(f"ERROR: Exception loading manager goals: {str(e)}")

    # Fetch historical exchange rates for charting using Excel file
    # Try to fetch new exchange rate emails and update the Excel file before reading
    if fetch_and_update:
        try:
            summary = fetch_and_update(dry_run=False)
            print(f"DEBUG fetch_and_update summary: {summary}")
        except Exception as e:
            print(f"WARNING: fetch_and_update failed: {e}")

    excel_file_path = os.path.join(settings.BASE_DIR, 'dolar excel', 'Historial_TCBinance.xlsx')
    exchange_rate_data = get_exchange_rate_data(excel_file_path)
    
    exchange_dates = exchange_rate_data['dates']
    oficial_rates_history = exchange_rate_data['tasa_oficial']
    paralelo_rates_history = exchange_rate_data['tasa_paralelo']
    differential_history = exchange_rate_data['differential_percentage']
    
    print(f"DEBUG Exchange Rate: Loaded {len(exchange_dates)} records")
    print(f"DEBUG Exchange Rate: Last oficial rate: {exchange_rate_data['last_oficial']}")
    print(f"DEBUG Exchange Rate: Last paralelo rate: {exchange_rate_data['last_paralelo']}")
    print(f"DEBUG Exchange Rate: Last differential: {exchange_rate_data['last_differential']:.2f}%")
    # If a Service Line (selected_area) is provided, compute its four cards and add to context
    sl_cards_context = None
    if selected_area:
        try:
            if ServiceLineCardsService:
                # Pass current week date range so SL cards reflect the same reporting window
                sl_result = ServiceLineCardsService().get_cards_for_sl(selected_area, start_date=start_of_week, end_date=end_of_week)
                # Expecting {'sl_name': str, 'cards': [ { 'key','label','value' } ] }
                sl_cards_context = sl_result.get('cards') if isinstance(sl_result, dict) else sl_result
            else:
                # Fallback: compute directly from ORM using normalized, case-insensitive matching
                normalized_sl = selected_area.strip() if isinstance(selected_area, str) else selected_area
                sl_qs = RevenueEntry.objects.filter(
                    Q(engagement_service_line__iexact=normalized_sl) | Q(area__name__iexact=normalized_sl)
                )
                agg = sl_qs.aggregate(
                    sl_fytd_ansr=Sum('fytd_ansr_sintetico'),
                    sl_fytd_hours=Sum('fytd_charged_hours'),
                    sl_mtd_ansr=Sum('mtd_ansr_amt'),
                    sl_mtd_hours=Sum('mtd_charged_hours')
                )
                sl_cards_context = [
                    {'key': 'ANSR_YTD', 'label': 'ANSR YTD', 'value': agg.get('sl_fytd_ansr') or 0},
                    {'key': 'Horas_YTD', 'label': 'Horas Cargadas YTD', 'value': agg.get('sl_fytd_hours') or 0},
                    {'key': 'ANSR_MTD', 'label': 'ANSR MTD', 'value': agg.get('sl_mtd_ansr') or 0},
                    {'key': 'Horas_MTD', 'label': 'Horas Cargadas MTD', 'value': agg.get('sl_mtd_hours') or 0},
                ]
        except Exception as e:
            print(f"ERROR: ServiceLineCardsService failed: {e}")
            sl_cards_context = None

    # Debug: log the selected service line and the computed SL cards for troubleshooting
    try:
        print(f"DEBUG: SL_DEBUG selected_area='{selected_area}' sl_cards_context={sl_cards_context}")
    except Exception:
        # Failsafe to avoid crashing view if printing complex objects
        print(f"DEBUG: SL_DEBUG selected_area='{selected_area}' sl_cards_context=UNPRINTABLE")

    context = {
        'total_fytd_charged_hours': "{:,.0f}".format(total_fytd_charged_hours),
        'total_mtd_charged_hours': "{:,.0f}".format(total_mtd_charged_hours),
        'fytd_charged_hours_by_partner': fytd_charged_hours_by_partner,
        'mtd_charged_hours_by_partner': mtd_charged_hours_by_partner,
        'fytd_charged_hours_by_manager': fytd_charged_hours_by_manager,
        'mtd_charged_hours_by_manager': mtd_charged_hours_by_manager,
        'fytd_charged_hours_by_partner_with_labels': fytd_charged_hours_by_partner_with_labels,
        'mtd_charged_hours_by_partner_with_labels': mtd_charged_hours_by_partner_with_labels,
        'ansr_sintetico': ansr_sintetico,
        'total_clients': total_clients,
        'total_engagements': total_engagements,
        'fytd_revenue': fytd_revenue,
        'mtd_revenue': mtd_revenue,
        'daily_revenue': daily_revenue,
        'total_collections': total_collections,
        'total_billing': total_billing,
        'active_employees_venezuela': active_employees_venezuela,
        'top_partners': top_partners,
    'top_managers': top_managers,
    'all_managers_ranked': all_managers_ranked,
    'top_clients_rank': top_clients_rank,
    'all_clients_ranked': all_clients_ranked,
    'top_engagements': top_engagements,
    'all_engagements_ranked': all_engagements_ranked,
        'loss_per_differential': loss_per_differential,
        'area_labels': json.dumps(area_labels),
        'area_data': json.dumps(area_data),
        'client_labels': json.dumps(client_labels),
        'client_data': json.dumps(client_data),
        'trend_labels': json.dumps(trend_labels),
        'trend_data': json.dumps(trend_data),
        'recent_entries': recent_entries,

        'partners': partners,
        'managers': managers,
        'areas': areas,
        'sub_areas': sub_areas,
        'clients': clients,
        'available_weeks': available_weeks,

        'selected_partner': selected_partner,
        'selected_manager': selected_manager,
        'selected_area': selected_area,
        'selected_sub_area': selected_sub_area,
        'selected_client': selected_client,
        'selected_week': selected_week_filter, # Pass the selected_week_filter to the template

        'highlights': highlights,
        'top_clients_table': top_clients_table,

        # Nuevas métricas para el contexto
        'partner_distribution_labels': json.dumps(partner_distribution_labels),
        'partner_distribution_data': json.dumps(partner_distribution_data),
        'cartera_moneda_extranjera': cartera_moneda_extranjera,
        'cartera_local_ajustada': cartera_local_ajustada,
        'total_cxc': total_cxc,
        'promedio_antiguedad': promedio_antiguedad,
        'unbilled_labels': json.dumps(unbilled_labels),
        'unbilled_data': json.dumps(unbilled_data),
        'total_anticipos': total_anticipos,

        # Macro Section Data
    'macro_total_clients': "{:,.0f}".format(macro_total_clients),
    'macro_total_ansr_sintetico': macro_total_ansr_sintetico,
    # Keep existing formatted strings for backward compatibility
    'macro_margin': "${:,.2f}".format(macro_margin),
    'macro_margin_percentage': "{:.2f}%".format(macro_margin_percentage),
    # Provide numeric values for templates that need numeric formatting
    'macro_margin_value': macro_margin,
    'macro_margin_percentage_value': macro_margin_percentage,
    'macro_rph_value': macro_rph,
        'macro_rph': "${:,.2f}".format(macro_rph),
        'macro_monthly_tracker': macro_monthly_tracker,
        'total_fytd_charged_hours': "{:,.0f}".format(total_fytd_charged_hours),
        'total_mtd_charged_hours': "{:,.0f}".format(total_mtd_charged_hours),
        'macro_diferencial_final': macro_diferencial_final,
        'macro_diferencial_mtd': macro_diferencial_mtd,
        'macro_collected_total': macro_collected_total,
        'macro_collected_total_formatted': "${:,.2f}".format(macro_collected_total),
        'macro_billed_total': macro_billed_total,
        'macro_billed_total_formatted': "${:,.2f}".format(macro_billed_total),

    # New: default pill values (previous year and promedio) - kept None so template shows placeholders
    'ansr_fytd_prev_year': None,
    'ansr_fytd_promedio': None,
    'hours_fytd_prev_year': None,
    'hours_fytd_promedio': None,
    'rph_prev_year': None,
    'rph_promedio': None,
    'margin_prev_year': None,
    'margin_promedio': None,
    # Collected and Billed pill defaults for Macro Cobranzas/Facturacion cards
    'collected_fytd_prev_year': None,
    'collected_fytd_promedio': None,
    'billed_fytd_prev_year': None,
    'billed_fytd_promedio': None,

    # New: Ranking lists (populated by build_ranking)
    'partners_ranking': partners_ranking,
    'managers_ranking': managers_ranking,
    'service_lines_ranking': service_lines_ranking,
    'sub_service_lines_ranking': sub_service_lines_ranking,

        # MTD-specific metrics exposed to templates
        'macro_mtd_direct_cost': macro_mtd_direct_cost,
        'macro_rph_mtd': macro_rph_mtd,
        'macro_mtd_margin_value': macro_mtd_margin_value,
        'macro_mtd_margin_percentage': macro_mtd_margin_percentage,

        # New context for flip card
        'all_partners_ranked': all_partners_ranked,
        'all_fytd_charged_hours_by_partner': all_fytd_charged_hours_by_partner,

        # New: Accumulated sums for MTD_ChargedHours and FYTD_ChargedHours
        'total_mtd_charged_hours': "{:,.0f}".format(total_mtd_charged_hours),
        'total_fytd_charged_hours': "{:,.0f}".format(total_fytd_charged_hours),

        # New: Accumulated sums for MTD_ChargedHours and FYTD_ChargedHours
        'total_mtd_charged_hours': "{:,.0f}".format(total_mtd_charged_hours),
        'total_fytd_charged_hours': "{:,.0f}".format(total_fytd_charged_hours),

        'partner_spec_data': partner_spec_data,
        'manager_spec_data': manager_spec_data,

        # Exchange Rate History for Chart
        'exchange_dates': json.dumps(exchange_dates),
        'oficial_rates_history': json.dumps(oficial_rates_history),
        'paralelo_rates_history': json.dumps(paralelo_rates_history),
        'differential_history': json.dumps(differential_history),
        'diferencial_final_by_partner': diferencial_final_by_partner,
        
        # Latest Exchange Rate Values for Overview Bar
        'latest_tasa_oficial': exchange_rate_data['last_oficial'],
        'latest_tasa_binance': exchange_rate_data['last_paralelo'],
        'latest_exchange_date': exchange_rate_data.get('last_date', ''),
    }
    # Expose SL cards in context for template conditional rendering
    context['sl_cards'] = sl_cards_context
    # If a Sub Service Line (selected_sub_area) is provided, compute its four cards and add to context
    ssl_cards_context = None
    if selected_sub_area:
        try:
            if SubServiceLineCardsService:
                ssl_result = SubServiceLineCardsService().get_cards_for_ssl(selected_sub_area, start_date=start_of_week, end_date=end_of_week)
                ssl_cards_context = ssl_result.get('cards') if isinstance(ssl_result, dict) else ssl_result
            else:
                normalized_ssl = selected_sub_area.strip() if isinstance(selected_sub_area, str) else selected_sub_area
                ssl_qs = RevenueEntry.objects.filter(engagement_sub_service_line__iexact=normalized_ssl)
                if start_of_week and end_of_week:
                    ssl_qs = ssl_qs.filter(date__range=[start_of_week, end_of_week])
                agg = ssl_qs.aggregate(
                    ssl_fytd_ansr=Sum('fytd_ansr_sintetico'),
                    ssl_fytd_hours=Sum('fytd_charged_hours'),
                    ssl_mtd_ansr=Sum('mtd_ansr_amt'),
                    ssl_mtd_hours=Sum('mtd_charged_hours')
                )
                ssl_cards_context = [
                    {'key': 'ANSR_YTD', 'label': 'ANSR YTD', 'value': agg.get('ssl_fytd_ansr') or 0},
                    {'key': 'Horas_YTD', 'label': 'Horas Cargadas YTD', 'value': agg.get('ssl_fytd_hours') or 0},
                    {'key': 'ANSR_MTD', 'label': 'ANSR MTD', 'value': agg.get('ssl_mtd_ansr') or 0},
                    {'key': 'Horas_MTD', 'label': 'Horas Cargadas MTD', 'value': agg.get('ssl_mtd_hours') or 0},
                ]
        except Exception as e:
            print(f"ERROR: SubServiceLineCardsService failed: {e}")
            ssl_cards_context = None
    context['ssl_cards'] = ssl_cards_context
    # --- Goals Calculation ---
    ansr_fytd_goal = 0
    ansr_mtd_goal = 0
    ansr_fytd_completion_percentage = 0
    ansr_mtd_completion_percentage = 0
    hours_fytd_goal = 0
    hours_mtd_goal = 0
    hours_fytd_completion_percentage = 0
    hours_mtd_completion_percentage = 0

    try:
        metas_sl_path = os.path.join(settings.BASE_DIR, 'metas_SL.csv')
        if os.path.exists(metas_sl_path):
            metas_sl_df = pd.read_csv(metas_sl_path)

            # Determine the current report date
            current_report_date = None
            if selected_week_filter:
                current_report_date = datetime.datetime.strptime(selected_week_filter, '%Y-%m-%d').date()
            elif available_weeks:
                current_report_date = datetime.datetime.strptime(available_weeks[-1], '%Y-%m-%d').date()

            if current_report_date:
                # Get fiscal month and year using the new utility function
                fiscal_month_name_for_goal = get_fiscal_month_year(current_report_date)

                # Get monthly goal (ANSR MTD Goal) based on fiscal month (kept for MTD display)
                monthly_goal_row = metas_sl_df[(metas_sl_df['SL'] == 'Total general') & (metas_sl_df['Mes'] == fiscal_month_name_for_goal)]
                if not monthly_goal_row.empty:
                    ansr_mtd_goal = float(monthly_goal_row['ANSR Goal'].iloc[0])
                    hours_mtd_goal = float(monthly_goal_row['Horas Goal'].iloc[0])
                    print(f"DEBUG: Found MTD goal from metas_SL for {fiscal_month_name_for_goal}: {ansr_mtd_goal}, hours: {hours_mtd_goal}")

                # Compute FYTD goal as cumulative sum of monthly goals from fiscal year start up to report month
                try:
                    ansr_fytd_goal = compute_cumulative_goal(metas_sl_df, 'SL', 'Total general', current_report_date, 'ANSR Goal', mes_col='Mes', match_contains=False, label_eq=True)
                    hours_fytd_goal = compute_cumulative_goal(metas_sl_df, 'SL', 'Total general', current_report_date, 'Horas Goal', mes_col='Mes', match_contains=False, label_eq=True)
                    print(f"DEBUG: Computed cumulative FYTD goal from metas_SL: {ansr_fytd_goal}, hours: {hours_fytd_goal}")
                except Exception as e:
                    print(f"DEBUG: Error computing cumulative SL goals: {e}")

            # Calculate completion percentages
            # ANSR FYTD (formerly ansr_sintetico)
            if ansr_fytd_goal > 0:
                ansr_fytd_completion_percentage = (macro_total_ansr_sintetico / ansr_fytd_goal) * 100
                print(f"DEBUG: ANSR FYTD completion: {ansr_fytd_completion_percentage}%")

            # ANSR MTD (formerly monthly_tracker)
            if ansr_mtd_goal > 0:
                ansr_mtd_completion_percentage = (macro_monthly_tracker / ansr_mtd_goal) * 100
                print(f"DEBUG: ANSR MTD completion: {ansr_mtd_completion_percentage}%")

            # Hours FYTD
            hours_fytd_completion_percentage = 0
            if hours_fytd_goal > 0:
                total_fytd_charged_hours_float = float(str(total_fytd_charged_hours).replace(',', ''))
                hours_fytd_completion_percentage = (total_fytd_charged_hours_float / hours_fytd_goal) * 100
                print(f"DEBUG: Hours FYTD completion: {hours_fytd_completion_percentage}%")

            # Hours MTD
            hours_mtd_completion_percentage = 0
            if hours_mtd_goal > 0:
                total_mtd_charged_hours_float = float(str(total_mtd_charged_hours).replace(',', ''))
                hours_mtd_completion_percentage = (total_mtd_charged_hours_float / hours_mtd_goal) * 100
                print(f"DEBUG: Hours MTD completion: {hours_mtd_completion_percentage}%")
            else:
                hours_mtd_completion_percentage = 0

    except Exception as e:
        print(f"Error processing goals: {e}")
        traceback.print_exc() # Print full traceback for debugging

    context['ansr_fytd_value'] = macro_total_ansr_sintetico
    context['ansr_fytd_goal'] = ansr_fytd_goal
    context['ansr_fytd_completion_percentage'] = ansr_fytd_completion_percentage
    context['ansr_mtd_value'] = macro_monthly_tracker
    context['ansr_mtd_goal'] = ansr_mtd_goal
    context['ansr_mtd_completion_percentage'] = ansr_mtd_completion_percentage

    # Add hours goals to context
    context['hours_fytd_goal'] = hours_fytd_goal
    context['hours_mtd_goal'] = hours_mtd_goal
    context['hours_fytd_completion_percentage'] = hours_fytd_completion_percentage
    context['hours_mtd_completion_percentage'] = hours_mtd_completion_percentage
    
    print(f"DEBUG: Final context keys: {context.keys()}")
    if 'partner_spec_data' in context and context['partner_spec_data']:
        print(f"DEBUG: partner_spec_data is present in context.")
        for key, value in context['partner_spec_data'].items():
            print(f"DEBUG:   partner_spec_data['{key}']: {value}")
    else:
        print(f"DEBUG: partner_spec_data is NOT present or is empty in context.")

    # Compute latest available report date from historico_de_final_database so the dashboard can link to previews
    try:
        # --- NEW: prepare style-safe percentage values for progress bars ---
        def clamp_percent(value):
            try:
                v = float(value)
            except Exception:
                return 0
            if v < 0:
                return 0
            if v > 100:
                return 100
            return int(round(v))

        # map known completion keys to style-safe keys
        percent_keys = [
            'ansr_fytd_completion_percentage', 'ansr_mtd_completion_percentage',
            'hours_fytd_completion_percentage', 'hours_mtd_completion_percentage'
        ]
        for k in percent_keys:
            if k in context:
                context[f"{k}_style"] = clamp_percent(context.get(k, 0))
            else:
                context[f"{k}_style"] = 0
        # Also include manager and partner specific percentages if present
        if 'partner_spec_data' in context and context['partner_spec_data']:
            for pk in ['partner_fytd_ansr_completion_percentage','partner_mtd_ansr_completion_percentage','partner_fytd_hours_completion_percentage','partner_mtd_hours_completion_percentage']:
                context[f"{pk}_style"] = clamp_percent(context['partner_spec_data'].get(pk, 0))
        if 'manager_spec_data' in context and context['manager_spec_data']:
            for mk in ['manager_fytd_ansr_completion_percentage','manager_mtd_ansr_completion_percentage','manager_fytd_hours_completion_percentage','manager_mtd_hours_completion_percentage']:
                context[f"{mk}_style"] = clamp_percent(context['manager_spec_data'].get(mk, 0))
        # --- END NEW ---
        DATA_DIR = os.path.join(settings.MEDIA_ROOT, 'historico_de_final_database')
        latest_report_date = None
        if os.path.exists(DATA_DIR):
            weekly_dirs = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
            if weekly_dirs:
                latest_report_date = sorted(weekly_dirs, reverse=True)[0]
        context['latest_report_date'] = latest_report_date
        print(f"DEBUG: latest_report_date set to: {latest_report_date}")
    except Exception as e:
        print(f"Error computing latest_report_date: {e}")
        context['latest_report_date'] = None

    return render(request, 'core_dashboard/dashboard.html', context)


def data_downloads_view(request):
    DATA_DIR = os.path.join(settings.MEDIA_ROOT, 'historico_de_final_database')
    
    final_databases = []
    report_dates = []
    if os.path.exists(DATA_DIR):
        weekly_dirs = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
        report_dates = sorted(weekly_dirs, reverse=True)
        for d in weekly_dirs:
            dir_path = os.path.join(DATA_DIR, d)
            files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f)) and 'Final_Database' in f and f.endswith('.csv')]
            for f in files:
                final_databases.append({'date': d, 'filename': f, 'path': f'{d}/{f}'})

    # Handle file download
    download_path = request.GET.get('download')
    download_format = request.GET.get('format', 'csv')
    if download_path:
        file_path = os.path.join(DATA_DIR, download_path)
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            if download_format == 'excel':
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                output.seek(0)
                response = HttpResponse(output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                response['Content-Disposition'] = f'attachment; filename={os.path.splitext(os.path.basename(file_path))[0]}.xlsx'
                return response
            else: # CSV
                from django.http import HttpResponse
                response = HttpResponse(df.to_csv(index=False), content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename={os.path.basename(file_path)}'
                return response

    # Handle file preview
    selected_date = request.GET.get('report_date')
    df_html = None
    preview_path = None
    if selected_date:
        # Find the final database for the selected date
        for db in final_databases:
            if db['date'] == selected_date:
                preview_path = db['path']
                file_path = os.path.join(DATA_DIR, preview_path)
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    df_html = df.to_html(classes='table table-dark table-striped table-hover', index=False)
                break

    context = {
        'final_databases': sorted(final_databases, key=lambda x: x['date'], reverse=True),
        'report_dates': report_dates,
        'df_html': df_html,
        'selected_date': selected_date,
        'preview_path': preview_path,
    }
    return render(request, 'core_dashboard/data_downloads.html', context)


def help_view(request):
    return render(request, 'core_dashboard/help.html')


def settings_view(request):
    return render(request, 'core_dashboard/settings.html')
''