[![Build Status](https://travis-ci.org/fuomag9/ChaturbateBot.svg?branch=master)](https://travis-ci.org/fuomag9/ChaturbateBot)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/3bab44d73eb5417da2c650ebdb12050f)](https://www.codacy.com/app/fuomag9/ChaturbateBot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=fuomag9/ChaturbateBot&amp;utm_campaign=Badge_Grade)
<br>
ChaturbateBot, written using python3<br>
You have to install the dipendences using pip by doing <i>pip install -r requirements.txt</i> in order to be able to run this bot<br>
If you don't want to host it yourself you can use mine here http://t.me/chaturbatealertsbot

usage: ChaturbateBot.py [-h] -k KEY [-f WORKING_FOLDER] [-t TIME]

[-threads THREADS] [-l LIMIT] [-r REMOVE]

[-sentry SENTRY] [--admin-password ADMIN_PASSWORD]

optional arguments:

-h, --help show this help message and exit

-k KEY, --key KEY Telegram bot api key. It's required in order to run

this bot

-f WORKING_FOLDER, --working-folder WORKING_FOLDER

Set the bot's working-folder. Default=

ChaturbateBot.py's location

-t TIME, --time TIME Time wait between every connection made, in seconds.

Default=0.2

-threads THREADS The number of multiple http connection opened at the

same time to check chaturbate. Default=10

-l LIMIT, --limit LIMIT

The maximum number of multiple users a person can

follow

-r REMOVE, --remove REMOVE

Should the bot remove from the database anyone whom

blocks it? default= true

-sentry SENTRY Your sentry personal url

--admin-password ADMIN_PASSWORD

The password for the bot admin commands, disabled by

default