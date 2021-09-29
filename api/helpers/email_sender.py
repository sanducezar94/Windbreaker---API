import smtplib, ssl, datetime, math, random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from api.constants import CONSTANTS
from api import session, client
from api.models import Otp




text = """\
    <html>
        <body>
    <p>Buna ziua,</p>

    <p>Folositi codul de mai jos pentru a verifica email-ul:</p>

     <p style='font-weight: bold'>@code</p>
        </body>
    </html>
    """

def send_otp(email):
    context = ssl.create_default_context()
    otp_code = generate_otp()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server: 
        try:
            server.login(CONSTANTS['EMAIL'], CONSTANTS['EMAIL_PASSWORD'])
        except(Exception) as e:
            print(str(e))
        message = prepare_otp_message(email, otp_code)
        server.sendmail(CONSTANTS['EMAIL'], email, message.as_string())

    s = session()

    otp_check = s.query(Otp).filter(Otp.email == email).first()

    if otp_check is None:
        otp = Otp()
        otp.email = email
        otp.key = otp_code
        otp.created_on = datetime.datetime.utcnow()
        s.add(otp)
        s.commit()
    else:
        otp_check.email = email
        otp_check.key = otp_code
        otp_check.created_on = datetime.datetime.utcnow()
        s.add(otp_check)
        s.commit()


def prepare_otp_message(receiver_email, otp):
    message = MIMEMultipart("alternative")
    message["Subject"] = 'Confirmare email - Cu bicicleta pe drumuri de poveste'
    message["From"] = CONSTANTS["EMAIL"]
    message["To"] = receiver_email

   # email_header = MIMEText(text, 'plain')
    email_body = MIMEText(text.replace('@code', otp), 'html')

    #message.attach(email_header)
    message.attach(email_body)

    return message


def generate_otp():
    digits = "0123456789"
    OTP = ""
    for i in range(6):
        OTP+=digits[math.floor(random.random()*10)]
        
    return OTP