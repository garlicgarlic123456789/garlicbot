import discord
from cryptography.fernet import Fernet
from discord import app_commands
from discord.ext.commands import Bot


key = Fernet.generate_key()
cipher = Fernet(key)


# 허용 사용자 ID 리스트
encode_allow_user = [1273450447633645600, 1252894601833087056, 1237634991861665868, 1297882025121812502, 1296053433371066390, 1272449065862303809]  # 예: 암호화 권한 사용자
decode_allow_user = [1305492487137267722]  # 예: 해독 권한 사용자

def setup(bot: Bot):
    @bot.tree.command(name="encode", description="메시지를 암호화합니다.")
    async def encode(interaction: discord.Interaction, message: str):
        user_id = interaction.user.id  # 명령어를 사용한 유저의 ID
        user_name = interaction.user.name
        # if user_id in encode_allow_user:
        if True : 
            encrypted_message = cipher.encrypt(message.encode()).decode()
            print(f'user: {user_name}(이)가 다음 메시지를 암호화했습니다: {message}\n암호화 결과: {encrypted_message}')
            await interaction.response.send_message(f"암호화된 메시지: {encrypted_message}", ephemeral = True)
        else:
            await interaction.response.send_message("[오류!]** 명령어 사용 권한이 부족합니다. ACL그룹 encode_allow_user에 속해 있는 사용자(이)여야 합니다.", ephemeral = True)

    # /decode 명령어
    @bot.tree.command(name="decode", description="암호화된 메시지를 해독합니다.")
    async def decode(interaction: discord.Interaction, message: str):
        user_id = interaction.user.id  # 명령어를 사용한 유저의 ID
        user_name = interaction.user.name
        if user_id in decode_allow_user:
            try:
                decrypted_message = cipher.decrypt(message.encode()).decode()
                print(f'user: {user_name}(이)가 다음 메시지를 복호화했습니다: {message}\n복호화 결과: {decrypted_message}')
                await interaction.response.send_message(f"해독된 메시지: {decrypted_message}", ephemeral = True)
            except Exception as e:
                await interaction.response.send_message("**[오류!]** 해독에 실패했습니다.", ephemeral = True)
        else:
            await interaction.response.send_message("**[오류!]** 명령어 사용 권한이 부족합니다.", ephemeral = True)