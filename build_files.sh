#!/bin/bash
echo "Building Django Irrigation API V2..."
pip install -r requirements.txt
python manage.py collectstatic --noinput --clear
echo "Build complete."