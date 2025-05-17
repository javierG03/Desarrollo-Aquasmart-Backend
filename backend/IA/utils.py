import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime
from django.utils import timezone
load_dotenv()
LOCATION = str("4.60971%2C-74.08175")

#SCOPE =f"{LOCATION}?unitGroup=metric&include=days&key={key}&contentType=json"
now = timezone.now().strftime("%Y-%m-%d")



def api_climate_request(location,date):
    
    key = os.getenv("KEY_CLIMATE")
    scope =f"{location}/{date}/{date}?unitGroup=metric&include=days&key={key}&contentType=json"
    url_api = os.getenv("URL_CLIMATE")
    campos_deseados = [
    "datetime", "tempmax", "tempmin", "precip", "precipprob", "precipcover",
    "windgust", "windspeed", "pressure", "cloudcover",
    "solarradiation", "sunrise", "sunset"
]
    

    headers = {
        
        'Accept': 'application/json'
    }

    url_protegido = f"{url_api}{scope}"
    response = requests.get(url_protegido, headers=headers)   
    if response.status_code == 200:
        data = response.json()
        print("Datos recibidos desde la API:")
        #print(json.dumps(data, indent=4)) 
        dias = data.get("days", [])
        dias_filtrados = []
        print(json.dumps(dias[0], indent=4))
        for dia in dias:
            entrada = {clave: dia.get(clave) for clave in campos_deseados}          
            
            dias_filtrados.append(entrada)          
                    
        return data
    else:
        print(f"Error en solicitud protegida: {response.status_code}")
        return None

#api_climate_request(LOCATION,now)   