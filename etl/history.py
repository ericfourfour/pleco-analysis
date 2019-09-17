import numpy as np
import pandas as pd
import os
import re
import sqlite3

config = {
    "timezone": "America/Toronto",
    "db_folder": "data",
    "db_folder_rx": r"^\d{4}-\d{2}-\d{2} \d{2}.\d{2}.\d{2}$",
    "frame_folder": "frames",
    "events_file": "history.pickle",
    "processed_file": "history_processed.pickle",
}


def concat_events(events1: pd.DataFrame, events2: pd.DataFrame) -> pd.DataFrame:
    """
    Concatenate review events together
    """

    if events1 is None:
        return events2

    events = pd.concat([events1, events2], verify_integrity=True)
    events.sort_index(inplace=True)
    return events


def interpolate_row_events(group: pd.DataFrame) -> pd.DataFrame:
    """
    Transform a single row of Pleco scores into a sequence of review events
    """

    events = pd.DataFrame(columns=["reviewedtime", "result"])

    row = group.iloc[0].copy()
    reviewed = row["reviewed"]

    if reviewed == 0:
        return events

    firstreviewedtime = row["firstreviewedtime"]
    lastreviewedtime = row["lastreviewedtime"]
    history = row["history"]
    cumreviewed = row["cumreviewed"]

    duration = lastreviewedtime - firstreviewedtime
    interval = duration / reviewed
    for i in range(reviewed):
        reviewed_time = firstreviewedtime + (interval * (i + 1))
        result = int(history[i]) >= 4
        events = events.append(
            {"reviewedtime": reviewed_time, "result": result}, ignore_index=True
        )

    events.index = events.index + (cumreviewed - reviewed)
    events.index.name = "occurrence"
    return events


def interpolate_events(scores: pd.DataFrame) -> pd.DataFrame:
    """
    Given the scores or incremental scores, interpolate the sequence review events.
    """

    inc_scores = scores.query("reviewed > 0").copy()
    inc_scores.sort_index(inplace=True)
    return inc_scores.groupby(["dictid", "dictentry", "hw", "created"]).apply(
        interpolate_row_events
    )


def get_incremental_scores(
    scores1: pd.DataFrame, scores2: pd.DataFrame
) -> pd.DataFrame:
    """
    Gets the difference between two Pleco Databases
    """

    if scores1 is None:
        return scores2.copy()

    diff = scores2.copy()
    diff["inc_scores"] = (
        (scores2["reviewed"] - scores1["reviewed"]).fillna(0).astype("u4")
    )
    diff["inc_history"] = diff.apply(
        lambda x: x["history"][-x["inc_scores"] :] if x["inc_scores"] > 0 else np.nan,
        axis=1,
    )
    diff["last_frt"] = scores1["firstreviewedtime"]
    diff["last_lrt"] = scores1["lastreviewedtime"]
    diff["inc_firstreviewedtime"] = diff[["firstreviewedtime", "last_lrt"]].max(axis=1)

    diff = diff[
        [
            "inc_firstreviewedtime",
            "lastreviewedtime",
            "inc_scores",
            "cumreviewed",
            "inc_history",
        ]
    ]
    diff = diff.rename(
        columns={
            "inc_firstreviewedtime": "firstreviewedtime",
            "inc_scores": "reviewed",
            "inc_history": "history",
        }
    )
    return diff


def get_scores(db: sqlite3.Connection) -> pd.DataFrame:
    """
    Gets the scores from a Pleco Database
    """

    # Get & Format Cards
    cards = pd.read_sql_query("SELECT * FROM pleco_flash_cards", db)
    cards.rename(columns={"id": "card"}, inplace=True)
    cards.set_index("card", inplace=True)
    cards = cards[["dictid", "dictentry", "hw", "created"]]
    cards["hw"] = cards["hw"].str.replace("@", "")
    cards["created"] = (
        pd.to_datetime(cards["created"], unit="s")
        .dt.tz_localize("UTC")
        .dt.tz_convert(config["timezone"])
        .dt.tz_localize(None)
    )

    # Get & Format Scores
    scores = pd.read_sql_query("SELECT * FROM pleco_flash_scores_1", db)
    scores.set_index("card", inplace=True)
    scores = scores[["firstreviewedtime", "lastreviewedtime", "reviewed", "history"]]
    scores["firstreviewedtime"] = (
        pd.to_datetime(scores["firstreviewedtime"], unit="s")
        .dt.tz_localize("UTC")
        .dt.tz_convert(config["timezone"])
        .dt.tz_localize(None)
    )
    scores["lastreviewedtime"] = (
        pd.to_datetime(scores["lastreviewedtime"], unit="s")
        .dt.tz_localize("UTC")
        .dt.tz_convert(config["timezone"])
        .dt.tz_localize(None)
    )

    # Join Cards & Scores
    scores = cards.join(scores, on="card")
    scores.set_index(
        ["dictid", "dictentry", "hw", "created"], inplace=True, verify_integrity=True
    )
    scores["reviewed"] = scores["reviewed"].fillna(0).astype("u4")
    scores["cumreviewed"] = scores["reviewed"]
    scores = scores[
        ["firstreviewedtime", "lastreviewedtime", "reviewed", "cumreviewed", "history"]
    ]
    scores.sort_index(inplace=True)

    return scores


def process(config):
    """
    Process the files
    """

    events_file = os.path.join(config["frame_folder"], config["events_file"])
    processed_file = os.path.join(config["frame_folder"], config["processed_file"])
    db_folder_rx = re.compile(config["db_folder_rx"])

    # Ensure we have a folder for persisting dataframes
    if not os.path.exists(config["frame_folder"]):
        os.mkdir(config["frame_folder"])

    # Load the record of processed Pleco Databases
    if not os.path.exists(events_file):
        processed = pd.DataFrame(columns=["folder", "starttime", "endtime"])
    else:
        processed = pd.read_pickle(processed_file)

    # Get db folders
    db_folders = list(
        filter(lambda f: db_folder_rx.match(f), os.listdir(config["db_folder"]))
    )

    # Get new db folders
    new_db_folders = list(
        filter(lambda f: f not in processed["folder"].values, db_folders)
    )
    new_db_folders.sort()

    if len(new_db_folders) == 0:
        return

    # Load last scores
    if len(processed) > 0:
        db_file = os.path.join(
            config["db_folder"],
            processed.iloc[-1]["folder"],
            "Pleco Flashcard Database.pqb",
        )
        with sqlite3.connect(db_file) as db:
            last_scores = get_scores(db)
    else:
        last_scores = None

    # Get saved events
    if os.path.exists(events_file):
        events = pd.read_pickle(events_file)
    else:
        events = None

    for f in new_db_folders:
        db_file = os.path.join(config["db_folder"], f, "Pleco Flashcard Database.pqb")

        processed_db = {"folder": f, "starttime": pd.Timestamp.now(config["timezone"])}
        with sqlite3.connect(db_file) as db:
            scores = get_scores(db)
        incremental = get_incremental_scores(last_scores, scores)
        current_events = interpolate_events(incremental)
        events = concat_events(events, current_events)

        # Record processed db folder
        processed_db["endtime"] = pd.Timestamp.now(config["timezone"])
        processed = processed.append(processed_db, ignore_index=True)
        processed.reset_index(inplace=True, drop=True)

        last_scores = scores

    events.to_pickle(events_file)
    processed.to_pickle(processed_file)


if __name__ == "__main__":
    process(config)
