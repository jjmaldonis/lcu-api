from lcuapi import LCU, Event, EventProcessor


# EventProcessors are classes that handle/process different events.
# Create an EventProcessor by inherenting from the EventProcessor class.
# You then have to define two methods, "can_handle" and "handle".
class PrintSomeEventInfo(EventProcessor):

    # The "can_handle" method must return True and False.
    # Return True if this event handler can handle the event. Return False if not.
    def can_handle(self, event: Event):        
        if issubclass(event.__class__, Event):
            return True
        else:
            return False

    # The "handle" method defines the functionality of the handler.
    # This is where you write code to do something with the event.
    # In this example, I simply print out the URI of the event and the time at which it was created.
    # The only other attribute of an Event is: "event.data".
    def handle(self, event: Event):
        print(f"Event<uri={event.uri} created={event.created}>")


def main():
    # Create the LCU object.
    lcu = LCU()

    # Attach any event processors that we want to use to handle events.
    # You can also pass the event processors into the LCU object when you create it on the previous line.
    lcu.attach_event_processor(PrintSomeEventInfo())

    lcu.wait_for_client_to_open()
    lcu.wait_for_login()

    # Open a background thread and listen for + process events using the EventProcessors that were attached to the LCU.
    #lcu.process_event_stream()

    # Here is an example request to get data from the LCU.
    finished = lcu.get('/lol-platform-config/v1/initial-configuration-complete')
    print("Has the client finished it's starting up?", finished)

    # Prevent this program from exiting so that the event stream continues to be read.
    # Press Ctrl+C (and wait for another event to get triggered by the LCU) to gracefully terminate the program.
    #lcu.wait()


if __name__ == '__main__':
    main()