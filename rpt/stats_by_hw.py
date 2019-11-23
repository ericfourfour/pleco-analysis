import os
import pandas as pd
import pinyin
import pinyin.cedict

config = {"frame_folder": "frames", "hw_events_stats_file": "hw_events_stats.pickle"}


def get_stats_by_hw(
    config, start: pd.Timestamp = None, end: pd.Timestamp = None
) -> pd.DataFrame:

    stats_file = os.path.join(config["frame_folder"], config["hw_events_stats_file"])
    hw_stats = pd.read_pickle(stats_file)

    stats = hw_stats.copy()
    if start is not None:
        stats = stats[stats["revieweddate"] >= start].copy()
    if end is not None:
        stats = stats[stats["revieweddate"] < end].copy()

    first_review = stats.groupby(["hw"]).head(1).reset_index().set_index("hw").copy()
    last_review = stats.groupby(["hw"]).tail(1).reset_index().set_index("hw").copy()

    first_change = (
        stats[stats["netlearned"] != 0]
        .groupby(["hw"])
        .head(1)
        .reset_index()
        .set_index("hw")
        .copy()
    )
    last_change = (
        stats[stats["netlearned"] != 0]
        .groupby(["hw"])
        .tail(1)
        .reset_index()
        .set_index("hw")
        .copy()
    )

    rpt = pd.DataFrame({"reviewed": stats.groupby(["hw"]).size().astype("u2")})

    rpt["firstreviewed"] = first_review["revieweddate"]
    rpt["lastreviewed"] = last_review["revieweddate"]

    rpt["correct"] = stats.groupby(["hw"])[["result"]].sum().astype("u2")
    rpt["incorrect"] = stats.groupby(["hw"])[["invresult"]].sum().astype("u2")

    rpt["new"] = first_review["occurrence"].apply(lambda x: x == 0)
    rpt["knew"] = first_review["laglearned"].apply(lambda x: x == True)
    rpt["learned"] = first_change["netlearned"].apply(lambda x: x == 1)
    rpt["forgot"] = first_change["netlearned"].apply(lambda x: x == -1)

    rpt["knew"] = rpt["knew"].fillna(False)
    rpt["learned"] = rpt["learned"].fillna(False)
    rpt["forgot"] = rpt["forgot"].fillna(False)

    rpt["know"] = rpt.apply(
        lambda row: row["learned"] or (row["knew"] and not row["forgot"]), axis=1
    )

    rpt["pinyin"] = rpt.apply(lambda row: pinyin.get(row.name), axis=1)
    rpt["definition"] = rpt.apply(
        lambda row: pinyin.cedict.translate_word(row.name), axis=1
    )

    return rpt
