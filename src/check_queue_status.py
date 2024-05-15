import json
from argparse import ArgumentParser


def main():
    # Control printing colors
    RED = '\033[31m'
    YELLOW = '\033[33m'
    CYAN = '\033[36m'
    RESET = '\033[0m'

    # Load file locations from command line arguments
    parser = ArgumentParser()
    parser.add_argument("-q", "--queue", help="Download queue file location", default="./outputs/download_queue.json")
    args = parser.parse_args()

    with open(args.queue, "r", encoding="utf-8") as file:
        queue = json.load(file)

    for order_name in queue:
            order = queue[order_name]
            if not order["ordered"]:
                print(RED + order_name + RESET)
            elif order["ordered"] and not order["downloaded"]:
                print(YELLOW + order_name + RESET)
            elif order["downloaded"]:
                print(CYAN + order_name + RESET)
            else:
                print(RED + "Issue with" + order_name + RESET)


# If running script as standalone, run application
if __name__ == "__main__":
    main()
                