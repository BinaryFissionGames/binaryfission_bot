import json

from command import TextCommand, Command, AddCommand, DeleteCommand


# decode to Command objects from commands.json
# Takes the command array as a parameter
def get_command_decoder(commands):
    def as_command(dct):
        if 'command_type' in dct:
            if dct['command_type'] == 'text':
                return TextCommand(dct['text'], dct['cooldown'])
            elif dct['command_type'] == 'add':
                return AddCommand(commands)
            elif dct['command_type'] == 'delete':
                return DeleteCommand(commands)
        return dct

    return as_command

# encode Command objects to commands.json
class EncodeTextCommands(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, TextCommand):
            return {'command_type': 'text', 'cooldown': obj.cooldown, 'text': obj.text}
        elif isinstance(obj, AddCommand):
            return {'command_type': 'add'}
        elif isinstance(obj, DeleteCommand):
            return {'command_type': 'delete'}
        return json.JSONEncoder.default(self, obj)