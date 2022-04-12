from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path
from time import sleep

from dateutil.tz import UTC
from ics import Calendar, Event
from pypresence import Presence


def main() -> None:
    parser: ArgumentParser = ArgumentParser(prog="discord-cal",
                                            description="Publish your status on discord using data from an iCal calendar.")
    parser.add_argument("-i", "--id", dest="id", type=str, required=True,
                        help="The client ID of the Discord application.")
    parser.add_argument("-c", "--calendar", dest="cal", type=str, required=True,
                        help="The path to the iCal calendar.")
    parser.add_argument("-d", "--details", dest="details", action='store_const', const=True, default=False,
                        help="If set, the event details will be included in the status message.")
    args: Namespace = parser.parse_args()

    path_of_cal: Path = Path(args.cal)

    with open(path_of_cal) as fp:
        cal: Calendar = Calendar(fp.read())

    rpc: Presence = Presence(args.id)

    rpc.connect()
    print("Connected to Discord.")

    try:
        while True:
            processing_at: datetime = datetime.utcnow().replace(tzinfo=UTC)

            current_events: list[Event] = [
                event
                for event
                in sorted(cal.events.copy(), key=lambda e: e.begin)
                if not event.all_day
            ]

            for current_event in current_events.copy():
                if current_event.end.datetime < processing_at:
                    current_events.remove(current_event)

            occuring_events: list[Event] = sorted(
                [
                    event
                    for event
                    in current_events
                    if event.begin.datetime < processing_at < event.end.datetime
                ],
                key=lambda e: e.end,
                reverse=True,
            )

            highlight_event: Event | None = None

            if occuring_events:
                highlight_event = occuring_events[-1]
            elif current_events:
                highlight_event = current_events[0]

            if highlight_event:
                if args.details:
                    rpc.update(
                        state=
                        f"{'Ongoing:' if highlight_event.begin.datetime < processing_at < highlight_event.end.datetime else 'Waiting for:'}"
                        f" {highlight_event.name}",
                        details=highlight_event.description,
                        start=highlight_event.begin.datetime.timestamp(),
                        end=highlight_event.end.datetime.timestamp(),
                    )
                else:
                    rpc.update(
                        state=
                        'Busy until' if highlight_event.begin.datetime < processing_at < highlight_event.end.datetime else 'Free until',
                        start=highlight_event.begin.datetime.timestamp(),
                        end=highlight_event.end.datetime.timestamp(),
                    )
            else:
                rpc.clear()

            sleep(30)
            print("Updated status.")
    finally:
        rpc.close()


if __name__ == "__main__":
    main()
