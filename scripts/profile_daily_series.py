from core_dashboard.modules.cobranzas.services import CobranzasService
import time
s=CobranzasService()
start=time.time()
res1=s.get_daily_collections_and_rates()
mid=time.time()
res2=s.get_daily_collections_and_rates()
end=time.time()
print('First call secs:', mid-start)
print('Second call secs:', end-mid)
print('Dates length:', len(res1['dates']))
