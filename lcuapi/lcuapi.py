import types
import os
import datetime
import requests
import time
import json
import abc
if os.name == 'nt':
    WINDOWS = True
    import base64
    import ssl
    import websockets
    import wmi
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
else:
    WINDOWS = False

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from exceptions import LCUClosedError, LCUDisconnectedError

VERBOSE = 1


class Event:
    def __init__(self, uri, data, created):
        self.uri = uri
        self.data = data
        self.created = created

    def __str__(self):
        return f"<Event: {self.uri}, {self.created} {self.data}>"


class EventProcessor(abc.ABC):
    @abc.abstractmethod
    def can_handle(self, event):
        pass

    @abc.abstractmethod
    def handle(self, event: Event):
        pass


class LCU:
    def __init__(self, *processors, verbose: bool = VERBOSE):
        self.verbose = verbose
        self._cache = {"TIMEOUT": {}}
        self._processors = []

        self.socket_url = 'wss://localhost'
        self.lcu_url = 'https://127.0.0.1'
        self.install_directory = None
        self.port = None
        self.auth_key = None
        self.connected = False

        try:
            if self.logged_in:
                self.connected = True
            else:
                self.connected = False
        except:
            self.connected = False

        for processor in processors:
            self.attach_event_processor(processor)

    def cache(self, endpoint: str, timeout: int):
        """Pass in an endpoint that you want to cache the results of.
        All calls to `lcu.get` will cache the result (and return the cached result) if the endpoint given to `lcu.get`
        starts with the endpoint (str) passed into this method.

        The `timeout` parameter specifies how long the data should be kept, in units of seconds.

        It is especially useful to cache summoner results to pull summoner names.
        Example:  lcu.cache('/lol-summoner/v1/summoners/', 60*5)  # Cache for 5 min, the ~ duration of a lobby
        """
        self._cache[endpoint] = {}
        self._cache["TIMEOUT"][endpoint] = timeout

    @staticmethod
    def _get_cmd_args():
        c = wmi.WMI()
        for process in c.Win32_Process():
            if process.name == 'LeagueClientUx.exe':
                cmd = process.CommandLine
                for segment in cmd.split('" "'):
                    if '--app-port' in segment:
                        port = int(segment.split('=')[1])
                    if '--install-directory' in segment:
                        install_directory = segment.split('=')[1]
                break
        else:
            raise LCUClosedError('The League client must be running!')
        return install_directory, port

    @staticmethod
    def _parse_lockfile(install_directory):
        fn = os.path.join(install_directory, 'lockfile')
        with open(fn) as f:
            content = f.read()
        content = content.split(':')
        process, PID, port, password, protocol = content
        PID = int(PID)
        port = int(port)
        return process, PID, port, password, protocol

    def _load_auth_key(self):
        process, PID, port, password, protocol = self._parse_lockfile(self.install_directory)
        if port != self.port:
            raise RuntimeError('Port changed!')
        auth_key = base64.b64encode(f'riot:{password}'.encode()).decode()
        return auth_key

    def _load_startup_data(self):
        """Sets self.install_directory, self.port and self.auth_key."""
        self.install_directory, self.port = self._get_cmd_args()
        self.auth_key = self._load_auth_key()
        return self.install_directory, self.port, self.auth_key

    def get(self, endpoint):
        # It will be hard to generalize this. I likely need the swagger because knowing what fields are parameters is otherwise impossible.

        to_cache_result = False
        for _endpoint in self._cache:
            if endpoint.startswith(_endpoint):
                to_cache_result = _endpoint
                try:
                    result, inserted = self._cache[_endpoint][endpoint]
                    if (time.time() - inserted) < self._cache["TIMEOUT"][_endpoint]:
                        return result
                    else:
                        self._cache[_endpoint].pop(endpoint)  # Remove it from the cache
                except KeyError:
                    pass

        if not self.connected:
            raise LCUDisconnectedError()
        try:
            r = requests.get(f'{self.lcu_url}:{self.port}{endpoint}',
                headers={'Accept': 'application/json', 'Authorization': f'Basic {self.auth_key}'},
                verify=False)
        except requests.exceptions.ConnectionError:
            # Get the current port and try again
            self._load_startup_data()
            r = requests.get(f'{self.lcu_url}:{self.port}{endpoint}',
                headers={'Accept': 'application/json', 'Authorization': f'Basic {self.auth_key}'},
                verify=False)
        result = r.json()

        if to_cache_result:
            self._cache[to_cache_result][endpoint] = (result, time.time())

        return result

    def post(self, endpoint, data: dict = None):
        if data is None:
            data = {}
        # It will be hard to generalize this. I likely need the swagger because knowing what fields are parameters is otherwise impossible.
        if not self.connected:
            raise LCUDisconnectedError()
        try:
            r = requests.post(f'{self.lcu_url}:{self.port}{endpoint}',
                data=data,
                headers={'Accept': 'application/json', 'Authorization': f'Basic {self.auth_key}'},
                verify=False)
        except requests.exceptions.ConnectionError:
            # Get the current port and try again
            self._load_startup_data()
            r = requests.post(f'{self.lcu_url}:{self.port}{endpoint}',
                data=data,
                headers={'Accept': 'application/json', 'Authorization': f'Basic {self.auth_key}'},
                verify=False)
        return r

    def delete(self, endpoint, data: dict = None):
        if data is None:
            data = {}
        # It will be hard to generalize this. I likely need the swagger because knowing what fields are parameters is otherwise impossible.
        if not self.connected:
            raise LCUDisconnectedError()
        try:
            r = requests.delete(f'{self.lcu_url}:{self.port}{endpoint}',
                data=data,
                headers={'Accept': 'application/json', 'Authorization': f'Basic {self.auth_key}'},
                verify=False)
        except requests.exceptions.ConnectionError:
            # Get the current port and try again
            self._load_startup_data()
            r = requests.delete(f'{self.lcu_url}:{self.port}{endpoint}',
                data=data,
                headers={'Accept': 'application/json', 'Authorization': f'Basic {self.auth_key}'},
                verify=False)
        return r

    def patch(self, endpoint, encoded_data: bytes = None):
        if encoded_data is None:
            encoded_data = b'{}'
        # It will be hard to generalize this. I likely need the swagger because knowing what fields are parameters is otherwise impossible.
        if not self.connected:
            raise LCUDisconnectedError()
        try:
            r = requests.patch(f'{self.lcu_url}:{self.port}{endpoint}',
                data=encoded_data,
                headers={'Accept': 'application/json', 'Authorization': f'Basic {self.auth_key}'},
                verify=False)
        except requests.exceptions.ConnectionError:
            # Get the current port and try again
            self._load_startup_data()
            r = requests.patch(f'{self.lcu_url}:{self.port}{endpoint}',
                data=encoded_data,
                headers={'Accept': 'application/json', 'Authorization': f'Basic {self.auth_key}'},
                verify=False)
        return r

    @property
    def logged_in(self):
        if not self.connected:
            return False
        #try:
        is_logged_in = self.get('/lol-platform-config/v1/initial-configuration-complete')
        return is_logged_in
        #except requests.exceptions.ConnectionError as error:
        #    print("Error in `logged_in`:", error)
        #    self.connected = False
        #    return False

    def __wait_for_client_to_open_from_lockfile(self, check_interval=3, timeout=float('inf')):
        import os
        import win32file
        import win32event
        import win32con

        retried = 0

        path_to_watch = os.path.join(self.install_directory)

        if "lockfile" in os.listdir(path_to_watch):
            return retried

        # FindFirstChangeNotification sets up a handle for watching
        #  file changes. The first parameter is the path to be
        #  watched; the second is a boolean indicating whether the
        #  directories underneath the one specified are to be watched;
        #  the third is a list of flags as to what kind of changes to
        #  watch for. We're just looking at file additions / deletions.
        change_handle = win32file.FindFirstChangeNotification (
            path_to_watch,
            0,
            win32con.FILE_NOTIFY_CHANGE_FILE_NAME
        )

        # Loop forever, listing any file changes. The WaitFor... will
        #  time out every N/1000 seconds allowing for keyboard interrupts
        #  to terminate the loop.
        try:
            old_path_contents = dict([(f, None) for f in os.listdir(path_to_watch)])
            while True:
                result = win32event.WaitForSingleObject(change_handle, check_interval*1000)

                # If the WaitFor... returned because of a notification (as
                #  opposed to timing out or some error) then look for the
                #  changes in the directory contents.
                if result == win32con.WAIT_OBJECT_0:
                    new_path_contents = dict([(f, None) for f in os.listdir(path_to_watch)])
                    added = [f for f in new_path_contents if not f in old_path_contents]
                    #deleted = [f for f in old_path_contents if not f in new_path_contents]
                    if "lockfile" in added:
                        time.sleep(1)  # Wait another second for the lockfile to be written to
                        break

                    old_path_contents = new_path_contents
                    win32file.FindNextChangeNotification(change_handle)
                retried += check_interval
                if retried > timeout:
                    raise TimeoutError(f"Timed out waiting for LCU to open. Waited for {retried} seconds.")
        finally:
            win32file.FindCloseChangeNotification(change_handle)
        return retried

    def __wait_for_client_to_open_from_process(self, check_interval=3, timeout=float('inf')):
        while True:
            retried = 0
            try:
                self._load_startup_data()
                break
            except LCUClosedError:
                time.sleep(check_interval)
            retried += check_interval
            if retried > timeout:
                    raise TimeoutError(f"Timed out waiting for user to login. Waited for {retried} seconds.")
        return retried

    def wait_for_client_to_open(self, check_interval=3, timeout=float('inf')):
        if self.install_directory is None:
            print("Waiting for LCU to open from process...")
            retried = self.__wait_for_client_to_open_from_process(check_interval=check_interval, timeout=timeout)
        if self.install_directory is not None:
            print("Waiting for LCU to open from lockfile...")
            retried = self.__wait_for_client_to_open_from_lockfile(check_interval=check_interval, timeout=timeout)
        self.connected = True
        self._load_startup_data()
        return retried

    def wait_for_login(self, wait_for_client_to_open=True, check_interval=3, timeout=float('inf')):
        if wait_for_client_to_open:
            retried = self.wait_for_client_to_open(check_interval=check_interval, timeout=timeout)
        else:
            retried = 0
        self._load_startup_data()
        logged_in = self.logged_in
        if not logged_in:
            print("Waiting for login...")
            while not self.logged_in:
                # Every once in a while we should check to see if the client has closed before the user logged in
                if retried > 0 and retried % (10 * check_interval) == 0:
                    if wait_for_client_to_open:
                        retried += self.wait_for_client_to_open(check_interval=check_interval, timeout=timeout)
                        print("Waiting for login...")
                time.sleep(check_interval)
                retried += check_interval
                if retried > timeout:
                    raise TimeoutError(f"Timed out waiting for user to login. Waited for {retried} seconds.")
        return retried

    # Websocket methods

    @staticmethod
    def parse_websocket_event(event):
        j = json.loads(event)
        assert 'OnJsonApiEvent' in j
        j = [x for x in j if isinstance(x, dict)]
        assert len(j) == 1
        event = j[0]
        timestamp = datetime.datetime.now().timestamp()
        uri = event.pop('uri')
        event = Event(uri=uri, data=event, created=timestamp)
        return event

    async def listen(self, thread):
        if not self.connected:
            raise LCUClosedError("Can't connect to the LCU.")

        print("Ready and waiting for updates!\n\n")

        async with websockets.connect(f'{self.socket_url}:{self.port}', ssl=ssl_context, extra_headers=[('Authorization', f'Basic {self.auth_key}')], max_size=2**32) as websocket:
            await websocket.send('[5, "OnJsonApiEvent"]')

            try:
                while not thread.kill_received:
                    # Wait for a new event
                    event_string = await websocket.recv()
                    if not event_string:
                        continue
                    # Process the event
                    event = self.parse_websocket_event(event_string)
                    self._process_event(event)
            except websockets.exceptions.ConnectionClosed as closed_error:
                self.connected = False
                raise LCUClosedError("LCU was closed.") from closed_error
            except KeyboardInterrupt:
                thread.kill_received = True
                return

    def process_event_stream(self, blocking=False):
        import asyncio
        if blocking:
            thread = types.SimpleNamespace()
            thread.kill_received = False  # A flag to notify the thread that it should finish up and exit
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.listen(thread))
        else:
            import threading

            def loop_in_thread(loop, thread):
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.listen(thread))
            loop = asyncio.get_event_loop()

            class Worker(threading.Thread):
                def __init__(self):
                    threading.Thread.__init__(self)
                    self.kill_received = False  # A flag to notify the thread that it should finish up and exit
                    self.setDaemon(True)
                def run(self):
                    loop_in_thread(loop, self)

            #thread = threading.Thread(target=loop_in_thread, args=(loop,))
            thread = Worker()
            self._event_stream_thread = thread
            thread.start()

    def stop_processing_event_stream(self):
        self._event_stream_thread.kill_received = True
        self._event_stream_thread.join()

    def wait(self):
        print("\n\nPress Ctrl+C (and wait for another event to get triggered by the LCU) to gracefully terminate your program.\n\n")
        try:
            import time
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop_processing_event_stream()

    def attach_event_processor(self, processor: EventProcessor):
        processor.lcu = self
        self._processors.append(processor)

    def _process_event(self, event: Event):
        for processor in self._processors:
            if processor.can_handle(event):
                processor.handle(event)

    def _mock_data_stream(self, filename):
        with open(filename) as f:
            for line in f.readlines():
                event = json.loads(line)
                event = Event(uri=event['uri'], data=event['data'], created=event['timestamp'])
                self._process_event(event)
