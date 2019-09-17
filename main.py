import datetime as dt
import matplotlib.pyplot as plt
import pandas as pd
from rpt.stats_by_date import get_stats_by_date
from rpt.stats_by_hw import get_stats_by_hw

config = {"frame_folder": "frames", "hw_events_stats_file": "hw_events_stats.pickle"}


def all_time_report():
    report = get_stats_by_date(config)

    charts = report.plot.line()
    plt.axhline(0, color="white", linewidth=0.1, zorder=1)
    plt.axvspan(
        pd.to_datetime("2017-04-29"),
        pd.to_datetime("2017-05-13"),
        color="red",
        label="China Trip",
    )
    charts.axvline(
        pd.to_datetime("2018-09-02"), color="blue", linestyle="--", lw=2, label="SRS"
    )
    charts.axvline(
        pd.to_datetime("2018-07-31"),
        color="purple",
        linestyle="--",
        lw=2,
        label="TELUS",
    )
    charts.axvline(
        pd.to_datetime("2019-01-30"),
        color="green",
        linestyle="--",
        lw=2,
        label="Daily Backups",
    )
    charts.axvline(
        pd.to_datetime("2019-02-20"),
        color="purple",
        linestyle="--",
        lw=2,
        label="TELUS Restructuring",
    )
    plt.xticks(rotation=90)


def weekly_vocab_report():
    report = get_stats_by_hw(
        config, dt.datetime.today() - pd.DateOffset(7, "D"), pd.Timestamp.today()
    )
    print(report.to_string())


weekly_vocab_report()
