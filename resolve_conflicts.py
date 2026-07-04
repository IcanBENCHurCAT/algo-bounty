import re

# === deploy.sh: Keep BOTH GITHUB_PRIVATE_KEY (from HEAD) and DATABASE_URL (from PR) ===
with open('deploy.sh', 'r') as f:\n    content = f.read()\n\nstart = content.find('<<<<<<< HEAD')
end_marker = '>>>>>>> 787f472 (feat: transition database to production Supabase via DATABASE_URL env var)'
end = content.find(end_marker)
before = content[:start]
after = content[end + len(end_marker):]

new_section = '  --set-secrets="GITHUB_PRIVATE_KEY=algobounty-github-private-key:latest" \\\n  --set-secrets="DATABASE_URL=algobounty-db-url:latest"\n'
content = before + new_section + after

with open('deploy.sh', 'w') as f:\n    f.write(content)\nprint("deploy.sh resolved")

# === database.py: Use PR version (imports from supabase_migration) ===
with open('gateway/database.py', 'r') as f:\n    content = f.read()\n\nstart = content.find('<<<<<<< HEAD')
end_marker = '>>>>>>> 787f472 (feat: transition database to production Supabase via DATABASE_URL env var)'
end = content.find(end_marker)
before = content[:start]
after = content[end + len(end_marker):]

pr_section = content[start + len('<<<<<<< HEAD\n'):]
seps = pr_section.find('\n=======\n')
head_end = pr_section.find('\n=======')
pr_text = pr_section[seps + len('\n=======\n'):]

content = before + pr_text + after

with open('gateway/database.py', 'w') as f:\n    f.write(content)\nprint("database.py resolved")

# === supabase_migration.py: Merge HEAD + PR engine improvements ===
with open('gateway/supabase_migration.py', 'r') as f:\n    content = f.read()\n\nidx1 = content.find('<<<<<<< HEAD')
idx2 = content.find('\n=======\n', idx1)
idx3 = content.find(end_marker, idx2)

before = content[:idx1]
head_section = content[idx1 + len('<<<<<<< HEAD\n'):idx2]
pr_section = content[idx2 + len('\n=======\n'):idx3]
after = content[idx3 + len(end_marker):]

# Merge: HEAD structure + PR engine improvements
merged = head_section + pr_section

content = before + merged + after

with open('gateway/supabase_migration.py', 'w') as f:\n    f.write(content)\nprint("supabase_migration.py resolved")

print("\nAll conflicts resolved!")
