import os
import pandas as pd

config = {"frame_folder": "frames", "hw_events_stats_file": "hw_events_stats.pickle"}


def get_stats_by_date(config, start=None, end=None):
    stats_file = os.path.join(config["frame_folder"], config["hw_events_stats_file"])
    hw_stats = pd.read_pickle(stats_file)

    stats = hw_stats.loc[start:end].copy()

    rpt = pd.DataFrame(
        {"reviewed": stats.groupby(["revieweddate"]).size().astype("u2")}
    )
    rpt["new"] = hw_stats.query("occurrence == 0").groupby(["revieweddate"]).size()
    rpt["learned"] = hw_stats.query("learned == 1").groupby(["revieweddate"]).size()
    rpt["forgot"] = hw_stats.query("learned == -1").groupby(["revieweddate"]).size()
    rpt["netlearned"] = hw_stats.groupby(["revieweddate"])["netlearned"].sum()

    rpt["new"] = rpt["new"].fillna(0).astype("u2")
    rpt["learned"] = rpt["learned"].fillna(0).astype("u2")
    rpt["forgot"] = rpt["forgot"].fillna(0).astype("u2")
    rpt["netlearned"] = rpt["netlearned"].fillna(0).astype("i2")

    rpt["cumnew"] = rpt["new"].cumsum()
    rpt["cumnetlearned"] = rpt["netlearned"].cumsum()

    rpt["cumnew"] = rpt["cumnew"].fillna(0).astype("u2")
    rpt["cumnetlearned"] = rpt["cumnetlearned"].fillna(0).astype("i2")

    return rpt
