import asyncio
import configparser
import csv
import os
from enum import Enum

import discord
import pandas as pd
from discord.ext import commands
from logger import get_logger

LOGGER = get_logger(__name__)
BASE_DIR = os.path.dirname(__name__)
CONFIG_FILE = os.path.join(BASE_DIR, 'config.ini')


if os.path.exists("config.ini"):
    # This is for local deploy with a config file
    config = configparser.ConfigParser()
    config.read("config.ini")
else:
    # This is for Heroku where configvars are set as environ variables
    config = {
        "DEFAULT": {
            "Token": os.environ.get("Token"),
            "Guild": os.environ.get("Guild"),
            "Channel": os.environ.get("Channel"),
            "AdminChannel": os.environ.get("AdminChannel"),
            "Role": os.environ.get("Role"),
            "List": os.environ.get("List"),
            "ValidationField": os.environ.get("ValidationField")
        }
    }


TOKEN = config["DEFAULT"]["Token"]
GUILD = config["DEFAULT"]["Guild"]
CHANNEL = config["DEFAULT"]["Channel"]
ADMIN_CHANNEL = config["DEFAULT"]["AdminChannel"]
ROLE = config["DEFAULT"]["Role"]
VALIDATION_FIELD = config["DEFAULT"]["ValidationField"]

LIST_FILE = os.path.join(BASE_DIR, config['DEFAULT']['List'])
ATTENDANCE_FILE = os.path.join(BASE_DIR, 'ready.csv')

RIDS = set(pd.read_csv(LIST_FILE)[VALIDATION_FIELD].str.lower())

bot = commands.Bot(command_prefix="\\")

class RegistrationStatus(Enum):
    OK = 0
    NOT_FOUND = 1
    ALREADY_REGISTERED = 2


def get_ready_tickets():
    registered = set()
    with open(ATTENDANCE_FILE, "r") as f:
        reader = csv.reader(f)
        try:
            registered = set(line[0] for line in reader)
        except ValueError:
            print("Error converting lines to integeres")
    return registered


def register_user(ticket_id, msg):
    registered = get_ready_tickets()
    remaining = RIDS - registered
    if ticket_id in remaining:
        with open(ATTENDANCE_FILE, "a") as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow([ticket_id, msg.author, msg.created_at])
        return RegistrationStatus.OK
    elif ticket_id in registered:
        return RegistrationStatus.ALREADY_REGISTERED
    else:
        return RegistrationStatus.NOT_FOUND


@bot.command(name="estado", help="Comando para ver el estado actual de regitros", pass_context=True)
async def estado(ctx):
    if str(ctx.channel) == ADMIN_CHANNEL:
        registered = get_ready_tickets()
        total = len(RIDS)
        ready = len(registered)
        msg = f"Registros {ready}/{total} ({(ready/total)*100:.1f}%)"
        await ctx.send(msg)


@bot.command(name="registro", help="Comando de registro", pass_context=True)
async def registro(ctx, ticket_id: str):

    LOGGER.info("Command received", extra={'author': ctx.author.name})

    if not isinstance(ctx.channel, discord.DMChannel):
        LOGGER.error("Command must be sent as private message",
                     extra={'author': ctx.author.name})
        return

    LOGGER.info("Searching group member for user", extra={'author': ctx.author.name})
    # Load the server
    server = bot.get_guild(int(GUILD))
    # FIXME: This obscure hack to update the member list
    server._members = {m.id: m async for m in server.fetch_members()}
    # Load special role to give permissions
    role = discord.utils.get(server.roles, name=ROLE)
    member = server.get_member(ctx.message.author.id)

    msg = None

    if not member:
        LOGGER.error("User is not member of the PyConAr server",
                     extra={'author': ctx.author.name})
        msg = f"Tenes que ingresar al server de PyConAr 2020 antes de registrarte."
        await ctx.send(msg)
    else:
        LOGGER.info("Resolving status", extra={'author': ctx.author.name})

        status = register_user(ticket_id.lower(), ctx.message)

        LOGGER.error("Status resolved",
                     extra={'author': ctx.author.name, 'status': status})

        if status == RegistrationStatus.OK:
            msg = f"Usuario {ctx.message.author.mention} registrado! :)"
            # TODO: Check if user already has the role
            await member.add_roles(role)

            # Send final response
            await ctx.send(msg)
        elif status == RegistrationStatus.ALREADY_REGISTERED:
            msg = "Ticket ya registrado"
            await ctx.send(msg)
        elif status == RegistrationStatus.NOT_FOUND:
            msg = "El ticket no existe. Estas seguro que lo ingresaste correctamente?"
            await ctx.send(msg)
        else:
            # This should never happens, I Promise
            pass

# Removing help command
bot.remove_command("help")

# Starting the bot
bot.run(TOKEN)
