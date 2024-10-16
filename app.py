import os
import discord
from discord.ext import commands
import asyncio
import json
from datetime import datetime
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import threading
from flask import request

# Configuración del bot de Discord
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

@bot.event
async def on_ready():
    print(f'{bot.user} ha iniciado sesión!')
    server = bot.get_guild(SERVER_ID)
    if server:
        print(f"Buscando en el servidor: {server.name}")

        # Enviar mensajes a los canales específicos
        for channel_id in CHANNEL_IDS:
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send("**EJECUTA EL SIGUIENTE COMANDO PARA CONOCER MÁS DE TI:**\n\n 👉 **!Soy**")
                print(f"Mensaje enviado al canal: {channel.name}")
            else:
                print(f"No se pudo encontrar el canal con ID {channel_id}")



@bot.command()
async def Soy(ctx):
    if ctx.guild.id != SERVER_ID or ctx.channel.id not in CHANNEL_IDS:
        await ctx.send("Este comando solo puede ser usado en los canales designados para la encuesta.")
        return
    
    await iniciar_encuesta_personal(ctx.channel, ctx.author)

async def iniciar_encuesta_personal(channel, member):
    await channel.send(f"{member.mention}, por favor cuéntanos sobre ti!")
    
    preguntas = [
        "😁 - Nombre: ",
        "🔢 - Edad: ",
        "🌎 - País donde vives: "
    ]
    
    respuestas = {
        "nombre": member.name,
        "id": member.id,
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
    
    filename = f'respuestas_{channel.id}.json'
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        
        data[str(member.id)] = respuestas
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        await channel.send(f"{member.mention}, ¡gracias por participar en la encuesta! Tus respuestas han sido guardadas.")
    except Exception as e:
        await channel.send(f"Ocurrió un error al guardar las respuestas: {str(e)}")
        print(f"Error al guardar respuestas: {str(e)}")

# Variables globales para controlar el estado del bot
bot_thread = None
bot_running = False

# Configuración de la aplicación Dash
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Bot de Discord - Panel de Control"),
    html.Div([
        html.Button("Iniciar Bot", id="start-bot", n_clicks=0),
        html.Button("Detener Bot", id="stop-bot", n_clicks=0, disabled=True),
    ]),
    html.Div(id='bot-status'),
    dcc.Interval(
        id='interval-component',
        interval=5000,  # actualiza cada 5 segundos
        n_intervals=0
    ),
])

@app.callback(
    [Output('bot-status', 'children'),
     Output('start-bot', 'disabled'),
     Output('stop-bot', 'disabled')],
    [Input('start-bot', 'n_clicks'),
     Input('stop-bot', 'n_clicks'),
     Input('interval-component', 'n_intervals')],
    [State('start-bot', 'disabled'),
     State('stop-bot', 'disabled')]
)
def update_bot_status(start_clicks, stop_clicks, n_intervals, start_disabled, stop_disabled):
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
        status = f"Bot status: Online - Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        start_disabled = True
        stop_disabled = False
    else:
        status = "Bot status: Offline"
        start_disabled = False
        stop_disabled = True
    
    return status, start_disabled, stop_disabled

def run_discord_bot():
    global bot_running
    asyncio.set_event_loop(asyncio.new_event_loop())
    bot.run(TOKEN)
    bot_running = False

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))