import os
import pandas as pd

config = {
    "frame_folder": "frames",
    "hw_events_file": "hw_events.pickle",
    "hw_events_stats_file": "hw_events_stats.pickle",
}


def is_learned(row):
    return row["daycorrect"] > 0 and row["dayincorrect"] == 0


def get_net_learned(row):
    if not pd.isna(row["laglearned"]) and row["learned"] == row["laglearned"]:
        return 0
    if pd.isna(row["laglearned"]) and not row["learned"]:
        return 0
    if row["learned"]:
        return 1
    return -1


def process(config):

    hw_events_file = os.path.join(config["frame_folder"], config["hw_events_file"])
    hw_events = pd.read_pickle(hw_events_file)

    hw_events_stats = hw_events.copy()

    hw_events_stats["revieweddate"] = hw_events_stats["reviewedtime"].apply(
        lambda x: x.date()
    )
    hw_events_stats["cumcorrect"] = (
        hw_events_stats.groupby(["hw"])["result"]
        .apply(lambda x: x.cumsum())
        .astype("u2")
    )
    hw_events_stats["cumincorrect"] = (
        hw_events_stats.groupby(["hw"])["result"]
        .apply(lambda x: x.apply(lambda y: not y).cumsum())
        .astype("u2")
    )
    hw_events_stats["daycorrect"] = (
        hw_events_stats.groupby(["hw", "revieweddate"])["result"]
        .transform("sum")
        .astype("u2")
    )
    hw_events_stats["dayincorrect"] = (
        hw_events_stats.groupby(["hw", "revieweddate"])["result"]
        .transform(lambda x: x.apply(lambda y: not y).sum())
        .astype("u2")
    )
    hw_events_stats["learned"] = hw_events_stats.apply(is_learned, axis=1)
    hw_events_stats["laglearned"] = hw_events_stats.groupby(["hw"], as_index=False)[
        "learned"
    ].shift(1)
    hw_events_stats["netlearned"] = hw_events_stats.apply(get_net_learned, axis=1)

    hw_events_stats_file = os.path.join(
        config["frame_folder"], config["hw_events_stats_file"]
    )
    hw_events_stats.to_pickle(hw_events_stats_file)


if __name__ == "__main__":
    process(config)

