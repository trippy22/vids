import requests
from bs4 import BeautifulSoup
from retry import retry
import subprocess
import glob

IMDB_ID = '' # put imdb id, e.g: tt0773262

def call_cmd(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)

    while True:
        output = process.stdout.readline()
        if output == b'' and process.poll() is not None:
            break
        if output:
            print(output.decode('utf-8').strip())

    return_code = process.wait()
    print(f"Return code {return_code}")

def get_headers():
    h = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.8',
        'dnt': '1',
        'referer': 'https://v2.vidsrc.me/',
        'sec-ch-ua': '''"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"''',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': "Windows",
        'sec-fetch-dest': 'iframe',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-site',
        'sec-fetch-user': '?1',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
    }
    return h

def do_dl(output, url):
    new_url = url #requests.get(url, headers=get_headers())
    call_cmd(f'aria2c -c -s 16 -x 16 -k 1M -o {output}.mp4 -j 1 "{new_url}"')


def make_req(url):
    return requests.get(url, headers=get_headers()).text


def special_req(url):
    return requests.get(url, headers=get_headers())

@retry(tries=3, delay=5)
def handle_dl_saves(url, name):
    path = url.split('/')[-1]
    r = requests.post(f'https://vidsrc.xyz/api/source/{path}')
    if r.status_code == 200:
        r = r.json()
        data = r.get('data')
        for d in data:
            quality = d.get('label')
            if quality == '1080p':
                return d['file']
        for d in data:
            quality = d.get('label')
            if quality == '720p':
                return d['file']
    elif r.status_code == 429:
        raise Exception('429 Error: Too many requests... waiting')
    return None

def get_files():
    files = glob.glob("*.mp4")
    return [f.replace('.mp4', '') for f in files]

def main():
    url = f'https://v2.vidsrc.me/embed/{IMDB_ID}'
    result = make_req(url)
    
    page = BeautifulSoup(result, "html.parser")
    
    episodes = page.findAll("div", {"class": "ep"})
    output = {}
    files = get_files()
    for e in episodes:
        text = e.text.replace(' ', '_')
        if text in files:
            print(f'Skip: {text}')
            continue
        output[text] = f"https://vidsrc.me/{e['data-iframe']}"

    for o, k in output.items():
        r = requests.get(k, headers=get_headers())
        page = BeautifulSoup(r.text, "html.parser")
        sources = page.findAll("div", {"class": "source"})
        for s in sources:
            data_hash = s['data-hash']
            new_req = special_req(f'https://v2.vidsrc.me/srcrcp/{data_hash}').url
            if 'vidsrc.xyz' in new_req:
                dl = handle_dl_saves(new_req, o)
                if url:
                    print(f'DLing: {o} episode...')
                    do_dl(o, dl)
                else:
                    print(f'MISSING LINK FOR {o}')
                break
    

if __name__ == '__main__':
    main()
