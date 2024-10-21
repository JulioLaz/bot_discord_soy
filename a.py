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

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

def parse_json_from_env(env_var_name):
    json_string = os.getenv(env_var_name)
    if not json_string:
        print(f"Environment variable {env_var_name} not found")
        return None
    json_string = json_string.replace('\n', '\\n')
    json_string = json_string.replace("'",'"')
   #  json_string = json_string.replace('\\n-----END PRIVATE KEY-----', '5MhVJJmHA+5iFmbnN+7Uel0=\\n-----END PRIVATE KEY-----')
    return json_string
creds_dict_00 = parse_json_from_env('GOOGLE_CREDENTIALS_JSON')
print('type: ',type(creds_dict_00))
print('creds_dict_00: ',creds_dict_00)
creds_dict = json.loads(creds_dict_00)

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open_by_key('10aQD-tiBCvQ2IxwVVvtszRdH11atIL6NEmyaxq_gs4o')
worksheet = sheet.get_worksheet(0)