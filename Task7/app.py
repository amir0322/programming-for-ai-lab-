from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
from datetime import datetime
from config import Config

app = Flask(__name__, static_folder='static')
app.config.from_object(Config)
CORS(app)


class WeatherClient:
    def __init__(self, key):
        self.key = key
        self.base_url = "http://api.openweathermap.org/data/2.5"

    def get_city_weather(self, city, units="metric"):
        url = f"{self.base_url}/weather"
        params = {
            "q": city,
            "appid": self.key,
            "units": units,
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as err:
            if err.response.status_code == 401:
                raise Exception(
                    "API Key Invalid: Your OpenWeatherMap API key is not working. Possible reasons: (1) Key not yet activated - wait 1-2 hours after creating it, (2) Email not verified - check your inbox, (3) Invalid key - generate a new one at https://home.openweathermap.org/api_keys"
                )
            elif err.response.status_code == 404:
                raise Exception(f"City '{city}' not found. Please check the spelling.")
            else:
                raise Exception(f"Weather API error: {str(err)}")
        except requests.RequestException as err:
            raise Exception(f"Network error: {str(err)}")

    def get_coords_weather(self, lat, lon, units="metric"):
        url = f"{self.base_url}/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.key,
            "units": units,
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as err:
            if err.response.status_code == 401:
                raise Exception(
                    "API Key Invalid: Your OpenWeatherMap API key is not working. Possible reasons: (1) Key not yet activated - wait 1-2 hours after creating it, (2) Email not verified - check your inbox, (3) Invalid key - generate a new one at https://home.openweathermap.org/api_keys"
                )
            elif err.response.status_code == 400:
                raise Exception(f"Invalid coordinates: lat={lat}, lon={lon}")
            else:
                raise Exception(f"Weather API error: {str(err)}")
        except requests.RequestException as err:
            raise Exception(f"Network error: {str(err)}")

    def get_city_forecast(self, city, units="metric"):
        # The previous implementation used the 5-day/3-hour forecast endpoint
        # which only provided data in 3‑hour increments.  To return a 7‑day
        # forecast we now leverage the One Call API.  First we query the
        # current weather for the city to obtain its coordinates, then we
        # call the One Call endpoint asking for daily data.
        #
        # Note: the One Call API does not support location by name, so a
        # two–step process is required.
        try:
            # step 1: get coordinates
            location = self.get_city_weather(city, units)
            lat = location["coord"]["lat"]
            lon = location["coord"]["lon"]

            url = f"{self.base_url}/onecall"
            params = {
                "lat": lat,
                "lon": lon,
                "exclude": "current,minutely,hourly,alerts",
                "appid": self.key,
                "units": units,
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as err:
            if err.response.status_code == 401:
                raise Exception(
                    "API Key Invalid: Your OpenWeatherMap API key is not working. Possible reasons: (1) Key not yet activated - wait 1-2 hours after creating it, (2) Email not verified - check your inbox, (3) Invalid key - generate a new one at https://home.openweathermap.org/api_keys"
                )
            elif err.response.status_code == 404:
                raise Exception(f"City '{city}' not found for forecast.")
            else:
                raise Exception(f"Forecast API error: {str(err)}")
        except requests.RequestException as err:
            raise Exception(f"Network error: {str(err)}")


weather_service = WeatherClient(app.config["WEATHER_API_KEY"])


def format_weather_response(data):
    weather_info = data["weather"][0]
    main_info = data["main"]

    return {
        "city": data["name"],
        "country": data["sys"]["country"],
        "temperature": {
            "current": main_info["temp"],
            "feels_like": main_info["feels_like"],
            "min": main_info["temp_min"],
            "max": main_info["temp_max"],
        },
        "humidity": main_info["humidity"],
        "pressure": main_info["pressure"],
        "visibility": data.get("visibility", "N/A"),
        "weather": {
            "main": weather_info["main"],
            "description": weather_info["description"],
            "icon": weather_info["icon"],
        },
        "wind": {
            "speed": data["wind"]["speed"],
            "direction": data["wind"].get("deg", "N/A"),
        },
        "coordinates": {
            "lat": data["coord"]["lat"],
            "lon": data["coord"]["lon"],
        },
        "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M:%S"),
        "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M:%S"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def is_valid_units(units):
    return units in ["metric", "imperial", "kelvin"]


@app.route("/", methods=["GET"])
def home():
    return send_from_directory(".", "index.html")


@app.route("/api", methods=["GET"])
def api_info():
    return jsonify(
        {
            "message": "Flask Weather App API",
            "version": "1.0.0",
            "endpoints": {
                "current_weather": "/api/weather/current?city=<city_name>&units=<metric|imperial|kelvin>",
                "weather_by_coords": "/api/weather/coordinates?lat=<latitude>&lon=<longitude>&units=<metric|imperial|kelvin>",
                "forecast": "/api/weather/forecast?city=<city_name>&units=<metric|imperial|kelvin>",
                "health": "/api/health",
            },
        }
    )


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/weather/current", methods=["GET"])
def get_current_weather():
    city = request.args.get("city")
    units = request.args.get("units", "metric")

    if not city:
        return jsonify({"error": "City parameter is required"}), 400

    if not is_valid_units(units):
        return jsonify({"error": "Units must be metric, imperial, or kelvin"}), 400

    try:
        weather_data = weather_service.get_city_weather(city, units)
        formatted_data = format_weather_response(weather_data)
        formatted_data["units"] = units
        return jsonify({"success": True, "data": formatted_data})
    except Exception as err:
        return jsonify({"success": False, "error": str(err)}), 500


@app.route("/api/weather/coordinates", methods=["GET"])
def get_weather_by_coordinates():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    units = request.args.get("units", "metric")

    if not lat or not lon:
        return jsonify({"error": "Both lat and lon parameters are required"}), 400

    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        return jsonify({"error": "Invalid coordinates format"}), 400

    if not is_valid_units(units):
        return jsonify({"error": "Units must be metric, imperial, or kelvin"}), 400

    try:
        weather_data = weather_service.get_coords_weather(lat, lon, units)
        formatted_data = format_weather_response(weather_data)
        formatted_data["units"] = units
        return jsonify({"success": True, "data": formatted_data})
    except Exception as err:
        return jsonify({"success": False, "error": str(err)}), 500


@app.route("/api/weather/forecast", methods=["GET"])
def get_forecast():
    city = request.args.get("city")
    units = request.args.get("units", "metric")

    if not city:
        return jsonify({"error": "City parameter is required"}), 400

    if not is_valid_units(units):
        return jsonify({"error": "Units must be metric, imperial, or kelvin"}), 400

    try:
        forecast_data = weather_service.get_city_forecast(city, units)

        # The One Call response does not include a city object; we kept the
        # original weather call earlier, so use that to fill in metadata.
        location = weather_service.get_city_weather(city, units)

        formatted_forecast = {
            "city": location["name"],
            "country": location["sys"]["country"],
            "coordinates": {
                "lat": location["coord"]["lat"],
                "lon": location["coord"]["lon"],
            },
            "units": units,
            "forecast": [],
        }

        # iterate over daily entries (the first 5 days)
        for daily in forecast_data.get("daily", [])[:5]:
            ts = datetime.fromtimestamp(daily["dt"])
            forecast_item = {
                "datetime": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "date": ts.strftime("%Y-%m-%d"),
                "time": ts.strftime("%H:%M:%S"),
                "temperature": {
                    "temp": daily["temp"]["day"],
                    "feels_like": daily["feels_like"]["day"],
                    "min": daily["temp"]["min"],
                    "max": daily["temp"]["max"],
                },
                "weather": {
                    "main": daily["weather"][0]["main"],
                    "description": daily["weather"][0]["description"],
                    "icon": daily["weather"][0]["icon"],
                },
                "humidity": daily.get("humidity"),
                "pressure": daily.get("pressure"),
                "wind": {
                    "speed": daily.get("wind_speed"),
                    "direction": daily.get("wind_deg", "N/A"),
                },
                "clouds": daily.get("clouds"),
            }
            formatted_forecast["forecast"].append(forecast_item)

        return jsonify({"success": True, "data": formatted_forecast})
    except Exception as err:
        return jsonify({"success": False, "error": str(err)}), 500


@app.errorhandler(404)
def not_found_error(_error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(_error):
    return jsonify({"success": False, "error": "Internal server error"}), 500


if __name__ == "__main__":
    if not app.config.get("WEATHER_API_KEY"):
        print("Warning: WEATHER_API_KEY not configured. Please set your OpenWeatherMap API key.")

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=app.config.get("DEBUG", False),
    )