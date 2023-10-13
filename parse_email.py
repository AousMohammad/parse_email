import re

def extract_email_info(email_text):
    # Extract phone number
    phone_pattern = r'Whatsapp:\s*\+(\d{1,15}\s*\d{1,15})'
    phone = re.search(phone_pattern, email_text)
    
    # Extract email
    email_pattern = r'From:.*<([\w\.-]+@[\w\.-]+)>'
    email = re.search(email_pattern, email_text)
    
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
    subject_pattern = r'Subject: (.+)\n'
    subject = re.search(subject_pattern, email_text)
    
    # Store in a dictionary
    info = {
        'phone': '+' + phone.group(1).replace(" ", "") if phone else '',
        'email': email.group(1) if email else '',
        'name': name.group(1).strip() if name else '',
        'company': company.group(1).strip() if company else '',
        'country': country.group(1).strip() if country else '',
        'budget': budget.group(1) if budget else '',
        'subject': subject.group(1).strip() if subject else ''
    }
    
    return info

email_sample = """
From: Example Company <example@gmail.com>
Sent: Tuesday, April 18, 2023 5:42 PM
To: me@email.agency
Subject: Inquire

Hello
Lorem ipsum Lorem ipsum dolor sit amet, consectetur adipis vel magna 
Lorem ipsum Lorem ipsum dolor sit amet, consectetur adipis vel magna 
Lorem ipsum Lorem ipsum dolor sit amet, consectetur adipis vel magna with budget 20k-40k AED

Name Example
Founder of Example Company 
Bahrain
Whatsapp: +973 11223300
"""

info = extract_email_info(email_sample)
print(info)
