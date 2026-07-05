"""
Varsh's Personal AI — Bcrypt Hashing Tool
=========================================
Use this tool to generate secure bcrypt password hashes to put in your `.env` file.

Usage:
    python hash_tool.py
"""

import getpass
import bcrypt

def main():
    print("=== Varsh's Personal AI — Bcrypt Hashing Tool ===")
    print("Use this to generate secure password hashes for your .env file.\n")
    
    password = getpass.getpass("Enter the password to hash: ")
    if not password:
        print("Password cannot be empty.")
        return
        
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        return
        
    # Generate bcrypt hash
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    
    print("\nSuccess! Copy the line below and paste it into your `.env` file:")
    print("=" * 60)
    print(f"AUTH_PASSWORD_HASH={hashed.decode('utf-8')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
