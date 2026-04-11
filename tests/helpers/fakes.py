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
    def __init__(self, *, channel_id: int, mention: str | None = None, fail_on_send: bool = False):
        self.id = channel_id
        self.mention = mention or f"<#{channel_id}>"
        self.fail_on_send = fail_on_send
        self.sent_embeds = []
        self.sent_messages = []

    async def send(self, content=None, *, embed=None):
        if self.fail_on_send:
            raise RuntimeError("send failed")
        if embed is not None:
            self.sent_embeds.append(embed)
        self.sent_messages.append(
            {
                "content": content,
                "embed": embed,
            }
        )


class FakeRole:
    def __init__(self, role_id: int, *, mention: str | None = None):
        self.id = role_id
        self.mention = mention or f"<@&{role_id}>"


class FakeOwner:
    def __init__(self, owner_id: int, *, fail_on_send: bool = False):
        self.id = owner_id
        self.fail_on_send = fail_on_send
        self.sent_embeds = []

    async def send(self, content=None, *, embed=None):
        if self.fail_on_send:
            raise RuntimeError("owner send failed")
        self.sent_embeds.append(embed)


class FakeGuild:
    def __init__(self, guild_id: int, *, owner_id: int = 1, owner_fail_on_send: bool = False):
        self.id = guild_id
        self.channels = {}
        self.roles = {}
        self.default_role = FakeRole(0, mention="@everyone")
        self.owner = FakeOwner(owner_id, fail_on_send=owner_fail_on_send)
        self._invites = []
        self._audit_logs = {}

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    def get_role(self, role_id):
        return self.roles.get(role_id)

    async def invites(self):
        return list(self._invites)

    async def audit_logs(self, *, limit=1, action=None):
        entries = list(self._audit_logs.get(action, []))
        for entry in entries[:limit]:
            yield entry

    async def edit(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def ban(self, member, *, reason=None, delete_message_seconds=0):
        return None


class FakeMember:
    def __init__(
        self,
        member_id: int,
        *,
        guild,
        display_name: str = "마늘",
        bot: bool = False,
        roles=None,
        joined_at=None,
        timed_out_until=None,
    ):
        self.id = member_id
        self.guild = guild
        self.display_name = display_name
        self.bot = bot
        self.roles = list(roles or [guild.default_role])
        self.joined_at = joined_at
        self.timed_out_until = timed_out_until
        self.mention = f"<@{member_id}>"
        self.added_roles = []

    async def add_roles(self, role, *, reason=None):
        self.added_roles.append({"role": role, "reason": reason})
        if role is not None and role not in self.roles:
            self.roles.append(role)

    async def remove_roles(self, *roles):
        for role in roles:
            if role in self.roles:
                self.roles.remove(role)

    async def edit(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
