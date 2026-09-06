import os
import threading
import logging
import discord
from discord.ext import commands
from flask import Flask

# 🌐 웹 서버 (24/7 유지용)
app = Flask('')


@app.route('/')
def home():
  return "Bot is alive and running!"


def keep_alive():

  def run():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='0.0.0.0', port=8080)

  t = threading.Thread(target=run)
  t.daemon = True
  t.start()


# 🤖 디스코드 봇 설정
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!", intents=intents)

bot_config = {"rbx1": 1000, "rbx2": 1000}


def get_panel_embed():
  r1 = bot_config["rbx1"]
  r2 = bot_config["rbx2"]
  return discord.Embed(
      title="💎 로벅스 효율 계산기",
      description=(
          f"• 1번 조건: 1만원당 {r1:,} R\n• 2번 조건: 1.5만원당 {r2:,} R"
      ),
      color=discord.Color.blue(),
  )


class DirectInputModal(discord.ui.Modal, title="직접 입력"):
  amount = discord.ui.TextInput(label="로벅스 또는 원화", placeholder="24000")

  async def on_submit(self, interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    val = int(self.amount.value.replace("R", "").replace(",", "").strip())
    r1, r2 = bot_config["rbx1"], bot_config["rbx2"]
    c1, c2 = (val / r1) * 10000, (val / r2) * 15000
    await interaction.followup.send(
        f"목표 {val}R -> 1번: {c1:,.0f}원 / 2번: {c2:,.0f}원", ephemeral=True
    )


class CalculatorView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(label="500 R", style=discord.ButtonStyle.secondary)
  async def b500(self, interaction: discord.Interaction, button):
    await interaction.response.defer(thinking=True, ephemeral=True)
    r1, r2 = bot_config["rbx1"], bot_config["rbx2"]
    await interaction.followup.send(
        f"500R 필요금액 -> 1번: {(500/r1)*10000:,.0f}원", ephemeral=True
    )

  @discord.ui.button(label="직접 입력", style=discord.ButtonStyle.success)
  async def bdir(self, interaction: discord.Interaction, button):
    await interaction.response.send_modal(DirectInputModal())


@client.event
async def on_ready():
  print(f"로그인 완료: {client.user}")
  try:
    synced = await client.tree.sync()
    print(f"동기화된 명령어: {len(synced)}개")
  except Exception as e:
    print(f"동기화 에러: {e}")


@client.tree.command(name="계산패널", description="계산 패널을 띄웁니다.")
async def panel(interaction: discord.Interaction):
  await interaction.response.defer(ephemeral=True)
  await interaction.followup.send(
      embed=get_panel_embed(), view=CalculatorView()
  )


if __name__ == "__main__":
  keep_alive()
  TOKEN = os.environ.get("DISCORD_TOKEN")
  if TOKEN:
    client.run(TOKEN)
  else:
    print("토큰이 설정되지 않았습니다!")
