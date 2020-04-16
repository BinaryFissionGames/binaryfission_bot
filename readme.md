# binaryfission_bot

This is the bot I use for my [Twitch channel](https://www.twitch.tv/binaryfissiongames). That being said, this bot may
also be used for any other twitch channel, it simply needs to be configured for another channel.

## Configuration
### options.json
Copy options.example.json to options.json.
The following is a table describing the available options:

| Option Name     | Option Description                                                                                                                          | Example                        |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| channel_name    | The name of the channel the bot will monitor and talk in.                                                                                   | binaryfissiongames             |
| twitch_username | The username of the twitch user that will act as the bot.                                                                                   | binaryfission_bot              |
| twitch_password | The [OAuth token](https://twitchapps.com/tmi/) for the twitch user that will act as the bot. This does **NOT** include the `oauth:` prefix. | pzzpk2munbiuoudiaul19lab95as79 |

### commands.json

Copy commands.example.json to commands.json

This file is saved every 10 minutes while the bot is running. 

Each key will act as the command phrase, or "keyword" (e.g. `!<keyword>` in chat is used to activate the command). 
The value of the key is an object that must specify a `command_type` key. This key is a string that is either `add`,
which adds or deletes a new text command (only moderators or broadcasters may do this), `delete` which removes a text 
command (again, only broadcasters or mods have access to this command), or `text`, which specifies a text command.

If a `text` command is specified, then another field, `text` may be specified. This will be the text that the bot will 
relay in chat when the command is given from a user.

## Running the bot
Using python 3 on your system, run main.py (`python main.py`, or `python3 main.py`, depending on your system).

## Closing the bot down
Issuing a keyboard interrupt (ctrl+c) will stop the bot safely. Killing the bot through other methods may result in the 
loss of command data. 

(TODO: Use some SQLlite library to handle this stuff transactionally, 
to eliminate the chance of data loss)