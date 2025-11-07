# main.py
import os, re, time, requests
from urllib.parse import quote
from flask import Flask, request, jsonify, make_response
from bs4 import BeautifulSoup

app = Flask(__name__)
BRAND = os.getenv("BRAND", "Kalyug")

# ---------- Stylish Landing Page ----------
INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Kalyug RC Lookup — Fast Vehicle Info</title>
  <meta name="description" content="RC lookup tool by Kalyug. Fetch vehicle details instantly."/>
  <link rel="icon" href="https://fav.farm/🚗"/>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .glass { background: rgba(4,7,17,.6); border: 1px solid rgba(148,163,184,.2); backdrop-filter: blur(10px); }
    .code { background: rgba(0,0,0,.55); }
  </style>
</head>
<body class="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white selection:bg-indigo-500/40">
  <div class="max-w-3xl mx-auto py-14 px-4">
    <header class="mb-10 text-center">
      <h1 class="text-4xl md:text-5xl font-extrabold">Kalyug <span class="text-indigo-400">RC Lookup</span></h1>
      <p class="mt-3 text-slate-300">Instant JSON vehicle details — powered by Kalyug.</p>
    </header>

    <div class="glass rounded-2xl p-6 shadow-2xl">
      <label class="block text-sm mb-2">Enter RC Number</label>
      <div class="flex gap-2">
        <input id="rc" placeholder="e.g. DL01AB1234"
               class="w-full px-4 py-3 rounded-xl bg-slate-900/70 border border-slate-700 outline-none focus:ring-2 focus:ring-indigo-500"/>
        <button id="go"
                class="px-5 py-3 rounded-xl bg-indigo-500 hover:bg-indigo-400 active:scale-95 transition font-semibold">Search</button>
      </div>
      <p id="msg" class="mt-3 text-sm text-slate-400"></p>
      <pre id="out" class="code mt-5 p-4 rounded-xl overflow-auto text-sm"></pre>
    </div>
  </div>

  <script>
    async function fetchRc() {
      const rc = document.getElementById('rc').value.trim()
      const msg = document.getElementById('msg')
      const out = document.getElementById('out')
      if(!rc){ msg.textContent="Please enter RC number"; return }
      msg.textContent="Fetching..."
      out.textContent=""
      try {
        let r = await fetch(`/api/vehicle-info?rc=${encodeURIComponent(rc)}`)
        let d = await r.json()
        msg.textContent="Done!"
        out.textContent = JSON.stringify(d, null, 2)
      } catch(e){
        msg.textContent="Error"
        out.textContent = e.toString()
      }
    }
    document.getElementById('go').onclick = fetchRc
    document.getElementById('rc').onkeydown = e => { if(e.key==="Enter") fetchRc() }
  </script>
</body>
</html>
"""

# ---------- Scraper ----------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0)",
    "Referer": "https://vahanx.in/",
}

def _find_text(soup, label):
    try:
        span = soup.find("span", string=lambda s: s and s.strip().lower()==label.lower())
        if span:
            p = span.find_parent("div").find("p")
            return p.get_text(strip=True)
    except:
        pass
    return None

def _section_dict(soup, header_contains, keys):
    h3 = soup.find("h3", string=lambda s: s and header_contains.lower() in s.lower())
    card = h3.find_parent("div") if h3 else None
    out={}
    for k in keys:
        try:
            span = card.find("span", string=lambda s: s and k.lower() in s.lower())
            p = span.find_next("p") if span else None
            if p: out[k.lower().replace(" ", "_")] = p.get_text(strip=True)
        except: pass
    return out

def get_vehicle_details(rc):
    url = f"https://vahanx.in/rc-search/{quote(rc)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except Exception as e:
        return {"error": str(e), "powered_by": BRAND}

    soup = BeautifulSoup(r.text, "html.parser")
    reg = soup.find("h1").get_text(strip=True) if soup.find("h1") else rc

    def card(x):
        for div in soup.select(".hrcd-cardbody"):
            span = div.find("span")
            if span and x.lower() in span.text.lower():
                p = div.find("p")
                return p.get_text(strip=True)
        return None

    modal = card("Model Name") or _find_text(soup, "Model Name")
    owner = card("Owner Name") or _find_text(soup, "Owner Name")
    city  = card("City Name")  or _find_text(soup, "City Name")

    data = {
        "registration_number": reg,
        "status": "success",
        "powered_by": BRAND,
        "basic_info": {
            "model_name": modal,
            "owner_name": owner,
            "city": city
        }
    }
    return data

# ---------- Routes ----------
@app.get("/")
def home():
    r = make_response(INDEX_HTML,200)
    r.headers["Content-Type"]="text/html"
    return r

@app.get("/api/vehicle-info")
def api_vehicle():
    rc = request.args.get("rc","").strip().upper()
    if not rc:
        return jsonify({"error":"Missing rc","powered_by":BRAND}),400
    data = get_vehicle_details(rc)
    if "powered_by" not in data:
        data["powered_by"]=BRAND
    return jsonify(data)

@app.get("/health")
def health():
    return jsonify({"status":"ok","powered_by":BRAND})
