import imaplib
from email import message_from_bytes
import mysql.connector
from decouple import config
import spacy
import re
import logging

logging.basicConfig(filename='email_processing.log', level=logging.INFO)

IMAP_SERVER = config('IMAP_SERVER')
IMAP_PORT = int(config('IMAP_PORT'))
IMAP_USER = config('IMAP_USER')
IMAP_PASS = config('IMAP_PASS')
DB_HOST = config('DB_HOST')
DB_USER = config('DB_USER')
DB_PASS = config('DB_PASS')
DB_NAME = config('DB_NAME')


nlp = spacy.blank("en")
ner = nlp.add_pipe("ner")
labels = ["NAME", "COMPANY", "PHONE", "BUDGET", "COUNTRY"]

for label in labels:
    ner.add_label(label)

# Load your custom NER model
nlp.from_disk("astudio_email_parser")
nlp.initialize()

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
        if ent.label_ == 'PHONE':
            info['phone'] = ent.text
        elif ent.label_ == 'COMPANY':
            info['company'] = ent.text
        elif ent.label_ == 'COUNTRY':
            info['country'] = ent.text
        elif ent.label_ == 'BUDGET':
            info['budget'] = ent.text
        elif ent.label_ == 'NAME':
            info['name'] = ent.text

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

def main():
    for email_data in fetch_emails():
        print(email_data)
        data = extract_email_info(email_data['content'])
        data['sender'] = email_data['sender']
        data['subject'] = email_data['subject']
        print(data)
        # Uncomment the line below to store data in the database
        # store_to_db(data)

if __name__ == "__main__":
    main()
