#!/usr/bin/env python3
"""
Niet-lokale poster (draait op GitHub Actions). Plaatst de eerstvolgende post uit queue.json
op @koa_ai via de Instagram Graph API. Verwijdert 'm daarna uit de wachtrij.
Token via env IG_ACCESS_TOKEN (GitHub secret). Geen externe libs.
"""
import os, sys, json, time, urllib.parse, urllib.request, urllib.error

BASE = "https://graph.instagram.com/v21.0"
QUEUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "queue.json")
TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")

def post(path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(BASE + path, data=data, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": json.loads(e.read().decode()).get("error", str(e))}

def publish(item):
    urls, caption = item["media"], item["caption"]
    if len(urls) == 1:
        c = post("/me/media", image_url=urls[0], caption=caption)
        if "id" not in c: print("aanmaken mislukt:", c.get("error", c)); return False
        cid = c["id"]
    else:
        kids = []
        for u in urls:
            r = post("/me/media", image_url=u, is_carousel_item="true")
            if "id" not in r: print("slide mislukt:", r.get("error", r)); return False
            kids.append(r["id"]); time.sleep(1)
        r = post("/me/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)
        if "id" not in r: print("carrousel mislukt:", r.get("error", r)); return False
        cid = r["id"]
    time.sleep(3)
    pub = post("/me/media_publish", creation_id=cid)
    if "id" in pub: print("GEPUBLICEERD:", item.get("slug", "?"), "media", pub["id"]); return True
    print("publiceren mislukt:", pub.get("error", pub)); return False

def publish_story(video_url):
    """Plaats een video als Story (media_type=STORIES) met verwerkings-check."""
    c = post("/me/media", video_url=video_url, media_type="STORIES")
    if "id" not in c:
        print("story-aanmaken mislukt:", c.get("error", c)); return False
    cid = c["id"]
    for _ in range(20):
        r = json.loads(urllib.request.urlopen(
            "%s/%s?fields=status_code&access_token=%s" % (BASE, cid, TOKEN), timeout=30).read().decode())
        sc = r.get("status_code")
        if sc == "FINISHED":
            break
        if sc == "ERROR":
            print("story-verwerking mislukt"); return False
        time.sleep(6)
    pub = post("/me/media_publish", creation_id=cid)
    if "id" in pub:
        print("STORY GEPLAATST:", pub["id"]); return True
    print("story-publiceren mislukt:", pub.get("error", pub)); return False


def note_story(item):
    """Story NIET automatisch plaatsen (dan kan Hein zelf IG-muziek kiezen),
    maar op een 'nog te plaatsen'-lijst zetten met een downloadbaar beeld."""
    img = item.get("story_img") or item.get("story")
    if not img:
        return
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stories-te-plaatsen.md")
    if not os.path.exists(path):
        open(path, "w").write(
            "# Story's nog te plaatsen 📲\n\n"
            "Voor elke geplaatste post staat hier het bijbehorende story-beeld klaar. "
            "Download het, zet 't in de Instagram-app als **Story**, en voeg je eigen **muziek** toe. "
            "Vink af (`[x]`) als 't geplaatst is.\n\n")
    open(path, "a").write(
        "- [ ] **%s** — [download beeld](%s) → Instagram-app → Story → muziek erbij\n"
        % (item.get("slug", "?"), img))
    print("STORY TE PLAATSEN genoteerd:", item.get("slug"))

def main():
    if not TOKEN:
        print("Geen IG_ACCESS_TOKEN"); sys.exit(1)
    q = json.load(open(QUEUE)) if os.path.exists(QUEUE) else []
    if not q:
        print("Wachtrij leeg — niets te plaatsen."); return
    item = q[0]
    if publish(item):
        json.dump(q[1:], open(QUEUE, "w"), indent=2, ensure_ascii=False)
        print("Wachtrij nu:", len(q) - 1)
        # story NIET auto-plaatsen -> op de lijst zetten voor handmatig plaatsen + eigen muziek
        note_story(item)
    else:
        sys.exit(1)  # laat de post in de wachtrij; volgende run opnieuw

if __name__ == "__main__":
    main()
