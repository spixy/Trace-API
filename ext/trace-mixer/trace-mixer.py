import argparse
import subprocess
import json


def parse_configuration(config_file):
    with open(config_file, "r") as f:
        raw = f.read()
        data = json.loads(raw)
    return data


def mix(base_file, mixed_file, output_file):
    command = ["mergecap", base_file, mixed_file, "-w", output_file]

    command_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = command_process.communicate()

    if stderr:
        raise Exception("Error occurred: %s" % stderr)


def run_mixer(base_file, output_file, config_file):
    config = parse_configuration(config_file)

    mix(base_file, config["mix_file"], output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Configuration file.", type=str, required=True)
    parser.add_argument("-b", "--base_file", help="Base pcap file", type=str, required=True)
    parser.add_argument("-o", "--output", help="Output file", type=str, required=True)
    args = parser.parse_args()

    run_mixer(args.base_file, args.output, args.config)
