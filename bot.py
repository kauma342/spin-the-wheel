import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

# ── Config ─────────────────────────────────────────────────────────────────────
import os
TOKEN = os.environ["MTUwNjAxMzY4MzY2MTE0ODM3MA.Gx1P08.UDuppMgyjB96a2HnhexQ6AEuPlp4_-iWjx60TY"]
intents = discord.Intents.default()
intents.message_content = True

class SpinBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅  Slash commands synced.")

bot = SpinBot()

# ── Wheel state (in-memory) ────────────────────────────────────────────────────
wheel = {}

def has_wheel():
    return bool(wheel.get("names"))

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

# ── Embed helpers ──────────────────────────────────────────────────────────────
C_GOLD    = 0xF0B232
C_GREEN   = 0x57F287
C_RED     = 0xED4245
C_PURPLE  = 0x9B59B6
C_BLUE    = 0x5865F2
C_ORANGE  = 0xE67E22
C_DARK    = 0x2B2D31   # Discord dark bg — used for subtle embeds

def e(title="", desc="", color=C_PURPLE, fields=None, footer=None, thumbnail=None):
    """Shorthand embed builder."""
    em = discord.Embed(title=title, description=desc, color=color)
    for f in (fields or []):
        em.add_field(name=f[0], value=f[1], inline=f[2] if len(f) > 2 else False)
    if footer:
        em.set_footer(text=footer)
    if thumbnail:
        em.set_thumbnail(url=thumbnail)
    return em

@bot.event
async def on_ready():
    print(f"✅  Logged in as {bot.user}")

# ══════════════════════════════════════════════════════════════════════════════
#  /setup
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="setup", description="Load names + categories into the wheel and set timing/order")
@app_commands.describe(
    names      = "Comma-separated names — e.g: Ave, Anne, Mart  (max 60)",
    categories = "Comma-separated categories — must match name count — e.g: Germany, USA, UK",
    order      = "fixed = categories in your order  |  random = categories shuffled each spin",
    delay      = "Seconds between draws — fixed (e.g. 15) or range (e.g. 10-30)",
)
@app_commands.choices(order=[
    app_commands.Choice(name="fixed  — categories in the order you typed", value="fixed"),
    app_commands.Choice(name="random — categories shuffled each spin",      value="random"),
])
async def slash_setup(interaction: discord.Interaction, names: str, categories: str, order: str, delay: str):
    name_list = [n.strip() for n in names.split(",")      if n.strip()]
    cat_list  = [c.strip() for c in categories.split(",") if c.strip()]

    if not name_list or not cat_list:
        return await interaction.response.send_message(embed=e(
            "❌  Missing data", "Names and categories cannot be empty.", C_RED), ephemeral=True)
    if len(name_list) != len(cat_list):
        return await interaction.response.send_message(embed=e(
            "❌  Count mismatch",
            f"You gave **{len(name_list)} names** and **{len(cat_list)} categories**.\n"
            f"Every name needs exactly one category.", C_RED), ephemeral=True)
    if len(name_list) > 60:
        return await interaction.response.send_message(embed=e(
            "❌  Too many pairs", "Maximum is **60 pairs**.", C_RED), ephemeral=True)
    try:
        parse_delay(delay)
    except ValueError as err:
        return await interaction.response.send_message(embed=e(
            "❌  Bad delay", str(err), C_RED), ephemeral=True)

    wheel.clear()
    wheel.update({
        "names":      name_list.copy(),
        "categories": cat_list.copy(),
        "orig_names": name_list.copy(),
        "orig_cats":  cat_list.copy(),
        "cat_order":  order,
        "delay":      delay,
    })

    # Build pair list for display
    pair_lines = "\n".join(f"  {n:<20} →   {c}" for n, c in zip(name_list, cat_list))
    order_icon = "🔀" if order == "random" else "📋"
    order_text = "Random (shuffled each spin)" if order == "random" else "Fixed (your order)"

    em = discord.Embed(
        title="🎡  Wheel loaded!",
        description=f"```\n{pair_lines}\n```",
        color=C_GREEN,
    )
    em.add_field(name="Pairs",          value=f"**{len(name_list)}**",          inline=True)
    em.add_field(name="Category order", value=f"{order_icon}  {order_text}",    inline=True)
    em.add_field(name="Delay",          value=f"⏱️  `{delay}` seconds",         inline=True)
    em.set_footer(text="Use /spin to start drawing  •  /view to inspect the wheel")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /add
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="add", description="Add name–category pair(s) to the wheel")
@app_commands.describe(
    names      = "Comma-separated names to add",
    categories = "Comma-separated categories — must match name count",
)
async def slash_add(interaction: discord.Interaction, names: str, categories: str):
    if not has_wheel():
        return await interaction.response.send_message(embed=e(
            "❌  No wheel", "Use `/setup` first.", C_RED), ephemeral=True)

    new_names = [n.strip() for n in names.split(",")      if n.strip()]
    new_cats  = [c.strip() for c in categories.split(",") if c.strip()]

    if len(new_names) != len(new_cats):
        return await interaction.response.send_message(embed=e(
            "❌  Count mismatch",
            f"**{len(new_names)} names** vs **{len(new_cats)} categories** — must be equal.", C_RED), ephemeral=True)
    if len(wheel["names"]) + len(new_names) > 60:
        return await interaction.response.send_message(embed=e(
            "❌  Too many pairs",
            f"Would reach **{len(wheel['names']) + len(new_names)}** pairs — max is 60.", C_RED), ephemeral=True)

    wheel["names"].extend(new_names)
    wheel["categories"].extend(new_cats)
    wheel["orig_names"].extend(new_names)
    wheel["orig_cats"].extend(new_cats)

    added_lines = "\n".join(f"  + {n:<20} →   {c}" for n, c in zip(new_names, new_cats))
    em = discord.Embed(title="✅  Pairs added", description=f"```diff\n{added_lines}\n```", color=C_GREEN)
    em.set_footer(text=f"Wheel now has {len(wheel['names'])} pairs")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /remove
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="remove", description="Remove pair(s) from the wheel by name")
@app_commands.describe(names="Comma-separated names to remove")
async def slash_remove(interaction: discord.Interaction, names: str):
    if not has_wheel():
        return await interaction.response.send_message(embed=e(
            "❌  No wheel", "Use `/setup` first.", C_RED), ephemeral=True)

    targets = {n.strip().lower() for n in names.split(",") if n.strip()}
    removed, keep_n, keep_c = [], [], []

    for n, c in zip(wheel["names"], wheel["categories"]):
        if n.lower() in targets:
            removed.append((n, c))
        else:
            keep_n.append(n); keep_c.append(c)

    orig_n, orig_c = [], []
    for n, c in zip(wheel["orig_names"], wheel["orig_cats"]):
        if n.lower() not in targets:
            orig_n.append(n); orig_c.append(c)

    wheel["names"] = keep_n;  wheel["categories"] = keep_c
    wheel["orig_names"] = orig_n; wheel["orig_cats"] = orig_c

    if not removed:
        return await interaction.response.send_message(embed=e(
            "⚠️  Not found", "None of those names are in the wheel.", C_ORANGE), ephemeral=True)

    removed_lines = "\n".join(f"  - {n:<20} →   {c}" for n, c in removed)
    em = discord.Embed(title="🗑️  Pairs removed", description=f"```diff\n{removed_lines}\n```", color=C_ORANGE)
    em.set_footer(text=f"Wheel now has {len(wheel['names'])} pairs")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /spin
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="spin", description="Draw winners one by one with the configured delay")
@app_commands.describe(count="How many pairs to draw")
async def slash_spin(interaction: discord.Interaction, count: int):
    if not has_wheel():
        return await interaction.response.send_message(embed=e(
            "❌  No wheel", "Use `/setup` first.", C_RED), ephemeral=True)
    if count < 1:
        return await interaction.response.send_message(embed=e(
            "❌  Invalid count", "Count must be at least 1.", C_RED), ephemeral=True)
    if count > len(wheel["names"]):
        return await interaction.response.send_message(embed=e(
            "❌  Not enough pairs",
            f"Asked for **{count}** but only **{len(wheel['names'])}** remain.", C_RED), ephemeral=True)

    is_random, fixed, dmin, dmax = parse_delay(wheel["delay"])
    delay_desc  = f"{dmin}–{dmax}s" if is_random else f"{fixed}s"
    order_icon  = "🔀" if wheel["cat_order"] == "random" else "📋"
    order_label = "categories shuffled" if wheel["cat_order"] == "random" else "categories in order"

    # ── Start banner ──────────────────────────────────────────────────────────
    start_em = discord.Embed(
        title="🎡  Spin started!",
        description=(
            f"Drawing **{count}** pair{'s' if count != 1 else ''} "
            f"from **{len(wheel['names'])}** remaining\n\n"
            f"⏱️  Delay **{delay_desc}** between draws\n"
            f"{order_icon}  Categories **{order_label}**\n\n"
            f"*Stand by…*"
        ),
        color=C_GOLD,
    )
    await interaction.response.send_message(embed=start_em)

    # ── Pre-assign all pairs ───────────────────────────────────────────────────
    name_pool = wheel["names"].copy();  random.shuffle(name_pool)
    cat_pool  = wheel["categories"].copy()
    if wheel["cat_order"] == "random":  random.shuffle(cat_pool)

    spin_pairs = list(zip(cat_pool[:count], name_pool[:count]))
    for cat, name in spin_pairs:
        wheel["names"].remove(name);  wheel["categories"].remove(cat)

    # ── Reveal one by one ─────────────────────────────────────────────────────
    medal = ["🥇", "🥈", "🥉"]

    for i, (drawn_cat, drawn_name) in enumerate(spin_pairs):
        if i > 0:
            await asyncio.sleep(random.randint(dmin, dmax) if is_random else fixed)

        icon   = medal[i] if i < 3 else "🏅"
        remaining = len(wheel["names"])

        draw_em = discord.Embed(
            title=f"{icon}  Draw #{i+1} of {count}",
            color=C_GOLD,
        )
        draw_em.add_field(name="🌍  Nation", value=f"```\n{drawn_cat}\n```", inline=True)
        draw_em.add_field(name="👤  Name",   value=f"```\n{drawn_name}\n```", inline=True)
        draw_em.set_footer(text=(
            f"{'No pairs' if remaining == 0 else str(remaining) + ' pair' + ('' if remaining == 1 else 's')} remaining in pool"
        ))
        await interaction.followup.send(embed=draw_em)

    # ── Summary ───────────────────────────────────────────────────────────────
    summary_lines = "\n".join(
        f"  {'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else '🏅'}  {cat:<20} →   {name}"
        for i, (cat, name) in enumerate(spin_pairs)
    )
    summary_em = discord.Embed(
        title="🎉  All draws complete!",
        description=f"```\n{summary_lines}\n```",
        color=C_GREEN,
    )
    summary_em.set_footer(text=f"{len(wheel['names'])} pairs still in the pool  •  /spin again or /reset to restore")
    await interaction.followup.send(embed=summary_em)

# ══════════════════════════════════════════════════════════════════════════════
#  /reset
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="reset", description="Restore the wheel to the full original list")
async def slash_reset(interaction: discord.Interaction):
    if not wheel.get("orig_names"):
        return await interaction.response.send_message(embed=e(
            "❌  Nothing to reset", "Use `/setup` first.", C_RED), ephemeral=True)
    wheel["names"]      = wheel["orig_names"].copy()
    wheel["categories"] = wheel["orig_cats"].copy()
    em = discord.Embed(
        title="🔄  Wheel reset",
        description=f"All **{len(wheel['names'])} pairs** restored to the pool.",
        color=C_BLUE,
    )
    em.set_footer(text="Ready to spin again!")
    await interaction.response.send_message(embed=em)

# ══════════════════════════════════════════════════════════════════════════════
#  /view
# ══════════════════════════════════════════════════════════════════════════════
@bot.tree.command(name="view", description="Show all pairs currently in the wheel")
async def slash_view(interaction: discord.Interaction):
    if not has_wheel():
        return await interaction.response.send_message(embed=e(
            "🎡  Wheel is empty", "Use `/setup` to load names and categories.", C_ORANGE))

    lines = [f"  {n:<20} →   {c}" for n, c in zip(wheel["names"], wheel["categories"])]
    order_icon  = "🔀" if wheel["cat_order"] == "random" else "📋"
    order_label = "Random" if wheel["cat_order"] == "random" else "Fixed"
    text = "\n".join(lines)

    def base_embed():
        em = discord.Embed(
            title=f"🎡  Wheel  —  {len(wheel['names'])} pair{'s' if len(wheel['names']) != 1 else ''} remaining",
            color=C_PURPLE,
        )
        em.add_field(name="Category order", value=f"{order_icon}  {order_label}", inline=True)
        em.add_field(name="Delay",          value=f"⏱️  `{wheel['delay']}` seconds", inline=True)
        return em

    if len(text) <= 3800:
        em = base_embed()
        em.description = f"```\n{text}\n```"
        await interaction.response.send_message(embed=em)
    else:
        # Send in batches of 20
        batches = [lines[i:i+20] for i in range(0, len(lines), 20)]
        em = base_embed()
        em.set_footer(text=f"Showing in {len(batches)} batches…")
        await interaction.response.send_message(embed=em)
        for i, batch in enumerate(batches):
            batch_em = discord.Embed(
                description="```\n" + "\n".join(batch) + "\n```",
                color=C_PURPLE,
            )
            batch_em.set_footer(text=f"Batch {i+1}/{len(batches)}")
            await interaction.followup.send(embed=batch_em)

# ── Error handler ──────────────────────────────────────────────────────────────
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    em = e("❌  Something went wrong", str(error), C_RED)
    try:
        await interaction.response.send_message(embed=em, ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(embed=em, ephemeral=True)

# ── Run ────────────────────────────────────────────────────────────────────────
bot.run(TOKEN)