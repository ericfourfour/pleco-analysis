import sqlite3
import pandas as pd
import datetime as dt
import os
import re
import pickle
import os.path

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
            # print(hist)
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
            result = int(hist[i]) <= 3
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
