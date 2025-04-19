from flask import Flask, request, jsonify
from flask import abort
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timezone
import os
import json
from dotenv import load_dotenv


load_dotenv()
app = Flask(__name__)
## secret key to check in request header
API_SECRET_KEY = os.getenv('API_SECRET_KEY')

# Google Sheets Setup
SPREADSHEET_ID = '1q8tvTIuGhOD7dyjMXEuHSxrhRREWvTezcipBhgtG8EI'
RANGE_NAME = 'Sheet1!A:D'  # Adjust if needed
appenv = os.getenv('APP_ENV')
## Scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# Load credentials
SERVICE_ACCOUNT_FILE = 'safile.json'
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
# if not SERVICE_ACCOUNT_JSON:
#     raise Exception("GOOGLE_CREDENTIALS_JSON environment variable not set")

# info = json.loads(SERVICE_ACCOUNT_JSON)
# credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


service = build('sheets', 'v4', credentials=credentials)
sheet = service.spreadsheets()

## check if header contain secret key
def check_auth():
    key = request.headers.get('X-API-KEY')
    if not key or key != API_SECRET_KEY:
        print("check_auth failed")
        abort(403, description='Forbidden: Invalid API key, RJV')
    else:
        print("Check_auth success")


@app.route('/get-prompts', methods=['GET'])
def get_prompts():
    check_auth()
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing required query param: user_id'}), 400

        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()

        rows = result.get('values', [])
        headers = ['user_id', 'timestamp', 'prompt', 'response']
        
        # Filter rows that match the requested user_id
        filtered = [dict(zip(headers, row)) for row in rows if row and row[0] == user_id]

        return jsonify(filtered), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/save-prompt', methods=['POST'])
def save_prompt():
    check_auth()
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'anonymous')
        prompt = data.get('prompt', '')
        response_text = data.get('response', '')
        #timestamp = datetime.utcnow().isoformat()
        timestamp = datetime.now(timezone.utc).isoformat()

        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400

        values = [[user_id, timestamp, prompt, response_text]]
        body = {'values': values}

        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

        return jsonify({'status': 'success', 'updatedRange': result['updates']['updatedRange']}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    if appenv == 'LOCAL':
       app.run(port=port, debug=True)    
    else:
        app.run(host='0.0.0.0', port=port)    
