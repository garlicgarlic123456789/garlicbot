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
        self.registered_events = {}
        self.channels = {}

    def event(self, func):
        self.registered_events[func.__name__] = func
        return func

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)


class FakeTextChannel:
    def __init__(self, *, channel_id: int, mention: str | None = None):
        self.id = channel_id
        self.mention = mention or f"<#{channel_id}>"
        self.sent_embeds = []

    async def send(self, *, embed):
        self.sent_embeds.append(embed)
