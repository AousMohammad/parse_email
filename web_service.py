from flask import Flask, request, jsonify
import imaplib
from email import message_from_bytes
import mysql.connector
from decouple import config
import spacy
import re
import logging
import en_core_web_sm

app = Flask(__name__)

logging.basicConfig(filename='email_processing.log', level=logging.INFO)

IMAP_SERVER = config('IMAP_SERVER')
IMAP_PORT = int(config('IMAP_PORT'))
IMAP_USER = config('IMAP_USER')
IMAP_PASS = config('IMAP_PASS')
DB_HOST = config('DB_HOST')
DB_USER = config('DB_USER')
DB_PASS = config('DB_PASS')
DB_NAME = config('DB_NAME')


nlp = en_core_web_sm.load()

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

            sender = email_message.get('From')
            subject = email_message.get('Subject')

            content = None
            email_match = re.search(r'<([^>]+)>', sender)
            if email_match:
                sender = email_match.group(1)
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
                'content': content
            }

def extract_email_info(email_text):
    doc = nlp(email_text)

    info = {
        'phone': '',
        'name': '',
        'company': '',
        'country': '',
        'budget': '',
    }

    for ent in doc.ents:
        if ent.label_ == 'CARDINAL' and "k" in ent.text.lower():
            info['budget'] = ent.text
        elif ent.label_ == 'PERSON' and not info['name']:
            info['name'] = ent.text
        elif ent.label_ == 'ORG' and not info['company']:
            info['company'] = ent.text
        elif ent.label_ == 'GPE' and not info['country']:
            info['country'] = ent.text

    phone_pattern = re.compile(r'\+\d{1,3} \d{7,10}')
    phone_match = phone_pattern.search(email_text)
    if phone_match:
        info['phone'] = phone_match.group(0)

    budget_pattern = re.compile(r'\d+k-\d+k')
    budget_match = budget_pattern.search(email_text)
    if budget_match:
        info['budget'] = budget_match.group(0)

    return info

def store_to_db(data):
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )

        cursor = conn.cursor()

        insert_query = """
        INSERT INTO emails (phone, email, name, company, country, budget, subject)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (data['phone'], data['sender'], data['name'], data['company'], data['country'], data['budget'], data['subject']))
        conn.commit()
        cursor.close()
        conn.close()

    except mysql.connector.Error as e:
        logging.error(f"Database error: {str(e)}")

@app.route('/parse-emails', methods=['POST'])
def parse_emails():
    email_data_list = list(fetch_emails())
    results = []
    for email_data in email_data_list:
        clean_data = email_data['content'].replace('\r\n', ' ')
        data = extract_email_info(clean_data)
        data['sender'] = email_data['sender']
        data['subject'] = email_data['subject']
        results.append(data)
        store_to_db(data)

    return jsonify(results) 

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 
