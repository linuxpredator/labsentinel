# wsgi.py - PythonAnywhere WSGI entry point
# Salin kandungan ini ke /var/www/USERNAME_pythonanywhere_com_wsgi.py
# atau rujuk file ini dari PythonAnywhere web app settings.
#
# PENTING: Tukar USERNAME kepada username PythonAnywhere anda.

import sys
import os

# Path ke direktori projek di PythonAnywhere
project_path = '/home/linuxpredator/labsentinel'
sys.path.insert(0, project_path)
os.chdir(project_path)

from server import app as application
