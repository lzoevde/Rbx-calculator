import os
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread

# ----------------- 🌐 Render 24시간 안 꺼지게 하는 웹 서버 설정 -----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()
# -------------------------------------------------------------------------

# 봇 설정
intents = discord.Intents.default()
client = commands.Bot(command_prefix="!", intents=intents)

# 기본 시세 설정
bot_config = {
    "price1": 10000,
    "rbx1": 1300,  # 1만원당 1번 조건 로벅스
    "fee_rate": 0.3,
    "price2": 15000,
    "rbx2": 1000,  # 1.5만원당 2번 조건 로벅스
}


@client.event
async def on_ready():
  print(f"로그인 완료: {client.user}")
  try:
    synced = await client.tree.sync()
    print(f"총 {len(synced)}개의 명령어가 동기화되었습니다.")
  except Exception as e:
    print(e)


# 메인 패널 임베드 생성 함수 (실시간 연동용)
def get_panel_embed():
  embed = discord.Embed(
      title="💎 프리미엄 로벅스 효율 & 시세 계산기",
      description=(
          "가장 합리적인 거래 조건을 실시간으로 비교하고 계산하세요!\n\n"
          "📊 **[ 현재 적용된 실시간 시세 ]**\n"
          f"• **1번 조건**: `1만원당 {bot_config['rbx1']:,} R`\n"
          f"• **2번 조건**: `1.5만원당 {bot_config['rbx2']:,} R`\n"
          f"• **적용 수수료**: `{int(bot_config['fee_rate']*100)}%`"
      ),
      color=discord.Color.from_rgb(88, 101, 242),
  )
  embed.set_footer(text="✨ 버튼을 눌러 계산하거나 시세를 변경하세요.")
  return embed


# 공통 계산 및 결과 전송 함수
async def send_calc_result(
    interaction: discord.Interaction, n: int, custom_fee: float = None
):
  await interaction.response.defer(thinking=True)

  # 이전 계산 결과 메시지 청소
  try:
    async for message in interaction.channel.history(limit=10):
      if message.author == client.user and message.embeds:
        if "효율 비교 결과" in message.embeds[0].title:
          await message.delete()
  except Exception as e:
    print(f"이전 메시지 삭제 중 에러: {e}")

  fee = custom_fee if custom_fee is not None else bot_config["fee_rate"]

  # 계산 로직
  needed_rbx1 = n / (1 - fee) if fee > 0 else n
  cost1 = (needed_rbx1 / bot_config["rbx1"]) * bot_config["price1"]
  cost2 = (n / bot_config["rbx2"]) * bot_config["price2"]

  # 결과 임베드 디자인
  embed = discord.Embed(
      title="📊 로벅스 효율 비교 결과",
      description=f"🎯 목표 실질 획득량: **{n:,} Robux** (수수료 {int(fee*100)}% 반영)",
      color=discord.Color.from_rgb(46, 204, 113),
  )

  embed.add_field(
      name=f"📌 1번 조건 (1만원당 {bot_config['rbx1']:,}R)",
      value=(
          f"• 필요 금액: **{cost1:,.0f}원**\n• 구매 필요:"
          f" `{needed_rbx1:,.1f} rbx`"
      ),
      inline=False,
  )

  embed.add_field(
      name=f"📌 2번 조건 (1.5만원당 {bot_config['rbx2']:,}R)",
      value=f"• 필요 금액: **{cost2:,.0f}원**",
      inline=False,
  )

  if cost1 < cost2:
    diff = cost2 - cost1
    save_pct = (diff / cost2) * 100
    gauge = "▰" * min(int(save_pct // 5), 10) + "▱" * (
        10 - min(int(save_pct // 5), 10)
    )
    embed.add_field(
        name="💡 추천 및 분석",
        value=(
            f"✨ **1번 조건이 더 이득입니다!**\n• 절약 금액: 약"
            f" **{diff:,.0f}원** ({save_pct:.1f}% 절약)\n• 효율 게이지:"
            f" `[{gauge}]`"
        ),
        inline=False,
    )
  elif cost1 > cost2:
    diff = cost1 - cost2
    embed.add_field(
        name="💡 추천 및 분석",
        value=f"⚠️ **2번 조건이 더 이득입니다!**\n• 1번 선택 시 약 **{diff:,.0f}원** 손해",
        inline=False,
    )
  else:
    embed.add_field(
        name="💡 추천 및 분석",
        value="🤝 두 조건의 가치가 정확히 일치합니다!",
        inline=False,
    )

  embed.set_footer(text="Ultimate RBX Calculator • Powered by Python")
  await interaction.followup.send(embed=embed)


# 1. 수량 직접 입력 팝업
class CustomRobuxModal(discord.ui.Modal, title="🧮 직접 수량 입력하기"):
  robux_input = discord.ui.TextInput(
      label="원하는 실질 로벅스 수량",
      placeholder="예: 1000",
      style=discord.TextStyle.short,
      required=True,
  )

  async def on_submit(self, interaction: discord.Interaction):
    try:
      n = int(self.robux_input.value.replace(",", "").strip())
    except ValueError:
      await interaction.response.send_message(
          "❌ 숫자만 정확히 입력해주세요!", ephemeral=True
      )
      return
    if n <= 0:
      await interaction.response.send_message(
          "❌ 1 이상의 숫자를 입력해주세요.", ephemeral=True
      )
      return
    await send_calc_result(interaction, n)


# 2. 실시간 시세 변경 팝업
class MarketSettingModal(discord.ui.Modal, title="⚙️ 실시간 거래 시세 변경"):
  rbx1_input = discord.ui.TextInput(
      label="1번 조건 (1만원당 받을 로벅스)",
      placeholder=str(bot_config["rbx1"]),
      style=discord.TextStyle.short,
      required=True,
  )
  rbx2_input = discord.ui.TextInput(
      label="2번 조건 (1.5만원당 받을 로벅스)",
      placeholder=str(bot_config["rbx2"]),
      style=discord.TextStyle.short,
      required=True,
  )

  async def on_submit(self, interaction: discord.Interaction):
    try:
      new_rbx1 = int(self.rbx1_input.value.replace(",", "").strip())
      new_rbx2 = int(self.rbx2_input.value.replace(",", "").strip())
    except ValueError:
      await interaction.response.send_message(
          "❌ 올바른 숫자만 입력해주세요!", ephemeral=True
      )
      return

    bot_config["rbx1"] = new_rbx1
    bot_config["rbx2"] = new_rbx2

    try:
      await interaction.message.edit(embed=get_panel_embed())
    except Exception:
      pass

    await interaction.response.send_message(
        f"✅ 시세가 성공적으로 반영되었습니다!\n"
        f"• **1번 조건**: 1만원당 **{new_rbx1:,}R**\n"
        f"• **2번 조건**: 1.5만원당 **{new_rbx2:,}R**",
        ephemeral=True,
    )


# 3. 최신식 버튼 패널 뷰
class UltimateRobuxView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(
      label="500 R",
      style=discord.ButtonStyle.secondary,
      emoji="⚡",
      custom_id="btn_500r",
  )
  async def btn_500r(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await send_calc_result(interaction, 500)

  @discord.ui.button(
      label="1,000 R",
      style=discord.ButtonStyle.secondary,
      emoji="⚡",
      custom_id="btn_1000r",
  )
  async def btn_1000r(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await send_calc_result(interaction, 1000)

  @discord.ui.button(
      label="2,000 R",
      style=discord.ButtonStyle.secondary,
      emoji="⚡",
      custom_id="btn_2000r",
  )
  async def btn_2000r(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await send_calc_result(interaction, 2000)

  @discord.ui.button(
      label="직접 입력",
      style=discord.ButtonStyle.success,
      emoji="✏️",
      custom_id="btn_custom",
  )
  async def btn_custom(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_modal(CustomRobuxModal())

  @discord.ui.button(
      label="시세 설정",
      style=discord.ButtonStyle.primary,
      emoji="⚙️",
      custom_id="btn_market_setting",
  )
  async def btn_market_setting(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_modal(MarketSettingModal())


# /계산패널 명령어
@client.tree.command(
    name="계산패널", description="초고속 실시간 연동 기능이 포함된 최신식 로벅스 계산 패널을 소환합니다."
)
async def panel(interaction: discord.Interaction):
  await interaction.response.send_message(
      embed=get_panel_embed(), view=UltimateRobuxView()
  )


# ----------------- 🚀 실행 (웹 서버 + 봇 동시 구동) -----------------
if __name__ == "__main__":
  keep_alive()  # 렌더가 안 끄도록 웹 서버를 먼저 백그라운드로 실행합니다.

  TOKEN = os.environ.get("DISCORD_TOKEN")
  if TOKEN:
    client.run(TOKEN)
  else:
    print("Error: DISCORD_TOKEN 환경 변수가 설정되지 않았습니다!")
