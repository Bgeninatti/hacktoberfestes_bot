import csv
import email
import imaplib
import os
import pathlib
from datetime import datetime
from email.header import decode_header
from time import sleep

from config import load_config
from logger import get_logger

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

LOGGER = get_logger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config = load_config()

EMAIL_USER = config["DEFAULT"]["EmailUser"]
EMAIL_PASSWORD = config["DEFAULT"]["EmailPassword"]
FROM_EMAIL_EXPECTED = config["DEFAULT"]["FromEmailExpected"]
INSCRIPTES_FILEPATH = os.path.join(BASE_DIR, config['DEFAULT']['List'])

SUBJECT_PREFIX = "Inscriptes PyConAr 2020 - "

imap = imaplib.IMAP4_SSL("imap.gmail.com")
imap.login(EMAIL_USER, EMAIL_PASSWORD)

status, messages = imap.select("INBOX")
N = 3
messages = int(messages[0])

LAST_EMAIL_DATE = None

BACKUP_PATH = pathlib.Path("backups/")
BACKUP_PATH.mkdir(parents=True, exist_ok=True)


def get_regitered_tickets():
    registered = set()
    with open(INSCRIPTES_FILEPATH, "r") as inscriptes:
        reader = csv.reader(inscriptes)
        registered = set(line[0] for line in reader)
    return registered


def save_registered_tickets(registered):
    with open(INSCRIPTES_FILEPATH, "w") as inscriptes:
        inscriptes.write(registered)


def backup_registered_tickets(timestamp: datetime):
    with open(INSCRIPTES_FILEPATH, "r") as inscriptes:
        backup_name = f"{BACKUP_PATH}/{timestamp.strftime(DATETIME_FORMAT)}_{INSCRIPTES_FILEPATH}"
        with open(backup_name, "w") as inscriptes_backup:
            inscriptes_backup.write(inscriptes.read())


def _get_subject(msg):
    subject = decode_header(msg["Subject"])[0][0]
    if isinstance(subject, bytes):
        subject = subject.decode()
    return subject


def _get_from_email(msg):
    from_email, encoding = decode_header(msg.get("From"))[0]
    if isinstance(from_email, bytes):
        from_email = from_email.decode(encoding)
    return from_email


def run():
    for i in range(messages, messages - N, -1):
        res, msg = imap.fetch(str(i), "(RFC822)")
        for response in msg:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                subject = _get_subject(msg)

                if SUBJECT_PREFIX not in subject:
                    break

                from_email = _get_from_email(msg)

                if from_email != FROM_EMAIL_EXPECTED:
                    break

                timestamp = datetime.strptime(subject.replace(SUBJECT_PREFIX, ""), DATETIME_FORMAT)

                global LAST_EMAIL_DATE
                if LAST_EMAIL_DATE is None or LAST_EMAIL_DATE < timestamp:
                    LAST_EMAIL_DATE = timestamp
                else:
                    break

                LOGGER.info(f"Processing email from {timestamp}")

                payloads = msg.get_payload()

                for payload in payloads:
                    inner_payload = payload.get_payload(decode=True).decode("unicode_escape")
                    if "La lista de inscriptes para el PyConAr 2020" in inner_payload:
                        continue

                    backup_registered_tickets(timestamp)
                    save_registered_tickets(inner_payload)

                registered = get_regitered_tickets()
                LOGGER.info(f"New loaded registered: {len(registered)}")


if __name__ == "__main__":
    while True:
        run()
        sleep(60 * 5)  # 5 minutes
