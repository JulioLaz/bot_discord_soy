import os
import discord
from discord.ext import commands, tasks
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
import requests
import pandas as pd
import pytz

local_tz = pytz.timezone('America/Argentina/Buenos_Aires')
local_time_now = datetime.now(local_tz).strftime("%Y-%m-%d %H:%M")

KEEP_ALIVE_CHANNEL_ID = 1296836514457849947  # The channel ID for "yo"

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
SERVER_ID = 1273343475651317954
CHANNEL_IDS = [
    1292864959205867590,  # channel 1
    1292865411892641952,  # channel 2
    1292866910006018201,  # channel 3
    1292867115077865583,  # channel 4
    1296907360576606254,  # channel 5
    1296836514457849947   # yo
]

class KeepAliveBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        self.keep_alive.start()

    async def on_ready(self):
        logging.info(f'{self.user} ha iniciado sesión!')
        server = self.get_guild(SERVER_ID)
        if server:
            logging.info(f"Buscando en el servidor: {server.name}")
            for channel_id in CHANNEL_IDS:
                channel = self.get_channel(channel_id)
                if channel:
                    await channel.send("🙋‍♀️🙋‍♂️🙋 **Presentate:** 🙋‍♀️🙋‍♂️🙋\n\n Escribe lo siguiente y presiona enter: **!soy**")

    @tasks.loop(minutes=10)
    async def keep_alive(self):
        try:
            # Send a request to your Render URL
            requests.get("https://bot-discord-soy.onrender.com/")
            print("Keep-alive ping sent to Render")
            
            # Send a message to Discord
            channel = self.get_channel(KEEP_ALIVE_CHANNEL_ID)
            if channel:
                current_time = datetime.now(local_tz).strftime("%Y-%m-%d %H:%M")
                await channel.send(f"Keep alive - {current_time}")
                print("Keep-alive message sent to Discord")
            else:
                print(f"Error: Could not find channel with ID {KEEP_ALIVE_CHANNEL_ID}")
        except Exception as e:
            print(f"Error in keep_alive function: {e}")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = KeepAliveBot(command_prefix='!', intents=intents)

@bot.command()
async def soy(ctx):
    if ctx.guild.id != SERVER_ID or ctx.channel.id not in CHANNEL_IDS:
        await ctx.send("Este comando solo puede ser usado en los canales designados.")
        return
    await iniciar_encuesta_personal(ctx.channel, ctx.author)

def parse_json_from_env(env_var_name):
    json_string = os.getenv(env_var_name)
    if not json_string:
        print(f"Environment variable {env_var_name} not found")
        return None
    json_string = json_string.replace('\n', '\\n')
    json_string = json_string.replace("'",'"')
    # json_string = json_string.replace('\\n-----END PRIVATE KEY-----', '5MhVJJmHA+5iFmbnN+7Uel0=\\n-----END PRIVATE KEY-----')
    return json_string
creds_dict_00 = parse_json_from_env('GOOGLE_CREDENTIALS_JSON')
creds_dict = json.loads(creds_dict_00)

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open_by_key('10aQD-tiBCvQ2IxwVVvtszRdH11atIL6NEmyaxq_gs4o')
worksheet = sheet.get_worksheet(0)

def guardar_en_google_sheets(respuestas):
    try:
        row = [respuestas.get('user_discord'), respuestas.get('id_member'), respuestas.get(
            'id_channel'), respuestas.get('name_channel'), respuestas.get('timestamp')]
        for key, value in respuestas.items():
            if key not in ['user_discord', 'id_member', 'id_channel', 'name_channel', 'timestamp']:
                row.append(value)
        worksheet.append_row(row)
        logging.info(f"Datos guardados en Google Sheets: {row}")
    except Exception as e:
        logging.error(f"Error guardando en Google Sheets: {e}")

async def iniciar_encuesta_personal(channel, member):
    avatar_url = member.avatar.url
    await channel.send(f"**¡WELCOME, {member.mention}!**")
    await channel.send(avatar_url)   
    # await channel.send(f"{member.mention}, por favor cuéntanos sobre ti!")
    preguntas = [
        f"😁 **Cuál es tu nombre** {member.name}**:**",
        f"🔢 {member.mention} **tu Edad:**",
        f"🌎 {member.mention} **País donde vives:**",
        f"🤖 {member.mention} **Qué esperas de BX?**",
        f"👉 {member.mention} **Comparte tu linkedin**",
    ]
    respuestas = {
        "user_discord": member.name,
        "id_member": member.id,
        "id_channel": channel.id,
        "name_channel": channel.name,
        "timestamp": datetime.now(local_tz).strftime("%Y-%m-%d %H:%M")
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
    html.H1("Panel de Control - Encuestas BX",
            style={'textAlign': 'center', 'color': '#007bff'}),
    html.Div([
        html.Button("Iniciar Bot", id="start-bot", className='start-bot', n_clicks=0,
                    style={'margin': '10px', 'backgroundColor': '#28a745', 'color': 'white'}),
        html.Button("Detener Bot", id="stop-bot", n_clicks=0, disabled=True, className='stop-bot',
                    style={'margin': '10px', 'backgroundColor': '#dc3545', 'color': 'white'}),
    ], style={'textAlign': 'center'}),
    html.Div(id='bot-status',
             style={'textAlign': 'center', 'margin': '20px', 'fontWeight': 'bold'}),
    html.H2("Resultados de la Encuesta", style={
            'textAlign': 'center', 'color': '#007bff'}),
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
        html.Button("Descargar Tabla", id="download-btn", n_clicks=0,
                    style={'margin': '10px', 'backgroundColor': '#007bff', 'color': 'white'}),
        dcc.Download(id="download-dataframe-csv"),
    ], style={'textAlign': 'center'}),
    dcc.Interval(
        id='interval-component',
        interval=5000,
        n_intervals=0
    ),
], style={'padding': '20px'})

def obtener_datos_como_dataframe():
    headers, table_data = get_sheet_data()
    df = pd.DataFrame(table_data, columns=headers)
    return df

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
    'id_channel': 'id_channel',
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
        status = f"Estado del Bot: En línea\ninicio: {local_time_now} - actual: {datetime.now(local_tz).strftime('%Y-%m-%d %H:%M')}"
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
    # Iniciar el bot en un hilo separado
    bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
    bot_thread.start()
    
    # Ejecutar la aplicación Dash
    app.run_server(debug=True, host='127.0.0.1', port=int(os.getenv('PORT', 8080)))
