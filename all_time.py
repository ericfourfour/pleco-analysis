import matplotlib.pyplot as plt
import os
import pandas as pd

from rpt.stats_by_date import get_stats_by_date
from rpt.stats_by_hw import get_stats_by_hw

config = {
    "frame_folder": "frames",
    "hw_events_stats_file": "hw_events_stats.pickle",
    "image_folder": "images",
    "image_prefix": "all_time",
}


def plot_all_time_report(config):
    report = get_stats_by_date(config)[
        ["reviewed", "new", "netlearned", "cumnew", "cumnetlearned"]
    ].copy()

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
    plt.xticks(rotation=30)

    image_path = os.path.join(
        config["image_folder"],
        "{}_{}.png".format(
            config["image_prefix"], pd.Timestamp.today().strftime("%Y%m%d")
        ),
    )

    plt.savefig(image_path)


if __name__ == "__main__":
    plot_all_time_report(config)

