import asyncio
from asyncio import transports
from typing import List, Optional


class TcpInterfaceProtocol(asyncio.Protocol):
    # on_message is a message handling function; it gets the transport as it's first parameter,
    #   and the decoded message (as a string) as its second, and the Protocol as the third parameter
    # on_connection_lost is a coroutine function that accepts no parameters. It is called when the established
    #   connection is terminated.
    # sep is a bytes object that denotes a seperator between messages (defaults to newline)
    def __init__(self, username, password, channel_name, on_message, on_connection_lost=None, sep=bytes([0x0A])):
        self.buffer = bytearray(0)
        self.transport = None
        self.on_message = on_message
        self.username = username
        self.password = password
        self.channel_name = channel_name
        self.on_connection_lost = on_connection_lost
        self.sep = sep

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self.transport = transport
        # this tells twitch that we want the message tags, which give us info like if the user is a mod.
        transport.write(('CAP REQ :twitch.tv/tags\n').encode())
        transport.write(('PASS oauth:' + self.password + '\n').encode())
        transport.write(('NICK ' + self.username + '\n').encode())

    # This function buffers that data until the separator is found in the data stream. Then, on_message is called.
    def data_received(self, data: bytes) -> None:
        self.buffer.extend(data)

        if self.sep in self.buffer:
            rightmost_sep = self.buffer.rfind(self.sep)
            msgs: List[bytearray] = self.buffer[0:rightmost_sep+1].split(self.sep)
            self.buffer = self.buffer[rightmost_sep+1:-1]
            for msg in msgs:
                if len(msg) > 0:
                    self.on_message(self.transport, msg.decode(), self)

    # Write and IRC message; That is, put a message in chat as the bot.
    def write_message(self, msg):
        self.transport.write(('PRIVMSG #' + self.channel_name + ' :' + msg + '\n').encode())

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if self.on_connection_lost:
            asyncio.get_event_loop().create_task(self.on_connection_lost())