import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import os

# ── Config ─────────────────────────────────────────────────────────────────────
TOKEN = os.environ["TOKEN"]   # set in Railway variables

intents = discord.Intents.default()
intents.message_content = True

class SpinBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅  Slash commands synced.")

bot = SpinBot()

# ── State ──────────────────────────────────────────────────────────────────────
# wheel = {
#   "pool":       [...],   # names still available
#   "orig":       [...],   # full original list for /reset
#   "groups":     {1: ["Ave", "Anne"], 2: [...], ...},  # drawn groups so far
#   "group_size": 3,       # how many per group
#   "delay":      "10-30", # delay between each reveal
# }
wheel = {}

def has_wheel():
    return bool(wheel.get("pool"))

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

# ── Colours ────────────────────────────────────────────────────────────────────
C_GOLD   = 0xF0B232
C_GREEN  = 0x57F287
C_RED    = 0xED4245
C_PURPLE = 0x9B59B6
C_BLUE   = 0x5865F2
C_ORANGE = 0xE67E22

def err(msg):
    return discord.Embed(title="❌  Error", description=msg, color=C_RED)

@bot.event
async def on_ready():
    print(f"✅  Logged in as {bot.user}")

# ══════════════════════════════════════════════════════════════════════════════
#  /setup  — load names, set group size and delay
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="setup", description="Load names and configure group size + delay")
@app_commands.describe(
    names       = "Comma-separated names (max 100)  e.g: Ave, Anne, Mart, Lisa",
    group_size  = "How many names per group  e.g: 3",
    delay       = "Seconds between each name reveal — fixed (e.g. 5) or range (e.g. 3-10)",
)
async def slash_setup(interaction: discord.Interaction, names: str, group_size: int, delay: str):
    name_list = [n.strip() for n in names.split(",") if n.strip()]

    if not name_list:
        return await interaction.response.send_message(embed=err("No names provided."), ephemeral=True)
    if len(name_list) > 100:
        return await interaction.response.send_message(embed=err(f"Maximum **100 names** allowed. You gave {len(name_list)}."), ephemeral=True)
    if group_size < 1:
        return await interaction.response.send_message(embed=err("Group size must be at least 1."), ephemeral=True)
    if group_size > len(name_list):
        return await interaction.response.send_message(embed=err(f"Group size ({group_size}) can't be larger than the number of names ({len(name_list)})."), ephemeral=True)
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

    em = discord.Embed(title="✅  Wheel ready!", color=C_GREEN)
    em.add_field(name="👥  Names loaded",  value=f"**{len(name_list)}**",   inline=True)
    em.add_field(name="🔢  Per group",     value=f"**{group_size}**",       inline=True)
    em.add_field(name="📦  Max groups",    value=f"**{max_groups}**",       inline=True)
    em.add_field(name="⏱️  Delay",         value=f"`{delay}` seconds",      inline=True)
    if leftover:
        em.add_field(name="⚠️  Leftover", value=f"{leftover} name(s) won't fill a full group", inline=False)
    em.set_footer(text="Use /draw to create the next group  •  /view to see remaining names")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /draw  — draw the next group
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="draw", description="Draw the next group of names from the pool")
async def slash_draw(interaction: discord.Interaction):
    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    pool = wheel["pool"]
    size = wheel["group_size"]

    if len(pool) < size:
        if len(pool) == 0:
            return await interaction.response.send_message(embed=err("The pool is empty! Use `/reset` to start over."), ephemeral=True)
        # Offer to draw the remaining names as a partial group
        leftover = len(pool)
        em = discord.Embed(
            title="⚠️  Not enough names",
            description=f"Only **{leftover}** name(s) left — not enough for a full group of **{size}**.\nUse `/drawremaining` to assign them anyway, or `/reset` to start over.",
            color=C_ORANGE,
        )
        return await interaction.response.send_message(embed=em)

    is_random, fixed, dmin, dmax = parse_delay(wheel["delay"])
    delay_desc = f"{dmin}–{dmax}s" if is_random else f"{fixed}s"

    # Assign next group number
    group_num = len(wheel["groups"]) + 1

    # Pick names randomly
    drawn = random.sample(pool, size)
    for name in drawn:
        pool.remove(name)
    wheel["groups"][group_num] = drawn

    # Start embed
    em_start = discord.Embed(
        title=f"🎡  Drawing Group {group_num}…",
        description=f"Picking **{size}** names  •  Delay: **{delay_desc}** between reveals\n\n*Stand by…*",
        color=C_GOLD,
    )
    await interaction.response.send_message(embed=em_start)

    medal = ["🥇", "🥈", "🥉"]

    # Reveal one by one
    for i, name in enumerate(drawn):
        if i > 0:
            await asyncio.sleep(random.randint(dmin, dmax) if is_random else fixed)

        icon = medal[i] if i < 3 else "🏅"
        reveal_em = discord.Embed(
            title=f"👥  Group {group_num}  —  {i+1} of {size}",
            color=C_GOLD,
        )
        reveal_em.add_field(name=f"{icon}  Name", value=f"```\n{name}\n```", inline=False)
        reveal_em.set_footer(text=f"{len(pool)} names remaining in pool")
        await interaction.followup.send(embed=reveal_em)

    # Group summary
    names_list = "\n".join(f"  {medal[i] if i < 3 else '🏅'}  {n}" for i, n in enumerate(drawn))
    summary_em = discord.Embed(
        title=f"✅  Group {group_num} complete!",
        description=f"```\n{names_list}\n```",
        color=C_GREEN,
    )
    summary_em.set_footer(text=f"{len(pool)} names left  •  /draw for next group  •  /groups to see all results")
    await interaction.followup.send(embed=summary_em)

# ══════════════════════════════════════════════════════════════════════════════
#  /drawremaining  — assign leftover names that don't fill a full group
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="drawremaining", description="Assign the leftover names that don't fill a full group")
async def slash_drawremaining(interaction: discord.Interaction):
    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    pool = wheel["pool"]
    if not pool:
        return await interaction.response.send_message(embed=err("No names left in the pool."), ephemeral=True)
    if len(pool) >= wheel["group_size"]:
        return await interaction.response.send_message(embed=err(f"There are still **{len(pool)}** names — enough for a full group. Use `/draw` instead."), ephemeral=True)

    group_num = len(wheel["groups"]) + 1
    drawn = pool.copy()
    pool.clear()
    wheel["groups"][group_num] = drawn

    names_list = "\n".join(f"  🏅  {n}" for n in drawn)
    em = discord.Embed(
        title=f"✅  Group {group_num}  (partial)",
        description=f"```\n{names_list}\n```",
        color=C_GREEN,
    )
    em.set_footer(text="Pool is now empty  •  /groups to see all results  •  /reset to start over")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /groups  — show all drawn groups so far
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="groups", description="Show all groups drawn so far")
async def slash_groups(interaction: discord.Interaction):
    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    groups = wheel["groups"]
    if not groups:
        return await interaction.response.send_message(embed=discord.Embed(
            title="📋  No groups yet",
            description="Use `/draw` to create the first group.",
            color=C_PURPLE,
        ))

    lines = []
    for num, names in groups.items():
        lines.append(f"Group {num}:  {',  '.join(names)}")
    text = "\n".join(lines)

    em = discord.Embed(
        title=f"📋  Groups  —  {len(groups)} drawn",
        description=f"```\n{text}\n```",
        color=C_PURPLE,
    )
    em.set_footer(text=f"{len(wheel['pool'])} names still in pool")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /add  — add names to the pool
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="add", description="Add names to the pool")
@app_commands.describe(names="Comma-separated names to add")
async def slash_add(interaction: discord.Interaction, names: str):
    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    new = [n.strip() for n in names.split(",") if n.strip()]
    if len(wheel["pool"]) + len(new) > 100:
        return await interaction.response.send_message(embed=err(f"Would exceed 100 names ({len(wheel['pool']) + len(new)} total)."), ephemeral=True)

    wheel["pool"].extend(new)
    wheel["orig"].extend(new)

    added = "\n".join(f"  + {n}" for n in new)
    em = discord.Embed(title="✅  Names added", description=f"```diff\n{added}\n```", color=C_GREEN)
    em.set_footer(text=f"Pool now has {len(wheel['pool'])} names")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /remove  — remove names from the pool
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="remove", description="Remove names from the pool")
@app_commands.describe(names="Comma-separated names to remove")
async def slash_remove(interaction: discord.Interaction, names: str):
    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    targets = {n.strip().lower() for n in names.split(",") if n.strip()}
    removed = [n for n in wheel["pool"] if n.lower() in targets]
    wheel["pool"]  = [n for n in wheel["pool"] if n.lower() not in targets]
    wheel["orig"]  = [n for n in wheel["orig"] if n.lower() not in targets]

    if not removed:
        return await interaction.response.send_message(embed=err("None of those names were found in the pool."), ephemeral=True)

    lines = "\n".join(f"  - {n}" for n in removed)
    em = discord.Embed(title="🗑️  Names removed", description=f"```diff\n{lines}\n```", color=C_ORANGE)
    em.set_footer(text=f"Pool now has {len(wheel['pool'])} names")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /view  — show names still in the pool
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="view", description="Show all names still in the pool")
async def slash_view(interaction: discord.Interaction):
    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    pool = wheel["pool"]
    if not pool:
        return await interaction.response.send_message(embed=discord.Embed(
            title="🎡  Pool is empty",
            description="Use `/reset` to restore all names.",
            color=C_ORANGE,
        ))

    lines = "\n".join(f"  {i+1:>3}.  {n}" for i, n in enumerate(pool))
    em = discord.Embed(
        title=f"🎡  Pool  —  {len(pool)} names remaining",
        description=f"```\n{lines}\n```",
        color=C_PURPLE,
    )
    em.add_field(name="Per group", value=f"**{wheel['group_size']}**", inline=True)
    em.add_field(name="Delay",     value=f"`{wheel['delay']}` seconds", inline=True)
    em.add_field(name="Groups drawn so far", value=f"**{len(wheel['groups'])}**", inline=True)
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /reset  — restore pool to full original list, clear groups
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="reset", description="Restore the pool to the full original list and clear all groups")
async def slash_reset(interaction: discord.Interaction):
    if not wheel.get("orig"):
        return await interaction.response.send_message(embed=err("Nothing to reset. Use `/setup` first."), ephemeral=True)

    wheel["pool"]   = wheel["orig"].copy()
    wheel["groups"] = {}

    em = discord.Embed(
        title="🔄  Wheel reset",
        description=f"Pool restored to **{len(wheel['pool'])} names**. All groups cleared.",
        color=C_BLUE,
    )
    em.set_footer(text="Use /draw to start assigning groups again")
    await interaction.response.send_message(embed=em)

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
