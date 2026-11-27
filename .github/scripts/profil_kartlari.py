"""Profil README kartlarını (istatistik, dil, seri ve katkı grafiği) GitHub API'den üretir.

Paylaşımlı github-readme-stats sunucusunun önbellek/istek sınırı sorunlarını
ortadan kaldırmak için kartlar her gün bu repoda yeniden oluşturulur.
"""
import datetime
import json
import os
import urllib.request
from html import escape

KULLANICI = os.environ.get("KULLANICI", "mikbalyildiz")
TOKEN = os.environ["GITHUB_TOKEN"]
CIKTI = "profile"

BG, BASLIK, METIN, VURGU, KUTU = "#0f2027", "#2C9AB7", "#ffffff", "#2C9AB7", "#16313b"

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
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
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
    takvim = katki["contributionCalendar"]
    gunler = [g for h in takvim["weeks"] for g in h["contributionDays"]]
    return {
        "gunler": gunler,
        "yillik": takvim["totalContributions"],
        "ad": ilk["name"] or KULLANICI,
        "yildiz": yildiz,
        "commit": katki["totalCommitContributions"] + katki["restrictedContributionsCount"],
        "issue": ilk["issues"]["totalCount"],
        "diller": diller,
    }


def istatistik_karti(v):
    return kutulu_kart("GitHub İstatistikleri · Stats", [
        ("⭐", v["yildiz"], "Stars", "(Toplam Yıldız)"),
        ("📝", v["commit"], "Commits", "(Kod Kaydı · son 1 yıl)"),
        ("🐞", v["issue"], "Issues", "(Sorun Bildirimi)"),
    ])


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


def seriler(gunler):
    """Güncel ve en uzun katkı serisini (gün) hesaplar."""
    en_uzun = sayac = 0
    for g in gunler:
        sayac = sayac + 1 if g["contributionCount"] > 0 else 0
        en_uzun = max(en_uzun, sayac)
    guncel = 0
    sirali = list(gunler)
    # Bugün henüz katkı yoksa seri bozulmuş sayılmaz, dünden geriye sayılır.
    if sirali and sirali[-1]["contributionCount"] == 0:
        sirali = sirali[:-1]
    for g in reversed(sirali):
        if g["contributionCount"] == 0:
            break
        guncel += 1
    return guncel, en_uzun


def kutulu_kart(baslik, kutular):
    govde = ""
    for i, (ikon, deger, en, tr) in enumerate(kutular):
        x = 20 + i * 130
        orta = x + 60
        govde += f"""<g class="k" style="animation-delay:{i * 150}ms">
<rect x="{x}" y="56" width="120" height="124" rx="10" fill="{KUTU}" stroke="{VURGU}" stroke-opacity="0.35"/>
<text x="{orta}" y="84" text-anchor="middle" font-size="20">{ikon}</text>
<text x="{orta}" y="126" text-anchor="middle" class="d">{deger}</text>
<text x="{orta}" y="150" text-anchor="middle" class="m">{escape(en)}</text>
<text x="{orta}" y="167" text-anchor="middle" class="s">{escape(tr)}</text>
</g>"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="200" viewBox="0 0 420 200">
<style>.t{{font:600 18px 'Segoe UI',Ubuntu,sans-serif;fill:{BASLIK}}}.d{{font:800 34px 'Segoe UI',Ubuntu,sans-serif;fill:{VURGU}}}.m{{font:600 13px 'Segoe UI',Ubuntu,sans-serif;fill:{METIN}}}.s{{font:400 10.5px 'Segoe UI',Ubuntu,sans-serif;fill:#9fb3bd}}.k{{opacity:0;animation:g .6s ease-out forwards}}@keyframes g{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}</style>
<rect width="420" height="200" rx="6" fill="{BG}"/>
<text x="20" y="36" class="t">{escape(baslik)}</text>
{govde}
</svg>"""


def seri_karti(v):
    guncel, en_uzun = seriler(v["gunler"])
    return kutulu_kart("Katkı Serisi · Streak", [
        ("🔥", guncel, "Current", "(Güncel Seri · gün)"),
        ("🏆", en_uzun, "Longest", "(En Uzun Seri · gün)"),
        ("📅", v["yillik"], "Contributions", "(Son 1 Yıl Katkı)"),
    ])


AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def katki_grafigi(v):
    """Son bir yılın haftalık katkılarını kendini çizen bir alan grafiğiyle gösterir."""
    haftalar = []
    for i in range(0, len(v["gunler"]), 7):
        hafta = v["gunler"][i:i + 7]
        haftalar.append((hafta[0]["date"], sum(g["contributionCount"] for g in hafta)))
    G, Y, sol, sag, ust, alt = 420, 220, 34, 14, 56, 34
    en_cok = max((t for _, t in haftalar), default=0) or 1
    adim = (G - sol - sag) / max(len(haftalar) - 1, 1)
    nokta = [(sol + i * adim, Y - alt - (Y - ust - alt) * t / en_cok) for i, (_, t) in enumerate(haftalar)]
    cizgi = " ".join(f"{x:.1f},{y:.1f}" for x, y in nokta)
    alan = f"{sol},{Y - alt} {cizgi} {nokta[-1][0]:.1f},{Y - alt}" if nokta else ""
    etiket, onceki_ay = "", None
    for i, (tarih, _) in enumerate(haftalar):
        ay = int(tarih[5:7])
        if ay != onceki_ay:
            if onceki_ay is not None:
                etiket += f'<text x="{sol + i * adim:.1f}" y="{Y - 14}" class="e" text-anchor="middle">{AYLAR[ay - 1]}</text>'
            onceki_ay = ay
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{G}" height="{Y}" viewBox="0 0 {G} {Y}">
<style>.t{{font:600 18px 'Segoe UI',Ubuntu,sans-serif;fill:{BASLIK}}}.e{{font:400 10px 'Segoe UI',Ubuntu,sans-serif;fill:#9fb3bd}}
.c{{stroke-dasharray:3000;stroke-dashoffset:3000;animation:ciz 2.2s ease-out forwards}}
.a{{opacity:0;animation:belir 1s ease-out 1.4s forwards}}
@keyframes ciz{{to{{stroke-dashoffset:0}}}}@keyframes belir{{to{{opacity:1}}}}</style>
<defs><linearGradient id="dg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{VURGU}" stop-opacity="0.45"/><stop offset="1" stop-color="{VURGU}" stop-opacity="0"/></linearGradient></defs>
<rect width="{G}" height="{Y}" rx="6" fill="{BG}"/>
<text x="20" y="36" class="t">Katkı Grafiği · Contributions</text>
<line x1="{sol}" y1="{Y - alt}" x2="{G - sag}" y2="{Y - alt}" stroke="#2a4652"/>
<text x="{sol - 6}" y="{ust + 4}" class="e" text-anchor="end">{en_cok}</text>
<text x="{sol - 6}" y="{Y - alt + 4}" class="e" text-anchor="end">0</text>
<polygon class="a" points="{alan}" fill="url(#dg)"/>
<polyline class="c" points="{cizgi}" fill="none" stroke="{VURGU}" stroke-width="2.2" stroke-linejoin="round"/>
{etiket}
</svg>"""


def main():
    v = verileri_topla()
    os.makedirs(CIKTI, exist_ok=True)
    for ad, svg in [("stats.svg", istatistik_karti(v)), ("top-langs.svg", dil_karti(v)),
                    ("streak.svg", seri_karti(v)), ("activity.svg", katki_grafigi(v))]:
        with open(os.path.join(CIKTI, ad), "w", encoding="utf-8") as f:
            f.write(svg)
    print(f"Toplam yıldız: {v['yildiz']} · commit: {v['commit']}")


if __name__ == "__main__":
    main()
