import discord
from discord.ext import commands
from discord.ui import Button, View
import datetime
import os  # ✅ เพิ่ม import os
from myserver import server_on  # ⚠️ ต้องมีไฟล์ myserver.py อยู่จริงนะ

# --- ⚙️ การตั้งค่า ---
# ไม่ควรใส่ Token ตรงนี้ ให้ไปใส่ใน Environment Secrets (ถ้ารันใน Replit)
PREFIX = "!"
LOG_CHANNEL_ID = 1437395517545123860 # 🔴 ID ห้อง Log
WHITELIST = [1160547793782439976, 1303246365303898194]    # ID เจ้าของเซิร์ฟ

# ลิมิตความเร็ว
LIMITS = {
    "channel_create": {"max": 3, "seconds": 10},
    "channel_delete": {"max": 3, "seconds": 10},
    "role_create": {"max": 3, "seconds": 10},
    "ban_member": {"max": 3, "seconds": 10},
    "webhook": {"max": 2, "seconds": 10},
}

tracker = {k: {} for k in LIMITS.keys()}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# --- 🔘 ส่วนของระบบปุ่ม (UI) ---
class UnbanView(View):
    def __init__(self, user_id, user_name):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_name = user_name

    @discord.ui.button(label="🔓 ปลดแบนทันที (Unban)", style=discord.ButtonStyle.green, custom_id="unban_btn")
    async def unban_button(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in WHITELIST:
            await interaction.response.send_message("❌ คุณไม่มีสิทธิ์กดปุ่มนี้", ephemeral=True)
            return

        guild = interaction.guild
        try:
            user = await bot.fetch_user(self.user_id)
            await guild.unban(user, reason=f"Unbanned by {interaction.user} via Button")
            
            button.label = f"✅ ปลดแบน {self.user_name} แล้ว"
            button.disabled = True
            button.style = discord.ButtonStyle.grey
            await interaction.response.edit_message(view=self)
            
            await interaction.followup.send(f"✅ ปลดแบน **{self.user_name}** เรียบร้อยครับ!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ ไม่พบผู้ใช้นี้ในรายชื่อแบน (อาจจะถูกปลดไปแล้ว)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

class BanListView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📜 ดูรายชื่อคนถูกแบน (Show Bans)", style=discord.ButtonStyle.blurple, custom_id="show_bans_btn")
    async def show_bans(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ดูรายการแบน", ephemeral=True)
            return

        bans = [entry async for entry in interaction.guild.bans()]
        
        if not bans:
            await interaction.response.send_message("✅ เซิร์ฟเวอร์นี้สะอาดมาก! ไม่มีใครถูกแบนเลย", ephemeral=True)
            return

        msg = "**📋 รายชื่อผู้ถูกแบน (ล่าสุด):**\n"
        for entry in bans[:20]:
            msg += f"• **{entry.user}** (ID: `{entry.user.id}`) - เหตุผล: {entry.reason}\n"
        
        if len(bans) > 20:
            msg += f"\n...และอีก {len(bans)-20} คน"

        await interaction.response.send_message(msg, ephemeral=True)

# --- 🛠️ ฟังก์ชันตรวจสอบและลงโทษ ---
async def check_limits(action, member, guild):
    if member.id in WHITELIST or member.id == bot.user.id:
        return

    now = datetime.datetime.now()
    
    if member.id not in tracker[action]:
        tracker[action][member.id] = []

    limit_seconds = LIMITS[action]["seconds"]
    tracker[action][member.id] = [t for t in tracker[action][member.id] if (now - t).total_seconds() < limit_seconds]
    tracker[action][member.id].append(now)

    if len(tracker[action][member.id]) > LIMITS[action]["max"]:
        try:
            await guild.ban(member, reason=f"Anti-Nuke: Spamming {action}")
            del tracker[action][member.id]

            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(title="🚨 DETECTED NUKER!", color=discord.Color.red(), timestamp=now)
                embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
                embed.add_field(name="Action", value=f"Spamming **{action}**", inline=False)
                embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
                embed.set_footer(text="Anti-Nuke System")

                view = UnbanView(user_id=member.id, user_name=member.name)
                await log_channel.send(embed=embed, view=view)
            
            print(f"🚨 BANNED: {member} for {action}")
            
        except Exception as e:
            print(f"❌ Failed to ban {member}: {e}")

# --- 📡 Events ---
@bot.event
async def on_ready():
    print(f"🛡️ Security Bot Online: {bot.user}")

@bot.command()
async def panel(ctx):
    if ctx.author.id in WHITELIST or ctx.author.guild_permissions.administrator:
        embed = discord.Embed(title="🛡️ Admin Control Panel", description="กดปุ่มด้านล่างเพื่อดูรายชื่อคนที่ถูกแบนทั้งหมด", color=discord.Color.blue())
        view = BanListView()
        await ctx.send(embed=embed, view=view)

# Event Listeners
@bot.event
async def on_guild_channel_create(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
        await check_limits("channel_create", entry.user, channel.guild)

@bot.event
async def on_guild_channel_delete(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        await check_limits("channel_delete", entry.user, channel.guild)

@bot.event
async def on_guild_role_create(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        await check_limits("role_create", entry.user, role.guild)

@bot.event
async def on_member_ban(guild, user):
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        await check_limits("ban_member", entry.user, guild)

@bot.event
async def on_webhooks_update(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
        await check_limits("webhook", entry.user, channel.guild)

# รัน Server
server_on()

# ✅ รันบอท (ต้องตั้งค่าตัวแปร TOKEN ใน Secrets ของ Replit หรือ Environment Variables ของเครื่อง)
try:
    bot.run(os.getenv('TOKEN'))
except Exception as e:
    print(f"❌ Error starting bot: {e}")
    print("⚠️ อย่าลืมตรวจสอบว่าใส่ TOKEN ใน Secrets ถูกต้องหรือไม่")