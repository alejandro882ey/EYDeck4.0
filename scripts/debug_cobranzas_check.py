import os,sys
sys.path.append(r'c:\Users\CK624GF\OneDrive - EY\Documents\2025\dashboard_django')
os.environ['DJANGO_SETTINGS_MODULE']='dashboard_django.settings'
from core_dashboard.modules.cobranzas.services import CobranzasService
s=CobranzasService()
media = s.media_folder
print('media folder:', media)
files = [f for f in os.listdir(media) if f.lower().endswith(('.xlsx','.xls'))]
files = sorted(files)
print('files:', files)
for fn in files:
    p = os.path.join(media, fn)
    try:
        tot = s.get_totals_from_file(p)
    except Exception as e:
        tot = ('err',str(e))
    print(fn, '-> totals:', tot)

# Show per-date sums from combined df
df = s.get_all_processed_df()
if not df.empty:
    for date in ['2025-07-11','2025-07-18']:
        sel = df[df['fecha_day']==date]
        print('date', date, 'rows', len(sel), 'sum _usd_total_row=', float(sel['_usd_total_row'].sum()) if '_usd_total_row' in sel.columns else 'no col')
    # show unique files and dates
    print('\nUnique dates in df sample around July 2025:')
    print(sorted(set([d for d in df['fecha_day'] if d.startswith('2025-07')])))
