import base64
import mimetypes
import os
import pandas as pd
import pickle

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart, MIMEBase
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from rpt.stats_by_date import get_stats_by_date
from rpt.stats_by_hw import get_stats_by_hw

config = {
    "frame_folder": "frames",
    "hw_events_stats_file": "hw_events_stats.pickle",
    "subject": "Weekly Pleco Report",
    "to": "eric.porter1234+pleco@gmail.com",
    "attachment": "weekly_vocab.csv",
}


def weekly_vocab_report(config) -> pd.DataFrame:
    report = get_stats_by_hw(
        config, pd.Timestamp.today() - pd.DateOffset(7, "D"), pd.Timestamp.today()
    )
    return report


def get_message(report: pd.DataFrame) -> str:
    learned = report.query("learned").reset_index()[["hw", "pinyin", "definition"]]
    forgot = report.query("forgot").reset_index()[["hw", "pinyin", "definition"]]
    new_vocab = report.query("new").reset_index()[["hw", "pinyin", "definition"]]

    s = "你这个星期练习了{}个词呀！你的报告如下：<p>".format(len(report.index))
    if len(learned.index) > 0:
        s += "你学到了{}个词：<br>{}<p>".format(
            len(learned.index), learned.to_html(index=False, col_space=50)
        )
    if len(forgot.index) > 0:
        s += "你忘记了{}个词：<br>{}<p>".format(
            len(forgot.index), forgot.to_html(index=False, col_space=50)
        )
    if len(new_vocab.index) > 0:
        s += "你学了{}个生词：<br>{}".format(
            len(new_vocab.index), new_vocab.to_html(index=False, col_space=50)
        )
    return s


def create_message_with_attachment(to, subject, message_text, file):
    """Create a message for an email.

    Args:
        sender: Email address of the sender.
        to: Email address of the receiver.
        subject: The subject of the email message.
        message_text: The text of the email message.
        file: The path to the file to be attached.

    Returns:
        An object containing a base64url encoded email object.
    """
    message = MIMEMultipart()
    message["to"] = to
    message["subject"] = subject

    msg = MIMEText(message_text, "html")
    message.attach(msg)

    content_type, encoding = mimetypes.guess_type(file)

    if content_type is None or encoding is not None:
        content_type = "application/octet-stream"
    main_type, sub_type = content_type.split("/", 1)
    if main_type == "text":
        fp = open(file, "r", encoding="utf8")
        msg = MIMEText(fp.read(), _subtype=sub_type)
        fp.close()
    elif main_type == "image":
        fp = open(file, "rb")
        msg = MIMEImage(fp.read(), _subtype=sub_type)
        fp.close()
    elif main_type == "audio":
        fp = open(file, "rb")
        msg = MIMEAudio(fp.read(), _subtype=sub_type)
        fp.close()
    else:
        fp = open(file, "rb")
        msg = MIMEBase(main_type, sub_type)
        msg.set_payload(fp.read())
        fp.close()
    filename = os.path.basename(file)
    msg.add_header("Content-Disposition", "attachment", filename=filename)
    message.attach(msg)

    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}


def create_message(to, subject, message_text, file):
    message = MIMEText(message_text, "html")
    message["to"] = to
    message["subject"] = subject
    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}


def send_message(service, user_id, message):
    return service.users().messages().send(userId=user_id, body=message).execute()


def authenticate(scopes):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
            creds = flow.run_console()
        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    service = build("gmail", "v1", credentials=creds)

    return service


def process(config):
    service = authenticate(["https://www.googleapis.com/auth/gmail.send"])

    report = weekly_vocab_report(config)
    report_message = get_message(report)
    report.to_csv(config["attachment"], encoding="utf8")
    message = create_message_with_attachment(
        config["to"], config["subject"], report_message, config["attachment"]
    )
    send_message(service, "me", message)


process(config)
