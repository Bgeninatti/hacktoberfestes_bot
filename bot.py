import asyncio
import csv
import os
from enum import Enum

import discord
import pandas as pd
from config import load_config
from discord.ext import commands
from logger import get_logger

LOGGER = get_logger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config = load_config()

TOKEN = config["DEFAULT"]["Token"]
GUILD = int(config["DEFAULT"]["Guild"])
CHANNEL = config["DEFAULT"]["Channel"]
ADMIN_CHANNEL = config["DEFAULT"]["AdminChannel"]
ROLE = config["DEFAULT"]["Role"]
WORKSHOP_ROLE = config["DEFAULT"]["WorkshopRole"]

VALIDATION_FIELD = config["DEFAULT"]["ValidationField"]

LIST_FILE = os.path.join(BASE_DIR, config['DEFAULT']['List'])
ATTENDANCE_FILE = os.path.join(BASE_DIR, 'ready.csv')
WORKSHOP_FILE = os.path.join(BASE_DIR, config['DEFAULT']['WorkshopList'])
WORKSHOP_READY_FILE = os.path.join(BASE_DIR, 'workshop_ready.csv')


bot = commands.Bot(command_prefix="\\")

# --> UTILS

def load_rids(list_file):
    rids = set(pd.read_csv(list_file, encoding='iso-8859-1')[VALIDATION_FIELD].str.lower())
    return rids

class RegistrationStatus(Enum):
    OK = 0
    NOT_FOUND = 1
    ALREADY_REGISTERED = 2


def get_ready_tickets(attendance_file):
    registered = set()
    with open(attendance_file, "r") as f:
        reader = csv.reader(f)
        registered = set(line[0] for line in reader)
    return registered


def register_user(ticket_id, msg, rids, attendance_file):
    registered = get_ready_tickets(attendance_file)
    remaining = rids - registered
    if ticket_id in remaining:
        with open(attendance_file, "a") as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow([ticket_id, msg.author, msg.created_at])
        return RegistrationStatus.OK
    elif ticket_id in registered:
        return RegistrationStatus.ALREADY_REGISTERED
    else:
        return RegistrationStatus.NOT_FOUND


# --> Event Registration

@bot.command(name="estado", help="Comando para ver el estado actual de regitros", pass_context=True)
async def estado(ctx):
    if str(ctx.channel) == ADMIN_CHANNEL:
        registered = get_ready_tickets(ATTENDANCE_FILE)
        rids = load_rids(LIST_FILE)
        total = len(rids)
        ready = len(registered)
        msg = f"Registros {ready}/{total} ({(ready/total)*100:.1f}%)"
        LOGGER.info("Registration status", extra={'ready': ready, 'total': total})
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
    server = bot.get_guild(GUILD)
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

        rids = load_rids(LIST_FILE)
        status = register_user(ticket_id.lower(), ctx.message, rids, ATTENDANCE_FILE)

        LOGGER.info("Status resolved",
                     extra={'author': ctx.author.name, 'status': status})

        if status == RegistrationStatus.OK:
            msg = f"Listo {ctx.message.author.mention}! Ahora deberías poder ver todos los canales en el servidor del evento :D"
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

# --> Workshop Registration

@bot.command(name="estado_taller", help="Comando para ver el estado actual de regitros a los talleres", pass_context=True)
async def estado_taller(ctx):
    if str(ctx.channel) == ADMIN_CHANNEL:
        registered = get_ready_tickets(WORKSHOP_READY_FILE)
        rids = load_rids(WORKSHOP_FILE)
        total = len(rids)
        ready = len(registered)
        msg = f"Registros {ready}/{total} ({(ready/total)*100:.1f}%)"
        LOGGER.info("Registration status", extra={'ready': ready, 'total': total})
        await ctx.send(msg)

@bot.command(name="taller", help="Comando para darte de alta en el taller", pass_context=True)
async def taller(ctx, email):
    LOGGER.info("Command received", extra={'author': ctx.author.name})

    # FIXME: This piece of code will be repeated in all the PM commands
    if not isinstance(ctx.channel, discord.DMChannel):
        LOGGER.error("Command must be sent as private message",
                     extra={'author': ctx.author.name})
        return

    LOGGER.info("Searching group member for user", extra={'author': ctx.author.name})
    # Load the server
    server = bot.get_guild(GUILD)
    # FIXME: This obscure hack to update the member list
    server._members = {m.id: m async for m in server.fetch_members()}
    # Load special role to give permissions
    member = server.get_member(ctx.message.author.id)

    # -- End of repeated code ---

    role = discord.utils.get(server.roles, name=WORKSHOP_ROLE)

    msg = None

    if not member:
        LOGGER.error("User is not member of the PyConAr server",
                     extra={'author': ctx.author.name})
        msg = f"Tenes que ingresar al server de PyConAr 2020 antes de darte de alta en el taller."
        await ctx.send(msg)
    else:
        LOGGER.info("Resolving status", extra={'author': ctx.author.name})

        rids = load_rids(WORKSHOP_FILE)
        status = register_user(email.lower(), ctx.message, rids, WORKSHOP_READY_FILE)

        LOGGER.info("Status resolved",
                     extra={'author': ctx.author.name, 'status': status})

        if status == RegistrationStatus.OK:
            msg = f"Listo {ctx.message.author.mention}! Ahora deberías poder ver el canal de audio en la categoría Talleres. Recordá que el taller comienza el Miércoles 18 a las 16hs."
            # TODO: Check if user already has the role
            await member.add_roles(role)

            # Send final response
            await ctx.send(msg)
        elif status == RegistrationStatus.ALREADY_REGISTERED:
            msg = "Ese mail ya fue usado para registrarse al taller."
            await ctx.send(msg)
        elif status == RegistrationStatus.NOT_FOUND:
            msg = "No tenemos registrado ese mail dentro de los asistentes al taller del Miércoles 18 a las 16hs"
            await ctx.send(msg)
        else:
            # This should never happens, I Promise
            pass



# Removing help command
bot.remove_command("help")

# Starting the bot
bot.run(TOKEN)
