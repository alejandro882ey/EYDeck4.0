import os
p=os.path.join('media','cobranzas','cobranzas_combined_cache.pkl')
if os.path.exists(p):
    os.remove(p)
    print('deleted')
else:
    print('no file')
