from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime
import json
import re

UPLOADS = Path.home() / "camera-lab-v2" / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)

HTML = """<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Security Lab</title>
<style>
body{background:#080b10;color:white;font-family:Arial;text-align:center;padding:25px}
.box{max-width:650px;margin:auto;background:#111820;padding:25px;border-radius:16px}
button{padding:12px;margin:6px;border:0;border-radius:8px}
video{width:100%;margin-top:15px;background:#000;border-radius:12px}
#log{text-align:left;margin-top:15px}
</style>
</head>
<body>
<div class="box">
<h1>SECURITY VERIFICATION LAB</h1>
<p>Authorized educational test</p>
<h3 id="status">Waiting...</h3>

<button onclick="hit()">START TEST</button>
<button onclick="camera()">CAMERA TEST</button>
<button id="capture" onclick="capture()" disabled>CAPTURE</button>
<button onclick="files.click()">SELECT FILES</button>

<input id="files" type="file" multiple hidden>
<video id="video" autoplay playsinline></video>
<div id="log"></div>
</div>

<script>
window.addEventListener("load", async () => {
    document.getElementById("status").textContent =
        "TARGET HIT — CLIENT CONNECTED";
    show("TARGET HIT — CLIENT CONNECTED");
    await event("target_hit");
});

const video=document.getElementById("video");
const status=document.getElementById("status");
const log=document.getElementById("log");
const files=document.getElementById("files");
let stream;

function show(x){
 log.innerHTML+="<div>"+new Date().toLocaleTimeString()+" — "+x+"</div>";
}

async function event(type,data={}){
 await fetch("/event",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({type,...data})
 });
}

async function hit(){
 status.textContent="TARGET HIT";
 show("TARGET HIT");
 await event("target_hit");
}

async function camera(){
 try{
  stream=await navigator.mediaDevices.getUserMedia({
   video:true,
   audio:false
  });
  video.srcObject=stream;
  document.getElementById("capture").disabled=false;
  status.textContent="CAMERA PERMISSION GRANTED";
  show("CAMERA PERMISSION: GRANTED");
  await event("camera_permission_granted");
 }catch(e){
  status.textContent="CAMERA ERROR";
  show("CAMERA ERROR: "+e.message);
 }
}

async function capture(){
  if(!stream) return;
  await video.play();
  await new Promise(r => {
    if(video.readyState >= 2 && video.videoWidth > 0) r();
    else video.addEventListener("loadeddata", r, {once:true});
  });
  if(!video.videoWidth || !video.videoHeight){
    show("VIDEO FRAME NOT READY");
    return;
  }
 if (!video.videoWidth || !video.videoHeight) {
    await new Promise(resolve => {
        video.onloadedmetadata = () => resolve();
    });
}

const c=document.createElement("canvas");
c.width=video.videoWidth;
c.height=video.videoHeight;
 c.getContext("2d").drawImage(video,0,0);
 const blob=await new Promise(r=>c.toBlob(r,"image/jpeg",.9));
 const fd=new FormData();
 fd.append("file",blob,"capture.jpg");

 const r=await fetch("/upload",{method:"POST",body:fd});
 const j=await r.json();

 status.textContent="CAPTURE RECEIVED";
 show("CAPTURE: "+j.name+" ("+j.size+" bytes)");
}

files.onchange=async()=>{
 for(const file of files.files){
  show("FILE SELECTED: "+file.name);

  const fd=new FormData();
  fd.append("file",file,file.name);

  const r=await fetch("/upload",{method:"POST",body:fd});
  const j=await r.json();

  show("FILE RECEIVED: "+j.name+" ("+j.size+" bytes)");
 }
};
</script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):

    def log_message(self,*args):
        pass

    def send_json(self,data):
        raw=json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path in ["/","/index.html"]:
            raw=HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.send_header("Content-Length",str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        else:
            self.send_error(404)

    def do_POST(self):
        length=int(self.headers.get("Content-Length","0"))
        body=self.rfile.read(length)

        if self.path=="/event":
            try:
                data=json.loads(body)
            except:
                data={}
            now=datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] {data.get('type','EVENT').upper()}")
            self.send_json({"ok":True})
            return

        if self.path=="/upload":
            ctype=self.headers.get("Content-Type","")
            match=re.search(r'boundary="?([^";]+)',ctype)

            if not match:
                self.send_json({"ok":False})
                return

            boundary=("--"+match.group(1)).encode()
            parts=body.split(boundary)

            for part in parts:
                if b'filename="' not in part:
                    continue

                head,data=part.split(b"\r\n\r\n",1)

                match=re.search(
                    rb'filename="([^"]*)"',
                    head
                )

                name=(
                    match.group(1).decode(errors="ignore")
                    if match else "received.bin"
                )

                data=data.rstrip(b"\r\n-")

                name=Path(name).name
                output=UPLOADS/name
                output.write_bytes(data)

                now=datetime.now().strftime("%H:%M:%S")
                print(
                    f"[{now}] FILE RECEIVED | "
                    f"{name} | {len(data)} bytes"
                )

                self.send_json({
                    "ok":True,
                    "name":name,
                    "size":len(data)
                })
                return

            self.send_json({"ok":False})
            return

        self.send_error(404)

print("[+] CAMERA SECURITY LAB v2")
print("[+] http://127.0.0.1:9000")
print("[+] uploads:",UPLOADS)

ThreadingHTTPServer(
    ("0.0.0.0",9000),
    Handler
).serve_forever()
