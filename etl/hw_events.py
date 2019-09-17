import os
import pandas as pd

config = {
    "frame_folder": "frames",
    "events_file": "history.pickle",
    "hw_events_file": "hw_history.pickle",
}


def process(config):
    events_file = os.path.join(config["frame_folder"], config["events_file"])

    events = pd.read_pickle(events_file)
    events.reset_index()

    hw_events = (
        events.reset_index()[["hw", "reviewedtime", "result"]]
        .sort_values(by=["hw", "reviewedtime", "result"])
        .reset_index(drop=True)
    )
    hw_events["occurrence"] = hw_events.groupby(["hw"]).cumcount()
    hw_events.set_index(
        ["hw", "occurrence"], drop=True, inplace=True, verify_integrity=True
    )

    hw_events_file = os.path.join(config["frame_folder"], config["hw_events_file"])
    hw_events.to_pickle(hw_events_file)


if __name__ == "__main__":
    process(config)
