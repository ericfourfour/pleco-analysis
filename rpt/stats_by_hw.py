import os
import pandas as pd
import pinyin
import pinyin.cedict

config = {"frame_folder": "frames", "hw_events_stats_file": "hw_events_stats.pickle"}


def get_stats_by_hw(config, start, end):

    stats_file = os.path.join(config["frame_folder"], config["hw_events_stats_file"])
    hw_stats = pd.read_pickle(stats_file)

    stats = hw_stats.loc[start:end].copy()
    stats

    rpt = pd.DataFrame({"reviewed": stats.groupby(["hw"]).size().astype("u2")})
    net_learned = stats.groupby(["hw"])["netlearned"].sum()
    rpt["new"] = (
        stats.reset_index().groupby(["hw"])["occurrence"].min().apply(lambda x: x == 0)
    )
    rpt["learned"] = net_learned.apply(lambda x: x == 1)
    rpt["forgot"] = net_learned.apply(lambda x: x == -1)

    rpt["pinyin"] = rpt.apply(lambda row: pinyin.get(row.name), axis=1)
    rpt["definition"] = rpt.apply(
        lambda row: pinyin.cedict.translate_word(row.name), axis=1
    )

    return rpt
