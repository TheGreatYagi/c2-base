import secrets
from base64 import b64decode
import logging
from datetime import datetime
from pathlib import Path
from os import remove

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

    def get_pre_files_count(self):
        pre = self.home / "pre"
        files = [x for x in pre.iterdir()]
        return len(files)

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
            token = str(self.get_pre_files_count() + 1)
            path = pre / token
            logger.debug(f"NOW OPENING: {path}")
            try:
                with open(path,'a') as f:
                    res = f.write(data)
                    #res = f.write(data.decode('utf-8'))
                    logger.debug(f"saved {res} bytes")
                    self.files.append(path)
                    f.close()
                    return True
            except FileNotFoundError as e:
                logger.debug("Trying alt")
                with open(path,"w") as f:
                    res = f.write(data)
                    #res = f.write(data.decode('utf-8'))
                    logger.debug(f"Saved {res} bytes")
                    self.files.append(path)
                    f.close()
                    return True  
        except Exception as e:
            logger.error(f"E1: UNABLE TO WRITE CHUNK: {data[0:10]} for reason: {e}")
            return False
        # else:
        #     print(f"WRITE_CHUNK => E2: UNABLE TO WRITE CHUNK: {data}")
        #     return False
    
    """
    - Process all chunk files in <zombieID>/pre and rebuild them as one final file in <zombieID>/post
    """
    def process_file(self, zombieID:str):
        post = self.home / "post"
        pre = self.home / "pre"
        prefiles = [x for x in pre.iterdir()]
        prefiles.sort()
        token = secrets.token_hex(15)
        postfile_path = post / token
        file_num = self.get_pre_files_count()
        chunks = []
        # first read all chunk files into memory

        for file in prefiles:
            with open(file,'r') as f:
                chunks.append(f.read())
                f.close()
        logger.debug(f"now read {file_num} chunks into memory")

        # clean chunks
        clean = ""
        for chunk in chunks:
            clean = clean + chunk.split(":")[1]
        logger.debug(f"Cleaned chunk, combined size: {len(clean)}")

        # decode data and save to post
        data_enc = b64decode(clean)
        logger.debug(f"data_enc is of type {type(data_enc)}")
        logger.debug(f"first bytes: {data_enc[0:8]}")
        #data_raw = data_enc.decode('utf-8')
        logger.debug(f"raw data processed, now saving to {postfile_path}")
        with open(postfile_path, 'wb') as f:
            num = f.write(data_enc)
            f.close()
        logger.debug(f"file saved! Wrote: {num}")

        # clean up pre files
        logger.debug(f"now removing pre files: {prefiles}")
        for prefile in prefiles:
            try:
                remove(prefile)
            except Exception as e:
                logger.error(f"couldn't remove prefile {prefile} due to: {e}")
        return token


        # Now parse chunks
        # pre = self.files.pop()
        # post = self.home / "post"
        # token = secrets.token_hex(6)
        # postfile = post / token
        # with open(pre,"r") as f:
        #     pre_file = f.read()
        #     f.close()
        # #prefile should now contain all chunks recieved from client
        #     # - need to split and decode each chunk before writting
        # #print(f"PROCESS_FILE => preprocessed data found: {pre_file}")
        # chunks = pre_file.split("CHUNK:")[0:]
        # logger.debug(f"FOUND CHUNKS: {len(chunks)}")
        # data = "" 
        # logger.debug(f"DECODED DATA, WRITTING")
        # try:
        #     for chunk in chunks:
        #         logger.debug(f"in for loop, chunk len: {len(chunk)}")
        #         enc = b64decode(chunk)
        #         data += enc.decode('utf-8')
        #     with open(postfile,"a") as f:
        #         f.write(data)
        #         f.close()
        # except Exception as e:
        #     logger.error(f"ERROR, COUDLN'T DECODE: {e}")
        #     logger.debug(f"SAVING RAW CHUNKS.....")
        #     with open(postfile,"w") as f:
        #         f.write(pre_file)
        #         f.close()     
        # #print(f"PROCESS_FILE => now saving pre_file data to {postfile}")
        # try:
        #     try:
        #         logger.debug(f"now removing {pre}")
        #         remove(pre)
        #         return token
        #     except:
        #         logger.error(f"Couldn't delete file: {pre}")
        #         #logger.debug("BACKING UP AND DELETING")
        #         #files = './files'
        #         #Rename files directory and move out of way to be recreated by server
        #         #rename(files,f"./files-{token}")
        #         #remove(self.pre)
        #         return None
        # except Exception as e:
        #     logger.error(f"UNABLE TO FAIL SAFELY: {e}")
        #     return None
        
    
