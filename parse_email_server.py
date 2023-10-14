import imaplib
from email import message_from_bytes
import mysql.connector
import re
from decouple import config

IMAP_SERVER = config('IMAP_SERVER')
IMAP_PORT = int(config('IMAP_PORT'))
IMAP_USER = config('IMAP_USER')
IMAP_PASS = config('IMAP_PASS')
DB_HOST = config('DB_HOST')
DB_USER = config('DB_USER')
DB_PASS = config('DB_PASS')
DB_NAME = config('DB_NAME')

def fetch_emails():
    # Use the provided IMAP server and port details
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
            # Check if email is multipart
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition'))

                    # Only consider parts that are text/plain or text/html and not attachments
                    if "attachment" not in content_disposition and (content_type == "text/plain" or content_type == "text/html"):
                        content = part.get_payload(decode=True).decode('utf-8')
                        break
            else:
                # If email is not multipart, get the payload directly
                payload = email_message.get_payload(decode=True)
                if payload:
                    content = payload.decode('utf-8')

            yield {
                'sender': sender,
                'subject': subject,
                'content': content
            }

# Extract email info
def extract_email_info(email_text):
    # Extract phone number
    phone_pattern = r'Whatsapp:\s*\+(\d{1,15}\s*\d{1,15})'
    phone = re.search(phone_pattern, email_text)
    
    # Extract email
    # email_pattern = r'From:.*<([\w\.-]+@[\w\.-]+)>'
    # email = re.search(email_pattern, email_text)
    
    # Extract name of sender
    name_pattern = r'\n([\w\s]+)\nFounder'
    name = re.search(name_pattern, email_text)
    
    # Extract company name
    company_pattern = r'Founder of ([^\n]+)'
    company = re.search(company_pattern, email_text)
    
    # Extract country
    country_pattern = r'Founder of [\w\s]+\s*\n([\w\s]+)\nWhatsapp:'
    country = re.search(country_pattern, email_text)
    
    # Extract budget
    budget_pattern = r'(\d+k-\d+k AED)'
    budget = re.search(budget_pattern, email_text)
    
    # Extract subject
    # subject_pattern = r'Subject: (.+)\n'
    # subject = re.search(subject_pattern, email_text)
    
    # Store in a dictionary
    info = {
        'phone': '+' + phone.group(1).replace(" ", "") if phone else '',
        'name': name.group(1).strip() if name else '',
        'company': company.group(1).strip() if company else '',
        'country': country.group(1).strip() if country else '',
        'budget': budget.group(1) if budget else '',
    }
    
    return info

def store_to_db(data):
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
    cursor.execute(insert_query, (data['phone'], data['email'], data['name'], data['company'], data['country'], data['budget'], data['subject']))
    conn.commit()
    cursor.close()
    conn.close()

def main():
    for email_data in fetch_emails():
        print(email_data['content'])
        data = extract_email_info(email_data['content'])
        data['email'] = email_data['sender']
        data['subject'] = email_data['subject']
        store_to_db(data)

if __name__ == "__main__":
    main()
