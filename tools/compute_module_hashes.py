import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from core_dashboard.modules.shared.cache_utils import gather_module_files, compute_files_hash

for m in ('cobranzas', 'facturacion'):
    module_dir = os.path.join(ROOT, 'core_dashboard', 'modules', m)
    files = gather_module_files(module_dir)
    print(f"Module: {m}")
    print('  files: ', files)
    print('  hash:  ', compute_files_hash(files))
