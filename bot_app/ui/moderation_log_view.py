from __future__ import annotations

import discord

from bot_app.types.readability_contracts import ModerationLogEntry


TYPE_LABELS = {
    "warn": "경고",
    "unwarn": "경고 차감",
    "timeout": "타임아웃",
    "untimeout": "타임아웃 해제",
    "ban": "차단",
    "unban": "차단 해제",
    "kick": "추방",
}


def _format_timeout_duration(duration_seconds: int | None) -> str:
    """Render timeout durations in the legacy human-readable Korean format."""

    if duration_seconds is None:
        return "*(알 수 없음)*"
    if duration_seconds <= 0:
        return f"{duration_seconds}초"

    minutes, seconds = divmod(duration_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts: list[str] = []
    if days:
        parts.append(f"{days}일")
    if hours or days:
        parts.append(f"{hours}시간")
    if minutes or hours or days:
        parts.append(f"{minutes}분")
    if seconds or not parts:
        parts.append(f"{seconds}초")
    return " ".join(parts)


class ModerationLogView(discord.ui.View):
    """Render moderation log snapshot pages while preserving the old button UX."""

    def __init__(self, entries: tuple[ModerationLogEntry, ...], user, interact_user, page: int = 0):
        super().__init__()
        self.entries = entries
        self.user = user
        self.page = page
        self.interact_user = interact_user

    @property
    def max_pages(self) -> int:
        return (len(self.entries) - 1) // 10 + 1

    def get_embed(self) -> discord.Embed:
        """Build the current moderation-log page embed from normalized entries."""

        embed = discord.Embed(
            title=f"{self.user if self.user else '이 서버'}의 제재 내역",
            color=int("a5f0ff", 16),
        )
        start = self.page * 10
        end = start + 10
        for entry in self.entries[start:end]:
            title = f"{TYPE_LABELS.get(entry.type_label, '알 수 없는 제재 유형')} - #{entry.entry_id}"
            user_label = f"<@{entry.target_user_id}>" if entry.target_user_id is not None else "*(알 수 없음)*"
            admin_label = f"<@{entry.admin_user_id}>" if entry.admin_user_id is not None else "*(알 수 없음)*"
            content = f"사용자: {user_label}\n관리자: {admin_label}"
            if entry.type_label in {"warn", "unwarn"}:
                amount_label = "*(알 수 없음)*" if entry.extra_value is None else f"{'+' if entry.type_label == 'warn' else '-'}{entry.extra_value}"
                content += f"\n개수: {amount_label}"
            elif entry.type_label == "timeout":
                content += f"\n기간: {_format_timeout_duration(entry.extra_value)}"
            content += f"\n사유: {entry.reason}"
            embed.add_field(name=title, value=content, inline=False)
        embed.set_footer(text=f"페이지 {self.page + 1}/{self.max_pages}")
        return embed

    @discord.ui.button(label="이전", style=discord.ButtonStyle.gray, disabled=True)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interact_user.id:
            await interaction.response.send_message("자기 자신이 실행한 명령어 출력 결과의 버튼만 사용이 가능합니다.", ephemeral=True)
            return
        self.page -= 1
        if self.page == 0:
            button.disabled = True
        self.children[1].disabled = False
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="다음", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interact_user.id:
            await interaction.response.send_message("자기 자신이 실행한 명령어 출력 결과의 버튼만 사용이 가능합니다.", ephemeral=True)
            return
        self.page += 1
        if self.page >= self.max_pages - 1:
            button.disabled = True
        self.children[0].disabled = False
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="페이지 번호 입력", style=discord.ButtonStyle.primary)
    async def select_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interact_user.id:
            await interaction.response.send_message("자기 자신이 실행한 명령어 출력 결과의 버튼만 사용이 가능합니다.", ephemeral=True)
            return
        modal = self.PageInputModal(self)
        await interaction.response.send_modal(modal)

    class PageInputModal(discord.ui.Modal, title="페이지 번호로 이동"):
        def __init__(self, parent_view: "ModerationLogView"):
            super().__init__()
            self.parent_view = parent_view
            self.add_item(
                discord.ui.TextInput(
                    label="이동할 페이지 번호",
                    placeholder="이동할 페이지 번호",
                    required=True,
                )
            )

        async def on_submit(self, interaction: discord.Interaction):
            try:
                page_number = int(self.children[0].value)
            except ValueError:
                await interaction.response.send_message(
                    "유효하지 않은 페이지 번호 값입니다. 숫자를 입력해 주세요.",
                    ephemeral=True,
                )
                return
            if page_number > self.parent_view.max_pages or page_number < 1:
                await interaction.response.send_message(
                    f"유효하지 않은 페이지 번호 값입니다. 1 이상 {self.parent_view.max_pages} 이하의 값을 입력해 주세요.",
                    ephemeral=True,
                )
                return
            self.parent_view.page = page_number - 1
            await interaction.response.edit_message(embed=self.parent_view.get_embed(), view=self.parent_view)
