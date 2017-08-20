'''
A little utility to check the weather forecast for the next few days. This
version is custom made for iPhone, so it uses Pythonista 3. It makes use of
the web API provided by openweathermap.org and requires 'arrow' (which you can
install with pip using StaSh).

Developed in Python 3.5 for your enjoyment by:
        Victor Domingos
        http://victordomingos.com

© 2017 Victor Domingos
Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
'''

import requests
import sys
import arrow
import console
import datetime
import location

__app_name__ = "The NPK Weather App"
__author__ = "Victor Domingos"
__copyright__ = "© 2017 Victor Domingos"
__license__ = "Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)"
__version__ = "1.1"
__email__ = "info@victordomingos.com"
__status__ = "beta"


# ---------- Set these variables before use ----------
# Request an API key at: http://openweathermap.org/
APIKEY = 'APIKEY'
API_URL_CURRENT = 'http://api.openweathermap.org/data/2.5/weather'
API_URL = 'http://api.openweathermap.org/data/2.5/forecast'

# Default location to present in case it is not possible to obtain current
# location.
LOCATION = 'Braga,pt'

# Get current location from the device's GPS?
USE_LOCATION_SERVICES = True

HEADER_FONTSIZE = 16
TITLE_FONTSIZE = 12
TABLE_FONTSIZE = 10.5
TODAY_FONTSIZE = 38
TODAY_FONTSIZE2 = 13

# Set to True to see more data (forecast for each 3h)
DETAILED = False

# Set accordingly with Pythonista app current settings
DARK_MODE = True
# ----------------------------------------------------


def config_consola(localizacao):
    '''
    Sets console font size and color for Pythonista on iOS
    '''
    console.clear()
    console.set_color(.5, .5, .5)
    console.set_font("Menlo-Bold", HEADER_FONTSIZE)
    
    if DARK_MODE:
        console.set_color(0.5, 0.8, 1)
    else:
        console.set_color(0.2, 0.5, 1)
    
    line_length = 32
    if len(localizacao + __app_name__ + ' ') > line_length:
        str_title = "{}\n({})".format(__app_name__, localizacao)
    else:
        str_title = "{} ({})".format(__app_name__, localizacao)
        
    print(str_title)
    console.set_font("Menlo-Regular", 6.7)
    
    if DARK_MODE:
        console.set_color(0.7, 0.7, 0.7)
    else:
        console.set_color(0.5, 0.5, 0.5)
    print('{}, {}\n\n'.format(__copyright__, __license__))
    
    console.set_font("Menlo-Regular", TABLE_FONTSIZE)
    
    if DARK_MODE:
        console.set_color(1, 1, 1)
    else:
        console.set_color(0, 0, 0)


def obter_localizacao():
    try:
        coordinates = location.get_location()
        results = location.reverse_geocode(coordinates)
        cidade = results[0]['City']
        pais = results[0]['CountryCode']
        return '{},{}'.format(cidade, pais)
    except Exception:
        print('Não foi possível obter a localização atual.'
              '\nA utilizar predefinição...\n')
        return LOCATION
        

def dayNameFromWeekday(weekday):
    days = ["Segunda-feira", "Terça-feira", "Quarta-feira",
            "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    return days[weekday] if -1 < weekday < len(days) else None


def converter_vento(graus, metros_p_segundo):
    if graus != 0:
        direcoes = ["N", "NE", "E", "SE", "S", "SO", "O", "NO", "N"]
        posicao = int((graus+57.5)/45)-1
        kmph = int(metros_p_segundo*3.6)
        return (direcoes[posicao], kmph)
    else:
        return ('', 0)


def obter_nuvens(json):
    nuvens_str = ''
    if 'clouds' in json.keys():
        nuvens = json['clouds']['all']
        if nuvens == 0:
            return ''
        nuvens_str = 'N.'+str(nuvens)+'%'
    return nuvens_str
    
    
def obter_humidade(json):
    humidade_str = ''
    if 'humidity' in json['main'].keys():
        humidade = json['main']['humidity']
        if humidade == 0:
            return ''
        humidade_str = 'H.'+str(humidade)+'%'
    return humidade_str

        
def formatar_tempo(tempo, icone, chuva, ahora):
    tempo = tempo.replace('Garoa Fraca', 'Possib. Chuviscos Fracos')
    if tempo == 'Céu Claro':
        tempo = 'Céu Limpo'
        if ahora in ['22h', '01h', '04h']:
            icone = '🌙'
        else:
            icone = '☀️'
    elif tempo == 'Nuvens Quebrados':
        tempo = 'Céu Muito Nublado'
        icone = '☁️'
    elif tempo in ('Algumas Nuvens', 'Nuvens Dispersas'):
        tempo = 'Céu Pouco Nublado'
        icone = '⛅️'
    elif ('Nublado' in tempo):
        icone = '☁️'
    elif ('Neblina' in tempo):
        icone = '🌤'
        
    if 'Chuva' in tempo:
        tempo = tempo + ' ' + chuva

    return (tempo, icone)
    

def get_weather_data(location=None, kind='forecast'):
    if kind == 'forecast':
        api_URL = API_URL
    else:
        api_URL = API_URL_CURRENT
        
    try:
        console.show_activity()
        params = {'q': location,
                  'APPID': APIKEY,
                  'units': 'metric',
                  'lang': 'pt',
                  'mode': 'json'}
                  
        json_data = requests.get(api_URL, params=params, timeout=(2, 5)).json()
        console.hide_activity()
        return json_data
        
    except Exception as e:
        print(e)
        sys.exit(1)


def mostra_previsao(localizacao):
    previsoes = get_weather_data(location=localizacao, kind='forecast')['list']
    aagora = arrow.now()
    
    data_anterior = ''
    
    for previsao in previsoes:
        icone = ''
        data = previsao['dt_txt'].split()[0]
        
        adata = arrow.get(previsao['dt']).to('local')
        ahora = adata.to('local').format('HH')+'h'
         
        hoje = arrow.now().date().day
        adata_dia = adata.date().day
        
        if (adata-aagora <= datetime.timedelta(hours=+24)):
            show_more_info = True
        else:
            show_more_info = False
        
        if (not DETAILED) and (not show_more_info):
            if ahora in ('04h', '07h', '22h', '01h'):
                if ahora is '01h':
                    data_anterior = data
                continue
        
        temperatura_int = int(previsao['main']['temp'])
        temperatura = str(temperatura_int)+'°'
        tempo = previsao['weather'][0]['description'].title()
        
        arr_data = arrow.get(data)
        data_curta = arr_data.format('DD/MM')
        
        if 'rain' not in previsao.keys():
            chuva = ''
        elif '3h' in previsao['rain'].keys():
            tempo, chuva, icone = formatar_chuva(tempo,
                                                 previsao['rain']['3h'], '')
            
        nuvens_str = obter_nuvens(previsao)
        # humidade = obter_humidade(previsao)
        
        line_size = 48
        str_dia = ''
        spaces = ''
        console.set_font("Menlo-Bold", TITLE_FONTSIZE)
        if DARK_MODE:
            console.set_color(0.5, 0.8, 1)
        else:
            console.set_color(0.2, 0.5, 1)
        
        if data_anterior == '':
            if hoje == adata_dia:
                str_dia = '__Hoje ' + data_curta
                spaces = '_'*(line_size-len(str_dia))
                str_dia = str_dia + spaces
                print('\n'+str_dia)
            else:
                str_dia = '__Amanhã (' + data_curta + ')'
                spaces = '_'*(line_size-len(str_dia))
                str_dia = str_dia + spaces
                print('\n'+str_dia)
        elif data == data_anterior:
            pass
        else:
            dia_da_semana = dayNameFromWeekday(arr_data.weekday())
            str_dia = '__' + dia_da_semana + ' ' + data_curta
            spaces = '_'*(line_size-len(str_dia))
            str_dia = str_dia + spaces
            print('\n'+str_dia)
    
        if DARK_MODE:
            console.set_color(1, 1, 1)
        else:
            console.set_color(0, 0, 0)
        
        console.set_font("Menlo-Regular", TABLE_FONTSIZE)
        tempo, icone = formatar_tempo(tempo, icone, chuva, ahora)
        
        print(' ', ahora, temperatura, icone, tempo, nuvens_str)
        data_anterior = data
        
        
def mostra_estado_atual(localizacao):
    estado = get_weather_data(location=localizacao, kind='current')
    adata = arrow.get(estado['dt']).to('local')
    ahora = adata.to('local').format('HH')+'h'
    temperatura_int = int(estado['main']['temp'])
    temperatura = str(temperatura_int)+'°'
    tempo = estado['weather'][0]['description'].title()
    pressao = str(estado['main']['pressure'])+'hPa'
    
    if 'wind' in estado.keys():
        try:
            vento_dir = estado['wind']['deg']
            vento_veloc = estado['wind']['speed']
        except:
            vento_dir = 0
            vento_veloc = 0
    else:
        vento_dir = ''
        vento_veloc = 0
    # nuvens = estado['clouds']['all']
    str_tempo, icone = formatar_tempo(tempo, '', '', ahora)
        
    if 'rain' in estado.keys():
        if '3h' in estado['rain'].keys():
            tempo, chuva, icone = formatar_chuva(tempo,
                                                 estado['rain']['3h'],
                                                 '')
        else:
            chuva = ''
    else:
        chuva = ''
        
    nuvens_str = obter_nuvens(estado)
    humidade = obter_humidade(estado)
    
    adata_nascer = arrow.get(estado['sys']['sunrise']).to('local')
    ahora_nascer = adata_nascer.to('local').format('HH:mm')
    
    adata_por = arrow.get(estado['sys']['sunset']).to('local')
    ahora_por = adata_por.to('local').format('HH:mm')
    
    direcao, velocidade = converter_vento(vento_dir, vento_veloc)
    
    str_humidade = '{}Humidade: {}'.format(12*' ', humidade)
    str_pressao = 12*' ' + 'Pressão: ' + pressao
    str_vento = '\n{}Vento: {} {}km/h'.format(13*' ', direcao, str(velocidade))
    
    str_nascer = 'Amanhecer: ' + ahora_nascer + '         '
    str_por = 'Anoitecer: ' + ahora_por + '         '
    
    line_size = 56
    line1_spaces = ' '*(line_size-len(str_humidade)-len(str_nascer))
    line2_spaces = ' '*(line_size-len(str_pressao)-len(str_por))
    
    console.set_font("Menlo-bold", TODAY_FONTSIZE)
    print(4*' ', icone, temperatura)
    console.set_font("Menlo-Regular", TODAY_FONTSIZE2)
    
    line_size2 = 44
    str_line0 = '{} {} {}'.format(str_tempo, nuvens_str, chuva)
    line0_spaces = ' '*int((line_size2-len(str_line0))/2)
    print(line0_spaces, str_line0)
    
    console.set_font("Menlo-Regular", TABLE_FONTSIZE-1)
    print(str_vento)
    
    str1 = ' {}{}{}'.format(str_humidade, line1_spaces, str_nascer)
    str2 = ' {}{}{}'.format(str_pressao, line2_spaces, str_por)
    print(str1+'\n'+str2+'\n')
    

def formatar_chuva(tempo, que_chuva):
    chuva = str(que_chuva)
    fchuva = float(chuva)
    
    chuva = '({}mm/h)'.format(str(round(fchuva/3, 1)))
    icone = '🌧'
    
    if fchuva < .75:
        if tempo == 'Chuva Fraca':
            tempo = 'Possib. Chuva Fraca'
        icone = '☁️'
    elif .75 <= fchuva < 3:
        chuva += '💧'
    elif 3 <= fchuva < 12:
        chuva += '💧💧'
    elif 12 <= fchuva < 48:
        chuva += '💧💧💧'
    elif 48 <= fchuva:
        chuva += '💦💦☔️💦💦'
    return (tempo, chuva, icone)
        

if __name__ == "__main__":
    console.show_activity()
    if USE_LOCATION_SERVICES:
        localizacao = obter_localizacao()
    else:
        localizacao = LOCATION
    console.hide_activity()
    config_consola(localizacao)
    mostra_estado_atual(localizacao)
    mostra_previsao(localizacao)