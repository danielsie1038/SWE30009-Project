# AI Gateway Dashboard

PHP web app for estimating LLM usage costs, tested with Selenium.

![Test (Ubuntu)](https://github.com/<YOUR-USERNAME>/<YOUR-REPO>/actions/workflows/test-ubuntu.yml/badge.svg)
![Test (Windows)](https://github.com/<YOUR-USERNAME>/<YOUR-REPO>/actions/workflows/test-windows.yml/badge.svg)

## Run locally
```
php -S localhost:8000
pip install -r requirements.txt
APP_URL=http://localhost:8000/index.php python test_script.py
```
(On Windows PowerShell: `$env:APP_URL="http://localhost:8000/index.php"; python test_script.py`)
