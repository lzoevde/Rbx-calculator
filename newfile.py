import os
import threading
import discord
from discord.ext import commands
from flask import Flask

# ----------------- 🌐 Flask 웹 서버 (렌더 24/7 유지용) -----------------
app = Flask('')


@app.route('/')
def home():
  return "Bot is alive and running!"


def run_web():
  app.run(host='0.0.0.0', port=8080)


def keep_alive():
  t = threading.Thread(target=run_web)
  t.start()


# ----------------- 🤖 디스코드 봇 설정 -----------------
intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix="!", intents=intents)

# 기본 시세 설정값
bot_config = {"rbx1": 1000, "rbx2": 1000}


# ----------------- 📊 UI 및 임베드 생성 함수 -----------------
def get_panel_embed():
  r1 = bot_config["rbx1"]
  r2 = bot_config["rbx2"]

  embed = discord.Embed(
      title="💎 프리미엄 로벅스 효율 & 시세 계산기",
      description=(
          "가장 합리적인 거래 조건을 실시간으로 비교하고 계산하세요!\n\n"
          "📊 **[ 현재 적용된 실시간 시세 ]**\n"
          f"• **1번 조건:** 1만원당 `{r1:,} R`\n"
          f"• **2번 조건:** 1.5만원당 `{r2:,} R`\n"
          "• **적용 수수료:** `30%`\n\n"
          "✨ 버튼을 눌러 계산하거나 시세를 변경하세요."
      ),
      color=discord.Color.blue(),
  )
  return embed


# ----------------- 🧮 모달 및 뷰 (인터랙션 타임아웃 방지 적용) -----------------


# 1. 직접 입력 계산 팝업
class DirectInputModal(discord.ui.Modal, title="💰 직접 금액 입력 계산"):
  amount_input = discord.ui.TextInput(
      label="필요한 로벅스 (R) 또는 원화 (원)",
      placeholder="예: 24000 또는 35000",
      style=discord.TextStyle.short,
      required=True,
  )

  async def on_submit(self, interaction: discord.Interaction):
    # 디스코드 3초 타임아웃 방지를 위해 즉시 defer 응답
    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
      val = int(
          self.amount_input.value.replace("R", "")
          .replace("원", "")
          .replace(",", "")
          .strip()
      )
    except ValueError:
      await interaction.followup.send(
          "❌ 숫자만 정확하게 입력해주세요!", ephemeral=True
      )
      return

    r1 = bot_config["rbx1"]
    r2 = bot_config["rbx2"]

    # 계산 로직 (예시)
    cost1 = (val / r1) * 10000
    cost2 = (val / r2) * 15000

    embed = discord.Embed(
        title="📊 로벅스 효율 비교 결과 (직접 입력)",
        description=(
            f"🎯 **목표 로벅스:** `{val:,} Robux`\n\n"
            f"📌 **1번 조건 (1만원당 {r1}R)**\n"
            f"• 필요 금액: `{cost1:,.0f}원`\n\n"
            f"📌 **2번 조건 (1.5만원당 {r2}R)**\n"
            f"• 필요 금액: `{cost2:,.0f}원`\n"
        ),
        color=discord.Color.green(),
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


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
    # 타임아웃 방지를 위해 즉시 응답 처리
    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
      new_rbx1 = int(self.rbx1_input.value.replace(",", "").strip())
      new_rbx2 = int(self.rbx2_input.value.replace(",", "").strip())
    except ValueError:
      await interaction.followup.send(
          "❌ 올바른 숫자만 입력해주세요!", ephemeral=True
      )
      return

    bot_config["rbx1"] = new_rbx1
    bot_config["rbx2"] = new_rbx2

    try:
      if interaction.message:
        await interaction.message.edit(embed=get_panel_embed())
    except Exception:
      pass

    await interaction.followup.send(
        f"✅ 시세가 성공적으로 반영되었습니다!\n"
        f"• **1번 조건**: 1만원당 **{new_rbx1:,}R**\n"
        f"• **2번 조건**: 1.5만원당 **{new_rbx2:,}R**",
        ephemeral=True,
    )


# 3. 메인 인터랙션 버튼 뷰
class CalculatorView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)

  async def quick_calculate(
      self, interaction: discord.Interaction, target_robux: int
  ):
    # 3초 타임아웃 방어
    await interaction.response.defer(thinking=True, ephemeral=True)

    r1 = bot_config["rbx1"]
    r2 = bot_config["rbx2"]

    cost1 = (target_robux / r1) * 10000
    cost2 = (target_robux / r2) * 15000

    cheaper = "1번 조건" if cost1 < cost2 else "2번 조건"
    diff = abs(cost1 - cost2)

    embed = discord.Embed(
        title="📊 로벅스 효율 비교 결과",
        description=(
            f"🎯 **목표 실질 획득량:** `{target_robux:,} Robux` (수수료 30% 반영)\n\n"
            f"📌 **1번 조건 (1만원당 {r1}R)**\n"
            f"• 필요 금액: `{cost1:,.0f}원`\n\n"
            f"📌 **2번 조건 (1.5만원당 {r2}R)**\n"
            f"• 필요 금액: `{cost2:,.0f}원`\n\n"
            "💡 **추천 및 분석**\n"
            f"✨ **{cheaper}이 더 이득입니다!**\n"
            f"• 금액 차이: 약 `{diff:,.0f}원`"
        ),
        color=discord.Color.green(),
    )
    embed.set_footer(text="Ultimate RBX Calculator • Powered by Python")
    await interaction.followup.send(embed=embed, ephemeral=True)

  @discord.ui.button(
      label="500 R", style=discord.ButtonStyle.secondary, emoji="⚡"
  )
  async def btn_500(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.quick_calculate(interaction, 500)

  @discord.ui.button(
      label="1,000 R", style=discord.ButtonStyle.secondary, emoji="⚡"
  )
  async def btn_1000(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.quick_calculate(interaction, 1000)

  @discord.ui.button(
      label="2,000 R", style=discord.ButtonStyle.secondary, emoji="⚡"
  )
  async def btn_2000(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await self.quick_calculate(interaction, 2000)

  @discord.ui.button(
      label="직접 입력", style=discord.ButtonStyle.success, emoji="✏️"
  )
  async def btn_direct(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_modal(DirectInputModal())

  @discord.ui.button(
      label="시세 설정", style=discord.ButtonStyle.primary, emoji="⚙️"
  )
  async def btn_settings(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.send_modal(MarketSettingModal())


# ----------------- 🛠️ 슬래시 명령어 -----------------
@client.event
async def on_ready():
  print(f"로그인 완료: {client.user} (ID: {client.user.id})")
  try:
    synced = await client.tree.sync()
    print(f"총 {len(synced)}개의 명령어가 동기화되었습니다.")
  except Exception as e:
    print(f"명령어 동기화 실패: {e}")


@client.tree.command(name="계산패널", description="로벅스 효율 계산 패널을 소환합니다.")
async def calculator_panel(interaction: discord.Interaction):
  # 3초 타임아웃 방어
  await interaction.response.defer(ephemeral=True)
  embed = get_panel_embed()
  view = CalculatorView()
  await interaction.followup.send(embed=embed, view=view)


# ----------------- 🚀 실행 (웹 서버 + 봇 동시 구동) -----------------
if __name__ == "__main__":
  keep_alive()  # 렌더가 안 끄도록 웹 서버를 먼저 백그라운드로 실행합니다.

  TOKEN = os.environ.get("DISCORD_TOKEN")
  if TOKEN:
    client.run(TOKEN)
  else:
    print("Error: DISCORD_TOKEN 환경 변수가 설정되지 않았습니다!")
