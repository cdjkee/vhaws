#!/usr/bin/env python

import logging
from typing import Dict

from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PicklePersistence,
    filters,
    CallbackQueryHandler
)
from telegram.constants import ParseMode
from typing import Final
from functools import partial
import psutil
import subprocess
import signal
import aiofiles 
import asyncio
import os
import asyncio, asyncssh, sys
from functools import wraps

from config import valheimlog, server_proc_name, server_base_dir, ghaddress, ghusername

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("asyncssh").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
threads=[]
online=[]           #list of players steamids
#status='Stopped'
notifylist=[]       #list of userids to notify aout server events.
kbdConfirm = [
        [InlineKeyboardButton(text="kill",callback_data="kill")]
    ]
kbd = [
        [InlineKeyboardButton(text="Run Host",callback_data="RunHost")],
        [InlineKeyboardButton(text="Stop Host",callback_data="StopHost")],
        [InlineKeyboardButton(text="Run Modded",callback_data="RunModded")],
        [InlineKeyboardButton(text="Run Vanilla",callback_data="RunVanilla")],
        [InlineKeyboardButton(text="Status",callback_data="Status")],
        [InlineKeyboardButton(text="Stop",callback_data="Stop")],
        [InlineKeyboardButton(text="Online",callback_data="Online")],
        [InlineKeyboardButton(text="Button",callback_data="Button")]
    ]
kbdDesktop = [
        [InlineKeyboardButton(text="Run Modded",callback_data="RunModded"),InlineKeyboardButton(text="Run Vanilla",callback_data="RunVanilla")],
        [InlineKeyboardButton(text="Status",callback_data="Status"),InlineKeyboardButton(text="Online",callback_data="Online")],
        [InlineKeyboardButton(text="Stop",callback_data="Stop")],
        
    ]
KbdConfirmMarkupInline = InlineKeyboardMarkup(kbdConfirm)
ControlPanelMarkupReply = ReplyKeyboardMarkup(kbd)
ControlPanelMarkupReplyDesktop = ReplyKeyboardMarkup(kbdDesktop)

TOKEN:Final = os.environ.get('TOKENTG')
ADMINIDS:Final = os.environ.get('ADMINIDS')

print(f'TOKEN={TOKEN} and ADMINIDS={ADMINIDS}')
if(not (TOKEN and ADMINIDS)):
    print('Both TOKEN and ADMINIDS is necessary to run the bot. Supply them as environment variables and start the bot.')
    exit(1)
# WRAPPERS    
#wrapper for admin functions
def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id not in ADMINIDS:
            print(f"Unauthorized access denied for {user_id}.")
            await context.bot.send_message(chat_id = user_id, text="You are not allowed to use admin functions.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

#asyncssh connection
async def connect_ssh():
    connection = await asyncssh.connect(ghaddress, known_hosts=None, username=ghusername, client_keys=['/home/cdjkee/.ssh/id_rsa'])
    return connection

#GENERAL COMMAND HANDLERS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if str(update.effective_user.id) in ADMINIDS:
        reply_text = 'Hello, Admin!\nWelcome to Valheim Dedicated Server Control Bot\n/control gives you server control panel.'
    reply_text = 'Hello, user!\nWelcome to Valheim Dedicated Server Control Bot\n/control gives you server control panel.'
    await update.message.reply_text(reply_text,reply_markup=ControlPanelMarkupReply)  
    
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Control panel removed\n/start to get it again.',reply_markup=ReplyKeyboardRemove())
    
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text =  'List of commands, those marked with an asterisk require admin rights:' \
        '\n/control gives you server control panel' \
        '\n*/run starts the server' \
        '\n*/stop stops the server' \
        '\n/status gives you current status of server, if it starting, stopping and etc.' \
        '\n/online shows who online' \
        '\n/sw_layout switches server control panel layout to mobile or desktop' \
        '\n/cancel removes control panel'
    await update.message.reply_text(text)

#function sends control inline keyboard
async def send_control_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    layout = context.user_data.get('layout')
    if not layout:
        context.user_data["layout"] = 'mobile'
        layout = 'mobile'
    if layout == 'mobile':
        markup = ControlPanelMarkupReply
    if layout == 'desktop':
        markup = ControlPanelMarkupReplyDesktop

    await context.bot.send_message(chat_id = context._user_id, text='Control panel', reply_markup=markup)
    return 0

#switch control panel's layout
async def switch_layout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    layout = context.user_data.get('layout')
    if layout == 'mobile':
        context.user_data["layout"] = 'desktop'
    if layout == 'desktop':
        context.user_data["layout"] = 'mobile'
    await send_control_panel(update, context)
    
#SERVER MANAGEMENT FUNCTIONS
#TODO:RESTART
@restricted
async def request_server_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answers={
        0:'Shutdown process initiated',
        1:'Server has already stopped',
        2:'Server stop error'
    }
    result=answers.get(await server_stop())
    await context.bot.send_message(chat_id = context._user_id, text=result)

async def server_stop() -> int:
        status =  await server_status()
        if (status == "0"):
            print ("Server is stopped. PID = 0")
            return 1
        conn = await connect_ssh()
        result = await conn.run("kill $(ps -d | grep MainValheimThre | awk '{print $1}')", check=True)
        if not (result.stdout):
            return 0
        else:
            return 2
    
@restricted
async def request_server_run(update: Update, context: ContextTypes.DEFAULT_TYPE, mode='vanilla') -> int:
    answers={
        0:f'{mode} server starting process initiated',
        1:f'{mode} server is running',
        2:f'{mode} server start error'
    }
    # await context.bot.send_message(chat_id = context._user_id, text="Let's start the server")
    result=answers.get(await server_run(mode))
    await context.bot.send_message(chat_id = context._user_id, text=result)

async def server_run(mode) -> int:
        status =  await server_status()
        if not (status == "0"):
            print (f"Server is running. PID {status}")
            return 1
        conn = await connect_ssh()
        result = await conn.run(f'cd {server_base_dir};nohup ./start-test.sh > server.log 2>err.log &', check=True)
        if (not result.stdout):
            return 0
        else:
            return 2

@restricted
async def request_host_run(update: Update, context: ContextTypes.DEFAULT_TYPE, mode='vanilla') -> int:
    answers={
        0:f'{mode} server starting process initiated',
        1:f'{mode} server is running',
        2:f'{mode} server start error'
    }
    result=answers.get(await host_run(mode))
    await context.bot.send_message(chat_id = context._user_id, text=result)

async def host_run(mode) -> int:
    pass


@restricted
async def request_host_stop(update: Update, context: ContextTypes.DEFAULT_TYPE, mode='vanilla') -> int:
    answers={
        0:f'{mode} server starting process initiated',
        1:f'{mode} server is running',
        2:f'{mode} server start error'
    }
    result=answers.get(await host_stop(mode))
    await context.bot.send_message(chat_id = context._user_id, text=result)

async def host_stop(mode) -> int:
    pass

async def server_status() -> str:
    conn = await connect_ssh()
    result = await conn.run("ps -d | grep MainValheimThre | awk '{print $1}'", check=True)

    if (result.stdout):
        return result.stdout
    else:
        return "0"


async def request_server_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id = context._user_id, text=await server_status())
    

########################################

async def request_server_online(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(chat_id = context._user_id, text=server_online())

def server_online() -> str:
    #TODO: list online players with names
    return(f"{len(online)} player(s)")

#function sends a message with kill button (callback server_kill). Message will dissapear in 5 seconds.
@restricted
async def request_server_kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    term_msg = await context.bot.send_message(
        reply_markup=KbdConfirmMarkupInline,
        chat_id= context._user_id,
        text='Are you sure want to kill server? ' \
              'It may cause problem such as currupted save file and even ruin world completely.' \
              'This message will dissapear in 5 seconds.'
        )
    context.job_queue.run_once(callback=delete_message,when=5,chat_id=term_msg.chat_id,data=term_msg.message_id)

async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.delete_message(chat_id=job.chat_id, message_id=job.data)

async def process_control_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text
    # await query.answer()
    # await context.bot.send_message(chat_id = context._user_id, text=f'Processing command {query.data}')
    if command == 'Status':
        #await context.bot.send_message(chat_id = context._user_id, text=request_server_status())
        await request_server_status(update, context)
    if command == 'Run Modded':
        # await context.bot.send_message(chat_id = context._user_id, text=request_server_run(update, context))
        await request_server_run(update, context, mode = 'modded')
    if command == 'Run Vanilla':
        # await context.bot.send_message(chat_id = context._user_id, text=request_server_run(update, context))
        await request_server_run(update, context, mode = 'vanilla')
    if command == 'Stop':
        # await context.bot.send_message(chat_id = context._user_id, text=request_server_stop(update, context))
        await request_server_stop(update, context)
    if command == 'Online':
        # await context.bot.send_message(chat_id = context._user_id, text=request_server_online())
        await request_server_online(update, context)
    if command == 'Button':
        await request_server_online(update, context)

async def log_process() -> None:
    conn = await connect_ssh()
    async with conn.create_process(f'tail -f -n +1 {valheimlog}') as proc:
        async for line in proc.stdout:
            # print(f"{line}",end='')
            if(not line):
            #print('wait')
                await asyncio.sleep(0.1)
            else:
                # line = str(line)
                # print(line)
                if 'Got handshake from client' in line:
                    steamid = line.split()[-1]
                    if steamid not in online:
                        online.append(steamid)
                        print(f'CONNECTION DETECTED {steamid}')
                if 'Closing socket' in line:
                    steamid = line.split()[-1]
                    if steamid in online:
                        online.remove(steamid)
                        print(f'USER DISCONNECTED {steamid}')
                if 'Shuting down' in line:
                    # status = 'Stopping'
                    print(f'SERVER STARTED SHUT DOWN AT {line.split(" ",2)[1]}')
                if 'Net scene destroyed' in line:
                    # status = 'Stopped'
                    online.clear()
                    print(f'SERVER SHUT DOWN COMPLETELY AT {line.split(" ",2)[1]}')
                if 'Mono config path' in line:
                    # status = 'Starting'
                    print(f'SERVER STARTING')
                if 'Game server connected failed' in line:
                    # status = 'Starting'
                    print(f'STARTING ERROR')
                if 'Game server connected\n' in line:
                    # status = 'Online'
                    print(f'SERVER ONLINE')
    

async def main():
    #Application setup
    # Create the Application and pass it your bot's token.
    persistence = PicklePersistence(filepath="status_cache")
    application = Application.builder().token(TOKEN).persistence(persistence).build()

    application.add_handler(MessageHandler(filters.Regex("^(Status|Run Modded|Run Vanilla|Stop|Online|Button)$"), process_control_panel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help))

    #callbackquery handlers

    #General purpose commands
    handler = CommandHandler("start", start)
    application.add_handler(handler)
    handler = CommandHandler("cancel", cancel)
    application.add_handler(handler)
    handler = CommandHandler("help", help)
    application.add_handler(handler)
    handler = CommandHandler("control", send_control_panel)
    application.add_handler(handler)
    handler = CommandHandler("sw_layout", switch_layout)
    application.add_handler(handler)

    #Valheim server coomands
    handler = CommandHandler("status", request_server_status)
    application.add_handler(handler)
    handler = CommandHandler("runmodded", partial(request_server_run, mode='modded'))
    application.add_handler(handler)
    handler = CommandHandler("runvanilla", request_server_run)
    application.add_handler(handler)
    handler = CommandHandler("stop", request_server_stop)
    application.add_handler(handler)
    handler = CommandHandler("online", request_server_online)
    application.add_handler(handler)

    #AWS host commands
    handler = CommandHandler("stophost", request_host_stop)
    application.add_handler(handler)
    handler = CommandHandler("runhost", request_host_run)
    application.add_handler(handler)


    async with application: 
        print('----1-----')
        await application.initialize()
        print('----2-----')
        await application.start()
        print('----3-----')
        await application.updater.start_polling()
        print('----4-----')
        # await keep_reading_logfile()
        await log_process()
        print('----5-----')
        await application.updater.stop()
        print('----6-----')
        await application.stop()
        print('----7-----')

if __name__ == "__main__":
    asyncio.run(main())
    #main()