import json
import os
import re
import asyncio
import time

from command import TextCommand, AddCommand, DeleteCommand
from decoder_encoder import get_command_decoder, EncodeTextCommands
from tcp_interface_protocol import TcpInterfaceProtocol

PROP_CHANNEL_NAME = 'channel_name'  # Name of the channel we will be monitoring for poll inputs
PROP_TWITCH_USERNAME = 'twitch_username'  # twitch username to log into for monitoring chat
PROP_TWITCH_PASSWORD = 'twitch_password'  # OAUTH token for twitch user - THIS TOKEN IS WITHOUT THE oauth: PART APPENDED!

# Interval to save the commands, in seconds.
SAVE_INTERVAL = 1 * 60  # 10 minutes

commands = {}
options = None

# Starts the IRC connection. This runs the event loop, meaning this is blocking until the event loop is stopped
# currently, the only way of doing that is through a key interrupt
def create_irc_connection(host, port, ssl, username, password, channel):
    if username is None or password is None or channel is None or username == '' or password == '' or channel == '':
        print(
            "Cannot start connection to twitch IRC - Missing username, password or channel! please configure these first!",
        )
        return

    active_transport = None
    last_reconnect_backoff = 0
    stopping = False

    welcome_pattern = re.compile(':tmi.twitch.tv ([0-9]{3}) ([^ ]*) :(.*)')
    priv_msg_pattern = re.compile('@([^ ]*) :([^!]*)!([^@]*)([^.]*).tmi.twitch.tv PRIVMSG #' + channel + ' :([^\n]*)')

    def on_message(transport, msg, protocol):
        nonlocal welcome_pattern, priv_msg_pattern, last_reconnect_backoff
        global server_name, commands

        print(msg)
        # If twitch ACKS our capababilities, then we  should send the command CAP END
        # Note about this: when testing, I found this works either way.
        # My guess is that twitch actually just ignores this
        # and sets up an account before capabilities are sent anyways, which, while against the spec,
        # doesn't really matter due to the capabilities the twitch IRC server has.
        if msg.startswith(':tmi.twitch.tv CAP * ACK :twitch.tv/tags'):
            transport.write('CAP END\n'.encode())
            return

        # Around every 5 or so minutes, twitch sends a ping message. They expect a PONG reply, or the client
        # will be disconnected.
        if msg.startswith('PING'):
            transport.write('PONG :tmi.twitch.tv\n'.encode())
            return

        # Code that detects the welcome message, signalling that we can join a specific channel
        welcome_match = welcome_pattern.match(msg)
        if welcome_match:
            message_number = int(welcome_match.group(1))
            if message_number == 4:
                last_reconnect_backoff = 0
                print('Joining ' + channel)
                transport.write(('JOIN #' + channel + '\n').encode())

        # These PRIVMSGes are user chat messages
        elif 'PRIVMSG' in msg:
            priv_msg_match = priv_msg_pattern.match(msg)
            if priv_msg_match:
                (tags_str, msg_user, user_typed_msg) = priv_msg_match.group(1, 2, 5)
                user_typed_msg = user_typed_msg.strip()

                # Parse message tags into a map; This is pretty poorly done, and I think may have
                # security issues, as it does not take into account escape sequences, and thus is not
                # spec compliant. This would be a section to touch up in the future.
                tag_tuple_list = map(lambda x: (x.split('=')[0], x.split('=')[1]), tags_str.split(';'))
                tags = {}
                for tag_tuple in tag_tuple_list:
                    values = tag_tuple[1].split(',')
                    if len(values) > 1:
                        tags[tag_tuple[0]] = values
                    elif len(values) == 1:
                        tags[tag_tuple[0]] = values[0]

                # All commands start with !
                if user_typed_msg.startswith('!'):
                    command = user_typed_msg.split(' ')[0][1:]
                    print('Command was: ' + command)
                    if command in commands:
                        commands[command].action(protocol, msg_user, user_typed_msg, tags)

    async def on_connection_close():
        nonlocal stopping, active_transport, last_reconnect_backoff
        # Stopping = true if this is a manual stop action and no reconnect should be attempted.
        if not stopping:
            print("Connection to IRC chat lost, attempting to reconnect after " + str(
                last_reconnect_backoff) + " seconds...")
            # Try to reconnect - using the exponential backoff (immediate, 1 sec, 2 sec, 4 sec, etc.. to 16 seconds)
            if last_reconnect_backoff != 0:
                await asyncio.sleep(last_reconnect_backoff)
                last_reconnect_backoff = min(last_reconnect_backoff * 2,
                                             16)  # Waiting a max of 16 seconds between reconnects
            else:
                last_reconnect_backoff = 1

            (active_transport, _) = await asyncio.get_event_loop().create_connection(
                lambda: TcpInterfaceProtocol(username, password, channel, on_message,
                                             on_connection_lost=on_connection_close, sep=b'\n'),
                ssl=ssl,
                host=host,
                port=port)

    # This function saves commands every SAVE_INTERVAL
    def save_commands_timeout():
        global commands
        print('Saving commands!')
        save_commands(commands)
        asyncio.get_event_loop().call_later(SAVE_INTERVAL, save_commands_timeout)

    connect_coroutine = asyncio.get_event_loop().create_connection(
        lambda: TcpInterfaceProtocol(username, password, channel, on_message,
                                     on_connection_lost=on_connection_close, sep=b'\n'),
        ssl=ssl,
        host=host,
        port=port)

    asyncio.get_event_loop().call_later(SAVE_INTERVAL, save_commands_timeout)

    (active_transport, _) = asyncio.get_event_loop().run_until_complete(connect_coroutine)
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        global commands
        save_commands(commands)


def load_commands():
    global commands
    with open(os.path.dirname(os.path.realpath(__file__)) + "/commands.json") as file:
        commands.update(json.load(file, object_hook=get_command_decoder(commands)))


def save_commands(commands):
    with open(os.path.dirname(os.path.realpath(__file__)) + "/commands.json", 'w') as file:
        json.dump(commands, file, cls=EncodeTextCommands, indent=4)


def load_options():
    global options
    with open(os.path.dirname(os.path.realpath(__file__)) + "/options.json") as file:
        options = json.load(file)


load_options()
load_commands()

# Note: I do not have options for the URL, port, or whether to use SSL or not; for documentation purposes...
# 'irc.chat.twitch.tv' is the twitch IRC server, 6697 is the SSL port, True indicates we use SSL. These are hardcoded,
# and likely shouldn't be changed (esp. the ssl one)
create_irc_connection('irc.chat.twitch.tv', 6697, True, options[PROP_TWITCH_USERNAME], options[PROP_TWITCH_PASSWORD],
                      options[PROP_CHANNEL_NAME])
