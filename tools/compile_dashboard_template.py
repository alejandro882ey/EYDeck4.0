import os
import sys
from django.conf import settings

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, 'core_dashboard', 'templates', 'core_dashboard', 'dashboard.html')

if not settings.configured:
    settings.configure(DEBUG=True, TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'core_dashboard', 'templates')],
        'APP_DIRS': True,
    }])

from django.template import Engine

def compile_template(path):
    print('Compiling template:', path)
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    # Use a standalone Engine to avoid full Django app loading
    engine = Engine(dirs=[os.path.join(os.path.dirname(BASE_DIR), 'core_dashboard', 'templates')], debug=True)
    try:
        engine.from_string(src)
        print('Template compiled successfully')
    except Exception:
        print('Template compile error:')
        raise

if __name__ == '__main__':
    compile_template(TEMPLATE_PATH)
