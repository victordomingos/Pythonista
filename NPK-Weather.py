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
import threading

from queue import Queue
from objc_util import ObjCInstance, ObjCClass, ObjCBlock, c_void_p

__app_name__ = "The NPK Weather App"
__author__ = "Victor Domingos"
__copyright__ = "© 2017 Victor Domingos"
__license__ = "Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)"
__version__ = "1.3"
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
USE_BAROMETER = True

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

pressure = None


def config_consola(localizacao):
    '''
    Sets console font size and color for Pythonista on iOS
    '''
    console.clear()
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
    print(f'{__copyright__}, {__license__}\n\n')


def obter_localizacao():
    try:
        console.show_activity()
        location.start_updates()
        coordinates = location.get_location()
        location.stop_updates()
        console.hide_activity()
        results = location.reverse_geocode(coordinates)
        cidade = results[0]['City']
        pais = results[0]['CountryCode']
        return f'{cidade},{pais}'
    except Exception:
        print('Não foi possível obter a localização atual.'
              '\nA utilizar predefinição...\n')
        console.hide_activity()
        return LOCATION


def get_pressure():
    ''' Obter a pressão atmosférica do barómetro do próprio dispositivo, se
    existir '''

    def handler(_cmd, _data, _error):
        global pressure
        pressure = ObjCInstance(_data).pressure()

    handler_block = ObjCBlock(
        handler, restype=None, argtypes=[c_void_p, c_void_p, c_void_p])

    CMAltimeter = ObjCClass('CMAltimeter')
    NSOperationQueue = ObjCClass('NSOperationQueue')
    if not CMAltimeter.isRelativeAltitudeAvailable():
        # print('This device has no barometer.')
        return None
    altimeter = CMAltimeter.new()
    main_q = NSOperationQueue.mainQueue()
    altimeter.startRelativeAltitudeUpdatesToQueue_withHandler_(
        main_q, handler_block)

    try:
        while pressure is None:
            pass
    finally:
        altimeter.stopRelativeAltitudeUpdates()
        return pressure.floatValue() * 7.5006375541921


def obter_estado_atual(q, localizacao):
    estado_atual = get_weather_data(location=localizacao, kind='current')
    q.put(estado_atual)


def obter_previsoes(q, localizacao):
    previsoes = get_weather_data(location=localizacao, kind='forecast')['list']
    q.put(previsoes)


def dayNameFromWeekday(weekday):
    days = [
        "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
        "Sexta-feira", "Sábado", "Domingo"
    ]
    return days[weekday] if -1 < weekday < len(days) else None


def converter_vento(graus, metros_p_segundo):
    if graus != 0:
        direcoes = ["N", "NE", "E", "SE", "S", "SO", "O", "NO", "N"]
        posicao = int((graus + 57.5) / 45) - 1
        kmph = int(metros_p_segundo * 3.6)
        return (direcoes[posicao], kmph)
    else:
        return ('', 0)


def obter_nuvens(json):
    nuvens_str = ''
    if 'clouds' in json.keys():
        nuvens = json['clouds']['all']
        if nuvens == 0:
            return ''
        nuvens_str = 'N.' + str(nuvens) + '%'
    return nuvens_str


def obter_humidade(json):
    humidade_str = ''
    if 'humidity' in json['main'].keys():
        humidade = json['main']['humidity']
        if humidade == 0:
            return ''
        humidade_str = 'H.' + str(humidade) + '%'
    return humidade_str


def formatar_tempo(tempo, icone, chuva, ahora):
    tempo = tempo.replace('Garoa Fraca', 'Possib. Chuviscos Fracos')
    tempo = tempo.replace('Nuvens Quebrados', 'Céu Muito Nublado')

    if tempo == 'Céu Claro':
        tempo = 'Céu Limpo'
        if ahora in ('22h', '01h', '04h'):
            icone = '🌙'
        else:
            icone = '☀️'
    elif tempo == 'Céu Muito Nublado':
        icone = '☁️'
    elif tempo in ('Algumas Nuvens', 'Nuvens Dispersas'):
        tempo = 'Céu Pouco Nublado'
        icone = '⛅️'
    elif ('Nublado' in tempo) or ('Possib. Chuviscos Fracos' in tempo):
        icone = '☁️'
    elif ('Neblina' in tempo):
        icone = '🌤'
    elif ('Névoa' in tempo):
        icone = '🌤'
    elif tempo == 'Chuva De Intensidade Pesado':
        tempo = 'Chuva Forte'

    if ('Chuva' in tempo) or ('Chuviscos' in tempo):
        tempo = tempo + ' ' + chuva

    return (tempo, icone)


def set_weekday_font():
    console.set_font("Menlo-Bold", TITLE_FONTSIZE)
    if DARK_MODE:
        console.set_color(0.5, 0.8, 1)
    else:
        console.set_color(0.2, 0.5, 1)


def set_forecast_font():
    if DARK_MODE:
        console.set_color(1, 1, 1)
    else:
        console.set_color(0, 0, 0)

    console.set_font("Menlo-Regular", TABLE_FONTSIZE)


def get_weather_data(location=None, kind='forecast'):
    if kind == 'forecast':
        api_URL = API_URL
    else:
        api_URL = API_URL_CURRENT

    try:
        console.show_activity()
        params = {
            'q': location,
            'APPID': APIKEY,
            'units': 'metric',
            'lang': 'pt',
            'mode': 'json'
        }

        json_data = requests.get(api_URL, params=params, timeout=(2, 5)).json()
        console.hide_activity()
        return json_data

    except Exception as e:
        print(e)
        console.hide_activity()
        sys.exit(1)


def mostra_previsao(previsoes):
    aagora = arrow.now()

    data_anterior = txt_previsao = nova_linha = ''

    for previsao in previsoes:
        icone = chuva = ''
        data = previsao['dt_txt'].split()[0]

        adata = arrow.get(previsao['dt']).to('local')
        ahora = adata.to('local').format('HH') + 'h'

        hoje = arrow.now().date().day
        adata_dia = adata.date().day

        if (adata - aagora <= datetime.timedelta(hours=+24)):
            show_more_info = True
        else:
            show_more_info = False

        if (not DETAILED) and (not show_more_info):
            if ahora in ('04h', '03h', '07h', '06h', '22h', '23h', '01h',
                         '00h'):
                if (ahora is '01h'):
                    data_anterior = data
                continue

        temperatura_int = int(previsao['main']['temp'])
        temperatura = f'{str(temperatura_int).rjust(2)}°'
        tempo = previsao['weather'][0]['description'].title()

        arr_data = arrow.get(data)
        data_curta = arr_data.format('DD/MM')

        if 'rain' not in previsao.keys():
            chuva = ''
        elif '3h' in previsao['rain'].keys():
            tempo, chuva, icone = formatar_chuva(tempo, previsao['rain']['3h'])

        nuvens_str = obter_nuvens(previsao)
        # humidade = obter_humidade(previsao)

        line_size = 48
        str_dia = spaces = ''

        if data_anterior == '':
            if hoje == adata_dia:
                str_dia = '__Hoje ' + data_curta
                spaces = '_' * (line_size - len(str_dia))
                str_dia = str_dia + spaces
                set_weekday_font()
                print('\n' + str_dia)
                txt_previsao = ''
                nova_linha = ''
            else:
                str_dia = '__Amanhã (' + data_curta + ')'
                spaces = '_' * (line_size - len(str_dia))
                str_dia = str_dia + spaces
                set_forecast_font()
                print(txt_previsao)
                set_weekday_font()
                print('\n' + str_dia)
                txt_previsao = ''
                nova_linha = ''
        elif data == data_anterior:
            nova_linha = '\n'
        else:
            dia_da_semana = dayNameFromWeekday(arr_data.weekday())
            str_dia = '__' + dia_da_semana + ' ' + data_curta
            spaces = '_' * (line_size - len(str_dia))
            str_dia = str_dia + spaces
            set_forecast_font()
            print(txt_previsao)
            set_weekday_font()
            print('\n' + str_dia)
            txt_previsao = ''
            nova_linha = ''

        tempo, icone = formatar_tempo(tempo, icone, chuva, ahora)

        txt_previsao = f'{txt_previsao}{nova_linha}  {ahora} {temperatura} {icone} {tempo} {nuvens_str}'
        data_anterior = data

    set_forecast_font()
    print(txt_previsao)


def mostra_estado_atual(estado):
    adata = arrow.get(estado['dt']).to('local')
    ahora = adata.to('local').format('HH') + 'h'
    temperatura_int = int(estado['main']['temp'])
    temperatura = str(temperatura_int) + '°'
    tempo = estado['weather'][0]['description'].title()

    pressao_ = None
    mens_barometro = ""

    if USE_BAROMETER:
        try:
            pressao_ = get_pressure()
            mens_barometro = "(Barómetro do dispositivo)"
        except:
            pressao_ = float(estado['main']['pressure']) * 0.75006375541921
    else:
        pressao_ = float(estado['main']['pressure']) * 0.75006375541921

    pressao = f'{pressao_:.2f}mmHg'

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

    if 'rain' not in estado.keys():
        chuva = ''
    elif '3h' in estado['rain'].keys():
        tempo, chuva, icone = formatar_chuva(tempo, estado['rain']['3h'])

    nuvens_str = obter_nuvens(estado)
    humidade = obter_humidade(estado)

    adata_nascer = arrow.get(estado['sys']['sunrise']).to('local')
    ahora_nascer = adata_nascer.to('local').format('HH:mm')

    adata_por = arrow.get(estado['sys']['sunset']).to('local')
    ahora_por = adata_por.to('local').format('HH:mm')

    direcao, velocidade = converter_vento(vento_dir, vento_veloc)

    str_humidade = f'{6*" "}💦 Humidade: {humidade}'
    str_pressao = 6 * ' ' + '🕛 Pressão: ' + pressao
    str_vento = f'\n{7*" "}💨 Vento: {direcao} {str(velocidade)}km/h\n'

    str_nascer = f'☀️ Amanhecer: {ahora_nascer}    '
    str_por = f'🌙 Anoitecer: {ahora_por}     '

    line_size = 56
    line1_spaces = ' ' * (line_size - len(str_humidade) - len(str_nascer))
    line2_spaces = ' ' * (line_size - len(str_pressao) - len(str_por))

    console.set_font("Menlo-bold", TODAY_FONTSIZE)
    if DARK_MODE:
        console.set_color(1, 1, 1)
    else:
        console.set_color(0, 0, 0)

    print(4 * ' ', icone, temperatura)
    console.set_font("Menlo-Regular", TODAY_FONTSIZE2)

    line_size2 = 44
    str_line0 = '{} {} {}'.format(str_tempo, nuvens_str, chuva)
    line0_spaces = ' ' * int((line_size2 - len(str_line0)) / 2)
    print(line0_spaces, str_line0)

    console.set_font("Menlo-Regular", TABLE_FONTSIZE - 1)

    str1 = f' {str_humidade}{line1_spaces}{str_nascer}\n'
    str2 = f' {str_pressao}{line2_spaces}{str_por}'
    print(str_vento + str1 + str2)
    console.set_font("Menlo-Regular", 6.7)

    if DARK_MODE:
        console.set_color(0.7, 0.7, 0.7)
    else:
        console.set_color(0.5, 0.5, 0.5)

    if USE_BAROMETER:
        print(f"{14*' '}{mens_barometro}\n")
    else:
        print('')


def formatar_chuva(tempo, que_chuva):
    chuva = str(que_chuva)
    fchuva = float(chuva)

    chuva = f'({str(round(fchuva / 3, 1))}mm/h)'
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
    q_estado_atual = Queue()
    q_previsoes = Queue()

    if USE_LOCATION_SERVICES:
        localizacao = obter_localizacao()
    else:
        localizacao = LOCATION
    config_consola(localizacao)

    daemon1 = threading.Thread(
        target=obter_estado_atual, args=(q_estado_atual, localizacao))
    daemon1.setDaemon(True)
    daemon1.start()

    daemon2 = threading.Thread(
        target=obter_previsoes, args=(q_previsoes, localizacao))
    daemon2.setDaemon(True)
    daemon2.start()

    q_estado_atual.join()
    q_previsoes.join()

    estado_atual = q_estado_atual.get()
    previsoes = q_previsoes.get()

    mostra_estado_atual(estado_atual)
    mostra_previsao(previsoes)