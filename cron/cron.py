import sched
import time
import logging
from datetime import datetime

"""
- Methods that allow us to check on zombie and session validity
"""

logger = logging.getLogger("c2_server")
logging.basicConfig(level=logging.DEBUG, handlers=[
                        logging.FileHandler(f"c2_dev-{datetime.now().strftime('%Y%m%d_%H%S')}.log"),
                        logging.StreamHandler()
                    ], format="%(asctime)s || %(name)s->%(funcName)s:%(levelname)s => %(message)s    "
                    )


#print(f"[???] in cron/cron.py, name is: {__name__}")


class Cron():
    s = ""

    def __init__(self):
        self.s = sched.scheduler(time.time, time.sleep)
        return

    def scrub(self,table:str):
        if table == "sessions":
            print("found sessions",flush=True)
            return
        elif table == "zombies":
            print("found zombies",flush=True)
            return
        else:
            print("nope",flush=True)
            return

    def loop(self):
        print("Now in loop",flush=True)
        self.s.enter(5, 10, self.scrub, ("sessions",))
        self.s.enter(5, 10, self.scrub, ("zombies",))
        print("registering loop to keep going",flush=True)
        self.s.enter(25, 10, self.loop)
        return
    
    def run(self):
        self.s.run()
