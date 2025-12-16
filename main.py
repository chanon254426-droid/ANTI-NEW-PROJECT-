import discord
from discord.ext import commands
from discord.ui import Button, View
import datetime
import os
import json
import asyncio
from colorama import Fore, Style, init
from myserver import server_on

# Initialize Colorama
init(autoreset=True)

# ==========================================
# ⚙️ SYSTEM CONFIG (ตั้งค่าระบบหลัก)
# ==========================================
CONFIG = {
    "PREFIX": "!",
    "LOG_CHANNEL": 1437395517545123860, # 🔴 ใส่ ID ห้อง Log ของคุณ
    "OWNER_ID": 1160547793782439976,    # 👑 ใส่ ID เจ้าของคนเดียวพอ
    
    # 🛡️ ความไวในการจับ (Sensitivity)
    # "max": จำนวนครั้ง, "seconds": วินาที
    "LIMITS": {
        "channel_create": {"max": 3, "seconds": 10},
        "channel_delete": {"max": 1, "seconds": 10},
        "channel_update": {"max": 1, "seconds": 10},
        "role_create":    {"max": 3, "seconds": 10},
        "role_delete":    {"max": 1, "seconds": 10},
        "role_update":    {"max": 1, "seconds": 10},
        "ban_member":     {"max": 1, "seconds": 10},
        "kick_member":    {"max": 2, "seconds": 10},
        "webhook":        {"max": 1, "seconds": 60}, 
        "guild_update":   {"max": 1, "seconds": 60},
    }
}

# ไฟล์เก็บข้อมูล Whitelist
DB_FILE = "whitelist.json"

# ==========================================
# 🛠️ CORE FUNCTIONS
# ==========================================

def load_whitelist():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([CONFIG["OWNER_ID"]], f)
        return [CONFIG["OWNER_ID"]]
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_whitelist(ids):
    with open(DB_FILE, "w") as f:
        json.dump(ids, f)

whitelist = load_whitelist()
tracker = {k: {} for k in CONFIG["LIMITS"].keys()}
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=CONFIG["PREFIX"], intents=intents, help_command=None)

# --- 🎨 CONSOLE UI ---
def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = f"""
    {Fore.CYAN}╔════════════════════════════════════════════╗
    {Fore.CYAN}║     {Fore.MAGENTA}🛡️  CYBER SENTINEL ANTI-NUKE V3 {Fore.CYAN}     ║
    {Fore.CYAN}╠════════════════════════════════════════════╣
    {Fore.CYAN}║ {Fore.GREEN}● System Status: {Fore.WHITE}ONLINE                {Fore.CYAN}║
    {Fore.CYAN}║ {Fore.GREEN}● Protection:    {Fore.WHITE}ACTIVE (MAXIMUM)      {Fore.CYAN}║
    {Fore.CYAN}║ {Fore.GREEN}● Whitelisted:   {Fore.WHITE}{len(whitelist)} Users             {Fore.CYAN}║
    {Fore.CYAN}╚════════════════════════════════════════════╝
    {Style.RESET_ALL}
    """
    print(banner)

# --- 🖥️ DASHBOARD VIEW (PANEL) ---
class SecurityPanel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 LOCKDOWN SERVER", style=discord.ButtonStyle.danger, emoji="🚨", custom_id="panic_btn")
    async def panic_mode(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in whitelist:
            await interaction.response.send_message("❌ Access Denied", ephemeral=True)
            return
        
        await interaction.response.send_message("⚠️ INITIATING LOCKDOWN PROTOCOL...", ephemeral=True)
        guild = interaction.guild
        try:
            default_role = guild.default_role
            perms = default_role.permissions
            perms.send_messages = False
            perms.add_reactions = False
            perms.connect = False
            await default_role.edit(permissions=perms)
            
            embed = discord.Embed(title="🚨 SERVER LOCKDOWN ACTIVE", description="เซิร์ฟเวอร์ถูกปิดตายชั่วคราวโดยระบบความปลอดภัย", color=0xFF0000)
            embed.set_image(url="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3Z6eWxsMzZxeWxsMzZxeWxsMzZxeWxsMzZxeWxsMzZxeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/26tP7axeTIW5vD8TC/giphy.gif")
            await interaction.channel.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Lockdown Failed: {e}", ephemeral=True)

    @discord.ui.button(label="🔓 UNLOCK SERVER", style=discord.ButtonStyle.success, emoji="✅", custom_id="unlock_btn")
    async def unlock_mode(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in whitelist:
            await interaction.response.send_message("❌ Access Denied", ephemeral=True)
            return

        guild = interaction.guild
        default_role = guild.default_role
        perms = default_role.permissions
        perms.send_messages = True
        perms.add_reactions = True
        perms.connect = True
        await default_role.edit(permissions=perms)
        await interaction.response.send_message("✅ Server Unlocked.", ephemeral=True)

    @discord.ui.button(label="📜 Whitelist Info", style=discord.ButtonStyle.primary, emoji="👥", custom_id="wl_info")
    async def wl_check(self, interaction: discord.Interaction, button: Button):
        if not whitelist:
            users_text = "None"
        else:
            users_text = "\n".join([f"<@{uid}>" for uid in whitelist])
        embed = discord.Embed(title="🛡️ Trusted Personnel", description=users_text, color=0x00FFFF)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Logic: Core Security ---
async def check_limits(action, member, guild):
    if member.id in whitelist or member.id == bot.user.id:
        return

    now = datetime.datetime.now()
    if member.id not in tracker[action]:
        tracker[action][member.id] = []

    limit_sec = CONFIG["LIMITS"][action]["seconds"]
    tracker[action][member.id] = [t for t in tracker[action][member.id] if (now - t).total_seconds() < limit_sec]
    tracker[action][member.id].append(now)

    if len(tracker[action][member.id]) > CONFIG["LIMITS"][action]["max"]:
        try:
            del tracker[action][member.id]
            
            await guild.ban(member, reason=f"Security System: {action} Spam")
            
            log_ch = bot.get_channel(CONFIG["LOG_CHANNEL"])
            if log_ch:
                embed = discord.Embed(title="🛑 THREAT ELIMINATED", color=0xFF0000, timestamp=now)
                embed.set_author(name="Cyber Sentinel System", icon_url=bot.user.avatar.url if bot.user.avatar else None)
                embed.add_field(name="Offender", value=f"{member.mention}\nID: `{member.id}`", inline=True)
                embed.add_field(name="Violation", value=f"**{action.upper()}** Limit Exceeded", inline=True)
                embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
                embed.set_footer(text="Auto-Protection Active")
                
                view = View()
                unban_btn = Button(label="Unlock User", style=discord.ButtonStyle.green, emoji="🔓")
                
                async def unban_callback(interaction):
                    if interaction.user.id not in whitelist: return
                    await guild.unban(member)
                    await interaction.response.send_message(f"✅ Unbanned {member.name}", ephemeral=True)
                
                unban_btn.callback = unban_callback
                view.add_item(unban_btn)
                
                await log_ch.send(embed=embed, view=view)
                
            print(f"{Fore.RED}[ALERT] Banned {member} for {action}{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.YELLOW}[FAIL] Could not ban {member}: {e}{Style.RESET_ALL}")

# ==========================================
# 📡 EVENTS & COMMANDS
# ==========================================

@bot.event
async def on_ready():
    print_banner()
    log_channel = bot.get_channel(CONFIG["LOG_CHANNEL"])
    if log_channel:
        print(f"{Fore.GREEN}[OK] Log Channel Connected: #{log_channel.name}")
    else:
        print(f"{Fore.RED}[ERR] Log Channel ID Not Found!")

# คำสั่ง Panel ควบคุมหลัก
@bot.command()
async def panel(ctx):
    if ctx.author.id not in whitelist: return
    
    embed = discord.Embed(title="🛡️ CYBER SENTINEL CONTROL", description="Security Command Center", color=0x000000)
    embed.add_field(name="System Status", value="✅ **ONLINE**", inline=True)
    embed.add_field(name="Ping", value=f"`{round(bot.latency * 1000)}ms`", inline=True)
    embed.add_field(name="Security Level", value="🔥🔥 **MAXIMUM**", inline=False)
    embed.set_image(url="https://i.pinimg.com/originals/e8/15/f2/e815f2066fe7b92b6a94a29a4e21d33d.gif")
    embed.set_footer(text="Developed by You")
    
    view = SecurityPanel()
    await ctx.send(embed=embed, view=view)

# 🆕 คำสั่งโชว์กฎ Limits (Flexzy Style UI)
@bot.command()
async def limits(ctx):
    try: await ctx.message.delete()
    except: pass
    lim = CONFIG["LIMITS"]
    
    # สร้าง Embed หลัก
    embed = discord.Embed(
        title="🛡️ SECURITY THRESHOLDS", 
        description="> **Active Protection Status: `ONLINE`**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=0x2b2d31 # สีเทาเข้ม (Theme Dark)
    )

    # 1. กล่อง Channel Config (สีฟ้า)
    chan_info = (
        f"Create: \u001b[0;36m{lim['channel_create']['max']} / {lim['channel_create']['seconds']}s\u001b[0m\n"
        f"Delete: \u001b[0;36m{lim['channel_delete']['max']} / {lim['channel_delete']['seconds']}s\u001b[0m\n"
        f"Update: \u001b[0;36m{lim['channel_update']['max']} / {lim['channel_update']['seconds']}s\u001b[0m"
    )
    embed.add_field(name="📂 **Channel Config**", value=f"```ansi\n{chan_info}```", inline=False)

    # 2. กล่อง Role Config (สีชมพู)
    role_info = (
        f"Create: \u001b[0;35m{lim['role_create']['max']} / {lim['role_create']['seconds']}s\u001b[0m\n"
        f"Delete: \u001b[0;35m{lim['role_delete']['max']} / {lim['role_delete']['seconds']}s\u001b[0m\n"
        f"Update: \u001b[0;35m{lim['role_update']['max']} / {lim['role_update']['seconds']}s\u001b[0m"
    )
    embed.add_field(name="🪪 **Role Config**", value=f"```ansi\n{role_info}```", inline=False)

    # 3. กล่อง Critical Config (สีแดง)
    danger_info = (
        f"Ban/Kick : \u001b[0;31m{lim['ban_member']['max']} / {lim['ban_member']['seconds']}s\u001b[0m\n"
        f"Webhook  : \u001b[0;31m{lim['webhook']['max']} / {lim['webhook']['seconds']}s\u001b[0m\n"
        f"Server Up: \u001b[0;31m{lim['guild_update']['max']} / {lim['guild_update']['seconds']}s\u001b[0m"
    )
    embed.add_field(name="🚨 **Critical Security**", value=f"```ansi\n{danger_info}```", inline=False)

    # Footer
    footer_text = "\n⚡ **Auto-Ban System Active 24/7**\n⊂⊃ 🔐 **Webhook Protection Enabled**\n⊂⊃ 🛡️ **Anti-Nuke V3 Core System**"
    embed.add_field(name="\u200b", value=footer_text, inline=False)
    
    # Banner Image (เปลี่ยน URL รูปได้)
    embed.set_image(url="https://media.discordapp.net/attachments/1160547793782439976/118672000000000000/banner.png") 
    embed.set_footer(text="Cyber Sentinel • Advanced Security", icon_url=bot.user.avatar.url if bot.user.avatar else None)

    await ctx.send(embed=embed)

# คำสั่ง Trust System
@bot.command()
async def trust(ctx, member: discord.Member):
    if ctx.author.id != CONFIG["OWNER_ID"]: return
    
    if member.id not in whitelist:
        whitelist.append(member.id)
        save_whitelist(whitelist)
        await ctx.send(f"✅ **{member.name}** has been added to the Trusted Database.", delete_after=5)
    else:
        await ctx.send(f"⚠️ {member.name} is already trusted.", delete_after=5)

@bot.command()
async def untrust(ctx, member: discord.Member):
    if ctx.author.id != CONFIG["OWNER_ID"]: return
    
    if member.id in whitelist:
        whitelist.remove(member.id)
        save_whitelist(whitelist)
        await ctx.send(f"🚫 **{member.name}** removed from Trusted Database.", delete_after=5)

# --- Event Listeners ---
event_map = {
    'on_guild_channel_create': ('channel_create', discord.AuditLogAction.channel_create),
    'on_guild_channel_delete': ('channel_delete', discord.AuditLogAction.channel_delete),
    'on_guild_channel_update': ('channel_update', discord.AuditLogAction.channel_update),
    'on_guild_role_create': ('role_create', discord.AuditLogAction.role_create),
    'on_guild_role_delete': ('role_delete', discord.AuditLogAction.role_delete),
    'on_guild_role_update': ('role_update', discord.AuditLogAction.role_update),
    'on_member_ban': ('ban_member', discord.AuditLogAction.ban),
    'on_webhooks_update': ('webhook', discord.AuditLogAction.webhook_create),
    'on_guild_update': ('guild_update', discord.AuditLogAction.guild_update),
}

for event_name, (action_key, audit_action) in event_map.items():
    async def _wrapper(obj, a_key=action_key, a_action=audit_action):
        guild = obj.guild if hasattr(obj, 'guild') else obj
        if isinstance(obj, tuple): guild = obj[1].guild

        async for entry in guild.audit_logs(limit=1, action=a_action):
            await check_limits(a_key, entry.user, guild)
            
    bot.add_listener(_wrapper, event_name)

@bot.event
async def on_member_remove(member):
    async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
        if entry.target.id == member.id:
             await check_limits("kick_member", entry.user, member.guild)

# Start
server_on()
try:
    if not os.getenv('TOKEN'):
        print("⚠️ WARNING: Token not found in Environment Variables!")
    bot.run(os.getenv('TOKEN'))
except Exception as e:
    print(f"❌ Error: {e}")
