import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import os
import re
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
TOKEN = os.environ["TOKEN"]

intents = discord.Intents.default()
intents.message_content = True

class SpinBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅  Slash commands synced.")

bot = SpinBot()

# ── Auth ───────────────────────────────────────────────────────────────────────
OWNER_ID = 782306018682994751
ROLE_ID  = 1062736077921726566

def is_authorized(interaction: discord.Interaction) -> bool:
    if interaction.user.id == OWNER_ID:
        return True
    if interaction.guild:
        role = interaction.guild.get_role(ROLE_ID)
        if role and role in interaction.user.roles:
            return True
    return False

# ── Ads ───────────────────────────────────────────────────────────────────────
# Add your image URLs here — one per line. A random one is picked each denial.
ADS = [
    "https://media.discordapp.net/attachments/1506036018690658364/1507787771119407224/11.jpg?ex=6a132c49&is=6a11dac9&hm=f868cd621bd03227b6bf85686519573705015406b4b7176021693ab7755719f5&=&format=webp&width=2393&height=1197",
    "https://media.discordapp.net/attachments/1506036018690658364/1507787771706736731/12.jpg?ex=6a132c4a&is=6a11daca&hm=c4a48caeb88e8a0033bf76d650576412cfd2272715aa576899031dbc8ef38ea3&=&format=webp&width=2393&height=1197",
    "https://media.discordapp.net/attachments/1506036018690658364/1507787772193411242/13.jpg?ex=6a132c4a&is=6a11daca&hm=326d453c0f7b3eaadd69883f3a91cc59172808c1f6f1b599b954af6ef04186bb&=&format=webp&width=2393&height=1197",
    "https://media.discordapp.net/attachments/1506036018690658364/1507787792271413248/1.jpg?ex=6a132c4f&is=6a11dacf&hm=50ec6a9637c71200b7e6e5b5bdea851395625a6c097aa9058a33197456da15ec&=&format=webp&width=2393&height=1197",
    "https://media.discordapp.net/attachments/1506036018690658364/1507787792787177542/2.jpg?ex=6a132c4f&is=6a11dacf&hm=f777b6938c782a633c06782517832a50ca1ac22610474de268170532586cde59&=&format=webp&width=2393&height=1197",
    "https://media.discordapp.net/attachments/1506036018690658364/1507787793349349487/3.jpg?ex=6a132c4f&is=6a11dacf&hm=82440f8c9ebdd54f74acbb3f0fba1f8da5057a3b75abdda977297e151db48f03&=&format=webp&width=2393&height=1197",
    "https://media.discordapp.net/attachments/1506036018690658364/1507787794091868229/4.jpg?ex=6a132c4f&is=6a11dacf&hm=2a181dadbe453f1bfefdcc1f18221600acf4349180b8c843a44c3f822852a1af&=&format=webp&width=2393&height=1197",
    "https://media.discordapp.net/attachments/1506036018690658364/1507787794880139354/5.jpg?ex=6a132c4f&is=6a11dacf&hm=b4a8c3fd2fcce0c18a36f2056781fc3ac9131db212886efc4cf27148ad72f8fe&=&format=webp&width=2393&height=1197",
    "https://media.discordapp.net/attachments/1506036018690658364/1507787796171985007/7.jpg?ex=6a132c4f&is=6a11dacf&hm=17c3da608af2d9482353d4a925b5ea7903c1c0f4fb6307fa98c20da409406e49&=&format=webp&width=2393&height=1197",
    "https://media.discordapp.net/attachments/1506036018690658364/1507787796746731520/8.jpg?ex=6a132c50&is=6a11dad0&hm=e92c6688850cb62446f8f3b46bb4a9f7caf02c3d1dc167f5270cca9d7365b48e&=&format=webp&width=2393&height=1197",
    "https://media.discordapp.net/attachments/1506036018690658364/1507787797514162317/9.jpg?ex=6a132c50&is=6a11dad0&hm=01eaacbfbeaae8200a9c9a53077beae83ba5ce0869e34fdc13dcf8903860b89b&=&format=webp&width=2393&height=1197",
]

def no_perms():
    em = discord.Embed(
        title="🚫  Absolutely not.",
        description=(
            "This wheel was crafted for the chosen few.\n"
            "You, respectfully, are not one of them.\n\n"
            "-# kindly go touch grass and make an article 🌿"
        ),
        color=C_RED,
    )
    em.set_image(url=random.choice(ADS))
    return em

# ── State ──────────────────────────────────────────────────────────────────────
wheel = {}

def has_wheel():
    return bool(wheel.get("orig"))

def pool_has_enough():
    return len(wheel.get("pool", [])) >= wheel.get("group_size", 1)

def parse_delay(s):
    s = s.strip()
    if "-" in s:
        a, b = s.split("-", 1)
        dmin, dmax = int(a.strip()), int(b.strip())
        if dmin >= dmax:
            raise ValueError("Min must be less than max, e.g. `10-30`.")
        return True, None, dmin, dmax
    fixed = int(s)
    if fixed < 1:
        raise ValueError("Delay must be at least 1 second.")
    return False, fixed, None, None

def get_delay_seconds(is_random, fixed, dmin, dmax):
    return random.randint(dmin, dmax) if is_random else fixed

def delay_desc(wheel_delay):
    s = wheel_delay.strip()
    if "-" in s:
        return f"{s}s (random)"
    return f"{s}s"

# ── Colours ────────────────────────────────────────────────────────────────────
C_GOLD   = 0xF0B232
C_GREEN  = 0x2ECC71
C_RED    = 0xED4245
C_PURPLE = 0x9B59B6
C_BLUE   = 0x5865F2
C_ORANGE = 0xE67E22
C_TEAL   = 0x1ABC9C
C_DARK   = 0x2B2D31

MEDALS = ["🥇", "🥈", "🥉"]

def medal(i):
    return MEDALS[i] if i < 3 else "🏅"

MENTION_RE = re.compile(r"^<@!?(\d+)>$")

def is_mention(name: str) -> bool:
    return bool(MENTION_RE.match(name.strip()))

def display_name(name: str) -> str:
    return f"`{name}`" if is_mention(name.strip()) else name

def err(msg):
    return discord.Embed(title="❌  Error", description=msg, color=C_RED)

def pool_footer():
    pool = wheel.get("pool", [])
    groups = wheel.get("groups", {})
    size = wheel.get("group_size", 1)
    remaining_groups = len(pool) // size
    return f"{len(pool)} names left  ·  ~{remaining_groups} group(s) remaining  ·  {len(groups)} group(s) drawn"

@bot.event
async def on_ready():
    print(f"✅  Logged in as {bot.user}")

# ══════════════════════════════════════════════════════════════════════════════
#  /setup
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="setup", description="Load names and configure group size + delay")
@app_commands.describe(
    names      = "Comma-separated names (max 100)  e.g: Ave, Anne, Mart, Lisa",
    group_size = "How many names per group  e.g: 3",
    delay      = "Seconds between each name reveal — fixed (e.g. 5) or range (e.g. 3-10)",
)
async def slash_setup(interaction: discord.Interaction, names: str, group_size: int, delay: str):
    if not is_authorized(interaction):
        return await interaction.response.send_message(embed=no_perms())

    name_list = [n.strip() for n in names.split(",") if n.strip()]

    if not name_list:
        return await interaction.response.send_message(embed=err("No names provided."), ephemeral=True)
    if len(name_list) > 100:
        return await interaction.response.send_message(embed=err(f"Maximum **100 names** allowed. You gave **{len(name_list)}**."), ephemeral=True)
    if group_size < 1:
        return await interaction.response.send_message(embed=err("Group size must be at least **1**."), ephemeral=True)
    if group_size > len(name_list):
        return await interaction.response.send_message(embed=err(f"Group size (**{group_size}**) can't exceed number of names (**{len(name_list)}**)."), ephemeral=True)
    try:
        parse_delay(delay)
    except ValueError as e:
        return await interaction.response.send_message(embed=err(str(e)), ephemeral=True)

    wheel.clear()
    wheel.update({
        "pool":       name_list.copy(),
        "orig":       name_list.copy(),
        "groups":     {},
        "group_size": group_size,
        "delay":      delay,
    })

    max_groups = len(name_list) // group_size
    leftover   = len(name_list) % group_size

    em = discord.Embed(title="🎡  Wheel is ready!", color=C_GREEN)
    em.add_field(name="👥  Names",      value=f"**{len(name_list)}**",  inline=True)
    em.add_field(name="🔢  Per group",  value=f"**{group_size}**",      inline=True)
    em.add_field(name="📦  Max groups", value=f"**{max_groups}**",      inline=True)
    em.add_field(name="⏱️  Delay",      value=f"`{delay_desc(delay)}`", inline=True)

    preview_items = name_list[:10]
    name_preview = ",  ".join(preview_items)
    if len(name_list) > 10:
        name_preview += f"  …+{len(name_list) - 10} more"
    em.add_field(name="📋  Names loaded", value=name_preview, inline=False)

    if leftover:
        em.add_field(
            name="⚠️  Leftover",
            value=f"**{leftover}** name(s) won't fill a full group — use `/drawremaining` at the end.",
            inline=False,
        )

    em.set_footer(text="Use /draw to start  ·  /view to see the pool  ·  /groups to track results")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /draw  — draw one OR multiple groups in a row
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="draw", description="Draw the next group(s) of names from the pool")
@app_commands.describe(count="How many groups to draw in a row (default: 1)")
async def slash_draw(interaction: discord.Interaction, count: int = 1):
    if not is_authorized(interaction):
        return await interaction.response.send_message(embed=no_perms())

    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)
    if count < 1:
        return await interaction.response.send_message(embed=err("Count must be at least **1**."), ephemeral=True)

    pool = wheel["pool"]
    size = wheel["group_size"]

    if len(pool) == 0:
        return await interaction.response.send_message(embed=err("The pool is empty! Use `/reset` to start over."), ephemeral=True)
    if len(pool) < size:
        em = discord.Embed(
            title="⚠️  Not enough names",
            description=(
                f"Only **{len(pool)}** name(s) left — not enough for a full group of **{size}**.\n"
                f"Use `/drawremaining` to assign them anyway, or `/reset` to start over."
            ),
            color=C_ORANGE,
        )
        return await interaction.response.send_message(embed=em)

    max_drawable = len(pool) // size
    if count > max_drawable:
        count = max_drawable

    is_random, fixed, dmin, dmax = parse_delay(wheel["delay"])
    d_desc = f"{dmin}–{dmax}s" if is_random else f"{fixed}s"

    open_em = discord.Embed(
        title=f"🎡  Drawing {'group' if count == 1 else f'{count} groups'}…",
        description=f"**{size}** names per group  ·  **{d_desc}** delay between reveals",
        color=C_GOLD,
    )
    open_em.set_footer(text="Spinning the wheel — stand by!")
    await interaction.response.send_message(embed=open_em)

    for g in range(count):
        if len(pool) < size:
            warn_em = discord.Embed(
                title="⚠️  Pool ran dry",
                description=(
                    f"Stopped after **{g}** group(s) — only **{len(pool)}** name(s) remain.\n"
                    f"Use `/drawremaining` to assign them."
                ),
                color=C_ORANGE,
            )
            await interaction.followup.send(embed=warn_em)
            return

        group_num = len(wheel["groups"]) + 1
        drawn = random.sample(pool, size)
        for name in drawn:
            pool.remove(name)
        wheel["groups"][group_num] = drawn

        if count > 1:
            sep_em = discord.Embed(title=f"━━━  Group {group_num}  ━━━", color=C_DARK)
            await interaction.followup.send(embed=sep_em)

        for i, name in enumerate(drawn):
            if i > 0:
                await asyncio.sleep(get_delay_seconds(is_random, fixed, dmin, dmax))

            display = name if is_mention(name) else f"**{name}**"
            group_label = f"Group {group_num}  ·  " if count > 1 else ""
            reveal_em = discord.Embed(
                title=f"{medal(i)}  {group_label}Pick {i + 1} of {size}",
                description=f"### {display}",
                color=C_GOLD,
            )
            reveal_em.set_footer(text=pool_footer())
            ping = f"-# {name}" if is_mention(name) else None
            await interaction.followup.send(content=ping, embed=reveal_em)

        summary_em = discord.Embed(title=f"✅  Group {group_num} complete!", color=C_GREEN)
        for si, sn in enumerate(drawn):
            summary_em.add_field(name=f"{medal(si)}  Slot {si + 1}", value=sn, inline=True)
        summary_em.set_footer(text=pool_footer() + "  ·  /groups to see all")

        if g < count - 1:
            await asyncio.sleep(1.5)

        await interaction.followup.send(embed=summary_em)

    if count > 1:
        all_groups = wheel["groups"]
        wrap_em = discord.Embed(title=f"🏁  All {count} groups drawn!", color=C_TEAL)
        for num, names in list(all_groups.items())[-count:]:
            wrap_em.add_field(name=f"Group {num}", value="  ·  ".join(names), inline=False)
        wrap_em.set_footer(text=pool_footer())
        await interaction.followup.send(embed=wrap_em)

# ══════════════════════════════════════════════════════════════════════════════
#  /drawremaining
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="drawremaining", description="Assign the leftover names that don't fill a full group")
async def slash_drawremaining(interaction: discord.Interaction):
    if not is_authorized(interaction):
        return await interaction.response.send_message(embed=no_perms())

    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    pool = wheel["pool"]
    if not pool:
        return await interaction.response.send_message(embed=err("No names left in the pool."), ephemeral=True)
    if len(pool) >= wheel["group_size"]:
        return await interaction.response.send_message(
            embed=err(f"**{len(pool)}** names remain — enough for a full group. Use `/draw` instead."),
            ephemeral=True,
        )

    group_num = len(wheel["groups"]) + 1
    drawn = pool.copy()
    pool.clear()
    wheel["groups"][group_num] = drawn

    em = discord.Embed(title=f"✅  Group {group_num}  (partial — {len(drawn)} name(s))", color=C_GREEN)
    for si, sn in enumerate(drawn):
        em.add_field(name=f"🏅  Slot {si + 1}", value=sn, inline=True)
    em.set_footer(text="Pool is now empty  ·  /groups to see all results  ·  /reset to start over")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /groups
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="groups", description="Show all groups drawn so far")
async def slash_groups(interaction: discord.Interaction):
    if not is_authorized(interaction):
        return await interaction.response.send_message(embed=no_perms())

    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    groups = wheel.get("groups", {})
    if not groups:
        return await interaction.response.send_message(embed=discord.Embed(
            title="📋  No groups yet",
            description="Use `/draw` to create the first group.",
            color=C_PURPLE,
        ))

    em = discord.Embed(title=f"📋  All Groups  —  {len(groups)} drawn", color=C_PURPLE)
    for num, names in groups.items():
        label = "partial" if len(names) < wheel["group_size"] else ""
        field_name = f"Group {num}" + (f"  ({label})" if label else "")
        em.add_field(
            name=field_name,
            value="  ·  ".join(f"{medal(i)} {n}" for i, n in enumerate(names)),
            inline=False,
        )
    em.set_footer(text=pool_footer())
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /add
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="add", description="Add names to the pool")
@app_commands.describe(names="Comma-separated names to add")
async def slash_add(interaction: discord.Interaction, names: str):
    if not is_authorized(interaction):
        return await interaction.response.send_message(embed=no_perms())

    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    new = [n.strip() for n in names.split(",") if n.strip()]
    if not new:
        return await interaction.response.send_message(embed=err("No valid names provided."), ephemeral=True)
    if len(wheel["pool"]) + len(new) > 100:
        return await interaction.response.send_message(
            embed=err(f"Would exceed 100 names ({len(wheel['pool']) + len(new)} total)."), ephemeral=True
        )

    wheel["pool"].extend(new)
    wheel["orig"].extend(new)

    added = "\n".join(f"  + {n}" for n in new)
    em = discord.Embed(title="✅  Names added", description=f"```diff\n{added}\n```", color=C_GREEN)
    em.set_footer(text=f"Pool now has {len(wheel['pool'])} names")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /remove
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="remove", description="Remove names from the pool")
@app_commands.describe(names="Comma-separated names to remove")
async def slash_remove(interaction: discord.Interaction, names: str):
    if not is_authorized(interaction):
        return await interaction.response.send_message(embed=no_perms())

    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    targets = {n.strip().lower() for n in names.split(",") if n.strip()}
    removed = [n for n in wheel["pool"] if n.lower() in targets]
    wheel["pool"] = [n for n in wheel["pool"] if n.lower() not in targets]
    wheel["orig"] = [n for n in wheel["orig"] if n.lower() not in targets]

    if not removed:
        return await interaction.response.send_message(
            embed=err("None of those names were found in the pool."), ephemeral=True
        )

    lines = "\n".join(f"  - {n}" for n in removed)
    em = discord.Embed(title="🗑️  Names removed", description=f"```diff\n{lines}\n```", color=C_ORANGE)
    em.set_footer(text=f"Pool now has {len(wheel['pool'])} names")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /view
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="view", description="Show all names still in the pool")
async def slash_view(interaction: discord.Interaction):
    if not is_authorized(interaction):
        return await interaction.response.send_message(embed=no_perms())

    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    pool = wheel["pool"]
    if not pool:
        return await interaction.response.send_message(embed=discord.Embed(
            title="🎡  Pool is empty",
            description="Use `/reset` to restore all names, or `/drawremaining` if there were leftovers.",
            color=C_ORANGE,
        ))

    lines = "\n".join(f"  {i+1:>3}.  {n}" for i, n in enumerate(pool))
    em = discord.Embed(
        title=f"🎡  Pool  —  {len(pool)} names remaining",
        description=f"```\n{lines}\n```",
        color=C_PURPLE,
    )
    em.add_field(name="🔢  Per group",    value=f"**{wheel['group_size']}**",      inline=True)
    em.add_field(name="⏱️  Delay",        value=f"`{delay_desc(wheel['delay'])}`", inline=True)
    em.add_field(name="📦  Groups drawn", value=f"**{len(wheel['groups'])}**",     inline=True)
    remaining_groups = len(pool) // wheel["group_size"]
    em.add_field(name="📊  Groups left",  value=f"**~{remaining_groups}**",        inline=True)
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /reset
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="reset", description="Restore the pool to the full original list and clear all groups")
async def slash_reset(interaction: discord.Interaction):
    if not is_authorized(interaction):
        return await interaction.response.send_message(embed=no_perms())

    if not wheel.get("orig"):
        return await interaction.response.send_message(embed=err("Nothing to reset. Use `/setup` first."), ephemeral=True)

    wheel["pool"]   = wheel["orig"].copy()
    wheel["groups"] = {}

    em = discord.Embed(
        title="🔄  Wheel reset!",
        description=f"Pool restored to **{len(wheel['pool'])}** names. All groups cleared.",
        color=C_BLUE,
    )
    em.set_footer(text="Use /draw to start assigning groups again")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /help
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="help", description="Show all available commands")
async def slash_help(interaction: discord.Interaction):
    em = discord.Embed(title="🎡  SpinBot — Commands", color=C_BLUE)
    commands_info = [
        ("`/setup`",         "names, group_size, delay", "Load names and configure the wheel"),
        ("`/draw`",          "count (optional)",         "Draw the next group(s) — use `count` to draw multiple in a row"),
        ("`/drawremaining`", "—",                        "Assign leftover names that don't fill a full group"),
        ("`/groups`",        "—",                        "Show all groups drawn so far"),
        ("`/view`",          "—",                        "Show all names still in the pool"),
        ("`/add`",           "names",                    "Add names to the pool"),
        ("`/remove`",        "names",                    "Remove names from the pool"),
        ("`/reset`",         "—",                        "Restore pool to the original list, clear all groups"),
        ("`/help`",          "—",                        "Show this message"),
    ]
    for cmd, args, desc in commands_info:
        em.add_field(
            name=f"{cmd}  {f'`{args}`' if args != '—' else ''}",
            value=desc,
            inline=False,
        )
    em.set_footer(text="SpinBot  ·  Random group assignment made easy")
    await interaction.response.send_message(embed=em, ephemeral=True)

# ── Error handler ──────────────────────────────────────────────────────────────
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    em = discord.Embed(title="❌  Something went wrong", description=str(error), color=C_RED)
    try:
        await interaction.response.send_message(embed=em, ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(embed=em, ephemeral=True)

# ── Run ────────────────────────────────────────────────────────────────────────
bot.run(TOKEN)
