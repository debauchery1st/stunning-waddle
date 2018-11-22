#!/bin/env python
import sys
import io
from twisted.logger import (
    eventsFromJSONLogFile, textFileLogObserver
)

output = textFileLogObserver(sys.stdout)

if __name__ == "__main__":
    try:
        f = sys.argv[1]
        for event in eventsFromJSONLogFile(io.open(f)):
            output(event)
    except IndexError as e:
        print("EXAMPLE: python view_log.py ./log.json")
    except Exception as e:
        raise e
