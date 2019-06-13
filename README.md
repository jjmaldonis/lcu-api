# lcu-api

This is a (currently un-named) API for working with the League of Legends LCU.

## Usage

There are two ways to use this API.

First, you can make requests directly to the LCU client. You simply input the URI that you want to get data from (or send data to). You can send `GET`, `POST`, and `DELETE` requests manually, by calling, for example `lcu.get(...)`.

Second, you can set the `lcu-api` to passively listen for any events that occur in the client (and there are a lot of them). For example, you can listen for your summoner to enter champion select. This API is more complicated to use because you need to write `EventProcessor` classes that handle events as they are passively sent to this LCU connector. The `usage.py` file has a simple example.

## Example

```python

# Create the LCU object. Make sure the client is open on your computer.
lcu = LCU()

# Optionally attach `EventProcessor` classes to handle incoming events. See usage.py
#lcu.attach_event_processor(...)

lcu.wait_for_client_to_open()
lcu.wait_for_login()

# Open a background thread and listen for & process incoming events
# using the EventProcessors that were attached to the LCU (not shown here, see usage.py).
lcu.process_event_stream()

# Here is an example request to get data from the LCU
finished = lcu.get('/lol-platform-config/v1/initial-configuration-complete')
print("Has the client finished it's starting up?", finished)

...  # Make more requests to the LCU if you want.

# Prevent this program from exiting so that the event stream continues to be read.
# Press Ctrl+C (and wait for another event to get triggered by the LCU) to gracefully terminate the program.
lcu.wait()

```
