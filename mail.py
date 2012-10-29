import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.Utils import formatdate

import dartzshop_settings as settings


def get_mime_multipart_message(recipient, subject, body, codepage):
    """Return MIMEMuiltipart message object."""
    # Encode subject and body
    subject = unicode(subject).encode(codepage)
    body = unicode(body).encode(codepage)

    # Prepare message
    message = MIMEMultipart()
    message['From'] = settings.MAIL_USER
    message['To'] = recipient
    message['Reply-To'] = settings.MAIL_USER_FROM
    message['Date'] = formatdate(localtime=True)
    message['Subject'] = Header(subject, codepage)

    message.attach(MIMEText(body, 'html', codepage))
    return message


def send_mail(message_list, html=False, codepage='utf-8'):
    """Send email message, in case of exception returns error message.

    :message_list:    list of tuples (recipient, subject, body)

    Message is encoded in utf-8 and is attached as html.

    """
    mime_multipart_messages = []
    for recipient, subject, body in message_list:
        mime_multipart_messages.append(
            get_mime_multipart_message(recipient, subject, body, codepage))

    try:
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(settings.MAIL_USER, settings.MAIL_PASSWORD)
        sender = settings.MAIL_USER
        for message in mime_multipart_messages:
            server.sendmail(sender, message['To'], message.as_string())
        server.quit()
    except Exception, e:
        return e.message
