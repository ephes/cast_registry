postgres: postgres -D databases/postgres
web: PYTHONUNBUFFERED=true .venv/bin/python manage.py runserver 0.0.0.0:8000 --settings=config.settings.development
# notebook: DJANGO_ALLOW_ASYNC_UNSAFE=true DJANGO_SETTINGS_MODULE=config.settings.development python manage.py shell_plus --notebook
# deploy: cd ../fastdeploy && API_URL=http://localhost:8001 /Users/jochen/.virtualenvs/fd/bin/uvicorn app.main:app --reload --port 8001
# vite: cd ../fastdeploy/frontend && VITE_API_BASE_DEV=http://localhost:8001 VITE_WEBSOCKET_URL_DEV=ws://localhost:8001/deployments/ws npm run dev
