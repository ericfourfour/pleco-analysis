import sqlite3
import pandas as pd
import datetime as dt
import os
import re
import pickle
import os.path
import matplotlib.pyplot as plt
import numpy as np

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

full_history, last_dt, last_scores = load_history()
full_history, last_dt, last_scores = get_full_history(full_history, last_dt, last_scores)
save_history(full_history, last_dt, last_scores)

full_history.info()

prep = full_history.copy()
prep['review_dt'] = pd.to_datetime(prep['review_ts']).apply(lambda x: x.date())
prep = prep[['headword', 'review_dt', 'result', 'review_ts']]
prep = prep.sort_values(['headword', 'review_dt', 'review_ts'])
prep.reset_index(drop=True, inplace=True)

prep['n_correct'] = prep.groupby(['headword'])['result'].apply(lambda x: x.cumsum())
prep['n_incorrect'] = prep.groupby(['headword'])['result'].apply(lambda x: x.apply(lambda y: not y).cumsum())
prep['last_result'] = prep.groupby(['headword', 'review_dt'])['result'].transform('last')
prep['learned'] = prep[['n_correct', 'n_incorrect', 'last_result']].apply(lambda x: x[0] > x[1] and x[2], axis=1)
prep['lag_learned'] = prep.groupby(['headword'], as_index=False)['learned'].shift(1)

def get_net_learned(learned, lag_learned):
    if (not pd.isna(lag_learned) and learned == lag_learned) or (pd.isna(lag_learned) and not learned):
        return 0
    if learned:
        return 1
    return -1

prep['net_learned'] = prep[['learned', 'lag_learned']].apply(lambda x: get_net_learned(x[0], x[1]), axis=1)

n_reviewed = prep.groupby('review_dt')['headword'].count().rename('n_reviewed')
new_vocab = prep.groupby(['headword'], as_index=False)['review_dt'].min().groupby(['review_dt'])['headword'].count().rename('new_vocab')
net_learned = prep.groupby('review_dt')['net_learned'].sum()

review = pd.DataFrame({'n_reviewed': n_reviewed, 'new_vocab': new_vocab, 'net_learned': net_learned})
review['new_vocab'] = review['new_vocab'].apply(lambda x: 0 if pd.isna(x) else x)
review['vocab_size'] = review['new_vocab'].cumsum()
review['total_learned'] = review['net_learned'].cumsum()

charts = review.plot.line()
plt.axhline(0, color='white', linewidth=0.1, zorder=1)
plt.axvspan(pd.to_datetime('2017-04-29'), pd.to_datetime('2017-05-13'), color='red', label='China Trip')
charts.axvline(pd.to_datetime('2018-09-02'), color='blue', linestyle='--', lw=2, label='SRS')
charts.axvline(pd.to_datetime('2018-07-31'), color='purple', linestyle='--', lw=2, label='TELUS')
charts.axvline(pd.to_datetime('2019-01-30'), color='green', linestyle='--', lw=2, label='Daily Backups')
charts.axvline(pd.to_datetime('2019-02-20'), color='purple', linestyle='--', lw=2, label='TELUS Restructuring')
plt.xticks(rotation=90)
