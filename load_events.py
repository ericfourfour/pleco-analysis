import sqlite3
import pandas as pd
import datetime as dt
import os
import re
import pickle
import os.path
import matplotlib.pyplot as plt
import numpy as np
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
import base64

def get_history(start_dt, end_dt, last_scores):
    pleco_db = sqlite3.connect("data/{}/Pleco Flashcard Database.pqb".format(end_dt.strftime("%Y-%m-%d %H.%M.%S")))

    scores = pd.read_sql_query("SELECT * FROM pleco_flash_scores_1", pleco_db)
    cards = pd.read_sql_query("SELECT * FROM pleco_flash_cards", pleco_db)

    cards.rename(columns = {'id': 'card'}, inplace=True)
    cards.set_index('card', inplace=True)
    scores.set_index('card', inplace=True)

    scores['firstreviewedtime'] = pd.to_datetime(scores['firstreviewedtime'], unit='s')
    scores['lastreviewedtime'] = pd.to_datetime(scores['lastreviewedtime'], unit='s')

    scores2 = scores.join(cards, on='card')
    scores2 = scores2[['hw', 'dictid', 'dictentry', 'history', 'reviewed', 'firstreviewedtime', 'lastreviewedtime', 'created']]

    history = pd.DataFrame(columns=['review_ts', 'headword', 'dictid', 'dictentry', 'result', 'ts_is_exact', 'dt_is_exact'])

    for _, row in scores2.iterrows():
        if start_dt is not None and row['firstreviewedtime'] < start_dt:
            rvw_start_ts = start_dt
            rvw_end_ts = row['lastreviewedtime']
            last_num_rvw = last_scores.loc[(last_scores['hw'] == row['hw']) & (last_scores['dictid'] == row['dictid']) & (last_scores['dictentry'] == row['dictentry']) & (last_scores['created'] == row['created'])]['reviewed']
            num_rvw = int(row['reviewed'])
            if num_rvw == 0:
                continue
            num_rvw = int(num_rvw - last_num_rvw)
            hist = row['history'][-num_rvw:]
        else:
            rvw_start_ts = row['firstreviewedtime']
            rvw_end_ts = row['lastreviewedtime']
            num_rvw = int(row['reviewed'])
            hist = row['history']

        if num_rvw == 0:
            continue

        dur = rvw_end_ts - rvw_start_ts
        interval = dur / num_rvw
        for i in range(num_rvw):
            review_ts = rvw_start_ts + (interval * i)
            result = int(hist[i]) >= 4
            ts_is_exact = (rvw_start_ts == row['firstreviewedtime'] and i == 0) or i == num_rvw - 1
            dt_is_exact = ts_is_exact or rvw_start_ts.date() == rvw_end_ts.date()
            history = history.append({'review_ts': review_ts, 'headword': row['hw'], 'dictid': row['dictid'], 'dictentry': row['dictentry'], 'result': result, 'ts_is_exact': ts_is_exact, 'dt_is_exact': dt_is_exact}, ignore_index=True)

    return history, scores2[['hw', 'dictid', 'dictentry', 'reviewed', 'created']]

def get_full_history(full_history, last_dt, last_scores, num=-1):
    if num == 0:
        return

    pdb_dts = [
        dt.datetime.strptime(f.name, "%Y-%m-%d %H.%M.%S")
        for f in os.scandir('data')
        if f.is_dir() and re.match(r'\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2}', f.name)
    ]
    if last_dt is not None:
        pdb_dts = [d for d in pdb_dts if d > last_dt]
    if num > 0:
        pdb_dts = pdb_dts[:num]

    pdb_dts.sort()

    for curr_dt in pdb_dts:
        history, last_scores = get_history(last_dt, curr_dt, last_scores)
        if full_history is None:
            full_history = history
        else:
            full_history = full_history.append(history)
        last_dt = curr_dt
    
    return full_history, last_dt, last_scores

def load_history():
    if not os.path.exists('save/full_history.pickle') or not os.path.exists('save/last_scores.pickle') or not os.path.exists('save/last_dt.pickle'):
        return None, None, None

    full_history = pd.read_pickle('save/full_history.pickle')
    last_scores = pd.read_pickle('save/last_scores.pickle')
    with open('save/last_dt.pickle', 'rb') as f:
        last_dt = pickle.load(f)

    return full_history, last_dt, last_scores

def save_history(full_history, last_dt, last_scores):
    full_history.to_pickle('save/full_history.pickle')
    last_scores.to_pickle('save/last_scores.pickle')
    with open('save/last_dt.pickle', 'wb') as f:
        pickle.dump(last_dt, f)

def update_and_get_history():
    full_history, last_dt, last_scores = load_history()
    full_history, last_dt, last_scores = get_full_history(full_history, last_dt, last_scores)
    save_history(full_history, last_dt, last_scores)
    return full_history

def get_prep_frame(full_history):
    prep = full_history.copy()
    prep['review_ts'] = prep['review_ts'].dt.tz_localize('UTC').dt.tz_convert('America/Toronto').dt.tz_localize(None)
    prep['review_dt'] = pd.to_datetime(prep['review_ts']).apply(lambda x: x.date())
    prep = prep[['headword', 'review_dt', 'result', 'review_ts']]
    prep = prep.sort_values(['headword', 'review_dt', 'review_ts'])
    prep.reset_index(drop=True, inplace=True)

    prep['occurrence'] = prep.groupby(['headword']).cumcount() + 1
    prep['n_correct'] = prep.groupby(['headword'])['result'].apply(lambda x: x.cumsum())
    prep['n_incorrect'] = prep.groupby(['headword'])['result'].apply(lambda x: x.apply(lambda y: not y).cumsum())
    prep['n_correct_day'] = prep.groupby(['headword', 'review_dt'])['result'].transform('sum')
    prep['n_incorrect_day'] = prep.groupby(['headword', 'review_dt'])['result'].transform(lambda x: x.apply(lambda y: not y).sum())
    prep['result_eod'] = prep.groupby(['headword', 'review_dt'])['result'].transform('last')
    prep['result_bod'] = prep.groupby(['headword', 'review_dt'])['result'].transform('first')
    prep['learned'] = prep[['n_correct', 'n_incorrect', 'n_correct_day', 'n_incorrect_day', 'result_bod', 'result_eod']].apply(lambda x: x[0] > x[1] and x[2] > x[3] and x[4] and x[5], axis=1)
    prep['lag_learned'] = prep.groupby(['headword'], as_index=False)['learned'].shift(1)

    def get_net_learned(learned, lag_learned):
        if (not pd.isna(lag_learned) and learned == lag_learned) or (pd.isna(lag_learned) and not learned):
            return 0
        if learned:
            return 1
        return -1

    prep['net_learned'] = prep[['learned', 'lag_learned']].apply(lambda x: get_net_learned(x[0], x[1]), axis=1)

    return prep

def get_daily_stats(prep):
    n_reviewed = prep.groupby('review_dt')['headword'].count().rename('n_reviewed')
    new_vocab = prep.groupby(['headword'], as_index=False)['review_dt'].min().groupby(['review_dt'])['headword'].count().rename('new_vocab')
    net_learned = prep.groupby('review_dt')['net_learned'].sum()
    learned = prep[prep['net_learned'] == 1].groupby('review_dt')['net_learned'].count().rename('learned')
    forgotten = prep[prep['net_learned'] == -1].groupby('review_dt')['net_learned'].count().rename('forgotten')

    review = pd.DataFrame({'n_reviewed': n_reviewed, 'new_vocab': new_vocab, 'net_learned': net_learned, 'learned': learned, 'forgotten': forgotten})
    review['new_vocab'] = review['new_vocab'].apply(lambda x: 0 if pd.isna(x) else x)
    review['learned'] = review['learned'].apply(lambda x: 0 if pd.isna(x) else x)
    review['forgotten'] = review['forgotten'].apply(lambda x: 0 if pd.isna(x) else x)
    review['vocab_size'] = review['new_vocab'].cumsum()
    review['total_learned'] = review['net_learned'].cumsum()
    review.index = pd.to_datetime(review.index)
    review['n_reviewed'] = review['n_reviewed'].astype('u4')
    review['new_vocab'] = review['new_vocab'].astype('u4')
    review['net_learned'] = review['net_learned'].astype('i4')
    review['learned'] = review['learned'].astype('u4')
    review['forgotten'] = review['forgotten'].astype('u4')
    review['vocab_size'] = review['vocab_size'].astype('u4')
    review['total_learned'] = review['total_learned'].astype('i4')

    return review

def show_daily_report(review):
    charts = review.plot.line()
    plt.axhline(0, color='white', linewidth=0.1, zorder=1)
    plt.axvspan(pd.to_datetime('2017-04-29'), pd.to_datetime('2017-05-13'), color='red', label='China Trip')
    charts.axvline(pd.to_datetime('2018-09-02'), color='blue', linestyle='--', lw=2, label='SRS')
    charts.axvline(pd.to_datetime('2018-07-31'), color='purple', linestyle='--', lw=2, label='TELUS')
    charts.axvline(pd.to_datetime('2019-01-30'), color='green', linestyle='--', lw=2, label='Daily Backups')
    charts.axvline(pd.to_datetime('2019-02-20'), color='purple', linestyle='--', lw=2, label='TELUS Restructuring')
    plt.xticks(rotation=90)

def get_7_day_report(review):
    weekly = review.loc[dt.date.today() - pd.DateOffset(7, 'D'):].copy()

    weekly.rename(columns={'n_reviewed': 'reviewed'}, inplace=True)

    weekly['cum_reviewed'] = weekly['reviewed'].cumsum()
    weekly['cum_new_vocab'] = weekly['new_vocab'].cumsum()
    weekly['cum_net_learned'] = weekly['net_learned'].cumsum()
    weekly['cum_learned'] = weekly['learned'].cumsum()
    weekly['cum_forgotten'] = weekly['forgotten'].cumsum()
    
    return weekly[['reviewed', 'new_vocab', 'learned', 'forgotten', 'net_learned', 'cum_reviewed', 'cum_new_vocab', 'cum_net_learned', 'cum_learned', 'cum_forgotten']]

def get_7_day_vocab_report(prep):
    import pinyin
    import pinyin.cedict

    rpt = prep[prep['review_dt'] >= dt.date.today() - pd.DateOffset(7, 'D')].copy()
    rpt['headword'] = rpt['headword'].str.replace('@', '')

    net_learned = rpt.groupby(['headword'])['net_learned'].sum()
    occurrence = rpt.groupby(['headword'])['occurrence'].min()

    vocab_rpt = pd.DataFrame({'net_learned': net_learned, 'occurrence': occurrence})
    vocab_rpt['learned'] = vocab_rpt['net_learned'].apply(lambda x: x == 1)
    vocab_rpt['forgot'] = vocab_rpt['net_learned'].apply(lambda x: x == -1)
    vocab_rpt['new'] = vocab_rpt['occurrence'].apply(lambda x: x == 1)

    vocab_rpt.reset_index(inplace=True)

    vocab_rpt['pinyin'] = vocab_rpt['headword'].apply(lambda hw: pinyin.get(hw))
    vocab_rpt['defn'] = vocab_rpt['headword'].apply(lambda hw: pinyin.cedict.translate_word(hw))

    return vocab_rpt

def show_7_day_report(report):
    report[['cum_reviewed', 'cum_new_vocab', 'cum_net_learned']].plot.line()
    report[['reviewed', 'new_vocab', 'net_learned']].plot.line()
    report[['net_learned', 'learned', 'forgotten']].plot.line()

def create_message(to, subject, message_text):
    message = MIMEText(message_text, 'html')
    message['to'] = to
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def send_message(service, user_id, message):
    return (service.users().messages().send(userId=user_id, body=message).execute())

def authenticate(scopes):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes)
            creds = flow.run_console()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    return service

def get_message(vocab_rpt):
    learned = vocab_rpt.query('learned')[['headword', 'pinyin', 'defn']]
    forgot = vocab_rpt.query('forgot')[['headword', 'pinyin', 'defn']]
    new_vocab = vocab_rpt.query('occurrence == 1')[['headword', 'pinyin', 'defn']]

    s = "你这个星期练习了{}个词呀！你的报告如下：<p>".format(len(vocab_rpt.index))
    if len(learned.index) > 0:
        s += "你学到了{}个词：<br>{}<p>".format(len(learned.index), learned.to_html(index=False, col_space=50))
    if len(forgot.index) > 0:
        s += "你忘记了{}个词：<br>{}<p>".format(len(forgot.index), forgot.to_html(index=False, col_space=50))
    if len(new_vocab.index) > 0:
        s += "你学了{}个生词：<br>{}".format(len(new_vocab.index), new_vocab.to_html(index=False, col_space=50))
    return s

full_history = update_and_get_history()
prep = get_prep_frame(full_history)
review = get_daily_stats(prep)
show_daily_report(review)
weekly = get_7_day_report(review)
show_7_day_report(weekly)

vocab_rpt = get_7_day_vocab_report(prep)
vocab_rpt_message = get_message(vocab_rpt)

SCOPES = ['https://www.googleapis.com/auth/gmail.labels', 'https://www.googleapis.com/auth/gmail.send']

service = authenticate(SCOPES)

message = create_message('eric.porter1234+pleco@gmail.com', 'Weekly Pleco Report', vocab_rpt_message)

send_message(service, 'me', message)
