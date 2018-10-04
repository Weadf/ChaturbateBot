# -*- coding: utf-8 -*-
import argparse
import json
import os
import os.path
import sqlite3
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import telegram
from telegram.ext import Updater
from telegram.ext import CommandHandler


from requests_futures.sessions import FuturesSession

import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

ap = argparse.ArgumentParser()
ap.add_argument(
    "-k", "--key", required=True, type=str, help="Telegram bot key")
ap.add_argument(
    "-f",
    "--working-folder",
    required=False,
    type=str,
    default=os.getcwd(),
    help="set the bot's working-folder")
ap.add_argument(
    "-t",
    "--time",
    required=False,
    type=float,
    default=0.2,
    help="time wait between every connection made, in seconds")
ap.add_argument(
    "-threads",
    required=False,
    type=int,
    default=10,
    help=
    "The number of multiple http connection opened at the same to check chaturbate")
ap.add_argument(
    "-l",
    "--limit",
    required=False,
    type=int,
    default=0,
    help="The maximum number of multiple users a person can follow")
ap.add_argument(
    "-sentry",
    required=False,
    type=str,
    default="",
    help="Your sentry personal url")
args = vars(ap.parse_args())


updater=Updater(token=args["key"])
dispatcher = updater.dispatcher

bot_path = args["working_folder"]
wait_time = args["time"]
sentry_key = args["sentry"]
http_threads = args["threads"]
user_limit = args["limit"]
if sentry_key != "":
    import sentry_sdk
    sentry_sdk.init(sentry_key)

    def handle_exception(e):
        sentry_sdk.capture_exception()
else:

    def handle_exception(e):
        print(str(e))

def risposta(sender, messaggio, bot):
    try:
        bot.send_chat_action(chat_id=sender, action="typing")
        bot.send_message(chat_id=sender, text=messaggio)
    except Exception as e:
        handle_exception(e)  

def risposta_html(sender, messaggio, bot):
    try:
        bot.send_chat_action(chat_id=sender, action="typing")
        bot.send_message(chat_id=sender, text=messaggio,parse_mode=telegram.ParseMode.HTML)
    except Exception as e:
        handle_exception(e)            


def exec_query(query):
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


# default table creation
exec_query("""CREATE TABLE IF NOT EXISTS CHATURBATE (
        USERNAME  CHAR(60) NOT NULL,
        CHAT_ID  CHAR(100),
        ONLINE CHAR(1))""")



def start(bot,update):
        risposta_html(
            update.message.chat.id,
            "/add username to add an username to check \n/remove username to remove an username\n(you can use /remove <b>all</b> to remove all models at once) \n/list to see which users you are currently following",bot
        )

def add(bot,update,args):
        print("add")
        chatid = update.message.chat_id
        try:
            if len(args) > 1:
                risposta(
                    chatid,
                    "You may have made a mistake, check your input and try again",bot
                )
                return
            # not lowercase usernames bug the api calls
            username = args[0].lower()
        except Exception as e:
            risposta(chatid, "An error happened, try again",bot)
            handle_exception(e)
            return
        try:
            target = "https://en.chaturbate.com/api/chatvideocontext/" + username

            req = urllib.request.Request(
                target, headers={'User-Agent': 'Mozilla/5.0'})

            response = urllib.request.urlopen(req).read()
            response_json = json.loads(response) #server response + json parsing

            if ("status" in response_json):
                if "401" in str(response_json['status']) or username == "":
                    if "This room requires a password" in str(
                            response_json['detail']):
                        risposta(
                            chatid, username +
                            " has not been added because it requires a password and cannot be tracked",bot
                        )
                        print(
                            username,
                            "has not been added because it requires a password and cannot be tracked"
                        )
                    if "Room is deleted" in str(response_json['detail']):

                        risposta(
                            chatid, username +
                            " has not been added because room has been deleted",bot
                        )
                        print(
                            username,
                            "has not been added because room has been deleted")
                    if "This room has been banned" in str(response_json['detail']):

                        risposta(
                            chatid, username +
                            " has not been added because has been banned",bot)
                        print(username,
                              "has not been added because has been banned")

            else:
                username_list = []
                db = sqlite3.connect(bot_path + '/database.db')
                cursor = db.cursor()
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
                if len(
                        username_list
                ) < user_limit or user_limit == 0:  #0 is unlimited usernames
                    if username not in username_list:
                        exec_query(
                            "INSERT INTO CHATURBATE VALUES ('{}', '{}', '{}')".
                            format(username, chatid, "F"))
                        risposta(chatid, username + " has been added",bot)
                    else:
                        risposta(chatid, username + " has already been added",bot)
                else:
                    risposta(
                        chatid,
                        "You have reached your maximum number of permitted followed models, which is "
                        + str(user_limit),bot)
        except Exception as e:
            handle_exception(e)
            risposta(
                chatid, username +
                " was not added because it doesn't exist or it has been banned",bot
            )

def remove(bot,update,args):
        print("remove")
        chatid = update.message.chat.id
        username_list = []
        if len(args) > 1:
            risposta(
                chatid,
                "You may have made a mistake, check your input and try again",bot)
            return
        username = args[0].lower()
        if username == "":
            risposta(
                chatid,
                "The username you tried to remove doesn't exist or there has been an error",bot
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
            risposta(chatid, "All usernames have been removed",bot)

        elif username in username_list:  # this could have a better implementation but it works
            exec_query(
                "DELETE FROM CHATURBATE WHERE USERNAME='{}' AND CHAT_ID='{}'".
                format(username, chatid))
            risposta(chatid, username + " has been removed",bot)

        else:
            risposta(
                chatid,
                "You aren't following the username you have tried to remove",bot)

def list_command(bot,update):
        chatid = update.message.chat.id
        username_list = []
        online_list = []
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
                followed_users += username_list[x] + ": "
                if online_list[x] == "T":
                    followed_users += "<b>online</b>\n"
                else:
                    followed_users += "offline\n"
        finally:
            db.close()
        if followed_users == "":
            risposta(chatid, "You aren't following any user",bot)
        else:
            risposta_html(
                chatid, "These are the users you are currently following:\n" +
                followed_users,bot)


start_handler=CommandHandler('start',start)
dispatcher.add_handler(start_handler) #indagare sugli alias multipli
add_handler=CommandHandler('add',add, pass_args=True)
dispatcher.add_handler(add_handler)
remove_handler=CommandHandler('remove',remove, pass_args=True)
dispatcher.add_handler(remove_handler)
list_handler=CommandHandler('list',list_command)
dispatcher.add_handler(list_handler)

def telegram_bot():

    while True:
        try:
            updater.start_polling()
        except Exception as e:
            handle_exception(e)



def check_online_status():
    global updater
    bot=updater.bot
    while (1):
        username_list = []
        chatid_list = []
        online_list = []
        response_list = []
        sql = "SELECT * FROM CHATURBATE"
        try:
            db = sqlite3.connect(bot_path + '/database.db')
            cursor = db.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            for row in results:
                username_list.append(row[0])
                chatid_list.append(row[1])
                online_list.append(row[2])
        except Exception as e:
            handle_exception(e)
        finally:
            db.close()
        session = FuturesSession(
            executor=ThreadPoolExecutor(max_workers=http_threads))
        for x in range(0, len(username_list)):
            try:
                response = (
                    (session.
                     get("https://en.chaturbate.com/api/chatvideocontext/" +
                         username_list[x].lower())).result()
                ).content  # lowercase to fix old entries in db+ more safety
            except Exception as e:
                handle_exception(e)
                response = "error"
            response_list.append(response)
            time.sleep(wait_time)
        for x in range(0, len(response_list)):
            try:
                if ("status" not in json.loads(response_list[x])
                        and response != "error"):
                    if (json.loads(
                            response_list[x])["room_status"] == "offline"):
                        if online_list[x] == "T":
                            exec_query(
                                "UPDATE CHATURBATE SET ONLINE='{}' WHERE USERNAME='{}' AND CHAT_ID='{}'"
                                .format("F", username_list[x], chatid_list[x]))
                            risposta(chatid_list[x],
                                     username_list[x] + " is now offline",bot)
                    elif (online_list[x] == "F"):
                        risposta(
                            chatid_list[x], username_list[x] +
                            " is now online! You can watch the live here: http://en.chaturbate.com/"
                            + username_list[x],bot)
                        exec_query(
                            "UPDATE CHATURBATE SET ONLINE='{}' WHERE USERNAME='{}' AND CHAT_ID='{}'"
                            .format("T", username_list[x], chatid_list[x]))
                elif response != "error":
                    response = json.loads(response_list[x])
                    if "401" in str(response['status']):
                        if "This room requires a password" in str(
                                response['detail']):
                            exec_query(
                                "DELETE FROM CHATURBATE WHERE USERNAME='{}'".
                                format(username_list[x]))
                            risposta(
                                chatid_list[x], username_list[x] +
                                " has been removed because it requires a password and cannot be tracked",bot
                            )
                            print(
                                username_list[x],
                                "has been removed because it requires a password and cannot be tracked"
                            )
                        if "Room is deleted" in str(response['detail']):
                            exec_query(
                                "DELETE FROM CHATURBATE WHERE USERNAME='{}'".
                                format(username_list[x]))
                            risposta(
                                chatid_list[x], username_list[x] +
                                " has been removed because room has been deleted",bot
                            )
                            print(
                                username_list[x],
                                "has been removed because room has been deleted"
                            )
                        if "This room has been banned" in str(
                                response['detail']):
                            exec_query(
                                "DELETE FROM CHATURBATE WHERE USERNAME='{}'".
                                format(username_list[x]))
                            risposta(
                                chatid_list[x], username_list[x] +
                                " has been removed because has been banned",bot)
                            print(username_list[x],
                                  "has been removed because has been banned")
            except Exception as e:
                handle_exception(e)





threads = []
check_online_status_thread = threading.Thread(target=check_online_status)
telegram_bot_thread = threading.Thread(target=telegram_bot)
threads.append(check_online_status_thread)
threads.append(telegram_bot_thread)
check_online_status_thread.start()
telegram_bot_thread.start()