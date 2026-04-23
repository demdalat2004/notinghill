cd backend

# Craeete venv
python3 -m venv venv

# Active venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
uvicorn main:app --host 127.0.0.1 --port 7878 --reload
