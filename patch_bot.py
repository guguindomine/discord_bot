import re

def patch_file():
    with open('bot_main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update vouch_ticket
    vouch_old = """
        cfg = load_config()
        vouches_data = cfg.get("VOUCHES", {})
        p_id = str(self.claimer_id)
        
        count = vouches_data.get(p_id, 0) + 1
        vouches_data[p_id] = count
        cfg["VOUCHES"] = vouches_data
        save_config(cfg)
        
        level = (count // 5) + 1"""
    vouch_new = """
        cfg = load_config()
        p_id = str(self.claimer_id)
        
        # Database Update
        count = await db.get_vouches(p_id) + 1
        await db.set_vouches(p_id, count)
        
        level = (count // 5) + 1"""
    content = content.replace(vouch_old.strip(), vouch_new.strip())

    # 2. Update !vouches
    cmd_vouches_old = """
    member = member or ctx.author
    cfg = load_config()
    vouches = cfg.get("VOUCHES", {}).get(str(member.id), 0)
    level = (vouches // 5) + 1"""
    cmd_vouches_new = """
    member = member or ctx.author
    vouches = await db.get_vouches(str(member.id))
    level = (vouches // 5) + 1"""
    content = content.replace(cmd_vouches_old.strip(), cmd_vouches_new.strip())

    # 3. Update !setrank
    cmd_setrank_old = """
    vouches = (level - 1) * 5
    cfg = load_config()
    v_data = cfg.get("VOUCHES", {})
    v_data[str(member.id)] = vouches
    cfg["VOUCHES"] = v_data
    save_config(cfg)"""
    cmd_setrank_new = """
    vouches = (level - 1) * 5
    await db.set_vouches(str(member.id), vouches)"""
    content = content.replace(cmd_setrank_old.strip(), cmd_setrank_new.strip())

    # 4. Update !setvouches
    cmd_setvouches_old = """
    cfg = load_config()
    v_data = cfg.get("VOUCHES", {})
    v_data[str(member.id)] = vouches
    cfg["VOUCHES"] = v_data
    save_config(cfg)"""
    cmd_setvouches_new = """
    await db.set_vouches(str(member.id), vouches)"""
    content = content.replace(cmd_setvouches_old.strip(), cmd_setvouches_new.strip())

    # 5. Add !migrate command
    migrate_cmd = """
@bot.command(name="migrate")
@commands.has_permissions(administrator=True)
async def migrate_cmd(ctx: commands.Context, arg: str = None):
    \"\"\"Migrate data from config.json to MongoDB. Usage: !migrate db\"\"\"
    if arg != "db":
        await ctx.send("❓ Usage: `!migrate db`")
        return
        
    cfg = load_config()
    await ctx.send("🔄 Starting database migration...")
    
    # Migrate Vouches
    vouches = cfg.get("VOUCHES", {})
    for uid, count in vouches.items():
        await db.set_vouches(uid, count)
        
    # Migrate Scam Strikes
    scams = cfg.get("SCAM_INFRACTIONS", {})
    for uid, count in scams.items():
        for _ in range(count):
            await db.add_scam_strike(uid)
            
    # Migrate Infractions
    infractions = cfg.get("INFRACTIONS", {})
    for uid, inf_list in infractions.items():
        await db.set_infractions(uid, inf_list)
        
    # Migrate Quarantine
    quarantine = cfg.get("QUARANTINE_ROLES", {})
    for uid, roles in quarantine.items():
        await db.save_quarantine_roles(uid, roles)
        
    await ctx.send("✅ Migration complete! All user data has been transferred to MongoDB.")

# ══════════════════════════════════════════════
#  ERROR HANDLING"""
    content = content.replace("# ══════════════════════════════════════════════\n#  ERROR HANDLING", migrate_cmd)

    with open('bot_main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched!")

if __name__ == "__main__":
    patch_file()
