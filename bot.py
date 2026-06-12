import os
import discord
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, timedelta

# =========================
# 설정
# =========================

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================
# DB
# =========================

conn = sqlite3.connect(
    "mapleland.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS scales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    channel_id INTEGER,
    created_at TEXT
)
""")

conn.commit()

# =========================
# 비늘 버튼
# =========================

class ScaleView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="비늘 등록",
        emoji="🐟",
        style=discord.ButtonStyle.green,
        custom_id="scale_register"
    )
    async def register_scale(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        cursor.execute(
            """
            SELECT id
            FROM scales
            WHERE user_id=?
            """,
            (interaction.user.id,)
        )

        existing = cursor.fetchone()

        if existing:
            await interaction.response.send_message(
                "🐟 이미 등록된 비늘이 있습니다.\n/내비늘 로 확인하세요.",
                ephemeral=True
            )
            return

        now = datetime.now()

        cursor.execute(
            """
            INSERT INTO scales
            (user_id, channel_id, created_at)
            VALUES (?, ?, ?)
            """,
            (
                interaction.user.id,
                interaction.channel.id,
                now.isoformat()
            )
        )

        conn.commit()

        embed = discord.Embed(
            title="🐟 비늘 등록 완료",
            color=0x2ecc71
        )

        embed.add_field(
            name="등록일",
            value=now.strftime("%Y-%m-%d %H:%M"),
            inline=False
        )

        embed.add_field(
            name="재등록 가능",
            value=(
                now + timedelta(days=7)
            ).strftime("%Y-%m-%d %H:%M"),
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

# =========================
# 로그인
# =========================

@bot.event
async def on_ready():

    bot.add_view(ScaleView())

    synced = await bot.tree.sync()

    print(f"{bot.user} 로그인 완료!")
    print(f"{len(synced)}개 슬래시 명령어 동기화 완료!")

    if not check_scale.is_running():
        check_scale.start()

# =========================
# 비늘 패널
# =========================

@bot.tree.command(
    name="비늘패널",
    description="비늘 등록 패널"
)
async def scale_panel(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="🐟 비늘 관리 패널",
        description=
        "아래 버튼을 눌러 비늘을 등록하세요.\n\n"
        "⏰ 7일 후 자동 알림\n"
        "📩 DM 알림 지원",
        color=0x3498db
    )

    await interaction.response.send_message(
        embed=embed,
        view=ScaleView()
    )

# =========================
# 내 비늘
# =========================

@bot.tree.command(
    name="내비늘",
    description="내 비늘 확인"
)
async def my_scale(
    interaction: discord.Interaction
):

    cursor.execute(
        """
        SELECT id, created_at
        FROM scales
        WHERE user_id=?
        """,
        (interaction.user.id,)
    )

    row = cursor.fetchone()

    if not row:

        await interaction.response.send_message(
            "🐟 등록된 비늘이 없습니다.",
            ephemeral=True
        )
        return

    created = datetime.fromisoformat(
        row[1]
    )

    end_time = (
        created +
        timedelta(days=7)
    )

    remain = end_time - datetime.now()

    embed = discord.Embed(
        title="🐟 내 비늘 정보",
        color=0xf1c40f
    )

    embed.add_field(
        name="비늘 ID",
        value=str(row[0]),
        inline=False
    )

    embed.add_field(
        name="등록일",
        value=created.strftime(
            "%Y-%m-%d %H:%M"
        ),
        inline=False
    )

    embed.add_field(
        name="재등록 가능",
        value=end_time.strftime(
            "%Y-%m-%d %H:%M"
        ),
        inline=False
    )

    embed.add_field(
        name="남은 기간",
        value=f"{remain.days}일",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )

# =========================
# 비늘 삭제
# =========================

@bot.tree.command(
    name="비늘삭제",
    description="내 비늘 삭제"
)
async def delete_scale(
    interaction: discord.Interaction
):

    cursor.execute(
        """
        DELETE FROM scales
        WHERE user_id=?
        """,
        (interaction.user.id,)
    )

    conn.commit()

    await interaction.response.send_message(
        "🗑️ 비늘 삭제 완료",
        ephemeral=True
    )

# =========================
# 자동 알림
# =========================

@tasks.loop(minutes=1)
async def check_scale():

    now = datetime.now()

    cursor.execute(
        """
        SELECT
        id,
        user_id,
        channel_id,
        created_at
        FROM scales
        """
    )

    rows = cursor.fetchall()

    for row in rows:

        record_id = row[0]
        user_id = row[1]
        channel_id = row[2]

        created_at = datetime.fromisoformat(
            row[3]
        )

        if now >= (
            created_at +
            timedelta(days=7)
        ):

            channel = bot.get_channel(
                channel_id
            )

            if channel:

                await channel.send(
                    f"<@{user_id}> 🐟 비늘 재등록 가능!"
                )

            try:

                user = await bot.fetch_user(
                    user_id
                )

                await user.send(
                    "🐟 비늘 재등록 가능!"
                )

            except:
                pass

            cursor.execute(
                """
                DELETE FROM scales
                WHERE id=?
                """,
                (record_id,)
            )

            conn.commit()

# =========================
# 실행
# =========================

bot.run(TOKEN)