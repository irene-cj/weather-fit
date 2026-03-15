from flask import Flask, render_template, request, session
import requests
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "weatherfit-secret-2026")

API_KEY = os.getenv("WEATHER_API_KEY")
BASE    = "https://api.openweathermap.org"


# ── Outfit recommendation (item-list style) ──────────────────────────────────

def get_outfit_items(temp_f, condition):
    cond     = condition.lower()
    is_rainy = any(w in cond for w in ["rain", "drizzle", "shower", "storm"])
    is_snowy = any(w in cond for w in ["snow", "blizzard", "sleet"])
    is_windy = "wind" in cond
    items    = []

    # Top layer
    if temp_f < 20:
        items += ["Heavy winter coat", "Thick hoodie or crewneck", "Thermal undershirt"]
    elif temp_f < 32:
        items += ["Winter coat", "Hoodie or crewneck"]
    elif temp_f < 45:
        items += ["Puffer jacket", "Hoodie or sweater"]
    elif temp_f < 55:
        items += ["Light jacket or denim jacket", "Long sleeve shirt"]
    elif temp_f < 65:
        items += ["Hoodie or cardigan"]
    elif temp_f < 75:
        items += ["T-shirt", "Light layer optional for evening"]
    elif temp_f < 85:
        items += ["T-shirt or tank top"]
    else:
        items += ["Tank top or sleeveless shirt"]

    # Bottom
    if temp_f < 32:
        items += ["Thermal leggings under pants", "Warm pants or jeans"]
    elif temp_f < 55:
        items += ["Pants or jeans"]
    elif temp_f < 70:
        items += ["Jeans, pants, or chinos"]
    else:
        items += ["Shorts or light pants"]

    # Footwear
    if temp_f < 32 or is_snowy:
        items.append("Insulated waterproof boots")
    elif temp_f < 55:
        items.append("Closed-toe shoes or boots")
    elif temp_f < 70:
        items.append("Sneakers or casual shoes")
    else:
        items.append("Sneakers or sandals")

    # Accessories
    if temp_f < 20:
        items += ["Gloves", "Beanie", "Scarf"]
    elif temp_f < 32:
        items += ["Gloves", "Beanie"]
    elif temp_f < 45:
        items.append("Scarf optional")

    if is_rainy:  items.append("☂️ Umbrella or rain jacket")
    if is_snowy:  items.append("❄️ Waterproof outer layer")
    if is_windy and temp_f < 60:
        items.append("💨 Wind-resistant jacket")

    return items


def get_outfit_emoji(temp_f):
    if temp_f < 32: return "🧥"
    if temp_f < 50: return "🧤"
    if temp_f < 65: return "🧣"
    if temp_f < 75: return "👕"
    if temp_f < 85: return "🩳"
    return "🌞"


def get_outfit_summary(temp_f):
    if temp_f < 20: return "Dangerously cold — bundle up completely."
    if temp_f < 32: return "Freezing — full winter gear required."
    if temp_f < 45: return "Very cold — layer up."
    if temp_f < 55: return "Cold — a jacket is a must."
    if temp_f < 65: return "Cool — bring a light layer."
    if temp_f < 75: return "Comfortable — dress casually."
    if temp_f < 85: return "Warm — keep it light."
    return "Hot — stay cool and breathable."


# ── Outfit picker ─────────────────────────────────────────────────────────────

CLOTHING_WEIGHTS = {
    "winter coat": 10, "heavy coat": 10, "parka": 10,
    "jacket": 6,  "puffer": 7, "denim jacket": 5,
    "hoodie": 5,  "crewneck": 4, "sweater": 4, "cardigan": 3,
    "long sleeve": 3, "flannel": 4,
    "t-shirt": 1, "tee": 1, "tank": 0, "tank top": 0, "sleeveless": 0,
    "jeans": 2, "pants": 2, "sweats": 3, "sweatpants": 3, "leggings": 2,
    "shorts": 0, "skirt": 0,
    "boots": 3, "sneakers": 1, "shoes": 1,
    "sandals": 0, "crocs": 0, "flip flops": 0,
    "gloves": 3, "beanie": 3, "scarf": 2, "hat": 1,
}

def score_outfit(text):
    t = text.lower()
    score = 0
    for item, w in CLOTHING_WEIGHTS.items():
        if item in t:
            score += w
    return score

def pick_best_outfit(outfits, temp_f):
    if temp_f < 32:   ideal = 22
    elif temp_f < 45: ideal = 16
    elif temp_f < 55: ideal = 12
    elif temp_f < 65: ideal = 8
    elif temp_f < 75: ideal = 4
    elif temp_f < 85: ideal = 2
    else:             ideal = 0

    scored = []
    for i, o in enumerate(outfits):
        if o.strip():
            s = score_outfit(o)
            scored.append({"index": i+1, "text": o.strip(), "score": s, "diff": abs(s - ideal)})

    if not scored:
        return None

    best = min(scored, key=lambda x: x["diff"])

    if best["score"] > ideal + 4:
        reason = f"This is the warmest option — best suited for {round(temp_f)}°F weather."
    elif best["score"] < ideal - 4:
        reason = f"This is the lightest option — best for {round(temp_f)}°F, though consider adding a layer."
    else:
        reason = f"This outfit is the closest match for {round(temp_f)}°F. {get_outfit_summary(temp_f)}"

    return {"winner_index": best["index"], "winner_text": best["text"],
            "reason": reason, "all": scored}


# ── AQI helper ────────────────────────────────────────────────────────────────

def aqi_info(aqi):
    return {
        1: ("Good",      "#2ecc71", "Air quality is satisfactory with little or no risk."),
        2: ("Fair",      "#C9FFE2", "Acceptable air quality. Sensitive individuals may notice minor effects."),
        3: ("Moderate",  "#f39c12", "Sensitive groups may experience health effects."),
        4: ("Poor",      "#e67e22", "Everyone may experience health effects."),
        5: ("Very Poor", "#EF233C", "Health alert — everyone may experience serious effects."),
    }.get(aqi, ("Unknown", "#aaa", ""))


# ── Main route ────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    weather_data  = None
    outfit        = None
    forecast_days = None
    hourly_today  = None
    air_quality   = None
    outfit_pick   = None
    error         = None

    if request.method == "POST":
        city = request.form.get("city", "").strip()
        raw_outfits = [
            request.form.get("outfit1", "").strip(),
            request.form.get("outfit2", "").strip(),
            request.form.get("outfit3", "").strip(),
        ]
        user_outfits = [o for o in raw_outfits if o]

        if city:
            cur_url = f"{BASE}/data/2.5/weather?q={city}&appid={API_KEY}&units=imperial"
            try:
                r = requests.get(cur_url, timeout=5)
                if r.status_code != 200:
                    error = f'City "{city}" not found. Check the spelling and try again.'
                else:
                    d         = r.json()
                    temp_f    = round(d["main"]["temp"])
                    temp_c    = round((temp_f - 32) * 5 / 9)
                    feels_f   = round(d["main"]["feels_like"])
                    feels_c   = round((feels_f - 32) * 5 / 9)
                    humidity  = d["main"]["humidity"]
                    condition = d["weather"][0]["description"].title()
                    icon_code = d["weather"][0]["icon"]
                    wind_mph  = round(d["wind"]["speed"])
                    lat       = d["coord"]["lat"]
                    lon       = d["coord"]["lon"]

                    weather_data = {
                        "city": d["name"], "country": d["sys"]["country"],
                        "temp_f": temp_f,  "temp_c": temp_c,
                        "feels_f": feels_f, "feels_c": feels_c,
                        "humidity": humidity, "condition": condition,
                        "icon_url": f"https://openweathermap.org/img/wn/{icon_code}@2x.png",
                        "wind_mph": wind_mph, "wind_kph": round(wind_mph * 1.609),
                    }

                    outfit = {
                        "clothing":   get_outfit_items(temp_f, condition),
                        "emoji":   get_outfit_emoji(temp_f),
                        "summary": get_outfit_summary(temp_f),
                    }

                    if user_outfits:
                        outfit_pick = pick_best_outfit(user_outfits, temp_f)

                    # ── 5-day forecast ────────────────────────────────────
                    fc_r = requests.get(
                        f"{BASE}/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=imperial",
                        timeout=5)
                    if fc_r.status_code == 200:
                        today_str   = datetime.utcnow().strftime("%Y-%m-%d")
                        days_dict   = {}
                        hourly_list = []

                        for item in fc_r.json()["list"]:
                            dt  = datetime.utcfromtimestamp(item["dt"])
                            ds  = dt.strftime("%Y-%m-%d")
                            tf  = round(item["main"]["temp"])
                            tc  = round((tf - 32) * 5 / 9)
                            ic  = item["weather"][0]["icon"]
                            hr  = dt.strftime("%I %p").lstrip("0")

                            if ds == today_str:
                                hourly_list.append({"hour": hr, "temp_f": tf, "temp_c": tc})
                                continue

                            if ds not in days_dict:
                                days_dict[ds] = {"label": dt.strftime("%a"),
                                                 "date":  dt.strftime("%b %d"),
                                                 "temps_f": [], "temps_c": [],
                                                 "icons": [], "conds": []}
                            days_dict[ds]["temps_f"].append(tf)
                            days_dict[ds]["temps_c"].append(tc)
                            days_dict[ds]["icons"].append(ic)
                            days_dict[ds]["conds"].append(
                                item["weather"][0]["description"].title())

                        forecast_days = []
                        for ds, v in sorted(days_dict.items())[:5]:
                            mid = len(v["icons"]) // 2
                            forecast_days.append({
                                "label":     v["label"],
                                "date":      v["date"],
                                "high_f":    max(v["temps_f"]),
                                "low_f":     min(v["temps_f"]),
                                "high_c":    max(v["temps_c"]),
                                "low_c":     min(v["temps_c"]),
                                "icon_url":  f"https://openweathermap.org/img/wn/{v['icons'][mid]}.png",
                                "condition": v["conds"][mid],
                            })

                        hourly_today = hourly_list[:8]

                    # ── Air quality ───────────────────────────────────────
                    aq_r = requests.get(
                        f"{BASE}/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}",
                        timeout=5)
                    if aq_r.status_code == 200:
                        aq_d  = aq_r.json()
                        aqi   = aq_d["list"][0]["main"]["aqi"]
                        comps = aq_d["list"][0]["components"]
                        label, color, desc = aqi_info(aqi)
                        air_quality = {
                            "aqi": aqi, "label": label,
                            "color": color, "desc": desc,
                            "pm25": round(comps.get("pm2_5", 0), 1),
                            "pm10": round(comps.get("pm10",  0), 1),
                            "o3":   round(comps.get("o3",    0), 1),
                            "no2":  round(comps.get("no2",   0), 1),
                        }

            except requests.exceptions.Timeout:
                error = "Request timed out. Please try again."
            except Exception as e:
                error = f"Something went wrong: {str(e)}"

    return render_template("index.html",
        weather=weather_data, outfit=outfit,
        forecast=forecast_days, hourly=hourly_today,
        air=air_quality, outfit_pick=outfit_pick,
        error=error)


if __name__ == "__main__":
    app.run(debug=True)