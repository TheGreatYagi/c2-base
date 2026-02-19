import multiprocessing
import time
#Custom
from database.database import Database
from server.server import Server
import logging
from datetime import datetime
from os import environ
from pathlib import Path


logger = logging.getLogger("c2_server")
logging.basicConfig(level=logging.DEBUG, handlers=[
                        logging.FileHandler(f"c2_dev-{datetime.now().strftime('%Y%m%d_%H%S')}.log"),
                        logging.StreamHandler()
                    ], format="%(asctime)s || %(name)s->%(funcName)s:%(levelname)s => %(message)s    "
                    )
#
#print(f"[???] in c2_server.py, name is: {__name__}")
# This disables the majority of flask logs
flask_log = logging.getLogger('werkzeug')
flask_log.setLevel(logging.ERROR)



def check_envvars() -> bool:
    try:
        base_path = environ['base_path']
        logger.debug(f"Found base_path: {base_path}")
    except KeyError as e:
        logger.error("base_path wasn't found, quitting.")
        return False
    try:
        environ['admin_cred']
        logger.debug(f"admin_cred is set")
    except KeyError as e:
        logger.error("admin_cred wasn't found, exiting")
        return False
    try:
        db_path = environ['db_path']
        logger.debug(f"found db_path: {db_path}")
    except KeyError as e:
        logger.debug("db_path wasn't set, using default value")
    try:
        db_name = environ['db_name']
        logger.debug(f"Found db_name: {db_name}")
    except KeyError as e:
        logger.debug("db_name wasn't set, using default value")
    return True
    
def put_help() -> None:
    """
    - prints out the required envvars
    """
    print("The following envvars are required: ")
    print("REQUIRED: base_path => full path to webserver files")
    print("REQUIRED: admin_cred => cred for admin user")
    print("OPTIONAL: db_path => path to database file, defaults to base_path")
    print("OPTIONAL: db_name => file to name database, defaults to database.db")

"""
 - Set up background jobs to clean up stale database entries.
"""

def scrub_loop(db):
    """
    Continuously scrubs database tables in parallel and then recurses.
    """
    tables_to_scrub = ["sessions", "zombies", "commands", "data"]
    processes = []

    for table in tables_to_scrub:
        process = multiprocessing.Process(target=db.scrub_table, args=(table,))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    time.sleep(30)
    loop = multiprocessing.Process(target=scrub_loop, args=(db,))
    loop.start()
    loop.join()


if __name__ == "__main__":
    if (check_envvars()):
        db = Database()
        scrub = multiprocessing.Process(target=scrub_loop, args=(db,))
        scrub.start()
        logger.debug("Started scrub loop")
        if db.init():
            base_dir = environ['base_dir']
            app = Server(base_dir)
            logger.debug("Launching Flask!")
            app.run()
        else:
            logger.error("Couldn't init db. Exiting...")
            exit()
    else:
        put_help()
        exit()
    #app.run(port=8080)
