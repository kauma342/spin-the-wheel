import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import os
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

import re
MENTION_RE = re.compile(r"^<@!?(\d+)>$")

def is_mention(name: str) -> bool:
    return bool(MENTION_RE.match(name.strip()))

def display_name(name: str) -> str:
    """For embeds: show the raw mention string in a code block so it doesn't ping twice."""
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

    em = discord.Embed(
        title="🎡  Wheel is ready!",
        color=C_GREEN,
    )
    em.add_field(name="👥  Names",       value=f"**{len(name_list)}**",      inline=True)
    em.add_field(name="🔢  Per group",   value=f"**{group_size}**",          inline=True)
    em.add_field(name="📦  Max groups",  value=f"**{max_groups}**",          inline=True)
    em.add_field(name="⏱️  Delay",       value=f"`{delay_desc(delay)}`",     inline=True)

    # Plain text join — embeds resolve mentions to @username without pinging
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
@app_commands.describe(
    count = "How many groups to draw in a row (default: 1)"
)
async def slash_draw(interaction: discord.Interaction, count: int = 1):
    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    if count < 1:
        return await interaction.response.send_message(embed=err("Count must be at least **1**."), ephemeral=True)

    pool = wheel["pool"]
    size = wheel["group_size"]

    if len(pool) == 0:
        return await interaction.response.send_message(
            embed=err("The pool is empty! Use `/reset` to start over."), ephemeral=True
        )
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

    # Cap count to how many full groups we can actually draw
    max_drawable = len(pool) // size
    if count > max_drawable:
        count = max_drawable

    is_random, fixed, dmin, dmax = parse_delay(wheel["delay"])
    d_desc = f"{dmin}–{dmax}s" if is_random else f"{fixed}s"

    # ── Opening message ────────────────────────────────────────────────────────
    open_em = discord.Embed(
        title=f"🎡  Drawing {'group' if count == 1 else f'{count} groups'}…",
        description=f"**{size}** names per group  ·  **{d_desc}** delay between reveals",
        color=C_GOLD,
    )
    open_em.set_footer(text="Spinning the wheel — stand by!")
    await interaction.response.send_message(embed=open_em)

    # ── Draw each group ────────────────────────────────────────────────────────
    for g in range(count):
        # Stop early if pool runs dry
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

        # Separator between multiple groups
        if count > 1:
            sep_em = discord.Embed(
                title=f"━━━  Group {group_num}  ━━━",
                color=C_DARK,
            )
            await interaction.followup.send(embed=sep_em)

        # Reveal names one by one
        for i, name in enumerate(drawn):
            if i > 0:
                await asyncio.sleep(get_delay_seconds(is_random, fixed, dmin, dmax))

            # In embed body, mentions render as @username without re-pinging
            display = name if is_mention(name) else f"**{name}**"
            group_label = f"Group {group_num}  ·  " if count > 1 else ""
            reveal_em = discord.Embed(
                title=f"{medal(i)}  {group_label}Pick {i + 1} of {size}",
                description=f"### {display}",
                color=C_GOLD,
            )
            reveal_em.set_footer(text=pool_footer())
            # -# renders as small text in Discord's new markdown; still triggers the ping
            ping = f"-# {name}" if is_mention(name) else None
            await interaction.followup.send(content=ping, embed=reveal_em)

        # Group summary — use plain description (no code block) so mentions resolve to @username
        summary_em = discord.Embed(
            title=f"✅  Group {group_num} complete!",
            color=C_GREEN,
        )
        for si, sn in enumerate(drawn):
            summary_em.add_field(name=f"{medal(si)}  Slot {si + 1}", value=sn, inline=True)
        summary_em.set_footer(text=pool_footer() + "  ·  /groups to see all")

        # Add a small pause between groups (before next group's separator)
        if g < count - 1:
            await asyncio.sleep(1.5)

        await interaction.followup.send(embed=summary_em)

    # ── Final wrap-up when drawing multiple groups ─────────────────────────────
    if count > 1:
        all_groups = wheel["groups"]
        wrap_em = discord.Embed(
            title=f"🏁  All {count} groups drawn!",
            color=C_TEAL,
        )
        for num, names in list(all_groups.items())[-count:]:
            wrap_em.add_field(
                name=f"Group {num}",
                value="  ·  ".join(names),
                inline=False,
            )
        wrap_em.set_footer(text=pool_footer())
        await interaction.followup.send(embed=wrap_em)

# ══════════════════════════════════════════════════════════════════════════════
#  /drawremaining  — assign leftover names
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="drawremaining", description="Assign the leftover names that don't fill a full group")
async def slash_drawremaining(interaction: discord.Interaction):
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

    em = discord.Embed(
        title=f"✅  Group {group_num}  (partial — {len(drawn)} name(s))",
        color=C_GREEN,
    )
    for si, sn in enumerate(drawn):
        em.add_field(name=f"🏅  Slot {si + 1}", value=sn, inline=True)
    em.set_footer(text="Pool is now empty  ·  /groups to see all results  ·  /reset to start over")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /groups  — show all drawn groups
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="groups", description="Show all groups drawn so far")
async def slash_groups(interaction: discord.Interaction):
    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    groups = wheel.get("groups", {})

    if not groups:
        em = discord.Embed(
            title="📋  No groups yet",
            description="Use `/draw` to create the first group.",
            color=C_PURPLE,
        )
        return await interaction.response.send_message(embed=em)

    em = discord.Embed(
        title=f"📋  All Groups  —  {len(groups)} drawn",
        color=C_PURPLE,
    )

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
#  /add  — add names to the pool
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="add", description="Add names to the pool")
@app_commands.describe(names="Comma-separated names to add")
async def slash_add(interaction: discord.Interaction, names: str):
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
#  /remove  — remove names from the pool
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="remove", description="Remove names from the pool")
@app_commands.describe(names="Comma-separated names to remove")
async def slash_remove(interaction: discord.Interaction, names: str):
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
#  /view  — show names still in the pool
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="view", description="Show all names still in the pool")
async def slash_view(interaction: discord.Interaction):
    if not has_wheel():
        return await interaction.response.send_message(embed=err("No wheel set up. Use `/setup` first."), ephemeral=True)

    pool = wheel["pool"]
    if not pool:
        em = discord.Embed(
            title="🎡  Pool is empty",
            description="Use `/reset` to restore all names, or `/drawremaining` if there were leftovers.",
            color=C_ORANGE,
        )
        return await interaction.response.send_message(embed=em)

    lines = "\n".join(f"  {i+1:>3}.  {n}" for i, n in enumerate(pool))
    em = discord.Embed(
        title=f"🎡  Pool  —  {len(pool)} names remaining",
        description=f"```\n{lines}\n```",
        color=C_PURPLE,
    )
    em.add_field(name="🔢  Per group",       value=f"**{wheel['group_size']}**",       inline=True)
    em.add_field(name="⏱️  Delay",           value=f"`{delay_desc(wheel['delay'])}`",  inline=True)
    em.add_field(name="📦  Groups drawn",    value=f"**{len(wheel['groups'])}**",      inline=True)

    remaining_groups = len(pool) // wheel["group_size"]
    em.add_field(name="📊  Groups left",     value=f"**~{remaining_groups}**",         inline=True)
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /reset  — restore pool to full original list
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="reset", description="Restore the pool to the full original list and clear all groups")
async def slash_reset(interaction: discord.Interaction):
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
#  /help  — show available commands
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="help", description="Show all available commands")
async def slash_help(interaction: discord.Interaction):
    em = discord.Embed(
        title="🎡  SpinBot — Commands",
        color=C_BLUE,
    )
    commands_info = [
        ("`/setup`",          "names, group_size, delay",   "Load names and configure the wheel"),
        ("`/draw`",           "count (optional)",           "Draw the next group(s) — use `count` to draw multiple in a row"),
        ("`/drawremaining`",  "—",                          "Assign leftover names that don't fill a full group"),
        ("`/groups`",         "—",                          "Show all groups drawn so far"),
        ("`/view`",           "—",                          "Show all names still in the pool"),
        ("`/add`",            "names",                      "Add names to the pool"),
        ("`/remove`",         "names",                      "Remove names from the pool"),
        ("`/reset`",          "—",                          "Restore pool to the original list, clear all groups"),
        ("`/help`",           "—",                          "Show this message"),
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
