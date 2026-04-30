import re

def patch_file():
    with open('bot_main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update Scam Detection (lines 740-745 approx)
    scam_old = """
            scam_infractions = cfg.get("SCAM_INFRACTIONS", {})
            scam_count = scam_infractions.get(user_id, 0) + 1
            scam_infractions[user_id] = scam_count
            cfg["SCAM_INFRACTIONS"] = scam_infractions
            save_config(cfg)"""
    scam_new = """
            scam_count = await db.add_scam_strike(user_id)"""
    content = content.replace(scam_old.strip(), scam_new.strip())

    # 2. Update Swear Filter (lines 768-795 approx)
    swear_old = """
        infractions = cfg.get("INFRACTIONS", {})
        if user_id not in infractions:
            infractions[user_id] = []
        
        # Cooldown/Reset Check
        if infractions[user_id]:
            last_inf = infractions[user_id][-1]
            last_time = datetime.strptime(last_inf["time"], "%Y-%m-%d %H:%M:%S")
            time_diff = datetime.now() - last_time
            count_before = len(infractions[user_id])
            
            reset_needed = False
            if count_before <= 3 and time_diff > timedelta(minutes=30): reset_needed = True
            elif count_before == 4 and time_diff > timedelta(hours=1): reset_needed = True
            elif count_before >= 5 and time_diff > timedelta(days=1): reset_needed = True
            
            if reset_needed:
                infractions[user_id] = []

        # Log new infraction
        word_found = find_swear_word(message.content, swear_list)
        infractions[user_id].append({
            "word": word_found,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "channel": message.channel.name
        })
        cfg["INFRACTIONS"] = infractions
        save_config(cfg)
        
        count = len(infractions[user_id])"""
    swear_new = """
        user_infs = await db.get_infractions(user_id)
        
        # Cooldown/Reset Check
        if user_infs:
            last_inf = user_infs[-1]
            last_time = datetime.strptime(last_inf["time"], "%Y-%m-%d %H:%M:%S")
            time_diff = datetime.now() - last_time
            count_before = len(user_infs)
            
            reset_needed = False
            if count_before <= 3 and time_diff > timedelta(minutes=30): reset_needed = True
            elif count_before == 4 and time_diff > timedelta(hours=1): reset_needed = True
            elif count_before >= 5 and time_diff > timedelta(days=1): reset_needed = True
            
            if reset_needed:
                await db.clear_infractions(user_id)
                user_infs = []

        # Log new infraction
        word_found = find_swear_word(message.content, swear_list)
        count = await db.add_infraction(user_id, word_found, message.channel.name)"""
    content = content.replace(swear_old.strip(), swear_new.strip())

    # 3. Update apply_quarantine
    apply_q_old = """
    quarantine_data = cfg.get("QUARANTINE_ROLES", {})
    quarantine_data[str(member.id)] = role_ids
    cfg["QUARANTINE_ROLES"] = quarantine_data
    save_config(cfg)"""
    apply_q_new = """
    await db.save_quarantine_roles(str(member.id), role_ids)"""
    content = content.replace(apply_q_old.strip(), apply_q_new.strip())

    # 4. Update clearscamlog
    clearscam_old = """
    cfg = load_config()
    scam_infractions = cfg.get("SCAM_INFRACTIONS", {})
    if str(member.id) in scam_infractions:
        del scam_infractions[str(member.id)]
        cfg["SCAM_INFRACTIONS"] = scam_infractions
        save_config(cfg)
        await ctx.send(f"✅ Histórico de phishing de {member.display_name} foi limpo.")
    else:
        await ctx.send("ℹ️ Este usuário não possui histórico de phishing.")"""
    clearscam_new = """
    strikes = await db.get_scam_strikes(str(member.id))
    if strikes > 0:
        await db.clear_scam_strikes(str(member.id))
        await ctx.send(f"✅ Histórico de phishing de {member.display_name} foi limpo.")
    else:
        await ctx.send("ℹ️ Este usuário não possui histórico de phishing.")"""
    content = content.replace(clearscam_old.strip(), clearscam_new.strip())

    # 5. Update unquarantine
    unq_old = """
        # Restore saved roles
        quarantine_data = cfg.get("QUARANTINE_ROLES", {})
        saved_role_ids = quarantine_data.get(str(member.id), [])"""
    unq_new = """
        # Restore saved roles
        saved_role_ids = await db.get_quarantine_roles(str(member.id))"""
    content = content.replace(unq_old.strip(), unq_new.strip())
    
    unq2_old = """
        # Clean up config
        if str(member.id) in quarantine_data:
            del quarantine_data[str(member.id)]
            cfg["QUARANTINE_ROLES"] = quarantine_data
            save_config(cfg)"""
    unq2_new = """
        # Clean up db
        await db.clear_quarantine_roles(str(member.id))"""
    content = content.replace(unq2_old.strip(), unq2_new.strip())

    # 6. Update swearlog
    swearlog_old = """
    cfg = load_config()
    infractions = cfg.get("INFRACTIONS", {})
    
    if member:
        # Show log for specific user
        user_id = str(member.id)
        user_data = infractions.get(user_id, [])"""
    swearlog_new = """
    if member:
        # Show log for specific user
        user_id = str(member.id)
        user_data = await db.get_infractions(user_id)"""
    content = content.replace(swearlog_old.strip(), swearlog_new.strip())

    swearlog_all_old = """
        # Show general stats
        if not infractions:
            await ctx.send("ℹ️ Nenhum palavrão registrado ainda.")
            return
            
        embed = discord.Embed(title="📊 Top Infratores", color=0xE74C3C)
        sorted_inf = sorted(infractions.items(), key=lambda x: len(x[1]), reverse=True)"""
    swearlog_all_new = """
        # Show general stats
        infractions = await db.get_all_infractions()
        if not infractions:
            await ctx.send("ℹ️ Nenhum palavrão registrado ainda.")
            return
            
        embed = discord.Embed(title="📊 Top Infratores", color=0xE74C3C)
        sorted_inf = sorted(infractions.items(), key=lambda x: len(x[1]), reverse=True)"""
    content = content.replace(swearlog_all_old.strip(), swearlog_all_new.strip())

    with open('bot_main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched part 2!")

if __name__ == "__main__":
    patch_file()
