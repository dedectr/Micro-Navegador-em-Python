from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
import httpx
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup

app = FastAPI()

HOME = """
<!DOCTYPE html>
<html>
<head>
    <title>Mini Browser</title>

    <style>
        body{
            margin:0;
            background:#111;
            color:white;
            font-family:Arial;
        }

        #bar{
            display:flex;
            padding:10px;
            background:#222;
            gap:10px;
        }

        input{
            flex:1;
            padding:10px;
            border:none;
            border-radius:10px;
            background:#333;
            color:white;
            font-size:16px;
        }

        button{
            padding:10px 20px;
            border:none;
            border-radius:10px;
            background:#00aaff;
            color:white;
            cursor:pointer;
        }

        #page{
            width:100%;
            height:calc(100vh - 60px);
            border:none;
            background:white;
        }
    </style>
</head>
<body>

<div id="bar">
    <input id="url" placeholder="Pesquisar ou URL">
    <button onclick="go()">Ir</button>
</div>

<div id="page"></div>

<script>

async function go(){

    let url = document.getElementById("url").value;

    if(!url.startsWith("http")){
        url = "https://www.google.com/search?q=" + encodeURIComponent(url);
    }

    load(url);
}

async function load(url){

    let r = await fetch("/browse?url=" + encodeURIComponent(url));

    let html = await r.text();

    document.getElementById("page").innerHTML = html;

    intercept();
}

function intercept(){

    document.querySelectorAll("#page a").forEach(a => {

        a.onclick = (e) => {

            e.preventDefault();

            let href = a.href;

            if(href){
                load(href);
            }
        };
    });

    document.querySelectorAll("#page form").forEach(form => {

        form.onsubmit = async (e) => {

            e.preventDefault();

            let action = form.action || window.location.href;

            let data = new FormData(form);

            let params = new URLSearchParams(data);

            load(action + "?" + params.toString());
        };
    });
}

</script>

</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HOME


@app.get("/browse")
async def browse(url: str):

    headers = {
        "User-Agent":
        "Mozilla/5.0 Chrome/122 Safari/537.36"
    }

    async with httpx.AsyncClient(
        follow_redirects=True,
        verify=False
    ) as client:

        r = await client.get(
            url,
            headers=headers,
            timeout=30
        )

    content_type = r.headers.get("content-type", "")

    if "text/html" not in content_type:
        return Response(
            content=r.content,
            media_type=content_type
        )

    soup = BeautifulSoup(r.text, "html.parser")

    base_url = str(r.url)

    # corrige links
    for tag, attr in {
        "a":"href",
        "img":"src",
        "script":"src",
        "iframe":"src",
        "link":"href",
        "video":"src",
        "audio":"src",
        "source":"src"
    }.items():

        for t in soup.find_all(tag):

            if t.get(attr):

                t[attr] = urljoin(base_url, t[attr])

    # remove CSP
    for meta in soup.find_all("meta"):

        if meta.get("http-equiv", "").lower() in [
            "content-security-policy",
            "x-frame-options"
        ]:
            meta.decompose()

    return HTMLResponse(str(soup))