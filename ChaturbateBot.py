# -*- coding: utf-8 -*-
import argparse
import json
import logging
import os
import os.path
import sqlite3
import threading
import time
import urllib.request
import requests
from queue import Queue

from concurrent.futures import ThreadPoolExecutor

import telegram
from requests_futures.sessions import FuturesSession
from telegram.error import (BadRequest, ChatMigrated, NetworkError,
                            TelegramError, TimedOut, Unauthorized)
from telegram.ext import CommandHandler, Updater


ap = argparse.ArgumentParser()
ap.add_argument(
    "-k", "--key", required=True, type=str, help="Telegram bot api key. It's required in order to run this bot")
ap.add_argument(
    "-f",
    "--working-folder",
    required=False,
    type=str,
    default=os.getcwd(),
    help="Set the bot's working-folder. Default= ChaturbateBot.py's location")
ap.add_argument(
    "-t",
    "--time",
    required=False,
    type=float,
    default=0.3,
    help="Time wait between every connection made, in seconds. Default=0.3s")
ap.add_argument(
    "-threads",
    required=False,
    type=int,
    default=10,
    help="The number of multiple http connection opened at the same time to check chaturbate. Default=10")
ap.add_argument(
    "-l",
    "--limit",
    required=False,
    type=int,
    default=0,
    help="The maximum number of multiple users a person can follow, 0=unlimited")
ap.add_argument(
    "-r",
    "--remove",
    required=False,
    type=bool,
    default=True,
    help="Should the bot remove from the database anyone whom blocks it? default= true")
ap.add_argument(
    "-sentry",
    required=False,
    type=str,
    default="",
    help="Your sentry personal url")
ap.add_argument(
    "--admin-password",
    required=False,
    type=str,
    default="",
    help="The password for the bot admin commands, disabled by default")
args = vars(ap.parse_args())


updater = Updater(token=args["key"])
dispatcher = updater.dispatcher

bot_path = args["working_folder"]
wait_time = args["time"]
sentry_key = args["sentry"]
http_threads = args["threads"]
user_limit = args["limit"]
auto_remove = args["remove"]
admin_pw = args["admin_password"]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO,filename=bot_path+"program_log.log")


# enable sentry if sentry_key is passed as an argument
if sentry_key != "":
    import sentry_sdk
    sentry_sdk.init(sentry_key)

    def handle_exception(e):
        try:
         sentry_sdk.capture_exception()
        except Exception as e:
            logging.error(e,exc_info=True)
            sentry_sdk.capture_message("Sentry ha failato ad handlare l'exception"+"l'exception avvenuta è "+str(e))

else:

    def handle_exception(e):
        logging.error(e,exc_info=True)


def exec_query(query):
    """Executes a db query

    Parameters:

    query (str): The sql query to execute

    """

    # Open database connection
    db = sqlite3.connect(bot_path + '/database.db')
    # prepare a cursor object using cursor() method
    cursor = db.cursor()
    # Prepare SQL query to INSERT a record into the database.
    try:
        # Execute the SQL command
        cursor.execute(query)
        # Commit your changes in the database
        db.commit()
    except Exception as e:
        # Rollback in case there is any error
        handle_exception(e)
        db.rollback()
    # disconnect from server
    db.close()


def risposta(sender, messaggio, bot, html=False):
    """Sends a message to a telegram user

    Parameters:

    sender (str): The chat id of the user who will receive the message

    messaggio (str): The message who the user will receive

    bot: telegram bot instance

    html (str): if html markdown should be enabled in the message


    """

    try:
        bot.send_chat_action(chat_id=sender, action="typing")
        if html == True:
            bot.send_message(chat_id=sender, text=messaggio,
                             parse_mode=telegram.ParseMode.HTML)
        else:
            bot.send_message(chat_id=sender, text=messaggio)
    except Unauthorized:
        if auto_remove == True:
            logging.info(
                "{} blocked the bot, he's been removed from the database".format(sender))
            exec_query(
                "DELETE FROM CHATURBATE WHERE CHAT_ID='{}'".format(sender))
    except Exception as e:
        handle_exception(e)


def admin_check(chatid):
    """Checks if a chatid is present in the admin database

    Parameters:

    chatid (str): The chat id of the user who will be checked


    Returns:
    bool: the logic value of the check

    """

    admin_list = []

    db = sqlite3.connect(bot_path + '/database.db')
    cursor = db.cursor()

    sql = "SELECT * FROM ADMIN"
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            admin_list.append(row[0])
    except Exception as e:
        handle_exception(e)
    finally:
        db.close()

    if str(chatid) not in admin_list:
        return False
    else:
        return True


# default table creation
exec_query("""CREATE TABLE IF NOT EXISTS CHATURBATE (
        USERNAME  CHAR(60) NOT NULL,
        CHAT_ID  CHAR(100),
        ONLINE CHAR(1))""")

# admin table creation
exec_query("""CREATE TABLE IF NOT EXISTS ADMIN (
        CHAT_ID  CHAR(100))""")

# normal functions


def start(bot, update):
    risposta(
        update.message.chat.id,
        "/add username to add an username to check \n/remove username to remove an username\n(you can use /remove <b>all</b> to remove all models at once) \n/list to see which users you are currently following", bot, html=True
    )


def add(bot, update, args):
    logging.info("add")
    chatid = update.message.chat_id
    try:
        if len(args) != 1:
            risposta(
                chatid,
                "You need to specify an username to follow, use the command like /add <b>test</b>", bot, html=True
            )
            return
        # not lowercase usernames bug the api calls
        username = args[0].lower()
    except Exception as e:
        risposta(chatid, "An error happened, try again", bot)
        handle_exception(e)
        return
    try:
        target = "https://en.chaturbate.com/api/chatvideocontext/" + username

        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36', }
        response = requests.get(target, headers=headers)
        # server response + json parsing
        response_json = json.loads(response.content)

        # check for not existing models and errors
        if (("status" in response_json) and ("401" in str(response_json['status'])) and ("This room requires a password" not in str(response_json['detail']))):

            if "Room is deleted" in str(response_json['detail']):

                risposta(
                    chatid, username +
                    " has not been added because room has been deleted", bot
                )
                logging.info(
                    username+
                    " has not been added because room has been deleted")
            if "This room has been banned" in str(response_json['detail']):

                risposta(
                    chatid, username +
                    " has not been added because has been banned", bot)
                logging.info(username+
                      " has not been added because has been banned")

        else:
            username_list = []
            db = sqlite3.connect(bot_path + '/database.db')
            cursor = db.cursor()

            # obtain present usernames
            sql = "SELECT * FROM CHATURBATE WHERE CHAT_ID='{}'".format(
                chatid)
            try:
                cursor.execute(sql)
                results = cursor.fetchall()
                for row in results:
                    username_list.append(row[0])
            except Exception as e:
                handle_exception(e)
            finally:
                db.close()

            user_limit_local = user_limit

            if admin_check(chatid):
                user_limit_local = 0  # admin has power, bitches

            # 0 is unlimited usernames
            if len(username_list) < user_limit_local or user_limit_local == 0:
                if username not in username_list:
                    exec_query(
                        "INSERT INTO CHATURBATE VALUES ('{}', '{}', '{}')".
                        format(username, chatid, "F"))
                    try:
                        status = str(response_json['detail'])
                        if "This room requires a password" in status:
                            risposta(
                                chatid, username + " uses a password for his/her room, it has been added but tracking could be unstable", bot)
                    except KeyError:
                        risposta(chatid, username + " has been added", bot)

                else:
                    risposta(chatid, username +
                             " has already been added", bot)
            else:
                risposta(
                    chatid,
                    "You have reached your maximum number of permitted followed models, which is "
                    + str(user_limit_local), bot)
    except Exception as e:
        handle_exception(e)
        risposta(
            chatid, username +
            " was not added because it doesn't exist or it has been banned", bot
        )


def remove(bot, update, args):
    logging.info("remove")
    chatid = update.message.chat.id
    username_list = []
    if len(args) != 1:
        risposta(
            chatid,
            "You need to specify an username to follow, use the command like /remove <b>test</b>", bot, html=True)
        return
    username = args[0].lower()
    if username == "":
        risposta(
            chatid,
            "The username you tried to remove doesn't exist or there has been an error", bot
        )
        return

    sql = "SELECT * FROM CHATURBATE WHERE USERNAME='{}' AND CHAT_ID='{}'".format(
        username, chatid)
    try:
        db = sqlite3.connect(bot_path + '/database.db')
        cursor = db.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            username_list.append(row[0])
    except Exception as e:
        handle_exception(e)
    finally:
        db.close()

    if username == "all":
        exec_query(
            "DELETE FROM CHATURBATE WHERE CHAT_ID='{}'".format(chatid))
        risposta(chatid, "All usernames have been removed", bot)

    elif username in username_list:  # this could have a better implementation but it works
        exec_query(
            "DELETE FROM CHATURBATE WHERE USERNAME='{}' AND CHAT_ID='{}'".
            format(username, chatid))
        risposta(chatid, username + " has been removed", bot)

    else:
        risposta(
            chatid,
            "You aren't following the username you have tried to remove", bot)


def list_command(bot, update):
    chatid = update.message.chat.id
    username_list = []
    online_list = []
    username_dict = {}
    followed_users = ""
    db = sqlite3.connect(bot_path + '/database.db')
    cursor = db.cursor()
    sql = "SELECT * FROM CHATURBATE WHERE CHAT_ID='{}'".format(chatid)

    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            username_list.append(row[0])
            online_list.append(row[2])
    except Exception as e:
        handle_exception(e)
    else:  # else means that the code will get executed if an exception doesn't happen

        for x in range(0, len(username_list)):
            # dictionary with usernames and online_status
            username_dict.update({username_list[x]: online_list[x]})

        for username in sorted(username_dict):
            followed_users += username + ": "
            if username_dict[username] == "T":
                followed_users += "<b>online</b>\n"
            else:
                followed_users += "offline\n"
    finally:
        db.close()
    if followed_users == "":
        risposta(chatid, "You aren't following any user", bot)
    else:
        risposta(
            chatid, "You are currently following these {} users:\n".format(len(username_list)) +
            followed_users, bot, html=True)

# end of normal funcionts


def authorize_admin(bot, update, args):

    logging.info("admin-auth")
    chatid = update.message.chat_id
    if len(args) != 1:
        risposta(
            chatid,
            "You need to specify the admin password, use the command like /authorize_admin <b>password</b>", bot, html=True
        )
        return
    elif admin_pw == "":
        risposta(
            chatid,
            "The admin is disabled, check your telegram bot configuration", bot
        )
        return
    if args[0] == admin_pw and admin_check(chatid) == False:
        exec_query("""INSERT INTO ADMIN VALUES ({})""".format(chatid))
        risposta(chatid, "Admin abilitato", bot)
    else:
        risposta(chatid, "la password è errata", bot)


def send_message_to_everyone(bot, update, args):
    chatid = update.message.chat.id
    message = ""

    if admin_check(chatid) == False:
        risposta(chatid, "non sei autorizzato", bot)
        return

    chatid_list = []

    sql = "SELECT DISTINCT CHAT_ID FROM CHATURBATE"
    try:
        db = sqlite3.connect(bot_path + '/database.db')
        cursor = db.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            chatid_list.append(row[0])
    except Exception as e:
        handle_exception(e)
    finally:
        db.close()

    for word in args:
        message += word+" "
    message = message[:-1]

    for x in chatid_list:
        risposta(x, message, bot)

# end of admin functions


# threads

def check_online_status():
    global updater
    bot = updater.bot
    while (1):
        

        username_list = []
        online_dict = {}
        chatid_dict = {}

        # create a dictionary with usernames and online using distinct
        sql = "SELECT DISTINCT USERNAME,ONLINE FROM CHATURBATE"
        try:
            db = sqlite3.connect(bot_path + '/database.db')
            cursor = db.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            for row in results:
                online_dict[row[0]]=row[1]
                #username row0
                #online row1
        except Exception as e:
            handle_exception(e)
        finally:
            db.close()
        
        #create username_list
        for username in online_dict.keys():
            username_list.append(username)
        



        # obtain chatid
        for username in username_list:
                chatid_list = []
                sql = "SELECT CHAT_ID FROM CHATURBATE WHERE USERNAME='{}'".format(username)
                try:
                            db = sqlite3.connect(bot_path + '/database.db')
                            cursor = db.cursor()
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            for row in results:
                                chatid_list.append(row[0])
                except Exception as e:
                            handle_exception(e)
                finally:
                            db.close()
                chatid_dict[username]=chatid_list            


        # Threaded function for queue processing.
        def crawl(q, response_list):
            while not q.empty():
                work = q.get()                      #fetch new work from the Queue
                try:
                    target = "https://en.chaturbate.com/api/chatvideocontext/" + work[1].lower()
                    headers = {
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36', }
                    response = requests.get(target, headers=headers)
                    response_json = json.loads(response.content)
                    
                    response_list[work[1]] = response_json


                except (json.JSONDecodeError,ConnectionError) as e:
                    handle_exception(e)
                    response_list[work[1]] = "error"              
                except Exception as e:
                    handle_exception(e)
                    response_list[work[1]] = "error"
                #signal to the queue that task has been processed
                q.task_done()
            return True

        q = Queue(maxsize=0)
        #Populating Queue with tasks
        response_list = {}

        #load up the queue with the username_list to fetch and the index for each job (as a tuple):
        for i in range(len(username_list)):
            #need the index and the url in each queue item.
            q.put((i,username_list[i]))    
        
        #Starting worker threads on queue processing
        for i in range(http_threads):
            
            worker = threading.Thread(target=crawl, args=(q,response_list), daemon=True)
            worker.start()
            time.sleep(wait_time)  #avoid server spamming by time-limiting the start of requests
        
        #now we wait until the queue has been processed
        q.join()
        
        
            
        

        for username in username_list:
            response=response_list[username]
            
            try:

                if ("status" not in response
                        and response != "error"):
                    if (response["room_status"] == "offline"):

                        if online_dict[username] == "T" :
                            exec_query(
                                "UPDATE CHATURBATE SET ONLINE='{}' WHERE USERNAME='{}'"
                                .format("F", username))

                            for y in chatid_dict[username]:
                                risposta(y, username + " is now offline", bot)


                    elif online_dict[username] == "F":

                            exec_query(
                                "UPDATE CHATURBATE SET ONLINE='{}' WHERE USERNAME='{}'"
                                .format("T", username))

                            for y in chatid_dict[username]:    
                                risposta(y, username +" is now online! You can watch the live here: http://en.chaturbate.com/"+ username, bot)

                            


                elif response != "error":
                    if "401" in str(response['status']):
                        if "This room requires a password" in str(response['detail']):

                            if (online_dict[username] == "F"):

                                exec_query("UPDATE CHATURBATE SET ONLINE='{}' WHERE USERNAME='{}'".format("T", username))
                                
                                for y in chatid_dict[username]:    
                                    risposta(y, username +" is now online! You can watch the live here: http://en.chaturbate.com/"+ username, bot)

                        if "Room is deleted" in str(response['detail']):
                            exec_query(
                                "DELETE FROM CHATURBATE WHERE USERNAME='{}'".
                                format(username))
                            for y in chatid_dict[username]:
                                risposta(y, username +" has been removed because room has been deleted", bot)
                            logging.info(
                                username+
                                " has been removed because room has been deleted"
                            )

                        if "This room has been banned" in str(
                                response['detail']):
                            exec_query(
                                "DELETE FROM CHATURBATE WHERE USERNAME='{}'".
                                format(username))
                            for y in chatid_dict[username]:
                                risposta(y, username +" has been removed because room has been deleted", bot)
                            logging.info(username+
                                  " has been removed because has been banned")

                        if "This room is not available to your region or gender." in str(
                                response['detail']):
                            exec_query(
                                "DELETE FROM CHATURBATE WHERE USERNAME='{}'".
                                format(username))
                            for y in chatid_dict[username]:
                                risposta(y, username +" has been removed because of geoblocking, I'm going to try to fix this soon", bot)
                            logging.info(username+
                                  " has been removed because of blocking")          
            except Exception as e:
                handle_exception(e)




start_handler = CommandHandler(('start', 'help'), start)
dispatcher.add_handler(start_handler)

add_handler = CommandHandler('add', add, pass_args=True)
dispatcher.add_handler(add_handler)

remove_handler = CommandHandler('remove', remove, pass_args=True)
dispatcher.add_handler(remove_handler)

list_handler = CommandHandler('list', list_command)
dispatcher.add_handler(list_handler)

authorize_admin_handler = CommandHandler(
    'authorize_admin', authorize_admin, pass_args=True)
dispatcher.add_handler(authorize_admin_handler)


send_message_to_everyone_handler = CommandHandler(
    'send_message_to_everyone', send_message_to_everyone, pass_args=True)
dispatcher.add_handler(send_message_to_everyone_handler)


threading.Thread(target=check_online_status,daemon=True).start()

while True:
    try:
        updater.start_polling()
    except Exception as e:
        handle_exception(e)
