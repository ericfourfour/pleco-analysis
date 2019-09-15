"""
Downloads all of the new Pleco databases
"""

import os
import paramiko
import re

config = {
    "remote_host": "192.168.2.201",
    "remote_username": "pi",
    "remote_folder": "/home/pi/PlecoDatabase",
    "local_folder": "data",
    "db_folder_rx": r"^\d{4}-\d{2}-\d{2} \d{2}.\d{2}.\d{2}$",
}


def process(config):
    db_folder_rx = re.compile(config["db_folder_rx"])

    # Get local folders
    local_subfolders = list(
        filter(lambda f: db_folder_rx.match(f), os.listdir(config["local_folder"]))
    )

    # Connect to Remote
    with paramiko.SSHClient() as ssh_client:
        ssh_client.load_system_host_keys()
        ssh_client.connect(config["remote_host"], username=config["remote_username"])

        # Get remote folders
        _, stdout, _ = ssh_client.exec_command("ls {}".format(config["remote_folder"]))
        remote_subfolders = list(
            filter(
                lambda f: db_folder_rx.match(f),
                map(lambda f: f.strip(), stdout.readlines()),
            )
        )

        # Get new folders
        new_subfolders = list(
            filter(lambda f: f not in local_subfolders, remote_subfolders)
        )

        # Download new folders
        with ssh_client.open_sftp() as sftp_client:
            for f in new_subfolders:
                local_subfolder = os.path.join(config["local_folder"], f)
                if not os.path.exists(local_subfolder):
                    os.mkdir(local_subfolder)
                local_file = os.path.join(
                    local_subfolder, "Pleco Flashcard Database.pqb"
                )
                remote_file = "/{}/{}/Pleco Flashcard Database.pqb".format(
                    config["remote_folder"], f
                )
                sftp_client.get(remote_file, local_file)


if __name__ == "__main__":
    process(config)
