from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
import httpx
from urllib.parse import urljoin
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
            min-height:100vh;
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

let currentUrl = "";

async function go(){

    let url = document.getElementById("url").value;

    if(!url.startsWith("http")){
        url =
            "https://www.google.com/search?q=" +
            encodeURIComponent(url);
    }

    await load(url);
}

async function load(url){

    currentUrl = url;

    document.getElementById("url").value = url;

    const r = await fetch(
        "/browse?url=" + encodeURIComponent(url)
    );

    const html = await r.text();

    document.getElementById("page").innerHTML = html;
}

document.addEventListener("click", async (e) => {

    const a = e.target.closest("a");

    if(!a) return;

    const href = a.href;

    if(!href) return;

    if(
        href.startsWith("javascript:") ||
        href.startsWith("mailto:") ||
        href.startsWith("tel:")
    ){
        return;
    }

    e.preventDefault();

    await load(href);
});

document.addEventListener("submit", async (e) => {

    e.preventDefault();

    const form = e.target;

    const action = form.action || currentUrl;

    const method =
        (form.method || "GET").toUpperCase();

    const data = new FormData(form);

    if(method === "GET"){

        const params = new URLSearchParams(data);

        await load(
            action + "?" + params.toString()
        );

    }else{

        const r = await fetch(
            "/browse?url=" +
            encodeURIComponent(action),
            {
                method:"POST",
                body:data
            }
        );

        const html = await r.text();

        document.getElementById("page").innerHTML =
            html;
    }
});

</script>

</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HOME


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.api_route(
    "/browse",
    methods=["GET", "POST"]
)
async def browse(request: Request, url: str):

    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/122 Safari/537.36"
    }

    try:

        async with httpx.AsyncClient(
            follow_redirects=True,
            verify=False
        ) as client:

            if request.method == "POST":

                form = await request.form()

                r = await client.post(
                    url,
                    data=form,
                    headers=headers,
                    timeout=30
                )

            else:

                r = await client.get(
                    url,
                    headers=headers,
                    timeout=30
                )

        content_type = r.headers.get(
            "content-type",
            ""
        )

        if "text/html" not in content_type:

            return Response(
                content=r.content,
                media_type=content_type
            )

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        base_url = str(r.url)

        # corrige assets
        assets = {
            "a":"href",
            "img":"src",
            "script":"src",
            "iframe":"src",
            "link":"href",
            "video":"src",
            "audio":"src",
            "source":"src",
            "form":"action"
        }

        for tag, attr in assets.items():

            for t in soup.find_all(tag):

                if t.get(attr):

                    t[attr] = urljoin(
                        base_url,
                        t[attr]
                    )

        # remove CSP
        for meta in soup.find_all("meta"):

            http_equiv = (
                meta.get(
                    "http-equiv",
                    ""
                ).lower()
            )

            if http_equiv in [
                "content-security-policy",
                "x-frame-options",
                "cross-origin-opener-policy",
                "cross-origin-embedder-policy",
                "cross-origin-resource-policy"
            ]:
                meta.decompose()

        return HTMLResponse(str(soup))

    except Exception as e:

        return HTMLResponse(f"""
        <html>
        <body style="
            background:#111;
            color:white;
            font-family:Arial;
            padding:30px;
        ">
            <h1>Erro</h1>
            <pre>{e}</pre>
        </body>
        </html>
        """)