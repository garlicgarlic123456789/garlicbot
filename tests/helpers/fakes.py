class FakeTree:
    def __init__(self):
        self.registered_commands = []
        self.added_commands = []

    def command(self, *, name: str, description: str):
        def decorator(func):
            self.registered_commands.append(
                {
                    "name": name,
                    "description": description,
                    "callback": func,
                }
            )
            return func

        return decorator

    def add_command(self, command):
        self.added_commands.append(command)


class FakeBot:
    def __init__(self):
        self.tree = FakeTree()
