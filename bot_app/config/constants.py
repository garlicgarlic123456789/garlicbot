import discord

WARN_LAW = (
    "**[경고!]** 본 자료는 법적 조언이 아닌 일반적인 정보 제공 목적만을 가지고 있습니다. "
    "특정 상황에 대해 결정하시기 전, 반드시 법률 전문가와 상의하시기 바랍니다. "
    "본 자료를 신뢰하여 생기는 손해나 피해에 대한 책임은 사용자의 판단에 따라 전적으로 사용자에게 있습니다."
)

WARN_SECRET = (
    "**[경고!]** 이 문서에는 기밀 정보가 포함되어 있습니다. "
    "다른 사람(사용자)에게 유출되지 않도록 주의가 필요합니다."
)

BLOCKED_USERS_FILE = "command_blocked_user.json"

TRANSFER_WARN = (
    "**[경고!]** 일부 또는 모든 노선 간 환승 시 환승 통로가 길거나, "
    "계단이 많은 등 환승이 불편한 역입니다.\n\n"
)


def build_allowed_mentions() -> discord.AllowedMentions:
    return discord.AllowedMentions(
        everyone=False,
        users=True,
        roles=True,
        replied_user=True,
    )
