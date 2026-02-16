import multiprocessing
import time
#Custom
from database.database import Database
from server.server import Server
import logging
from datetime import datetime
import os

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

"""
 I want this file to EITHER take a config file (and generate a temp one) or accept args / envvars to configure server
 I also want to setup required directory structure here before app starts
"""

"""
What does this file do currently? 
    - Setup database files and structures
        uses database class to init file structures.  
    - Setup web_root file structure
        done using the Builder init.
    - Start scheduled tasks
        done using scrub_loop and multiprocessing
    - Start webserver

What do I want this to do? 
    - Read envvars / config file to:
        - Use argparse 
        - determine where the app is located on the FS
            - base path
                - build if needed
        - Check and build out required file structures and database file
            - db_path
                - build if needed
            - db_name
        - check if admin_user and admin_pass is set
            yes? pass to db_init
            no? let db check if prior admin has been created
    - Initialize database:
        - if database doesn't exist, create file structures to house it
        - Check if admin exists 
            if yes, check if admin_pass is same
                if not create new admin and remove old
        - Add admin user based on admin cred if not 
        - Initalize database tables
    - Setup scheduled tasks:
        - Currently cron isn't used. Do we put loop in that file OR remove it entirely.
        - database table scrubs
        - Stale file cleanup
    - Start Webserver:
        - I want webserver to take database object instead of creating a new instance every use
            - provides a single init
        

"""


def check_envvars() -> bool:
    try:
        base_path = os.environ['base_path']
        logger.debug(f"Found base_path: {base_path}")
    except KeyError as e:
        logger.error("base_path wasn't found, quitting.")
        return False
    try:
        os.environ['admin_cred']
        logger.debug(f"admin_cred is set")
    except KeyError as e:
        logger.error("admin_cred wasn't found, exiting")
        return False
    try:
        db_path = os.environ['db_path']
        logger.debug(f"found db_path: {db_path}")
    except KeyError as e:
        logger.debug("db_path wasn't set, using default value")
    try:
        db_name = os.environ['db_name']
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
    pass

"""
file structure:
<path_to_c2-base>/
    /files
        /pre/
        /post/
        /stale/
"""

def build_dirs(base_path, db_path) -> bool:
    """
    verify base_path exists. If db_path doesn't exist, build it 
    """
    # if base_path doesn't exist, then we have issues. 

    pass


"""
 - Set up background jobs to clean up stale database entries.
"""

def scrub_loop(db):
    # This loop looks ugly, can it be cleaned up?
    logger.debug("scrub_loop start")
    scrubS = multiprocessing.Process(target=db.scrub_table, args=("sessions",))
    scrubZ = multiprocessing.Process(target=db.scrub_table, args=("zombies",))
    scrubC = multiprocessing.Process(target=db.scrub_table, args=("commands",))
    scrubD = multiprocessing.Process(target=db.scrub_table, args=("data",))
    # print("SCRUB_LOOP => starting scrub workers")
    scrubZ.start()
    scrubS.start()
    scrubC.start()
    scrubD.start()
    scrubZ.join()
    scrubS.join()
    scrubC.join()
    scrubD.join()
    # print("SCRUB_LOOP => scrub should be done now")
    loop = multiprocessing.Process(target=scrub_loop,args=(db,))
    # print("SCRUB_LOOP => now sleeping 300")
    time.sleep(30)
    # print("SCRUB_LOOP => starting loop again")
    loop.start()
    loop.join()

def init_server():

    # envvars required so far: base_path, db_name, db_path, admin_cred
    db = Database()
    # Build workers to periodically scrub tables.
    scrub = multiprocessing.Process(target=scrub_loop, args=(db,))
    scrub.start()
    print("Started scrub loop")
    # Setup Database and start app
    res = db.init()
    print("Database has been init!")
    if res is False:
        # print("FATAL ERROR, COULDN'T INIT DB")
        exit()
    else:
        # Handle setting up the flask app
        app = Server()
        print("Now running app!")
        app.run()


if __name__ == "__main__":
    if (check_envvars()):
        init_server()
    else:
        put_help()
        exit()
    #app.run(port=8080)
