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
    "LIMITS": {
        "channel_create": {"max": 3, "seconds": 10},
        "channel_delete": {"max": 3, "seconds": 10},
        "channel_update": {"max": 5, "seconds": 10},
        "role_create":    {"max": 3, "seconds": 10},
        "role_delete":    {"max": 2, "seconds": 10},
        "role_update":    {"max": 5, "seconds": 10},
        "ban_member":     {"max": 3, "seconds": 10},
        "kick_member":    {"max": 3, "seconds": 10},
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

# --- 🖥️ BUTTONS VIEW (SMART LOCKDOWN) ---
class SecurityPanel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="LOCKDOWN", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="panic_btn")
    async def panic_mode(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in whitelist:
            await interaction.response.send_message("❌ Access Denied", ephemeral=True)
            return
        
        # แจ้งเตือนก่อนทำงาน (Defer) เพราะการแจกยศอาจใช้เวลา 2-3 วินาที
        await interaction.response.defer()
        
        guild = interaction.guild
        try:
            # 1. สร้างยศพิเศษ "Override Access" (ถ้ายังไม่มี)
            override_role = discord.utils.get(guild.roles, name="🛡️ Override Access")
            if not override_role:
                override_role = await guild.create_role(
                    name="🛡️ Override Access",
                    permissions=discord.Permissions(send_messages=True, read_messages=True),
                    color=discord.Color.green(),
                    reason="Anti-Nuke Lockdown Bypass"
                )
                # พยายามเลื่อนยศนี้ไปไว้สูงๆ (ใต้บอท)
                try: await override_role.edit(position=guild.me.top_role.position - 1)
                except: pass

            # 2. แจกยศพิเศษให้คนใน Whitelist (เพื่อให้พิมพ์ได้)
            for uid in whitelist:
                member = guild.get_member(uid)
                if member:
                    try: await member.add_roles(override_role)
                    except: pass

            # 3. ปิดปาก @everyone (ห้ามพิมพ์)
            default_role = guild.default_role
            perms = default_role.permissions
            perms.send_messages = False
            perms.add_reactions = False
            perms.connect = False
            await default_role.edit(permissions=perms)
            
            embed = discord.Embed(
                title="🚨 SERVER LOCKDOWN ACTIVE", 
                description="✅ **คนใน Whitelist ยังสามารถพิมพ์ได้**\n⛔ **สมาชิกทั่วไปถูกระงับการพิมพ์ชั่วคราว**", 
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Lockdown Failed: {e}", ephemeral=True)

    @discord.ui.button(label="UNLOCK", style=discord.ButtonStyle.success, emoji="🔓", custom_id="unlock_btn")
    async def unlock_mode(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id not in whitelist:
            await interaction.response.send_message("❌ Access Denied", ephemeral=True)
            return

        await interaction.response.defer()
        guild = interaction.guild
        
        try:
            # 1. เปิดปาก @everyone คืน
            default_role = guild.default_role
            perms = default_role.permissions
            perms.send_messages = True
            perms.add_reactions = True
            perms.connect = True
            await default_role.edit(permissions=perms)

            # 2. ดึงยศพิเศษคืนจากคนใน Whitelist (หรือลบยศทิ้ง)
            override_role = discord.utils.get(guild.roles, name="🛡️ Override Access")
            if override_role:
                try: await override_role.delete()
                except: pass # ถ้าลบไม่ได้ก็ปล่อยไว้

            await interaction.followup.send("✅ **Server Unlocked.** กลับสู่สถานะปกติ")

        except Exception as e:
            await interaction.followup.send(f"❌ Unlock Error: {e}", ephemeral=True)

    @discord.ui.button(label="Whitelist Info", style=discord.ButtonStyle.secondary, emoji="📜", custom_id="wl_info")
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

# คำสั่ง Limits (UI ใหม่ตามที่ขอ + ปุ่มกด Smart Lockdown)
@bot.command()
async def limits(ctx):
    try: await ctx.message.delete()
    except: pass
    lim = CONFIG["LIMITS"]
    
    config_text = f"""```ansi
[ 📂 CHANNELS ]
• Create Limit [สร้างห้อง] : \u001b[0;36m{lim['channel_create']['max']} actions / {lim['channel_create']['seconds']}s\u001b[0m
• Delete Limit [ลบห้อง] : \u001b[0;36m{lim['channel_delete']['max']} actions / {lim['channel_delete']['seconds']}s\u001b[0m
• Update Limit [เปลี่ยนชื่อห้อง] : \u001b[0;36m{lim['channel_update']['max']} actions / {lim['channel_update']['seconds']}s\u001b[0m

[ 🛡️ ROLES ]
• Create Limit [สร้างยศ] : \u001b[0;35m{lim['role_create']['max']} actions / {lim['role_create']['seconds']}s\u001b[0m
• Delete Limit [ลบยศ] : \u001b[0;35m{lim['role_delete']['max']} actions / {lim['role_delete']['seconds']}s\u001b[0m
• Update Limit [แก้ไขยศ] : \u001b[0;35m{lim['role_update']['max']} actions / {lim['role_update']['seconds']}s\u001b[0m

[ 👤 MEMBERS ]
• Mass Ban     : \u001b[0;31m{lim['ban_member']['max']} users   / {lim['ban_member']['seconds']}s\u001b[0m
• Mass Kick    : \u001b[0;31m{lim['kick_member']['max']} users   / {lim['kick_member']['seconds']}s\u001b[0m

[ 🚨 CRITICAL ]
• Anti-Webhook : \u001b[0;31m{lim['webhook']['max']} action  / {lim['webhook']['seconds']}s (STRICT)\u001b[0m
• Server Update: \u001b[0;31m{lim['guild_update']['max']} action  / {lim['guild_update']['seconds']}s\u001b[0m
```"""

    embed = discord.Embed(
        title="🔒 SECURITY CONFIGURATION", 
        description=config_text,
        color=0x2b2d31
    )

    embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━━━━━", value="⚠️ *ผู้ที่ฝ่าฝืนเงื่อนไขด้านบนจะถูก **BAN** ทันทีโดยอัตโนมัติ*", inline=False)
    embed.set_image(url="https://media.discordapp.net/attachments/1160547793782439976/118672000000000000/banner.png") 
    
    await ctx.send(embed=embed, view=SecurityPanel())

# Trust System
@bot.command()
async def trust(ctx, member: discord.Member):
    if ctx.author.id != CONFIG["OWNER_ID"]: return
    if member.id not in whitelist:
        whitelist.append(member.id)
        save_whitelist(whitelist)
        await ctx.send(f"✅ **{member.name}** added to Whitelist.", delete_after=5)
    else:
        await ctx.send(f"⚠️ {member.name} is already trusted.", delete_after=5)

@bot.command()
async def untrust(ctx, member: discord.Member):
    if ctx.author.id != CONFIG["OWNER_ID"]: return
    if member.id in whitelist:
        whitelist.remove(member.id)
        save_whitelist(whitelist)
        await ctx.send(f"🚫 **{member.name}** removed from Whitelist.", delete_after=5)

# Events
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
