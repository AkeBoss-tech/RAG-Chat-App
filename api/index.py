import sys
sys.path.append("..")
from flask_api import app

# Vercel requires a handler
def handler(request):
    return app(request) 