"""Profil README kartlarını (istatistik ve dil kartı) GitHub API'den üretir.

Paylaşımlı github-readme-stats sunucusunun önbellek/istek sınırı sorunlarını
ortadan kaldırmak için kartlar her gün bu repoda yeniden oluşturulur.
"""
import json
import os
import urllib.request
from html import escape

KULLANICI = os.environ.get("KULLANICI", "mikbalyildiz")
TOKEN = os.environ["GITHUB_TOKEN"]
CIKTI = "profile"

BG, BASLIK, METIN, VURGU = "#0f2027", "#2C9AB7", "#ffffff", "#2C9AB7"

SORGU = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    name
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    issues { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
    }
  }
}
"""


def graphql(degiskenler):
    istek = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": SORGU, "variables": degiskenler}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(istek) as yanit:
        veri = json.load(yanit)
    if "errors" in veri:
        raise SystemExit(f"GraphQL hatası: {veri['errors']}")
    return veri["data"]["user"]


def verileri_topla():
    yildiz, diller, cursor, ilk = 0, {}, None, None
    while True:
        kullanici = graphql({"login": KULLANICI, "cursor": cursor})
        ilk = ilk or kullanici
        repolar = kullanici["repositories"]
        for repo in repolar["nodes"]:
            yildiz += repo["stargazerCount"]
            for kenar in repo["languages"]["edges"]:
                ad = kenar["node"]["name"]
                renk = kenar["node"]["color"] or "#888888"
                onceki = diller.get(ad, (0, renk))[0]
                diller[ad] = (onceki + kenar["size"], renk)
        if not repolar["pageInfo"]["hasNextPage"]:
            break
        cursor = repolar["pageInfo"]["endCursor"]
    katki = ilk["contributionsCollection"]
    return {
        "ad": ilk["name"] or KULLANICI,
        "yildiz": yildiz,
        "commit": katki["totalCommitContributions"] + katki["restrictedContributionsCount"],
        "issue": ilk["issues"]["totalCount"],
        "diller": diller,
    }


def istatistik_karti(v):
    satirlar = [
        ("Toplam Yıldız · Stars", v["yildiz"]),
        ("Commit (son 1 yıl)", v["commit"]),
        ("Issue", v["issue"]),
    ]
    govde = "".join(
        f'<text x="25" y="{80 + i * 26}" class="m">{escape(ad)}:</text>'
        f'<text x="300" y="{80 + i * 26}" class="d" text-anchor="end">{deger}</text>'
        for i, (ad, deger) in enumerate(satirlar)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="165" viewBox="0 0 420 165">
<style>.t{{font:600 18px 'Segoe UI',Ubuntu,sans-serif;fill:{BASLIK}}}.m{{font:600 14px 'Segoe UI',Ubuntu,sans-serif;fill:{METIN}}}.d{{font:700 15px 'Segoe UI',Ubuntu,sans-serif;fill:{VURGU}}}</style>
<rect width="420" height="165" rx="6" fill="{BG}"/>
<text x="25" y="38" class="t">GitHub İstatistikleri · Stats</text>
{govde}
<text x="365" y="112" text-anchor="middle" font-size="40">⭐</text>
</svg>"""


def dil_karti(v):
    toplam = sum(b for b, _ in v["diller"].values()) or 1
    ilk_alti = sorted(v["diller"].items(), key=lambda x: -x[1][0])[:8]
    cubuk, x = "", 25.0
    for _, (boyut, renk) in ilk_alti:
        w = 370 * boyut / toplam
        cubuk += f'<rect x="{x:.1f}" y="55" width="{w:.1f}" height="8" fill="{renk}"/>'
        x += w
    etiket = ""
    for i, (ad, (boyut, renk)) in enumerate(ilk_alti):
        ex, ey = 25 + (i % 2) * 190, 90 + (i // 2) * 24
        etiket += (f'<circle cx="{ex + 5}" cy="{ey - 4}" r="5" fill="{renk}"/>'
                   f'<text x="{ex + 15}" y="{ey}" class="m">{escape(ad)} {100 * boyut / toplam:.1f}%</text>')
    h = 100 + ((len(ilk_alti) + 1) // 2) * 24
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="{h}" viewBox="0 0 420 {h}">
<style>.t{{font:600 18px 'Segoe UI',Ubuntu,sans-serif;fill:{BASLIK}}}.m{{font:400 12px 'Segoe UI',Ubuntu,sans-serif;fill:{METIN}}}</style>
<rect width="420" height="{h}" rx="6" fill="{BG}"/>
<text x="25" y="35" class="t">En Çok Kullanılan Diller</text>
<clipPath id="c"><rect x="25" y="55" width="370" height="8" rx="4"/></clipPath>
<g clip-path="url(#c)">{cubuk}</g>
{etiket}
</svg>"""


def main():
    v = verileri_topla()
    os.makedirs(CIKTI, exist_ok=True)
    for ad, svg in [("stats.svg", istatistik_karti(v)), ("top-langs.svg", dil_karti(v))]:
        with open(os.path.join(CIKTI, ad), "w", encoding="utf-8") as f:
            f.write(svg)
    print(f"Toplam yıldız: {v['yildiz']} · commit: {v['commit']}")


if __name__ == "__main__":
    main()
