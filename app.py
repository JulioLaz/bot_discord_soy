import os
import discord
from discord.ext import commands
import asyncio
import json
from datetime import datetime
import dash
from dash import html, dcc, Output, Input, State, dash_table
from dash.dependencies import Input, Output, State
import threading
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import logging
import requests  # Importa la librería requests
import time  # Importa time para usar en el bucle keep_alive
import pandas as pd


# https://docs.google.com/spreadsheets/d/10aQD-tiBCvQ2IxwVVvtszRdH11atIL6NEmyaxq_gs4o/edit?usp=sharing
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
SERVER_ID = 1273343475651317954
CHANNEL_IDS = [
    1292864959205867590,  # Canal 1
    1292865411892641952,  # Canal 2
    1292866910006018201,  # Canal 3
    1292867115077865583   # Canal 4
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

def keep_alive():
    while True:
        try:
            requests.get("https://bot-discord-soy.onrender.com/")  # Reemplaza con tu URL en Render
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
        time.sleep(1000)  # Realiza un ping cada 10 minutos

threading.Thread(target=keep_alive, daemon=True).start()


@bot.event
async def on_ready():
    logging.info(f'{bot.user} ha iniciado sesión!')
    server = bot.get_guild(SERVER_ID)
    if server:
        logging.info(f"Buscando en el servidor: {server.name}")
        for channel_id in CHANNEL_IDS:
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send("🙋‍♀️🙋‍♂️🙋 **Presentate:** 🙋‍♀️🙋‍♂️🙋\n\n Escribe lo siguiente y presiona enter: **!soy**")

@bot.command()
async def soy(ctx):
    if ctx.guild.id != SERVER_ID or ctx.channel.id not in CHANNEL_IDS:
        await ctx.send("Este comando solo puede ser usado en los canales designados para la encuesta.")
        return
    await iniciar_encuesta_personal(ctx.channel, ctx.author)

google_creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
if google_creds_json is None:
    logging.error("La variable de entorno 'GOOGLE_CREDENTIALS_JSON' no está configurada.")
else:
    logging.info("Variable de entorno 'GOOGLE_CREDENTIALS_JSON' cargada correctamente.")

creds_dict = json.loads(google_creds_json)
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open_by_key('10aQD-tiBCvQ2IxwVVvtszRdH11atIL6NEmyaxq_gs4o')
# sheet = client.open_by_key('1UTPCzSd5CFSptpjFgZtuDPAiFYU8TtZUbUJUl1WECh8')
worksheet = sheet.get_worksheet(0)


def guardar_en_google_sheetsoo(respuestas):
    try:
        # Ensure the row matches the headers in Google Sheets
        row = [
            respuestas.get('nombre', ''),
            respuestas.get('id_member', ''),
            respuestas.get('id_channel', ''),
            respuestas.get('timestamp', ''),
            respuestas.get(' - Nombre: ', ''),
            respuestas.get(' - Edad: ', ''),
            respuestas.get(' - País donde vives: ', ''),
            respuestas.get(' - Qué esperas de BX? ', ''),
            respuestas.get(' - comparte tu linkedin ', '')
        ]
        worksheet.append_row(row)
        logging.info(f"Datos guardados en Google Sheets: {row}")
    except Exception as e:
        logging.error(f"Error guardando en Google Sheets: {e}")


def guardar_en_google_sheets(respuestas):
    try:
        row = [respuestas.get('user_discord'), respuestas.get('id_member'),respuestas.get('id_channel'), respuestas.get('timestamp')]
        for key, value in respuestas.items():
            if key not in ['user_discord', 'id_member', 'id_channel', 'timestamp']:
                row.append(value)
        worksheet.append_row(row)
        logging.info(f"Datos guardados en Google Sheets: {row}")
    except Exception as e:
        logging.error(f"Error guardando en Google Sheets: {e}")

async def iniciar_encuesta_personal(channel, member):
    await channel.send(f"{member.mention}, por favor cuéntanos sobre ti!")
    preguntas = [
        "😁 - Nombre: ",
        "🔢 - Edad: ",
        "🌎 - País donde vives: ",
        "🤖 - Qué esperas de BX? ",
        "👉 - comparte tu linkedin ",
    ]
    respuestas = {
        "user_discord": member.name,
        "id_member": member.id,
        "id_channel": channel.id,
        "timestamp": datetime.now().isoformat()
    }
    for pregunta in preguntas:
        await channel.send(pregunta)
        def check(m):
            return m.author == member and m.channel == channel
        try:
            respuesta = await bot.wait_for('message', check=check, timeout=300.0)
            respuestas[pregunta] = respuesta.content
        except asyncio.TimeoutError:
            await channel.send(f"{member.mention} no respondió a tiempo.")
            respuestas[pregunta] = "No respondió"
    guardar_en_google_sheets(respuestas)
    await channel.send(f"👏👏👏 {member.mention} **¡Gracias por participar!** 😁👌")

bot_thread = None
bot_running = False

app = dash.Dash(
    __name__,
    title="BotMessage",
    external_stylesheets=[],
    assets_folder='assets'
)

server = app.server

# Estilos personalizados
table_styles = [
    {
        'selector': 'th',
        'rule': 'background-color: #007bff; color: white; text-align: center; font-weight: bold; padding: 10px;'
    },
    {
        'selector': 'td',
        'rule': 'text-align: center; padding: 10px;'
    },
    {
        'selector': 'tr:nth-child(even)',
        'rule': 'background-color: #f2f2f2;'
    }
]

app.layout = html.Div([
    html.H1("Panel de Control - Encuestas BX", style={'textAlign': 'center', 'color': '#007bff'}),
    html.Div([
        html.Button("Iniciar Bot", id="start-bot", className='start-bot', n_clicks=0, style={'margin': '10px', 'backgroundColor': '#28a745', 'color': 'white'}),
        html.Button("Detener Bot", id="stop-bot", n_clicks=0, disabled=True, className='stop-bot', style={'margin': '10px', 'backgroundColor': '#dc3545', 'color': 'white'}),
    ], style={'textAlign': 'center'}),
    html.Div(id='bot-status', style={'textAlign': 'center', 'margin': '20px', 'fontWeight': 'bold'}),
    html.H2("Resultados de la Encuesta", style={'textAlign': 'center', 'color': '#007bff'}),
    dash_table.DataTable(
        id='table',
        columns=[],
        data=[],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
        style_header={
            'backgroundColor': '#007bff',
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ],
    ),
    html.Div([
        html.Button("Descargar Tabla", id="download-btn", n_clicks=0, style={'margin': '10px', 'backgroundColor': '#007bff', 'color': 'white'}),
        dcc.Download(id="download-dataframe-csv"),        
    ], style={'textAlign': 'center'}),    
    dcc.Interval(
        id='interval-component',
        interval=5000,
        n_intervals=0
    ),
], style={'padding': '20px'})

# Función para obtener los datos de Google Sheets en formato de DataFrame
def obtener_datos_como_dataframe():
    headers, table_data = get_sheet_data()  # Tu función existente para obtener datos
    df = pd.DataFrame(table_data, columns=headers)
    return df

# Callback para manejar la descarga
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("download-btn", "n_clicks"),
    prevent_initial_call=True
)
def descargar_csv(n_clicks):
    df = obtener_datos_como_dataframe()
    
    return dcc.send_data_frame(df.to_csv, "datos_encuesta.csv", index=False)


column_names = {
    'nombre': 'user_discord',
    'id_member': 'id_member',
    'id_channel' : 'id_channel',
    'timestamp': 'timestamp',
    '😁 - Nombre: ': 'name',
    '🔢 - Edad: ': 'age',
    '🌎 - País donde vives: ': 'country',
    '🤖 - Qué esperas de BX? ': 'expectations',
    '👉 - comparte tu linkedin ': 'Linkedin'
}

def get_sheet_data():
    try:
        all_data = worksheet.get_all_values()
        headers = all_data[0]
        data = all_data[1:]
        
        # Usar los nombres de columnas personalizados
        headers = [column_names.get(h, h) for h in headers]
        
        table_data = [dict(zip(headers, row)) for row in data]
        
        logging.info(f"Encabezados obtenidos: {headers}")
        logging.info(f"Muestra de datos: {table_data[:2]}")
        return headers, table_data
    except Exception as e:
        logging.error(f"Error obteniendo datos de Google Sheets: {e}")
        return [], []

@app.callback(
    [Output('bot-status', 'children'),
     Output('start-bot', 'disabled'),
     Output('stop-bot', 'disabled'),
     Output('table', 'columns'),
     Output('table', 'data')],
    [Input('start-bot', 'n_clicks'),
     Input('stop-bot', 'n_clicks'),
     Input('interval-component', 'n_intervals')],
    [State('start-bot', 'disabled'),
     State('stop-bot', 'disabled')]
)
def update_bot_status_and_table(start_clicks, stop_clicks, n_intervals, start_disabled, stop_disabled):
    global bot_thread, bot_running
    
    ctx = dash.callback_context
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'start-bot' and not bot_running:
            bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
            bot_thread.start()
            bot_running = True
        elif button_id == 'stop-bot' and bot_running:
            bot_running = False
            if bot_thread:
                bot_thread.join(timeout=5)
    
    if bot_running:
        status = f"Estado del Bot: En línea - Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        start_disabled = True
        stop_disabled = False
    else:
        status = "Estado del Bot: Fuera de línea"
        start_disabled = False
        stop_disabled = True
    
    headers, table_data = get_sheet_data()
    columns = [{"name": i, "id": i} for i in headers]
    
    return status, start_disabled, stop_disabled, columns, table_data

def run_discord_bot():
    global bot_running
    asyncio.set_event_loop(asyncio.new_event_loop())
    bot.run(TOKEN)
    bot_running = False

if __name__ == '__main__':
    app.run_server(debug=True, host='127.0.0.1', port=int(os.getenv('PORT', 8080)))