import os
import pandas as pd

config = {
    "frame_folder": "frames",
    "card_events_file": "card_events.pickle",
    "hw_events_file": "hw_events.pickle",
}


def process(config):
    card_events_file = os.path.join(config["frame_folder"], config["card_events_file"])

    card_events = pd.read_pickle(card_events_file)
    card_events.reset_index()

    hw_events = (
        card_events.reset_index()[["hw", "reviewedtime", "result"]]
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
