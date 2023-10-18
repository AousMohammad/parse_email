from flask import Flask, jsonify
import imaplib
from email import message_from_bytes
import spacy
import re
import logging
import en_core_web_sm
import requests
from decouple import config
from datetime import datetime

app = Flask(__name__)

logging.basicConfig(filename='email_processing.log', level=logging.INFO)

IMAP_SERVER = config('IMAP_SERVER')
IMAP_PORT = int(config('IMAP_PORT'))
IMAP_USER = config('IMAP_USER')
IMAP_PASS = config('IMAP_PASS')
API_ENDPOINT = config('API_ENDPOINT')
API_KEY = config('API_KEY')
WHITELIST_EMAIL = config('WHITELIST_EMAIL')

nlp = en_core_web_sm.load()

def parse_date(email_date):
    date_formats = [
        '%Y-%m-%d %H:%M:%S',
        '%a, %d %b %Y %H:%M:%S %z'
    ]
    
    for date_format in date_formats:
        try:
            return datetime.strptime(email_date, date_format)
        except ValueError:
            continue
    
    logging.error(f"Failed to parse email date: {email_date}")
    return None

def fetch_emails():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(IMAP_USER, IMAP_PASS)
    mail.select('inbox')
    result, data = mail.search(None, '(UNSEEN)')
    if result == 'OK':
        for num in data[0].split():
            result, email_data = mail.fetch(num, '(RFC822)')
            raw_email = email_data[0][1]
            email_message = message_from_bytes(raw_email)
            date_received = email_message.get('Date')
            sender = email_message.get('From')
            subject = email_message.get('Subject')

            content = None
            email_match = re.search(r'<([^>]+)>', sender)
            if email_match:
                sender = email_match.group(1)
            if sender != WHITELIST_EMAIL:
                continue
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition'))

                    if "attachment" not in content_disposition and (content_type == "text/plain" or content_type == "text/html"):
                        content = part.get_payload(decode=True).decode('utf-8')
                        break
            else:
                payload = email_message.get_payload(decode=True)
                if payload:
                    content = payload.decode('utf-8')

            yield {
                'sender': sender,
                'subject': subject,
                'content': content,
                'date': date_received
            }

def extract_email_info(email_text, email_date):
    doc = nlp(email_text)

    info = {
        'phone': '',
        'name': '',
        'company': '',
        'notes': email_text,
        'country': '',
        'budget': '',
        'website': '',
        'day_of_lead': '',
        'date': ''
    }

    website_pattern = re.compile(r'https?://\S+')
    website_match = website_pattern.search(email_text)
    if website_match:
        info['website'] = website_match.group(0)

    email_datetime = parse_date(email_date)
    if email_datetime:
        info['day_of_lead'] = email_datetime.strftime('%A')
        info['date'] = email_datetime.strftime('%Y-%m-%d %H:%M:%S')
    
    for ent in doc.ents:
        if ent.label_ == 'CARDINAL' and "k" in ent.text.lower():
            info['budget'] = ent.text
        elif ent.label_ == 'PERSON' and not info['name']:
            info['name'] = ent.text
        elif ent.label_ == 'ORG' and not info['company']:
            info['company'] = ent.text
        elif ent.label_ == 'GPE' and not info['country']:
            info['country'] = ent.text

    if ' ' in info['name']:
        info['first_name'], info['last_name'] = info['name'].split(' ', 1)
    else:
        info['first_name'] = info['name']
        info['last_name'] = ''
    phone_pattern = re.compile(r'\+\d{1,3} \d{7,10}')
    phone_match = phone_pattern.search(email_text)
    if phone_match:
        info['phone'] = phone_match.group(0)

    budget_pattern = re.compile(r'(\d+k\s*-\s*\d+k\s*[A-Z]{3}|\d+k\s*[A-Z]{3})')
    budget_match = budget_pattern.search(email_text)
    if budget_match:
        info['budget'] = budget_match.group(0)

    return info

def send_to_api(data):
    payload = {
        'form': {
            'name': 'Email Lead',
            'company_name': data['company'],
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'full_name': data['name'],
            'email': data['sender'],
            'phone': data['phone'],
            'notes': data['notes'],
            'website': data['website'],
            'communication': 'Email AI',
            'day_of_lead': data['day_of_lead'],
            'date': data['date'],
            'progress_stage': 'Lead Open',
            'budget': data['budget']
        },
        'api_key': API_KEY
    }
    response = requests.post(API_ENDPOINT, json=payload)
    if response.status_code != 200:
        logging.error(f"API error: {response.text}")

@app.route('/parse-emails', methods=['POST'])
def parse_emails():
    email_data_list = list(fetch_emails())
    results = []
    for email_data in email_data_list:
        clean_data = email_data['content'].replace('\r\n', ' ')
        data = extract_email_info(clean_data, email_data.get('date', ''))
        data['sender'] = email_data['sender']
        data['subject'] = email_data['subject']
        results.append(data)
        send_to_api(data)

    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
