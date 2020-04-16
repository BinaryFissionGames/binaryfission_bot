import re
import time

ADMIN_GROUPS = ['broadcaster', 'moderator']

# Check if the tags indicates that an admin (mod or the broadcaster) has sent the message
def has_admin_tag(tags):
    if 'badges' in tags:
        badges = tags['badges']
        for badge in badges:
            for admin_group in ADMIN_GROUPS:
                if admin_group in badge:
                    print('User has badge ' + admin_group)
                    return True
    return False

# Abstract base class for commands.
class Command:
    # Cooldown in seconds
    def __init__(self, cooldown=30):
        self.cooldown = cooldown
        self.cooldown_start = None

    # activated when !<keyword> is put in chat:
    def action(self, tcp_interface_protocol, user, msg, tags):
        raise NotImplementedError

    # Check if the cooldown is over; This cooldown is necessary, since the bot (like normal users) can only
    # say so many messages per minute and per day. If this is not used, users could abuse this to have the bot
    # quickly hit its rate limit.
    def is_cooldown_over(self):
        if self.cooldown_start:
            return time.monotonic() >= self.cooldown_start + self.cooldown
        return True

# Command that allows any user to query for a pre-determined text response.
class TextCommand(Command):
    def __init__(self, text, cooldown=30):
        super(TextCommand, self).__init__( cooldown)
        self.text = text

    def action(self, tcp_interface_protocol, user, msg, tags):
        if self.is_cooldown_over():
            tcp_interface_protocol.write_message(self.text)
            self.cooldown_start = time.monotonic()

# Command that allows mods to add/replace text commands
class AddCommand(Command):
    def __init__(self, commands):
        super(AddCommand, self).__init__()
        self.commands = commands
        self.msg_pattern = re.compile('^![A-Za-z0-9]+ ([A-Za-z0-9]+) (.*)$')

    def action(self, tcp_interface_protocol, user, msg, tags):
        if not has_admin_tag(tags):
            return

        msg_match = self.msg_pattern.match(msg)
        print(msg)
        if msg_match:
            (keyword, text) = msg_match.group(1, 2)
            print('Attempting to add command "' + keyword + '" with text "' + text + '".')
            if keyword in self.commands:
                if isinstance(self.commands[keyword], TextCommand):
                    self.commands[keyword] = TextCommand(text)
                    tcp_interface_protocol.write_message('Replaced command "' + keyword + '"')
                else:
                    tcp_interface_protocol.write_message('Cannot replace command "' + keyword + '"; This is not a text command!')
            else:
                self.commands[keyword] = TextCommand(text)
                tcp_interface_protocol.write_message('Added command "' + keyword + '"')

# Command that allows mods to remove text commands
class DeleteCommand(Command):
    def __init__(self, commands):
        super(DeleteCommand, self).__init__()
        self.commands = commands
        self.msg_pattern = re.compile('^![A-Za-z0-9]+ ([A-Za-z0-9]+)$')

    def action(self, tcp_interface_protocol, user, msg, tags):
        if not has_admin_tag(tags):
            return

        msg_match = self.msg_pattern.match(msg)
        print(msg)
        if msg_match:
            keyword = msg_match.group(1)
            if keyword in self.commands:
                if isinstance(self.commands[keyword], TextCommand):
                    del self.commands[keyword]
                    tcp_interface_protocol.write_message('Deleted command "' + keyword + '"')
                else:
                    tcp_interface_protocol.write_message('Cannot delete command "' + keyword + '"; This is not a text command!')
            else:
                tcp_interface_protocol.write_message('Command "' + keyword + '" does not exist.')
