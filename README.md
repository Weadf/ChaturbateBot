[![Build Status](https://travis-ci.org/fuomag9/ChaturbateBot.svg?branch=master)](https://travis-ci.org/fuomag9/ChaturbateBot)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/3bab44d73eb5417da2c650ebdb12050f)](https://www.codacy.com/app/fuomag9/ChaturbateBot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=fuomag9/ChaturbateBot&amp;utm_campaign=Badge_Grade)
<br>
ChaturbateBot, written using python3<br>
You have to install the dipendences using pip by doing <i>pip install -r requirements.txt</i> in order to be able to run this bot<br>
If you don't want to host it yourself you can use mine here http://t.me/chaturbatealertsbot

usage: ChaturbateBot.py [-h] -k KEY [-f WORKING_FOLDER] [-t TIME]<br>
                        [-threads THREADS] [-l LIMIT] [-r REMOVE]<br>
                        [-sentry SENTRY] [--admin-password ADMIN_PASSWORD]<br>

optional arguments:<br>
  -h, --help            show this help message and exit<br>
  -k KEY, --key KEY     Telegram bot api key. It's required in order to run<br>
                        this bot<br>
  -f WORKING_FOLDER, --working-folder WORKING_FOLDER<br>
                        Set the bot's working-folder. Default=<br>
                        ChaturbateBot.py's location<br>
  -t TIME, --time TIME  Time wait between every connection made, in seconds.<br>
                        Default=0.2<br>
  -threads THREADS      The number of multiple http connection opened at the<br>
                        same time to check chaturbate. Default=10<br>
  -l LIMIT, --limit LIMIT<br>
                        The maximum number of multiple users a person can<br>
                        follow<br>
  -r REMOVE, --remove REMOVE<br>
                        Should the bot remove from the database anyone whom<br>
                        blocks it? default= true<br>
  -sentry SENTRY        Your sentry personal url<br>
  --admin-password ADMIN_PASSWORD<br>
                        The password for the bot admin commands, disabled by<br>
                        default